"""
AQUORA Phase 6C.2D Automated Test Suite: Reproducible Terrain Preparation & Spatial Validation.

Validates:
1. Preservation and immutability of raw Copernicus DEM source and legacy clipped DEM.
2. Exact spatial parameters of derived 30m UTM43N study extent raster (CRS, dimensions, bounds, transform).
3. 100% valid-data coverage and absence of artificial 0.1m flat fill clamping.
4. Comprehensive Mithi catchment landmark coverage (receiving water to northern headwater divide).
5. Source-to-output elevation fidelity within bilinear resampling tolerance (< 2.0m).
6. Manifest schema, SHA-256 recording, and hydrological evidence status tracking.
7. Error handling for missing or checksum-mismatched source inputs.
"""

from pathlib import Path
import tempfile
import numpy as np
import pytest
import rasterio
import yaml

from scripts.prepare_phase6c2d_terrain import (
    GRID_BOTTOM,
    GRID_HEIGHT,
    GRID_LEFT,
    GRID_RES_M,
    GRID_RIGHT,
    GRID_TOP,
    GRID_WIDTH,
    NODATA_VAL,
    OUTPUT_DEM_PATH,
    PROJECT_ROOT,
    RAW_DEM_PATH,
    TARGET_CRS,
    VALIDATION_LANDMARKS,
    compute_sha256,
    prepare_terrain,
    validate_prepared_terrain,
)

EXPECTED_RAW_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_DERIVED_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"


@pytest.fixture
def derived_dem() -> Path:
    assert OUTPUT_DEM_PATH.exists(), f"Derived DEM missing: {OUTPUT_DEM_PATH}"
    return OUTPUT_DEM_PATH


def test_raw_source_preservation_and_integrity():
    """Verify raw Copernicus DEM is unchanged and matches authentic SHA-256."""
    assert RAW_DEM_PATH.is_file(), f"Raw source DEM missing: {RAW_DEM_PATH}"
    actual_hash = compute_sha256(RAW_DEM_PATH)
    assert actual_hash == EXPECTED_RAW_SHA256, f"Raw DEM altered! {actual_hash} != {EXPECTED_RAW_SHA256}"


def test_legacy_clipped_dem_preserved():
    """Verify legacy clipped DEM (elevation_30m.tif) is preserved and untouched."""
    legacy_path = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m.tif"
    assert legacy_path.exists(), "Legacy DEM must be preserved"
    with rasterio.open(legacy_path) as ds:
        assert ds.width == 392
        assert ds.height == 476


def test_derived_dem_metadata(derived_dem: Path):
    """Verify GeoTIFF driver, CRS, resolution, bounds, and transform of derived DEM."""
    actual_hash = compute_sha256(derived_dem)
    assert actual_hash == EXPECTED_DERIVED_SHA256, f"Derived DEM checksum mismatch: {actual_hash}"

    with rasterio.open(derived_dem) as ds:
        assert ds.driver == "GTiff"
        assert ds.crs.to_epsg() == 32643
        assert ds.width == GRID_WIDTH
        assert ds.height == GRID_HEIGHT
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.nodata == NODATA_VAL

        # Resolution
        assert abs(ds.res[0] - GRID_RES_M) < 1e-4
        assert abs(ds.res[1] - GRID_RES_M) < 1e-4

        # Bounds
        assert abs(ds.bounds.left - GRID_LEFT) < 1e-3
        assert abs(ds.bounds.right - GRID_RIGHT) < 1e-3
        assert abs(ds.bounds.bottom - GRID_BOTTOM) < 1e-3
        assert abs(ds.bounds.top - GRID_TOP) < 1e-3

        # Transform
        assert ds.transform.a == GRID_RES_M
        assert ds.transform.e == -GRID_RES_M
        assert ds.transform.c == GRID_LEFT
        assert ds.transform.f == GRID_TOP


def test_valid_data_coverage_and_no_artificial_flattening(derived_dem: Path):
    """Verify 100% valid data coverage and absence of artificial 0.1m flat fill clamping."""
    with rasterio.open(derived_dem) as ds:
        elev = ds.read(1)
        valid_mask = elev != ds.nodata
        assert np.all(valid_mask), "Derived DEM must have 100% valid data coverage across working domain"

        min_val = float(np.min(elev))
        max_val = float(np.max(elev))

        # Physical bounds: Mahim Bay near sea level, SGNP peak < 500m
        assert -10.0 <= min_val <= 0.0, f"Minimum elevation unexpected: {min_val}"
        assert 450.0 <= max_val <= 520.0, f"Maximum elevation unexpected: {max_val}"

        # Absence of artificial 0.1m flat fill
        flat_01_count = np.sum(elev == 0.1)
        flat_01_pct = (flat_01_count / elev.size) * 100.0
        assert flat_01_pct < 0.1, f"Artificial 0.1m flat fill detected: {flat_01_pct:.2f}%"


def test_landmark_spatial_coverage_and_indices(derived_dem: Path):
    """Verify all Mithi landmarks (including outfall buffer) are inside raster bounds."""
    with rasterio.open(derived_dem) as ds:
        valid, val_report = validate_prepared_terrain(RAW_DEM_PATH, derived_dem)
        assert valid is True, f"Validation failed: {val_report['errors']}"

        for name, info in val_report["landmark_comparison"].items():
            row = info["grid_row"]
            col = info["grid_col"]
            assert 0 <= row < ds.height, f"{name} row {row} out of bounds"
            assert 0 <= col < ds.width, f"{name} col {col} out of bounds"

        # Outfall must NOT be on edge (unlike legacy Col 0)
        outfall_info = val_report["landmark_comparison"]["Mahim_Causeway_Outfall"]
        assert outfall_info["grid_col"] >= 50, "Outfall must have western downstream buffer"
        assert outfall_info["grid_row"] <= ds.height - 50, "Outfall must have southern buffer"


def test_source_to_derived_elevation_fidelity(derived_dem: Path):
    """Verify source-to-derived elevation difference is within bilinear tolerance (< 2.0m)."""
    valid, val_report = validate_prepared_terrain(RAW_DEM_PATH, derived_dem)
    assert valid is True

    for name, info in val_report["landmark_comparison"].items():
        diff = info["difference_m"]
        assert diff < 2.0, f"Elevation fidelity failure at {name}: diff={diff:.2f}m >= 2.0m"


def test_manifest_integrity():
    """Verify Phase 6C.2D manifest exists, matches derived SHA-256, and records governance."""
    manifest_path = PROJECT_ROOT / "data" / "manifests" / "phase6c2d_terrain_manifest.yaml"
    assert manifest_path.exists(), f"Manifest missing: {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    assert m["phase"] == "PHASE_6C_2D_TERRAIN_PREPARATION"
    assert m["governance"]["status"] == "VALIDATED_WORKING_DEM_PREPARED"
    assert m["input_asset"]["sha256"] == EXPECTED_RAW_SHA256
    assert m["output_asset"]["sha256"] == EXPECTED_DERIVED_SHA256
    assert m["output_asset"]["dimensions"]["width"] == GRID_WIDTH
    assert m["output_asset"]["dimensions"]["height"] == GRID_HEIGHT
    assert m["hydrological_evidence_status"]["catchment_polygon"].startswith("UNVERIFIED")
    assert m["hydrological_evidence_status"]["airport_runway_culvert"].startswith("MISSING_EVIDENCE")


def test_error_handling_on_corrupt_or_missing_source():
    """Verify prepare_terrain rejects missing and invalid source files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        non_existent = Path(tmp_dir) / "nonexistent.tif"
        out_file = Path(tmp_dir) / "out.tif"
        success, info = prepare_terrain(non_existent, out_file)
        assert success is False
        assert "missing" in info.get("error", "").lower()

        corrupt_file = Path(tmp_dir) / "corrupt.tif"
        corrupt_file.write_bytes(b"CORRUPTED_BYTES")
        success2, info2 = prepare_terrain(corrupt_file, out_file)
        assert success2 is False
        assert "checksum mismatch" in info2.get("error", "").lower()
