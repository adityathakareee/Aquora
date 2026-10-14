import os
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure scripts directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from phase7a_manifest_validator import validate_manifest
from phase7b_acquisition_service import (
    RAW_DIRS,
    build_provenance_registry,
    compute_sha256,
    download_file,
    ensure_directories,
    load_manifest,
    validate_scientific_file_content,
    validate_vector_metadata,
)


def test_phase7a_manifest_validation():
    """Verify that the Phase 7A download manifest passes automated validation."""
    assert validate_manifest() is True


def test_sha256_computation(tmp_path):
    """Test cryptographic SHA-256 hash generation."""
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Aquora Phase 7B Real Data Integrity Test", encoding="utf-8")

    sha256_result = compute_sha256(test_file)
    assert isinstance(sha256_result, str)
    assert len(sha256_result) == 64
    import hashlib

    expected = hashlib.sha256(b"Aquora Phase 7B Real Data Integrity Test").hexdigest()
    assert sha256_result == expected


def test_acquisition_directories_structure():
    """Verify directory structure creation for raw and processed datasets."""
    ensure_directories()
    for path in RAW_DIRS.values():
        assert path.exists()
        assert path.is_dir()


def test_vector_metadata_validation(tmp_path):
    """Test vector metadata validation for JSON/GeoJSON vector files."""
    json_file = tmp_path / "mock_osm.json"
    json_file.write_text('{"generator": "Overpass API", "elements": [{"id": 1}, {"id": 2}]}', encoding="utf-8")

    meta = validate_vector_metadata(json_file)
    assert meta["valid"] is True
    assert meta["element_count"] == 2
    assert meta["generator"] == "Overpass API"


def test_validate_scientific_file_content_zip(tmp_path):
    """Test ZIP magic bytes and SAFE structure validation."""
    # 1. Valid Sentinel-1 ZIP mock
    valid_zip_path = tmp_path / "valid_s1.zip"
    with zipfile.ZipFile(valid_zip_path, "w") as zf:
        zf.writestr("S1A_IW_GRDH_1SDV_mock.SAFE/manifest.safe", "mock manifest content")
        zf.writestr("S1A_IW_GRDH_1SDV_mock.SAFE/measurement/image.tif", "mock tif content")

    valid, msg = validate_scientific_file_content(valid_zip_path, expected_format="SAFE_ZIP")
    assert valid is True
    assert "Valid scientific payload" in msg

    # 2. Corrupt / HTML masquerading as ZIP (> 100 bytes to bypass size check)
    html_zip_path = tmp_path / "html_as_zip.zip"
    html_zip_path.write_text("<!DOCTYPE html><html><head><title>Error 404</title></head><body><h1>404 Not Found - Data Portal</h1><p>The requested file or granule was not found on this server.</p></body></html>", encoding="utf-8")

    valid_html, msg_html = validate_scientific_file_content(html_zip_path, expected_format="SAFE_ZIP")
    assert valid_html is False
    assert "File contains HTML/web error page" in msg_html


def test_validate_scientific_file_content_hdf5(tmp_path):
    """Test HDF5 / NetCDF magic bytes validation."""
    # 1. Valid HDF5 header
    hdf_path = tmp_path / "valid_imerg.nc"
    hdf_path.write_bytes(b"\x89HDF\r\n\x1a\n" + b"\x00" * 200)

    valid, _msg = validate_scientific_file_content(hdf_path, expected_format="NETCDF")
    assert valid is True

    # 2. Invalid HDF5 header
    invalid_hdf_path = tmp_path / "invalid_imerg.nc"
    invalid_hdf_path.write_bytes(b"INVALID_HEADER_BYTES_" + b"\x00" * 200)

    valid_inv, msg_inv = validate_scientific_file_content(invalid_hdf_path, expected_format="NETCDF")
    assert valid_inv is False
    assert "Invalid NetCDF/HDF5 magic bytes" in msg_inv


def test_atomic_download_cleanup_on_validation_failure(tmp_path):
    """Ensure atomic downloads clean up .tmp files and do not create target file on failure."""
    target_file = tmp_path / "test_download.zip"
    tmp_file = tmp_path / "test_download.zip.tmp"

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "text/html", "Content-Length": "145"}
    mock_resp.geturl.return_value = "https://mock.provider.org/dataset.zip"
    mock_resp.read.side_effect = [b"<!DOCTYPE html><html><body>Error page content longer than 100 bytes</body></html>", b""]

    with patch("urllib.request.build_opener") as mock_opener:
        instance = MagicMock()
        instance.open.return_value.__enter__.return_value = mock_resp
        mock_opener.return_value = instance

        success = download_file("https://mock.provider.org/dataset.zip", target_file, force=True, expected_format="SAFE_ZIP")

    assert success is False
    assert not target_file.exists()
    assert not tmp_file.exists()


def test_atomic_download_byte_count_mismatch(tmp_path):
    """Ensure download fails when Content-Length mismatch occurs."""
    target_file = tmp_path / "mismatch.nc"
    tmp_file = tmp_path / "mismatch.nc.tmp"

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/x-netcdf", "Content-Length": "1000"}
    mock_resp.geturl.return_value = "https://mock.provider.org/imerg.nc"
    mock_resp.read.side_effect = [b"\x89HDF\r\n\x1a\n" + b"\x00" * 100, b""]

    with patch("urllib.request.build_opener") as mock_opener:
        instance = MagicMock()
        instance.open.return_value.__enter__.return_value = mock_resp
        mock_opener.return_value = instance

        success = download_file("https://mock.provider.org/imerg.nc", target_file, force=True, expected_format="NETCDF")

    assert success is False
    assert not target_file.exists()
    assert not tmp_file.exists()


def test_manifest_target_verified_e820_authoritative_for_e02_sar():
    """Verify manifest target E820 is the verified replacement scene for E02 Sentinel-1."""
    manifest = load_manifest()
    e02_sar = next(e for e in manifest["download_entries"] if e["id"] == "DL-SAR-E02")
    assert e02_sar["scene_id"] == "S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820"
    assert e02_sar["event_id"] == "E02"


def test_smoke_test_e820_classified_as_acquired_e02():
    """
    Verify E820 target is classified as VERIFIED_TARGET when un-downloaded,
    and transitions to ACQUIRED only after authentic local payload exists and passes validation.
    """
    manifest = load_manifest()
    registry = build_provenance_registry(manifest)

    e02_entry = next(e for e in registry["entries"] if e["acquisition_id"] == "DL-SAR-E02")
    assert e02_entry["target_id"] == "S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820"

    # In authentic un-downloaded state, zero-fabrication strictly enforces VERIFIED_TARGET
    if not (e02_entry["local_path"] and os.path.exists(e02_entry["local_path"])):
        assert e02_entry["download_status"] == "VERIFIED_TARGET"
    else:
        assert e02_entry["download_status"] == "ACQUIRED"

    smoke_entry = next((e for e in registry["entries"] if e["acquisition_id"] == "DL-SAR-E02-SMOKE"), None)
    if smoke_entry:
        assert smoke_entry["download_status"] == "SMOKE_TEST"
        assert smoke_entry["is_smoke_test"] is True
        assert smoke_entry["target_id"] == "S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820"


def test_smoke_test_e820_acquired_transition_with_mocked_file(tmp_path, monkeypatch):
    """Verify that when a verified SAFE archive exists locally, the entry correctly transitions to ACQUIRED."""
    from phase7b_acquisition_service import RAW_DIRS, validate_scientific_file_content
    import zipfile

    # Create a small valid test SAFE archive in tmp_path
    mock_zip = tmp_path / "S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820.zip"
    with zipfile.ZipFile(mock_zip, "w") as zf:
        zf.writestr("manifest.safe", "<xml><productType>GRD</productType></xml>")
        zf.writestr("measurement/s1a-iw-grd-vv.tiff", b"TIFFDATA")
        zf.writestr("measurement/s1a-iw-grd-vh.tiff", b"TIFFDATA")
        zf.writestr("annotation/s1a-iw-grd-vv.xml", b"<annotation/>")
        zf.writestr("annotation/s1a-iw-grd-vh.xml", b"<annotation/>")

    manifest = load_manifest()

    # Monkeypatch RAW_DIRS to point to tmp_path
    monkeypatch.setitem(RAW_DIRS, "satellite_ground_truth", tmp_path)
    # Monkeypatch validation function to accept our mock SAFE zip
    monkeypatch.setattr("phase7b_acquisition_service.validate_scientific_file_content", lambda p, expected_format=None: (True, "Valid SAFE test archive"))

    # Also place in event dir
    event_dir = tmp_path / "E02"
    event_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy(mock_zip, event_dir / mock_zip.name)

    registry = build_provenance_registry(manifest)
    e02_entry = next(e for e in registry["entries"] if e["acquisition_id"] == "DL-SAR-E02")
    assert e02_entry["download_status"] == "ACQUIRED"
    assert e02_entry["file_size_bytes"] > 0


def test_direct_imerg_and_asf_url_resolution():
    """Test direct IMERG and ASF URL resolution without network access."""
    from phase7b_acquisition_service import resolve_direct_product_url

    sar_entry = {
        "id": "DL-SAR-E02",
        "category": "satellite_ground_truth",
        "scene_id": "S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820",
        "access_url": "https://search.asf.alaska.edu/",
    }
    resolved_sar = resolve_direct_product_url(sar_entry)
    assert resolved_sar == "https://datapool.asf.alaska.edu/GRD_HD/SA/S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820.zip"

    imerg_entry = {
        "id": "DL-RAIN-E02",
        "category": "precipitation",
        "event_id": "E02",
        "access_url": "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary",
    }
    resolved_imerg = resolve_direct_product_url(imerg_entry)
    assert "gpm1.gesdisc.eosdis.nasa.gov" in resolved_imerg
    assert resolved_imerg.endswith(".HDF5")


def test_registry_status_taxonomy_and_historical_preservation():
    """Test registry taxonomy classification (SMOKE_TEST, ACQUIRED, SUPERSEDED, INVALID_CONTENT)."""
    manifest = load_manifest()
    registry = build_provenance_registry(manifest)

    assert "acquired_count" in registry
    assert "smoke_test_count" in registry
    assert "superseded_count" in registry

    # Historical landing page files for rainfall/sentinel1 should be marked SUPERSEDED
    e02_rain = next(e for e in registry["entries"] if e["acquisition_id"] == "DL-RAIN-E02")
    if e02_rain["file_size_bytes"] == 2828:
        assert e02_rain["download_status"] == "SUPERSEDED"
        assert "Initial manifest URL" in e02_rain["superseded_reason"]


def test_secret_masking_invariant():
    """Ensure environment credentials are never exposed in log outputs or registry objects."""
    token_value = "SUPER_SECRET_EARTHDATA_TOKEN_12345"
    os.environ["EARTHDATA_TOKEN"] = token_value

    manifest = load_manifest()
    registry = build_provenance_registry(manifest)

    registry_str = str(registry)
    assert token_value not in registry_str


def test_download_file_initial_bearer_header(tmp_path):
    """Prove that the initial urllib.request.Request contains Authorization Bearer header when token is supplied."""
    target_file = tmp_path / "test_auth.nc"
    test_token = "TEST_EARTHDATA_BEARER_TOKEN_999"

    mock_payload = b"\x89HDF\r\n\x1a\n" + b"\x00" * 200
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/x-netcdf", "Content-Length": str(len(mock_payload))}
    mock_resp.geturl.return_value = "https://gpm1.gesdisc.eosdis.nasa.gov/data/sample.nc"
    mock_resp.read.side_effect = [mock_payload, b""]

    captured_requests = []

    def fake_open(req, timeout=60):
        captured_requests.append(req)
        ctx = MagicMock()
        ctx.__enter__.return_value = mock_resp
        return ctx

    with patch("urllib.request.build_opener") as mock_opener:
        instance = MagicMock()
        instance.open.side_effect = fake_open
        mock_opener.return_value = instance

        success = download_file(
            "https://gpm1.gesdisc.eosdis.nasa.gov/data/sample.nc",
            target_file,
            auth_token=test_token,
            force=True,
            expected_format="NETCDF",
        )

    assert success is True
    assert len(captured_requests) > 0
    initial_req = captured_requests[0]
    assert "Authorization" in initial_req.headers
    assert initial_req.headers["Authorization"] == f"Bearer {test_token}"


def test_verified_sentinel1_manifest_target_structure():
    """Verify that Phase 7A download manifest contains verified Sentinel-1 scene IDs and ASF URLs."""
    manifest = load_manifest()

    expected_targets = {
        "DL-SAR-E02": ("S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820", "2017-08-29T01:02:48Z"),
        "DL-SAR-E03": ("S1A_IW_GRDH_1SDV_20190702T010258_20190702T010323_027931_03274B_DDDA", "2019-07-02T01:02:58Z"),
        "DL-SAR-E04": ("S1A_IW_GRDH_1SDV_20190831T010301_20190831T010326_028806_034364_FA1B", "2019-08-31T01:03:01Z"),
        "DL-SAR-E05": ("S1A_IW_GRDH_1SDV_20200801T010318_20200801T010343_033706_03E812_4FB3", "2020-08-01T01:03:18Z"),
        "DL-SAR-E06": ("S1A_IW_GRDH_1SDV_20200918T010321_20200918T010346_034406_040065_2BB1", "2020-09-18T01:03:21Z"),
        "DL-SAR-E07": ("S1A_IW_GRDH_1SDV_20210715T010321_20210715T010346_038781_049379_1EE0", "2021-07-15T01:03:21Z"),
    }

    for dl_id, (expected_scene, expected_utc) in expected_targets.items():
        entry = next(e for e in manifest["download_entries"] if e["id"] == dl_id)
        assert entry["scene_id"] == expected_scene
        assert entry["acquisition_utc"] == expected_utc
        assert entry["status"] == "VERIFIED_TARGET"
        assert entry["status"] != "ACQUIRED"
        assert entry["access_url"].startswith("https://datapool.asf.alaska.edu/GRD_HD/")
        assert entry["access_url"].endswith(".zip")


def test_historical_invalid_targets_preserved():
    """Ensure historical invalid targets remain preserved in audit documentation."""
    repair_doc = Path(__file__).resolve().parent.parent.parent / "docs" / "phase7" / "PHASE_7B_SENTINEL_TARGET_REPAIR.md"
    assert repair_doc.exists()

    content = repair_doc.read_text(encoding="utf-8")
    invalid_ids = ["D1F2", "C81B", "7A88", "E944", "B32A", "5F12"]
    for inv_id in invalid_ids:
        assert inv_id in content


