"""
AQUORA 2.0 — Phase 2D Sentinel-1 SAR Ingestion & Verification Test Suite.

Exhaustive tests covering:
1. Scene discovery, filtering, and eligibility validation
2. Provider credential checks and secret redaction
3. Safe bounded acquisition jobs and idempotency
4. Bitemporal SAR preprocessing, orbital compatibility, and quality masking
5. Flood candidate evidence generation with strict zero-fabrication
6. Multi-basin coverage across Indian pilot domains
7. FastAPI async endpoints, background jobs, and error handling
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import pytest
import zipfile

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.providers.sar import CopernicusSentinel1Provider
from app.schemas.sar import (
    SARAcquisitionRequest,
    SARAcquisitionStatus,
    SARDiscoveryRequest,
    SAREvidenceClassification,
    SARJobStatus,
    SARProcessingRequest,
)
from app.services.india_sar_service import IndiaSARService


@pytest.fixture
def sar_service():
    return IndiaSARService()


@pytest.fixture
def sar_provider():
    return CopernicusSentinel1Provider()


# ==============================================================================
# 1. Provider Discovery & Eligibility Validation
# ==============================================================================

@pytest.mark.asyncio
async def test_01_provider_discovery_by_domain(sar_service):
    """Verify discovery resolves pilot domain bounds and discovers eligible scenes."""
    req = SARDiscoveryRequest(domain_id="ganga_patna")
    res = await sar_service.discover_scenes(req)

    assert res.domain_id == "ganga_patna"
    assert res.total_discovered >= 2
    for sc in res.scenes:
        assert sc.sensor_mode == "IW"
        assert sc.product_type in ("GRD", "GRD_HD")
        assert "VV" in sc.polarizations
        assert sc.orbit_direction in ("DESCENDING", "ASCENDING")


@pytest.mark.asyncio
async def test_02_provider_discovery_by_bbox(sar_service):
    """Verify discovery with explicit WGS84 bounding box."""
    # Assam / Guwahati bounding box
    bbox = [91.0, 25.5, 92.5, 26.8]
    req = SARDiscoveryRequest(bbox=bbox)
    res = await sar_service.discover_scenes(req)

    assert res.total_discovered >= 2
    for sc in res.scenes:
        assert sc.orbit_direction == "ASCENDING"


@pytest.mark.asyncio
async def test_03_orbit_direction_filter(sar_service):
    """Verify filtering by orbit direction."""
    req = SARDiscoveryRequest(orbit_direction="DESCENDING")
    res = await sar_service.discover_scenes(req)

    assert res.total_discovered > 0
    for sc in res.scenes:
        assert sc.orbit_direction == "DESCENDING"


def test_04_credentials_redaction_and_unconfigured_state(sar_provider):
    """Verify credentials check does not expose secrets and reports configuration state."""
    creds = sar_provider.check_credentials()
    assert "provider" in creds
    assert "credentials_configured" in creds
    assert "operational_status" in creds

    # Ensure no token string or password is leaked in the dict
    creds_str = str(creds)
    assert "password" not in creds_str.lower()
    assert "secret" not in creds_str.lower()


# ==============================================================================
# 2. Safe Bounded Acquisition & Job Management
# ==============================================================================

@pytest.mark.asyncio
async def test_05_dry_run_acquisition_job(sar_service):
    """Verify dry-run acquisition validates target without downloading large binaries."""
    scene_id = "S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820"
    req = SARAcquisitionRequest(scene_ids=[scene_id], dry_run=True)
    res = await sar_service.submit_acquisition_job(req)

    assert res.job_id.startswith("sar_job_")
    assert res.status == SARJobStatus.COMPLETED
    assert res.scene_statuses[scene_id] == SARAcquisitionStatus.VERIFIED_TARGET.value


@pytest.mark.asyncio
async def test_06_unauthenticated_live_acquisition_blocked(sar_service, monkeypatch):
    """Verify live acquisition is blocked when Earthdata credentials are not configured."""
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    monkeypatch.delenv("CDSE_TOKEN", raising=False)
    monkeypatch.delenv("ASF_TOKEN", raising=False)
    monkeypatch.delenv("EARTHDATA_USER", raising=False)
    monkeypatch.delenv("EARTHDATA_PASS", raising=False)
    monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
    monkeypatch.delenv("CDSE_CLIENT_SECRET", raising=False)

    scene_id = "S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820"
    req = SARAcquisitionRequest(scene_ids=[scene_id], dry_run=False)
    res = await sar_service.submit_acquisition_job(req)

    assert res.status == SARJobStatus.BLOCKED
    assert res.scene_statuses[scene_id] == SARAcquisitionStatus.DOWNLOAD_BLOCKED.value
    assert len(res.errors) > 0


@pytest.mark.asyncio
async def test_07_job_polling_and_listing(sar_service):
    """Verify job status lookup and listing."""
    req = SARAcquisitionRequest(scene_ids=["S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820"], dry_run=True)
    created = await sar_service.submit_acquisition_job(req)

    polled = sar_service.get_job_status(created.job_id)
    assert polled is not None
    assert polled.job_id == created.job_id

    jobs = sar_service.list_jobs()
    assert any(j.job_id == created.job_id for j in jobs)


# ==============================================================================
# 3. SAR Preprocessing & Orbital Compatibility
# ==============================================================================

@pytest.mark.asyncio
async def test_08_incompatible_orbits_rejected(sar_service):
    """Verify pre/co scenes with different orbit directions are rejected."""
    # pre is DESCENDING (Patna), co is ASCENDING (Guwahati)
    req = SARProcessingRequest(
        domain_id="ganga_patna",
        pre_event_scene_id="S1A_IW_GRDH_1SDV_20230706T001814_20230706T001839_049296_05EE10_B219",
        co_event_scene_id="S1A_IW_GRDH_1SDV_20220616T115822_20220616T115847_043688_053723_A412",
    )
    with pytest.raises(ValueError, match="Incompatible orbit directions"):
        await sar_service.process_bitemporal_pair(req)


@pytest.mark.asyncio
async def test_09_missing_raw_scenes_returns_unavailable_state(sar_service):
    """Verify that unacquired scenes return explicit UNAVAILABLE status, preserving zero-fabrication."""
    req = SARProcessingRequest(
        domain_id="ganga_patna",
        pre_event_scene_id="S1A_IW_GRDH_1SDV_20230706T001814_20230706T001839_049296_05EE10_B219",
        co_event_scene_id="S1A_IW_GRDH_1SDV_20230718T001815_20230718T001840_049471_05F390_E981",
    )
    ev = await sar_service.process_bitemporal_pair(req)

    assert ev.evidence_classification == SAREvidenceClassification.UNAVAILABLE
    assert ev.validation_status == "UNAVAILABLE_RAW_GRANULES_NOT_ON_DISK"
    assert ev.candidate_flood_pixels is None


def test_10_safe_archive_validation(sar_provider, tmp_path):
    """Verify SAFE ZIP structure verification."""
    # 1. Non-existent file
    valid, msg, _ = sar_provider.validate_scene_archive(tmp_path / "absent.zip")
    assert valid is False
    assert "missing" in msg.lower()

    # 2. Too small
    small = tmp_path / "tiny.zip"
    small.write_bytes(b"PK\x03\x04" + b"\x00" * 50)
    valid, msg, _ = sar_provider.validate_scene_archive(small)
    assert valid is False
    assert "suspiciously small" in msg.lower()

    # 3. Valid structure
    valid_zip = tmp_path / "valid_test_scene.zip"
    with zipfile.ZipFile(valid_zip, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("manifest.safe", """<?xml version="1.0" encoding="UTF-8"?>
<xfdu:XFDU xmlns:xfdu="urn:ccsds:schema:xfdu:encodings:extension:ee:standard">
  <metadataSection>
    <pass>DESCENDING</pass>
    <relativeOrbitNumber>18</relativeOrbitNumber>
    <startTime>2017-08-29T01:02:48.000000Z</startTime>
    <stopTime>2017-08-29T01:03:13.000000Z</stopTime>
    <mode>IW</mode>
    <productType>GRD</productType>
  </metadataSection>
</xfdu:XFDU>""")
        zf.writestr("measurement/s1a-iw-grd-vv.tiff", b"TIFF_VV")
        zf.writestr("measurement/s1a-iw-grd-vh.tiff", b"TIFF_VH")
        zf.writestr("annotation/s1a-iw-grd-vv.xml", b"<annotation/>")
        zf.writestr("annotation/s1a-iw-grd-vh.xml", b"<annotation/>")
        zf.writestr("padding.dat", b"0" * 51_000_000)

    valid, msg, meta = sar_provider.validate_scene_archive(valid_zip)
    assert valid is True
    assert meta["pass"] == "DESCENDING"
    assert meta["productType"] == "GRD"
    assert meta["mode"] == "IW"


# ==============================================================================
# 4. Multi-Basin Coverage & Evidence Semantics
# ==============================================================================

def test_11_multi_basin_coverage_overview(sar_service):
    """Verify coverage report covers all 5 pilot domains."""
    cov = sar_service.get_coverage_overview()
    assert "ganga_patna" in cov.supported_domains
    assert "brahmaputra_guwahati" in cov.supported_domains
    assert "godavari_nashik" in cov.supported_domains
    assert "narmada_bharuch" in cov.supported_domains
    assert "deep_mumbai_mithi" in cov.supported_domains

    patna = cov.domain_catalog["ganga_patna"]
    assert patna["pair_available_in_catalog"] is True
    assert patna["orbit_direction"] == "DESCENDING"


def test_12_evidence_catalog_query(sar_service):
    """Verify domain evidence lookup distinguishes registered catalog target from unacquired data."""
    ev = sar_service.get_evidence("ganga_patna")
    assert ev is not None
    assert ev.domain_id == "ganga_patna"
    assert ev.evidence_classification == SAREvidenceClassification.UNAVAILABLE
    assert ev.delta_threshold_db == -3.0


# ==============================================================================
# 5. FastAPI Async Endpoints Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_13_api_get_scenes():
    """Verify GET /api/v1/sar/scenes endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/sar/scenes?domain_id=ganga_patna")
    assert res.status_code == 200
    data = res.json()
    assert data["total_discovered"] >= 2
    assert "provenance" in data


@pytest.mark.asyncio
async def test_14_api_post_discover():
    """Verify POST /api/v1/sar/discover endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/sar/discover", json={"domain_id": "deep_mumbai_mithi", "limit": 5})
    assert res.status_code == 200
    data = res.json()
    assert data["domain_id"] == "deep_mumbai_mithi"
    assert len(data["scenes"]) >= 2


@pytest.mark.asyncio
async def test_15_api_post_acquire_dry_run():
    """Verify POST /api/v1/sar/acquire endpoint in dry-run mode."""
    payload = {
        "scene_ids": ["S1A_IW_GRDH_1SDV_20170829T010248_20170829T010313_018131_01E74F_E820"],
        "dry_run": True,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/sar/acquire", json=payload)
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert "job_id" in data


@pytest.mark.asyncio
async def test_16_api_get_coverage():
    """Verify GET /api/v1/sar/coverage endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/sar/coverage")
    assert res.status_code == 200
    data = res.json()
    assert len(data["supported_domains"]) == 5
    assert "deep_mumbai_mithi" in data["supported_domains"]


@pytest.mark.asyncio
async def test_17_api_get_evidence_domain():
    """Verify GET /api/v1/sar/evidence/{domain_id} endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/sar/evidence/brahmaputra_guwahati")
    assert res.status_code == 200
    data = res.json()
    assert data["domain_id"] == "brahmaputra_guwahati"
    assert data["evidence_classification"] == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_18_api_get_metadata_scene():
    """Verify GET /api/v1/sar/metadata/{scene_id} endpoint."""
    scene_id = "S1A_IW_GRDH_1SDV_20170817T010248_20170817T010313_017956_01E202_67C3"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/sar/metadata/{scene_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["scene_id"] == scene_id
    assert data["platform"] == "Sentinel-1A"
    assert data["orbit_direction"] == "DESCENDING"
    assert data["acquisition_status"] in ("VERIFIED_TARGET", "ACQUIRED")


@pytest.mark.asyncio
async def test_19_api_unknown_domain_404():
    """Verify 400/404 error handling for unrecognized domain."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/sar/evidence/unknown_domain_xyz")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_20_oauth2_token_exchange_flow(sar_provider, monkeypatch):
    """Verify OAuth2 client credentials token exchange handles missing and unconfigured credentials safely."""
    monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
    monkeypatch.delenv("CDSE_CLIENT_SECRET", raising=False)

    success, msg, token = await sar_provider.exchange_oauth2_token()
    assert success is False
    assert "not configured" in msg.lower()
    assert token is None


def test_21_configured_credentials_distinguished_from_authenticated(sar_provider, monkeypatch):
    """Verify configured credentials report CONFIGURED_UNAUTHENTICATED and never assume upstream success."""
    monkeypatch.setenv("CDSE_TOKEN", "mock_token_value_xyz")
    creds = sar_provider.check_credentials()

    assert creds["credentials_configured"] is True
    assert creds["operational_status"] == "CONFIGURED_UNAUTHENTICATED"
    # Verify the secret token is NOT leaked in the status response
    assert "mock_token_value_xyz" not in str(creds)


def test_22_corrupted_archive_cannot_be_marked_acquired(tmp_path, sar_provider):
    """Verify a corrupted or fake large archive cannot transition to ACQUIRED without passing validation."""
    fake_zip = tmp_path / "fake_archive.zip"
    fake_zip.write_bytes(b"PK\x03\x04" + b"0" * 105_000_000)

    is_valid, msg, _ = sar_provider.validate_scene_archive(fake_zip)
    assert is_valid is False
    assert "incomplete safe structure" in msg.lower() or "corrupted" in msg.lower()
