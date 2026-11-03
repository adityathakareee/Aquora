"""
AQUORA Phase 6A — NASA GPM IMERG V07B Scientific Content Validation Tests.

Validates authentic HDF5 file integrity, coordinate conventions, units, fill values,
rate vs. accumulation distinctions, and derived 30m GeoTIFF alignment for Event E02.
"""

import hashlib
from pathlib import Path
import h5py
import numpy as np
import pytest
import rasterio

from app.providers.rainfall import IMERGRainfallProvider

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_HDF5_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "phase7"
    / "rainfall"
    / "imerg"
    / "final"
    / "2017"
    / "08"
    / "3B-HHR.MS.MRG.3IMERG.20170829-S233000-E235959.1410.V07B.HDF5"
)
PROCESSED_TIF_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "E02_rainfall_30m.tif"
DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m.tif"

EXPECTED_SHA256 = "fafd7e6cb238d925e744a89f3457c508b0ff7bb2f5290337ca7e6364e0ab6625"


# ==============================================================================
# 1. RAW FILE INTEGRITY & CHECKSUM
# ==============================================================================


def test_imerg_raw_file_existence_and_checksum():
    """Verify raw IMERG HDF5 file exists and cryptographic SHA-256 matches manifest."""
    assert RAW_HDF5_PATH.exists(), f"Raw IMERG file missing at {RAW_HDF5_PATH}"
    size = RAW_HDF5_PATH.stat().st_size
    assert size == 8170876, f"File size mismatch: expected 8,170,876 bytes, got {size}"

    hasher = hashlib.sha256()
    with open(RAW_HDF5_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    actual_sha = hasher.hexdigest()
    assert actual_sha == EXPECTED_SHA256, f"SHA-256 mismatch: {actual_sha} != {EXPECTED_SHA256}"


def test_imerg_hdf5_magic_bytes():
    """Verify file begins with official HDF5 magic bytes, preventing HTML auth error pages."""
    with open(RAW_HDF5_PATH, "rb") as f:
        header = f.read(8)
    assert header.startswith(b"\x89HDF"), f"Invalid HDF5 header: {header!r}"


# ==============================================================================
# 2. HDF5 METADATA & COORDINATE CONVENTIONS
# ==============================================================================


def test_imerg_coordinate_arrays():
    """Verify longitude and latitude coordinate arrays, ranges, and resolution."""
    with h5py.File(RAW_HDF5_PATH, "r") as h5:
        lons = h5["Grid/lon"][:]
        lats = h5["Grid/lat"][:]

        assert lons.shape == (3600,)
        assert lats.shape == (1800,)

        # Global grid extents
        assert np.isclose(lons[0], -179.95, atol=1e-2)
        assert np.isclose(lons[-1], 179.95, atol=1e-2)
        assert np.isclose(lats[0], -89.95, atol=1e-2)
        assert np.isclose(lats[-1], 89.95, atol=1e-2)

        # 0.1 degree resolution
        lon_step = np.mean(np.diff(lons))
        lat_step = np.mean(np.diff(lats))
        assert np.isclose(lon_step, 0.1, atol=1e-4)
        assert np.isclose(lat_step, 0.1, atol=1e-4)


def test_imerg_time_metadata():
    """Verify granule header timestamps confirm exact half-hour window."""
    with h5py.File(RAW_HDF5_PATH, "r") as h5:
        header = h5.attrs.get("FileHeader")
        assert header is not None
        header_str = header.decode("utf-8") if isinstance(header, bytes) else str(header)

        assert "StartGranuleDateTime=2017-08-29T23:30:00.000Z" in header_str
        assert "StopGranuleDateTime=2017-08-29T23:59:59.999Z" in header_str
        assert "TimeInterval=HALF_HOUR" in header_str
        assert "ProductVersion=V07B" in header_str


# ==============================================================================
# 3. PRECIPITATION VARIABLE & SCIENTIFIC ATTRIBUTES
# ==============================================================================


def test_imerg_precipitation_attributes():
    """Verify precipitation variable name, units, dimensions, and fill value."""
    with h5py.File(RAW_HDF5_PATH, "r") as h5:
        assert "Grid/precipitation" in h5, "Dataset Grid/precipitation missing"
        precip = h5["Grid/precipitation"]

        # Dimensions: time, lon, lat
        assert precip.shape == (1, 3600, 1800)
        assert precip.dtype == np.float32

        # Units attribute
        units = precip.attrs.get("Units") or precip.attrs.get("units")
        units_str = units.decode("utf-8") if isinstance(units, bytes) else str(units)
        assert units_str == "mm/hr"

        # Missing / fill value attribute
        fill_val = float(precip.attrs.get("_FillValue", 0.0))
        assert np.isclose(fill_val, -9999.9, atol=1e-1)


def test_imerg_quality_index_dataset():
    """Verify precipitationQualityIndex exists and matches spatial dimensions."""
    with h5py.File(RAW_HDF5_PATH, "r") as h5:
        assert "Grid/precipitationQualityIndex" in h5
        qi = h5["Grid/precipitationQualityIndex"]
        assert qi.shape == (1, 3600, 1800)


# ==============================================================================
# 4. MUMBAI SUBGRID EXTRACTION & ACCUMULATION DISTINCTION
# ==============================================================================


def test_mumbai_cell_extraction_and_accumulation():
    """
    Extract precipitation for Mumbai cell (19.05N, 72.85E) and verify distinction
    between half-hourly rate (mm/hr) and half-hourly accumulation (mm).
    """
    with h5py.File(RAW_HDF5_PATH, "r") as h5:
        lons = h5["Grid/lon"][:]
        lats = h5["Grid/lat"][:]
        precip = h5["Grid/precipitation"][0]

        lon_idx = int(np.argmin(np.abs(lons - 72.85)))
        lat_idx = int(np.argmin(np.abs(lats - 19.05)))

        rate_mm_hr = float(precip[lon_idx, lat_idx])
        assert 0.35 <= rate_mm_hr <= 0.55, f"Unexpected rate for Mumbai cell: {rate_mm_hr}"

        # Invariant: single half-hour granule (30 min) yields half-hourly accumulation
        # Accumulation = Rate * 0.5 hours
        accumulation_30min_mm = rate_mm_hr * 0.5
        assert 0.15 <= accumulation_30min_mm <= 0.30

        # Invariant: single half-hour granule is NOT labeled as daily total (315 mm)
        assert accumulation_30min_mm < 10.0


# ==============================================================================
# 5. DERIVED PROCESSED GEOTIFF RASTERS VALIDATION
# ==============================================================================

NATIVE_TIF_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "E02_rainfall_native_0.1deg.tif"
METADATA_JSON_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "E02_rainfall_metadata.json"


def test_native_resolution_raster_properties():
    """
    Verify E02_rainfall_native_0.1deg.tif exists as the primary scientific output,
    with genuine 0.1 degree resolution in EPSG:4326, no artificial spatial downscaling.
    """
    assert NATIVE_TIF_PATH.exists(), f"Native GeoTIFF missing at {NATIVE_TIF_PATH}"

    with rasterio.open(NATIVE_TIF_PATH) as src:
        assert src.crs.to_epsg() == 4326
        assert src.width == 10
        assert src.height == 10
        assert np.isclose(src.res[0], 0.1, atol=1e-4)
        assert np.isclose(src.res[1], 0.1, atol=1e-4)

        data = src.read(1)
        assert data.dtype == np.float32

        tags = src.tags()
        assert tags.get("is_native_resolution") == "true"
        assert tags.get("is_resampled") == "false"
        assert "0.1 degree" in tags.get("native_spatial_resolution", "")
        assert tags.get("temporal_window_utc") == "2017-08-29T23:30:00Z to 2017-08-29T23:59:59Z"
        assert tags.get("temporal_window_ist") == "2017-08-30T05:00:00+05:30 to 2017-08-30T05:30:00+05:30"
        assert tags.get("event_phase") == "POST_EVENT_TRAILING_DISSIPATION"

        # Mumbai center cell (row 4, col 3) corresponds to lon 72.85, lat 19.05
        assert np.isclose(data[4, 3], 0.43, atol=1e-2)


def test_derived_e02_rainfall_geotiff_resampled_convenience():
    """
    Verify derived E02_rainfall_30m.tif is explicitly tagged as a resampled convenience layer
    (NOT genuine 30m resolution), matches DEM mesh, and contains no unexpected zeros/NaNs.
    """
    assert PROCESSED_TIF_PATH.exists(), f"Processed GeoTIFF missing at {PROCESSED_TIF_PATH}"

    with rasterio.open(DEM_PATH) as dem_src, rasterio.open(PROCESSED_TIF_PATH) as rain_src:
        # Spatial alignment with DEM
        assert rain_src.crs == dem_src.crs
        assert rain_src.width == dem_src.width == 392
        assert rain_src.height == dem_src.height == 476
        assert np.allclose(rain_src.bounds, dem_src.bounds, atol=1e-1)

        rain_arr = rain_src.read(1)
        assert rain_arr.dtype == np.float32
        assert not np.isnan(rain_arr).any(), "Found unexpected NaNs in resampled raster"
        assert (rain_arr == 0.0).sum() == 0, "Found unexpected zero rainfall in resampled raster"
        assert (rain_arr == rain_src.nodata).sum() == 0, "Unexpected NoData in valid urban study area"

        assert 0.35 <= rain_arr.min() <= 0.45
        assert 0.45 <= rain_arr.max() <= 0.55
        assert 0.40 <= rain_arr.mean() <= 0.50

        # Scientific honesty tags
        tags = rain_src.tags()
        assert tags.get("is_resampled_convenience_layer") == "true"
        assert tags.get("is_genuine_30m_resolution") == "false"
        assert tags.get("resampling_method") == "bilinear"
        assert "0.1 degree" in tags.get("native_spatial_resolution", "")
        assert tags.get("temporal_window_utc") == "2017-08-29T23:30:00Z to 2017-08-29T23:59:59Z"
        assert tags.get("temporal_window_ist") == "2017-08-30T05:00:00+05:30 to 2017-08-30T05:30:00+05:30"
        assert tags.get("nodata_value") == "-9999.0"


def test_nodata_preservation_reprojection_behavior():
    """
    Verify that when source contains missing values (-9999.9), converting to NaN
    before reprojection ensures destination NoData (-9999.0) is preserved and missing pixels never silently become zero.
    """
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, Resampling

    src_arr = np.array([
        [-9999.9, -9999.9],
        [-9999.9, 0.43]
    ], dtype=np.float32)
    # Applying the audited pipeline: convert fill value to NaN before GDAL reprojection
    src_arr[src_arr <= -9000.0] = np.nan

    src_trans = from_origin(72.0, 20.0, 0.5, 0.5)

    dst_arr = np.full((4, 4), np.nan, dtype=np.float32)
    dst_trans = from_origin(72.0, 20.0, 0.25, 0.25)

    reproject(
        source=src_arr,
        destination=dst_arr,
        src_transform=src_trans,
        src_crs="EPSG:4326",
        src_nodata=np.nan,
        dst_transform=dst_trans,
        dst_crs="EPSG:4326",
        dst_nodata=np.nan,
        resampling=Resampling.bilinear
    )

    dst_clean = np.nan_to_num(dst_arr, nan=-9999.0)

    # Missing pixels in the top half must remain destination NoData (-9999.0), NEVER 0.0
    assert (dst_clean[:2, :] == -9999.0).all()
    assert (dst_clean == 0.0).sum() == 0, "Missing source pixels were silently converted to 0.0!"
    assert np.isclose(dst_clean[3, 3], 0.43, atol=1e-2)


def test_companion_metadata_json():
    """Verify companion JSON metadata accurately reflects audit and limitations."""
    import json
    assert METADATA_JSON_PATH.exists(), f"Metadata JSON missing at {METADATA_JSON_PATH}"

    with open(METADATA_JSON_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["event_id"] == "E02"
    assert meta["temporal_coverage"]["window_utc"]["start"] == "2017-08-29T23:30:00Z"
    assert meta["temporal_coverage"]["window_ist"]["start"] == "2017-08-30T05:00:00+05:30"
    assert meta["temporal_coverage"]["duration_minutes"] == 30

    assert meta["primary_scientific_output"]["is_native_resolution"] is True
    assert meta["convenience_resampled_layer"]["is_genuine_30m_resolution"] is False

    assert meta["values_summary"]["mumbai_cell_rate_mm_hr"] == 0.43
    assert meta["values_summary"]["mumbai_cell_half_hour_accumulation_mm"] == 0.215


def test_imerg_provider_loads_e02_raster():
    """Verify IMERGRainfallProvider loads E02 raster with complete honest metadata."""
    provider = IMERGRainfallProvider()
    arr, meta = provider.load_event_rainfall_raster(event_id="E02")

    assert meta["event_id"] == "E02"
    assert meta["crs"] == "EPSG:32643"
    assert arr.shape == (476, 392)
    assert meta["units"] == "mm/hr"
    assert 0.40 <= meta["mean_intensity_mm_hr"] <= 0.50
    assert meta["is_synthetic"] is False
    assert meta["is_resampled_convenience_layer"] is True
    assert meta["is_genuine_30m_resolution"] is False
    assert "0.1 degree" in meta["native_spatial_resolution"]
    assert "2017-08-30T05:00:00+05:30" in meta["temporal_window_ist"]


def test_imerg_provider_loads_native_raster():
    """Verify IMERGRainfallProvider loads native 0.1 degree raster without resampling."""
    provider = IMERGRainfallProvider()
    arr, meta = provider.load_native_event_rainfall(event_id="E02")

    assert meta["event_id"] == "E02"
    assert meta["crs"] == "EPSG:4326"
    assert arr.shape == (10, 10)
    assert meta["is_native_resolution"] is True
    assert meta["is_resampled"] is False
    assert "0.1 degree" in meta["spatial_resolution"]
    assert "2017-08-30T05:00:00+05:30" in meta["temporal_window_ist"]
    assert np.isclose(arr[4, 3], 0.43, atol=1e-2)

