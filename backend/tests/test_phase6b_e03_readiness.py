"""
AQUORA Phase 6B.2: Event E03 Sentinel-1 SAR Acquisition Readiness Tests.

Validates the acquisition workflow, catalog manifest specifications, credential safety,
disk space evaluation, and archive validation logic without downloading full archives.
"""

import hashlib
import io
import shutil
import zipfile
from pathlib import Path
import pytest
import yaml

from scripts.acquire_phase6b_e03_sar import (
    E03_SCENES,
    check_disk_space,
    compute_checksums,
    validate_sar_archive,
    run_e03_acquisition,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6b_e03_sar_manifest.yaml"


def test_manifest_existence_and_structure():
    """Verify phase6b_e03_sar_manifest.yaml exists and parses cleanly."""
    assert MANIFEST_PATH.exists(), f"Manifest missing at {MANIFEST_PATH}"

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["phase"] == "PHASE_6B_E03_SENTINEL1_ACQUISITION_READINESS"
    assert manifest["event_target"]["event_id"] == "E03"
    assert manifest["governance"]["status"] in (
        "ACQUISITION_READY_AWAITING_USER_APPROVAL",
        "DOWNLOADED_AND_VALIDATED"
    )
    assert manifest["governance"]["zero_fabrication_enforced"] is True


def test_manifest_catalog_specifications_match_code():
    """Verify manifest byte counts, MD5s, and URLs match the script specifications."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    catalog = manifest["authoritative_catalog_evidence"]
    assert catalog["platform"] == "Sentinel-1A"
    assert catalog["track_relative_orbit"] == 34
    assert catalog["frame_number"] == 528
    assert catalog["beam_mode"] == "IW (Interferometric Wide Swath)"

    # Pre-event scene
    pre = catalog["primary_pair_candidates"]["pre_event_baseline"]
    assert pre["granule_name"] == E03_SCENES["pre_event"]["granule_name"]
    assert pre["exact_size_bytes"] == E03_SCENES["pre_event"]["exact_bytes"]
    assert pre["provider_md5"] == E03_SCENES["pre_event"]["provider_md5"]

    # Co-event scene
    co = catalog["primary_pair_candidates"]["co_event_crisis"]
    assert co["granule_name"] == E03_SCENES["co_event"]["granule_name"]
    assert co["exact_size_bytes"] == E03_SCENES["co_event"]["exact_bytes"]
    assert co["provider_md5"] == E03_SCENES["co_event"]["provider_md5"]

    # Optional post-event scene
    post = catalog["optional_seasonal_baseline"]["post_event_recession"]
    assert post["granule_name"] == E03_SCENES["post_event"]["granule_name"]
    assert post["exact_size_bytes"] == E03_SCENES["post_event"]["exact_bytes"]
    assert post["provider_md5"] == E03_SCENES["post_event"]["provider_md5"]


def test_disk_space_check_evaluates_correctly():
    """Verify check_disk_space accurately calculates available headroom."""
    disk = check_disk_space(required_gb=10.0)
    assert "free_gb" in disk
    assert "total_gb" in disk
    assert disk["free_gb"] > 0
    assert disk["sufficient"] == (disk["free_gb"] >= 10.0)


def test_validator_rejects_html_auth_error_page(tmp_path):
    """Verify validator catches HTML login redirection pages and flags auth error."""
    html_file = tmp_path / "fake_granule.zip"
    html_file.write_text("<!DOCTYPE html><html><head><title>Earthdata Login</title></head><body>Login</body></html>")

    spec = E03_SCENES["pre_event"]
    val = validate_sar_archive(html_file, spec)
    assert val["valid"] is False
    assert "HTML authentication redirect page" in val["error"]


def test_validator_rejects_size_mismatch(tmp_path):
    """Verify validator catches truncated or partial downloads."""
    truncated_file = tmp_path / "truncated.zip"
    truncated_file.write_bytes(b"PK\x03\x04" + b"\x00" * 5000000)

    spec = E03_SCENES["pre_event"]
    val = validate_sar_archive(truncated_file, spec)
    assert val["valid"] is False
    assert "Byte count mismatch" in val["error"]


def test_validator_accepts_valid_safe_zip(tmp_path):
    """Verify validator passes a syntactically valid zip containing SAFE structure and matching MD5."""
    valid_zip_path = tmp_path / "valid.zip"

    # Construct minimal in-memory SAFE zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("S1A_IW_GRDH_TEST.SAFE/manifest.safe", "<safe:manifest/>")
        zf.writestr("S1A_IW_GRDH_TEST.SAFE/measurement/s1a-iw-grd-vv-test.tiff", "TIFF_CONTENT")
        zf.writestr("S1A_IW_GRDH_TEST.SAFE/annotation/s1a-iw-grd-vv-test.xml", "<annotation/>")

    content = buf.getvalue()
    valid_zip_path.write_bytes(content)

    actual_md5 = hashlib.md5(content).hexdigest()
    mock_spec = {
        "granule_name": "S1A_IW_GRDH_TEST",
        "exact_bytes": len(content),
        "provider_md5": actual_md5
    }

    val = validate_sar_archive(valid_zip_path, mock_spec)
    assert val["valid"] is True
    assert val["validation_status"] == "VALIDATED_AUTHENTIC_SAFE_ZIP"
    assert val["md5"] == actual_md5


def test_dry_run_executes_safely_without_downloading():
    """Verify run_e03_acquisition in dry_run mode performs readiness check without writing files."""
    res = run_e03_acquisition(dry_run=True, include_post_event=True)
    assert res["status"] == "COMPLETED"
    assert res["results"]["pre_event"]["status"] in ("DRY_RUN", "CACHED")
    assert res["results"]["co_event"]["status"] in ("DRY_RUN", "CACHED")
    assert res["results"]["post_event"]["status"] == "DRY_RUN"


def test_downloaded_authentic_archives_and_coverage():
    """Verify downloaded Sentinel-1 archives on disk match exact sizes, MD5s, and cover Mithi catchment."""
    raw_dir = PROJECT_ROOT / "data" / "raw" / "phase7" / "sentinel1" / "E03"
    pre_path = raw_dir / f"{E03_SCENES['pre_event']['granule_name']}.zip"
    co_path = raw_dir / f"{E03_SCENES['co_event']['granule_name']}.zip"

    if not (pre_path.exists() and co_path.exists()):
        pytest.skip("Downloaded archives not present in target directory")

    mithi_bbox = {"min_lon": 72.84064, "max_lon": 72.95071, "min_lat": 18.99033, "max_lat": 19.12057}

    for key, fpath in [("pre_event", pre_path), ("co_event", co_path)]:
        spec = E03_SCENES[key]
        val = validate_sar_archive(fpath, spec)
        assert val["valid"] is True, f"Validation failed for {key}: {val.get('error')}"
        assert val["md5"] == spec["provider_md5"]
        assert fpath.stat().st_size == spec["exact_bytes"]

        # Geolocation footprint verification
        with zipfile.ZipFile(fpath, "r") as zf:
            manifest_files = [n for n in zf.namelist() if n.endswith("manifest.safe")]
            assert len(manifest_files) > 0, "manifest.safe missing"
            manifest_text = zf.read(manifest_files[0]).decode("utf-8")

            # Parse coordinates
            import xml.etree.ElementTree as ET
            root = ET.fromstring(manifest_text)
            coords_elem = None
            for elem in root.iter():
                if elem.tag.endswith("coordinates"):
                    coords_elem = elem
                    break
            assert coords_elem is not None, "Footprint coordinates missing in manifest.safe"

            coords_pairs = coords_elem.text.strip().split()
            pts = [tuple(map(float, p.split(","))) for p in coords_pairs]
            lats = [p[0] for p in pts]
            lons = [p[1] for p in pts]

            assert min(lats) <= mithi_bbox["min_lat"]
            assert max(lats) >= mithi_bbox["max_lat"]
            assert min(lons) <= mithi_bbox["min_lon"]
            assert max(lons) >= mithi_bbox["max_lon"]

