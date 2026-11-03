"""
AQUORA Phase 6C.2c Automated Test Suite: Copernicus DEM Acquisition & Validation.

Validates:
1. Physical existence, integrity, and exact SHA-256 checksum of raw DEM.
2. Rasterio metadata (driver, CRS, 3600x3600 dimensions, bounds).
3. Mithi watershed complete coverage (outfall to northern headwaters).
4. Physical elevation plausibility at verified reservoir landmarks.
5. Verification manifest schema and values.
6. Error handling for network drops, byte count mismatches, and corrupt files (mocked).
"""

import hashlib
import io
import os
import shutil
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import rasterio
import yaml

from scripts.acquire_phase6c2c_dem import (
    DEM_FILENAME,
    LEGACY_FILENAME,
    MITHI_LANDMARKS,
    OFFICIAL_DEM_URL,
    PROJECT_ROOT,
    RAW_DEM_DIR,
    compute_sha256,
    download_copernicus_dem,
    validate_copernicus_dem,
)

EXPECTED_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_FILE_SIZE = 13_336_459


@pytest.fixture
def dem_path() -> Path:
    p = RAW_DEM_DIR / DEM_FILENAME
    assert p.exists(), f"Required DEM file does not exist: {p}"
    return p


def test_dem_file_exists_and_size(dem_path: Path):
    """Verify downloaded DEM exists and matches exact byte length."""
    assert dem_path.is_file()
    assert dem_path.stat().st_size == EXPECTED_FILE_SIZE


def test_dem_sha256_checksum(dem_path: Path):
    """Verify computed SHA-256 matches the authentic baseline checksum."""
    actual_hash = compute_sha256(dem_path)
    assert actual_hash == EXPECTED_SHA256, f"Checksum mismatch: {actual_hash} != {EXPECTED_SHA256}"


def test_dem_raster_metadata(dem_path: Path):
    """Verify GeoTIFF driver, dimensions, CRS, and pixel-is-point bounds."""
    with rasterio.open(dem_path) as ds:
        assert ds.driver == "GTiff"
        assert ds.width == 3600
        assert ds.height == 3600
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert ds.crs.to_epsg() == 4326

        # Check bounds: 1 deg x 1 deg (with 0.5-pixel shift for Point registration)
        half_px = ds.res[0] / 2.0
        assert abs(ds.bounds.left - (72.0 - half_px)) < 1e-5
        assert abs(ds.bounds.right - (73.0 - half_px)) < 1e-5
        assert abs(ds.bounds.bottom - (19.0 + half_px)) < 1e-5
        assert abs(ds.bounds.top - (20.0 + half_px)) < 1e-5


def test_dem_mithi_basin_coverage(dem_path: Path):
    """Verify all key Mithi landmarks (outfall to headwaters) fall strictly within DEM."""
    with rasterio.open(dem_path) as ds:
        for name, (lon, lat) in MITHI_LANDMARKS.items():
            assert ds.bounds.left <= lon <= ds.bounds.right, f"{name} lon {lon} out of bounds"
            assert ds.bounds.bottom <= lat <= ds.bounds.top, f"{name} lat {lat} out of bounds"

            row, col = ds.index(lon, lat)
            assert 0 <= row < ds.height, f"{name} row {row} out of index"
            assert 0 <= col < ds.width, f"{name} col {col} out of index"


def test_dem_elevation_physics_plausibility(dem_path: Path):
    """Verify ground truth elevation levels at surveyed Mumbai water bodies."""
    with rasterio.open(dem_path) as ds:
        elev = ds.read(1)

        # Powai Lake (FSL ~33.5m)
        r_powai, c_powai = ds.index(*MITHI_LANDMARKS["Powai_Lake"])
        assert 30.0 <= elev[r_powai, c_powai] <= 37.0, f"Powai elev unexpected: {elev[r_powai, c_powai]}"

        # Vihar Lake (FSL ~52.4m)
        r_vihar, c_vihar = ds.index(*MITHI_LANDMARKS["Vihar_Lake"])
        assert 48.0 <= elev[r_vihar, c_vihar] <= 56.0, f"Vihar elev unexpected: {elev[r_vihar, c_vihar]}"

        # Tulsi Lake (FSL ~130m)
        r_tulsi, c_tulsi = ds.index(*MITHI_LANDMARKS["Tulsi_Lake_Headwaters"])
        assert 120.0 <= elev[r_tulsi, c_tulsi] <= 140.0, f"Tulsi elev unexpected: {elev[r_tulsi, c_tulsi]}"

        # BKC Floodplain (< 5m MSL)
        r_bkc, c_bkc = ds.index(*MITHI_LANDMARKS["Bandra_Kurla_Complex"])
        assert -1.0 <= elev[r_bkc, c_bkc] <= 10.0, f"BKC elev unexpected: {elev[r_bkc, c_bkc]}"


def test_dem_manifest_integrity():
    """Verify verification manifest exists and contains accurate metadata."""
    manifest_file = PROJECT_ROOT / "data" / "manifests" / "phase6c2c_dem_manifest.yaml"
    assert manifest_file.exists(), f"Manifest missing: {manifest_file}"

    with open(manifest_file, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    assert m["phase"] == "PHASE_6C_2C_COPERNICUS_DEM_ACQUISITION"
    assert m["governance"]["status"] == "AUTHENTIC_RAW_DEM_ACQUIRED_AND_VALIDATED"
    assert m["asset"]["sha256"] == EXPECTED_SHA256
    assert m["asset"]["file_size_bytes"] == EXPECTED_FILE_SIZE
    assert m["catchment_coverage_verification"]["covers_full_mithi_watershed"] is True
    assert m["catchment_coverage_verification"]["covers_headwaters_lakes"] is True


def test_download_error_handling_mocked():
    """Unit test: Verify safe handling of network drop and partial file cleanup."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dest_path = Path(tmp_dir) / "test_dem.tif"

        # Mock urllib.request.urlopen to simulate a network drop after 100 bytes
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.headers = {"Content-Length": "10000"}
        mock_resp.read.side_effect = [b"A" * 100, urllib.error.URLError("Connection reset")]

        with patch("urllib.request.urlopen", return_value=mock_resp):
            success, msg = download_copernicus_dem("http://mock.test/dem.tif", dest_path, max_retries=1)

            assert success is False
            assert not dest_path.exists(), "Corrupt destination file must not exist after failure"
            assert not dest_path.with_suffix(".tmp").exists(), "Temporary file must be cleaned up"


def test_validate_nonexistent_and_corrupt_file():
    """Unit test: Verify validator rejects missing and undersized dummy files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        non_existent = Path(tmp_dir) / "nonexistent.tif"
        valid, report = validate_copernicus_dem(non_existent)
        assert valid is False
        assert any("File not found" in e for e in report["errors"])

        dummy_file = Path(tmp_dir) / "dummy.tif"
        dummy_file.write_bytes(b"NOT_A_REAL_TIFF_JUST_BYTES")
        valid2, report2 = validate_copernicus_dem(dummy_file)
        assert valid2 is False
        assert any("suspiciously small" in e for e in report2["errors"])
