"""
AQUORA Consolidated Completion Execution 2 — End-to-End Integration & Working Demo Test Suite.

Verifies:
1. Root & Health APIs (Liveness, Readiness, Metadata).
2. Geographic Hierarchy & Location Navigation (India -> State -> Basin -> City -> Catchment).
3. Capability Governance (Strict isolation of Deep Zone to Mumbai Mithi).
4. National Screening (11 features extracted, uncalibrated status, out-of-bounds rejection).
5. Regional Watershed Intelligence (14 features, HydroBASINS Ganga/Brahmaputra/Godavari/Narmada, honest None handling).
6. Deep Intelligence & Physical Solver Primacy (30m DEM sampling, 366 critical facilities).
7. Unsupported Deep Zone Rejection without silent fallback.
8. Kaggle Readiness & Ground Truth Gate (BLOCKED_BY_GROUND_TRUTH enforced).
"""

import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.intelligence_contracts import IntelligenceLevel, CapabilityStatus

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_root_and_health_endpoints():
    """Verify backend starts and returns metadata and health status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Root
        root_resp = await client.get("/")
        assert root_resp.status_code == 200
        root_data = root_resp.json()
        assert "AQUORA" in root_data["name"]
        assert "/docs" in root_data["docs"]

        # Health live
        live_resp = await client.get("/api/v1/health/live")
        assert live_resp.status_code == 200
        assert live_resp.json()["status"] == "ok"

        # Health ready
        ready_resp = await client.get("/api/v1/health/ready")
        assert ready_resp.status_code in [200, 503]
        assert ready_resp.json()["status"] in ["ok", "degraded"]


@pytest.mark.asyncio
async def test_geographic_hierarchy_navigation():
    """Verify geographic discovery across India, states, basins, city, and catchment."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List all locations
        resp = await client.get("/api/v1/locations")
        assert resp.status_code == 200
        locations = resp.json()
        codes = [loc["entity_code"] for loc in locations]

        # Verify key entities present
        assert "IN" in codes
        assert "IN-MH" in codes
        assert "IN-MH-MUMBAI" in codes
        assert "CATCH-MITHI-01" in codes
        assert "BASIN-GANGA" in codes
        assert "BASIN-BRAHMAPUTRA" in codes
        assert "BASIN-GODAVARI" in codes
        assert "BASIN-NARMADA" in codes

        # Filter by entity_type=BASIN
        basin_resp = await client.get("/api/v1/locations?entity_type=BASIN")
        assert basin_resp.status_code == 200
        basin_data = basin_resp.json()
        assert len(basin_data) >= 4

        # Location detail for Ganga Basin
        ganga_resp = await client.get("/api/v1/locations/BASIN-GANGA")
        assert ganga_resp.status_code == 200
        ganga_data = ganga_resp.json()
        assert ganga_data["name"] == "Ganga River Basin"
        assert ganga_data["intelligence_level"] == "REGIONAL"

        # Location detail for Mumbai
        mum_resp = await client.get("/api/v1/locations/IN-MH-MUMBAI")
        assert mum_resp.status_code == 200
        mum_data = mum_resp.json()
        assert mum_data["name"] == "Mumbai"
        assert "CATCH-MITHI-01" in mum_data["child_codes"]

        # 404 for unknown location
        unknown_resp = await client.get("/api/v1/locations/NON_EXISTENT_ZONE")
        assert unknown_resp.status_code == 404


@pytest.mark.asyncio
async def test_capabilities_and_deep_zone_isolation():
    """Verify capabilities correctly reflect active tiers and restrict Deep Zone to Mumbai."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Mumbai capability: DEEP is available
        mum_caps = await client.get("/api/v1/intelligence/capabilities?location_code=IN-MH-MUMBAI")
        assert mum_caps.status_code == 200
        mum_data = mum_caps.json()
        assert mum_data["capabilities"]["deep_intelligence"] == "AVAILABLE"
        assert "deep_mumbai_mithi" in mum_data["deep_zone_ids"]

        # Ganga Basin capability: REGIONAL is available, DEEP is NOT_AVAILABLE
        ganga_caps = await client.get("/api/v1/intelligence/capabilities?location_code=BASIN-GANGA")
        assert ganga_caps.status_code == 200
        ganga_data = ganga_caps.json()
        assert ganga_data["capabilities"]["national_screening"] == "AVAILABLE"
        assert ganga_data["capabilities"]["regional_intelligence"] == "AVAILABLE"
        assert ganga_data["capabilities"]["deep_intelligence"] == "NOT_AVAILABLE"
        assert len(ganga_data["deep_zone_ids"]) == 0

        # Generic city (e.g. Patna / Delhi): DEEP is NOT_AVAILABLE
        patna_caps = await client.get("/api/v1/intelligence/capabilities?location_code=PATNA")
        assert patna_caps.status_code == 200
        patna_data = patna_caps.json()
        assert patna_data["capabilities"]["deep_intelligence"] == "NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_national_screening_point_and_bounds_rejection():
    """Verify National Screening extracts 11 features and rejects out-of-bounds coordinates."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Valid point within India (Patna: 25.60, 85.15)
        payload = {
            "latitude": 25.60,
            "longitude": 85.15,
            "allow_benchmark_rainfall": True,
        }
        resp = await client.post("/api/v1/intelligence/screening/national", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["READY", "MODEL_NOT_TRAINED"]
        assert data["calibration_status"] == "UNCALIBRATED_MACRO_SCREENING"
        assert len(data["features_used"]) == 11
        assert "rainfall_24h_mm" in data["feature_values"]
        assert "elevation_m" in data["feature_values"]
        assert "distance_to_river_m" in data["feature_values"]

        # 2. Out-of-bounds point outside India (London: 51.50, -0.12)
        oob_payload = {
            "latitude": 51.50,
            "longitude": -0.12,
            "allow_benchmark_rainfall": True,
        }
        oob_resp = await client.post("/api/v1/intelligence/screening/national", json=oob_payload)
        assert oob_resp.status_code == 200
        oob_data = oob_resp.json()
        assert oob_data["status"] == "OUTSIDE_COVERAGE"
        assert oob_data["resolved_zone"] == "OUTSIDE_INDIA_EXTENT"
        assert oob_data["features_used"] is None
        assert "outside" in oob_data["message"].lower()


@pytest.mark.asyncio
async def test_regional_watershed_intelligence_and_honest_missing_data():
    """Verify Regional Intelligence evaluates 14 features and reports uningested features as None."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Valid point in Ganga basin (Patna: 25.60, 85.15)
        payload = {
            "latitude": 25.60,
            "longitude": 85.15,
            "allow_benchmark_rainfall": True,
        }
        resp = await client.post("/api/v1/intelligence/regional", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "HEURISTIC_AVAILABLE"
        assert data["basin_id"] == "BASIN-GANGA"
        assert len(data["features_used"]) == 14
        assert data["feature_values"]["elevation_m"] is not None

        # Verify honest zero-fabrication: uningested regional features remain None
        assert data["feature_values"]["population_density_per_km2"] is None
        assert data["critical_facilities_count"] is None
        assert "UNCALIBRATED" in data["calibration_status"]

        # 2. Basin hydrographic summary endpoint
        summary_resp = await client.get("/api/v1/intelligence/regional/basins/BASIN-GANGA")
        assert summary_resp.status_code == 200
        summary_data = summary_resp.json()
        assert summary_data["basin_name"] == "Ganga River Basin"
        assert summary_data["drainage_area_km2"] > 800_000

        # 3. Non-basin coordinate rejection (Arabian Sea: 12.0, 70.0)
        sea_payload = {
            "latitude": 12.0,
            "longitude": 70.0,
            "allow_benchmark_rainfall": True,
        }
        sea_resp = await client.post("/api/v1/intelligence/regional", json=sea_payload)
        assert sea_resp.status_code == 200
        sea_data = sea_resp.json()
        assert sea_data["status"] == "OUTSIDE_REGIONAL_COVERAGE"


@pytest.mark.asyncio
async def test_deep_intelligence_point_sampling_and_unsupported_rejection():
    """Verify Deep Intelligence samples 30m rasters in Mumbai Mithi and rejects unsupported requests without fallback."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Valid Kurla coordinate in Mumbai Mithi Deep Zone
        kurla_payload = {
            "latitude": 19.0728,
            "longitude": 72.8826,
            "allow_benchmark_rainfall": True,
        }
        resp = await client.post("/api/v1/intelligence/deep", json=kurla_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "POINT_INSPECTED"
        assert data["point_in_zone"] is True
        assert data["raster_sampled"] is True
        assert data["elevation_m"] is not None
        assert data["slope_degrees"] is not None
        assert data["aspect_degrees"] is not None
        assert data["flow_accumulation_cells"] is not None
        assert data["drainage_proxy_score"] is not None
        assert data["critical_facilities_count"] == 366

        # 2. Unsupported coordinate (Patna: 25.60, 85.15) -> MUST reject without fallback to Mumbai
        patna_payload = {
            "latitude": 25.60,
            "longitude": 85.15,
            "allow_benchmark_rainfall": True,
        }
        patna_resp = await client.post("/api/v1/intelligence/deep", json=patna_payload)
        assert patna_resp.status_code == 200
        patna_data = patna_resp.json()
        assert patna_data["status"] == "OUTSIDE_DEEP_ZONE_COVERAGE"
        assert patna_data["point_in_zone"] is False
        assert patna_data["raster_sampled"] is False
        assert patna_data["elevation_m"] is None
        assert patna_data["critical_facilities_count"] is None
        assert "outside the verified Mumbai Mithi Deep Intelligence Zone" in patna_data["message"]


@pytest.mark.asyncio
async def test_kaggle_readiness_and_training_gate_artifacts():
    """Verify Kaggle manifest, notebook, and ground truth gate are properly emitted and enforced."""
    manifest_file = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase7_kaggle_dataset_manifest.json"
    assert manifest_file.exists(), "Kaggle dataset manifest missing!"

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["governance_gate"]["decision"] == "BLOCKED_BY_GROUND_TRUTH"
    assert manifest["governance_gate"]["supervised_training_permitted"] is False
    assert len(manifest["feature_specification"]["core_11_predictors"]) == 11
    assert "flood_label" in manifest["feature_specification"]["forbidden_leakage_columns"]

    notebook_file = PROJECT_ROOT / "notebooks" / "aquora_national_screening_kaggle.ipynb"
    assert notebook_file.exists(), "Kaggle notebook missing!"

    with open(notebook_file, "r", encoding="utf-8") as f:
        nb = json.load(f)

    assert nb["nbformat"] == 4
    assert len(nb["cells"]) >= 10
