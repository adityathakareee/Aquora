"""
AQUORA Phase 6C.1a — Authentic Historical IMERG Rainfall Verification Tests.

Validates authentic acquisition, time-window resolution, HDF5 integrity,
exact direct raw recalculation, coordinate indexing, SHA-256 checksums,
and consistency between summary metrics, timeseries JSON, and manifest.
"""

import hashlib
import json
from pathlib import Path
import h5py
import numpy as np
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_IMERG_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "rainfall" / "imerg" / "final" / "2019" / "07"
TIMESERIES_JSON_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "E03_imerg_timeseries_24h.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c1a_imerg_manifest.yaml"

EXPECTED_UTC_START = "2019-07-01T03:00:00Z"
EXPECTED_UTC_END = "2019-07-02T03:00:00Z"
EXPECTED_GRANULE_COUNT = 48
SAR_OVERPASS_UTC = "2019-07-02T01:02:58Z"

MUMBAI_EXPECTED_LON_IDX = 2528
MUMBAI_EXPECTED_LAT_IDX = 1090
EXPECTED_24H_ACCUMULATION_MM = 221.775  # Exactly 221.78 mm rounded
EXPECTED_OVERPASS_ACCUMULATION_MM = 208.88


def test_time_window_and_granule_catalog():
    """Verify exact 24-hour IMD gauge window resolution and 48-granule catalog."""
    from scripts.acquire_phase6c1a_imerg import build_granule_catalog

    catalog = build_granule_catalog()
    assert len(catalog) == EXPECTED_GRANULE_COUNT, f"Expected 48 granules, got {len(catalog)}"

    # First granule
    assert catalog[0]["start_utc"] == EXPECTED_UTC_START
    assert catalog[0]["filename"] == "3B-HHR.MS.MRG.3IMERG.20190701-S030000-E032959.0180.V07B.HDF5"

    # Last granule
    assert catalog[-1]["end_utc"] == "2019-07-02T02:59:59Z"
    assert catalog[-1]["filename"] == "3B-HHR.MS.MRG.3IMERG.20190702-S023000-E025959.0150.V07B.HDF5"


def test_sentinel1_sar_temporal_coincidence():
    """Verify Sentinel-1 SAR overpass at 01:02:58 UTC falls squarely inside granule 45 (step 44)."""
    from scripts.acquire_phase6c1a_imerg import build_granule_catalog

    catalog = build_granule_catalog()
    sar_steps = [c for c in catalog if c["is_sar_overpass_step"]]
    assert len(sar_steps) == 1, "Expected exactly 1 step coincident with SAR overpass"

    sar_item = sar_steps[0]
    assert sar_item["step_index"] == 44
    assert sar_item["filename"] == "3B-HHR.MS.MRG.3IMERG.20190702-S010000-E012959.0060.V07B.HDF5"
    assert sar_item["start_utc"] == "2019-07-02T01:00:00Z"
    assert sar_item["end_utc"] == "2019-07-02T01:29:59Z"

    # Confirm overpass timestamp 01:02:58 UTC is strictly inside the interval
    assert sar_item["start_utc"] <= SAR_OVERPASS_UTC <= sar_item["end_utc"]


def test_acquired_files_exist_and_have_valid_hdf5_magic():
    """Verify all 48 authentic HDF5 files exist on disk with valid magic bytes."""
    assert RAW_IMERG_DIR.exists(), f"Raw IMERG directory missing at {RAW_IMERG_DIR}"
    files = sorted(list(RAW_IMERG_DIR.glob("3B-HHR.MS.MRG.3IMERG.2019*.HDF5")))
    assert len(files) == EXPECTED_GRANULE_COUNT, f"Expected 48 downloaded HDF5 files, found {len(files)}"

    for fpath in files:
        assert fpath.stat().st_size > 1_000_000, f"File {fpath.name} is too small ({fpath.stat().st_size} bytes)"
        with open(fpath, "rb") as f:
            magic = f.read(8)
        assert magic.startswith(b"\x89HDF\r\n\x1a\n"), f"File {fpath.name} missing HDF5 magic bytes"


def test_granules_hdf5_structure_and_version():
    """Sample granules across the window and verify internal HDF5 structure, units, and version."""
    files = sorted(list(RAW_IMERG_DIR.glob("3B-HHR.MS.MRG.3IMERG.2019*.HDF5")))
    sample_indices = [0, 15, 30, 44, 47]  # Start, afternoon, cloudburst onset, SAR overpass, end

    for idx in sample_indices:
        fpath = files[idx]
        with h5py.File(fpath, "r") as h5:
            header = h5.attrs.get("FileHeader")
            header_str = header.decode("utf-8") if isinstance(header, bytes) else str(header)
            assert "ProductVersion=V07B" in header_str
            assert "TimeInterval=HALF_HOUR" in header_str

            assert "Grid/precipitation" in h5
            precip = h5["Grid/precipitation"]
            assert precip.shape == (1, 3600, 1800)
            units = precip.attrs.get("Units") or precip.attrs.get("units")
            units_str = units.decode("utf-8") if isinstance(units, bytes) else str(units)
            assert units_str == "mm/hr"
            fill = float(precip.attrs.get("_FillValue", 0.0))
            assert np.isclose(fill, -9999.9, atol=1e-1)


def test_coordinate_indexing_and_bounding_box():
    """Verify coordinate array indexing conventions and that cell bounds enclose Mithi catchment."""
    files = sorted(list(RAW_IMERG_DIR.glob("3B-HHR.MS.MRG.3IMERG.2019*.HDF5")))
    with h5py.File(files[0], "r") as h5:
        lons = h5["Grid/lon"][:]
        lats = h5["Grid/lat"][:]

        assert lons.shape == (3600,)
        assert lats.shape == (1800,)

        # Check calculated indices
        lon_idx = int(np.argmin(np.abs(lons - 72.85)))
        lat_idx = int(np.argmin(np.abs(lats - 19.05)))
        assert lon_idx == MUMBAI_EXPECTED_LON_IDX
        assert lat_idx == MUMBAI_EXPECTED_LAT_IDX

        # Cell center
        cell_lon = float(lons[lon_idx])
        cell_lat = float(lats[lat_idx])
        assert np.isclose(cell_lon, 72.850, atol=1e-3)
        assert np.isclose(cell_lat, 19.050, atol=1e-3)

        # Cell bounds: [72.80, 72.90] E, [19.00, 19.10] N
        min_lon, max_lon = cell_lon - 0.05, cell_lon + 0.05
        min_lat, max_lat = cell_lat - 0.05, cell_lat + 0.05

        # Mithi catchment centroid is at 19.076 N, 72.877 E
        mithi_lat, mithi_lon = 19.076, 72.877
        assert min_lon <= mithi_lon <= max_lon, f"Mithi lon {mithi_lon} outside cell [{min_lon}, {max_lon}]"
        assert min_lat <= mithi_lat <= max_lat, f"Mithi lat {mithi_lat} outside cell [{min_lat}, {max_lat}]"


def test_direct_raw_recalculation_matches_json_and_manifest():
    """
    Recalculate accumulation directly from all 48 raw HDF5 files on disk.
    Verify that sum of 30-min integrations equals 221.78 mm and matches JSON and manifest.
    """
    files = sorted(list(RAW_IMERG_DIR.glob("3B-HHR.MS.MRG.3IMERG.2019*.HDF5")))
    assert len(files) == 48

    raw_accumulations = []
    raw_rates = []
    for fpath in files:
        with h5py.File(fpath, "r") as h5:
            p_ds = h5["Grid/precipitation"]
            rate = float(p_ds[0, MUMBAI_EXPECTED_LON_IDX, MUMBAI_EXPECTED_LAT_IDX])
            fill = float(p_ds.attrs.get("_FillValue", -9999.9))
            if rate < 0.0 or np.isclose(rate, fill, atol=1.0):
                rate = 0.0
            raw_rates.append(rate)
            raw_accumulations.append(rate * 0.5)

    raw_total_mm = sum(raw_accumulations)
    assert np.isclose(raw_total_mm, EXPECTED_24H_ACCUMULATION_MM, atol=1e-2), (
        f"Raw accumulation mismatch: expected {EXPECTED_24H_ACCUMULATION_MM}, got {raw_total_mm}"
    )

    # Accumulation up to SAR overpass (step 44 inclusive = first 45 steps)
    overpass_accum_mm = sum(raw_accumulations[:45])
    assert np.isclose(overpass_accum_mm, EXPECTED_OVERPASS_ACCUMULATION_MM, atol=1e-2), (
        f"Overpass accumulation mismatch: expected {EXPECTED_OVERPASS_ACCUMULATION_MM}, got {overpass_accum_mm}"
    )

    # Check timeseries JSON
    with open(TIMESERIES_JSON_PATH, "r", encoding="utf-8") as f:
        ts = json.load(f)
    json_granules = ts["granules"]
    assert len(json_granules) == 48
    json_total = sum(g["mumbai_accumulation_30min_mm"] for g in json_granules)
    assert np.isclose(json_total, raw_total_mm, atol=1e-4)
    assert np.isclose(ts["summary_metrics"]["imerg_24h_total_accumulation_mm"], round(raw_total_mm, 2), atol=1e-2)

    # Check manifest
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    mf_granules = manifest["granule_manifest"]
    assert len(mf_granules) == 48
    mf_total = sum(g["accumulation_30min_mm"] for g in mf_granules)
    assert np.isclose(mf_total, raw_total_mm, atol=1e-4)
    assert np.isclose(
        manifest["precipitation_comparison"]["imerg_satellite_24h_accumulation_mm"],
        round(raw_total_mm, 2),
        atol=1e-2
    )


def test_all_48_sha256_checksums_match_raw_files():
    """Verify cryptographic SHA-256 for all 48 downloaded files against manifest and JSON."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    with open(TIMESERIES_JSON_PATH, "r", encoding="utf-8") as f:
        ts = json.load(f)

    mf_sha_map = {g["filename"]: g["sha256"] for g in manifest["granule_manifest"]}
    ts_sha_map = {g["filename"]: g["sha256"] for g in ts["granules"]}

    files = sorted(list(RAW_IMERG_DIR.glob("3B-HHR.MS.MRG.3IMERG.2019*.HDF5")))
    assert len(files) == 48

    for fpath in files:
        hasher = hashlib.sha256()
        with open(fpath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        actual_sha = hasher.hexdigest()

        assert actual_sha == mf_sha_map[fpath.name], f"SHA mismatch in manifest for {fpath.name}"
        assert actual_sha == ts_sha_map[fpath.name], f"SHA mismatch in JSON for {fpath.name}"


def test_manifest_governance_and_scale_distinction():
    """Verify non-conflation guard and point-vs-grid scale distinction in manifest."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    # Governance check
    assert manifest["governance"]["zero_fabrication_enforced"] is True
    assert manifest["governance"]["zero_synthetic_interpolation_enforced"] is True
    guard = manifest["governance"]["rainfall_inundation_conflation_guard"]
    assert "does NOT constitute proof of surface inundation" in guard

    # Scale distinction
    scale_note = manifest["precipitation_comparison"]["scale_distinction"]
    assert "0.1 deg" in scale_note
    assert "point gauge" in scale_note
    assert manifest["precipitation_comparison"]["imd_santacruz_gauge_24h_total_mm"] == 375.2
