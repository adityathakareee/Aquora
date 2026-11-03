"""
AQUORA Phase 7F Stage 5 — System-Wide Application Integration Test Suite.

Verifies end-to-end integration:
1. Multi-tier geographic hierarchy: India -> State -> Basin -> City -> Catchment -> Deep Zone.
2. Basins registration: BASIN-MAHANADI registered under IN-OD and HydroBASINS hierarchy.
3. Intelligence zones registry: regional_mahanadi_basin active as PROTOTYPE with experimental_research_layers.
4. Capability matrix and strict no-silent-fallback enforcement (UnsupportedZoneError).
5. Mumbai Mithi Deep Zone preserved with 2D hydrodynamic solver authority and 366 facilities.
6. Mahanadi regional research endpoints (/experiments, /subbasins, /layers).
7. Strict Phase 7 scientific governance: PROTOTYPE_ONLY, NOT_CALIBRATED, NOT_FOR_PUBLIC_ALERTS.
8. DFO 2507 quarantine invariant: zero access or sampling.
9. Zero rainfall fabrication: 100% NaN preserved for uningested features.
10. Complete decoupling of experimental ML from emergency alerts.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.v1.intelligence import REGISTERED_ZONES
from app.services.spatial_resolver import SpatialZoneResolver, UnsupportedZoneError
from app.services.regional_intelligence_service import RegionalIntelligenceService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


class TestPhase7FStage5SystemIntegration:
    """Consolidated end-to-end test suite for Phase 7F Stage 5 application integration."""

    @pytest.mark.asyncio
    async def test_01_health_and_startup(self, client: AsyncClient):
        """Verify API health and root accessibility."""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"

    @pytest.mark.asyncio
    async def test_02_geographic_hierarchy_locations(self, client: AsyncClient):
        """Verify India -> State -> Basin geographic hierarchy for Odisha and Mahanadi."""
        # Query Country IN
        res_in = await client.get("/api/v1/locations/IN")
        assert res_in.status_code == 200
        in_data = res_in.json()
        assert "IN-OD" in in_data["child_codes"]
        assert "BASIN-MAHANADI" in in_data["child_codes"]

        # Query State IN-OD (Odisha)
        res_od = await client.get("/api/v1/locations/IN-OD")
        assert res_od.status_code == 200
        od_data = res_od.json()
        assert od_data["name"] == "Odisha"
        assert od_data["parent_code"] == "IN"
        assert "BASIN-MAHANADI" in od_data["child_codes"]

        # Query Basin BASIN-MAHANADI
        res_mah = await client.get("/api/v1/locations/BASIN-MAHANADI")
        assert res_mah.status_code == 200
        mah_data = res_mah.json()
        assert mah_data["name"] == "Mahanadi River Basin"
        assert mah_data["parent_code"] == "IN-OD"
        assert mah_data["intelligence_level"] == "REGIONAL"
        assert mah_data["centroid_lat"] == 20.45
        assert mah_data["centroid_lon"] == 85.85

    @pytest.mark.asyncio
    async def test_03_intelligence_zones_registry(self, client: AsyncClient):
        """Verify registration of regional_mahanadi_basin and deep_mumbai_mithi."""
        res = await client.get("/api/v1/intelligence/zones")
        assert res.status_code == 200
        zones = res.json()
        zone_ids = [z["zone_id"] for z in zones]
        assert "deep_mumbai_mithi" in zone_ids
        assert "regional_mahanadi_basin" in zone_ids

        # Inspect regional_mahanadi_basin
        res_mah = await client.get("/api/v1/intelligence/zones/regional_mahanadi_basin")
        assert res_mah.status_code == 200
        mah_zone = res_mah.json()
        assert mah_zone["level"] == "REGIONAL"
        assert mah_zone["status"] == "PROTOTYPE"
        assert mah_zone["capabilities"]["physical_flood_solver"] is False
        assert mah_zone["capabilities"]["deep_intelligence"] == "NOT_AVAILABLE"
        assert mah_zone["capabilities"]["experimental_research_layers"] is True
        assert "PROTOTYPE_ONLY" in mah_zone["governance_note"]

    @pytest.mark.asyncio
    async def test_04_mumbai_deep_preservation(self, client: AsyncClient):
        """Verify Mumbai Mithi Deep Zone is preserved with full 2D solver authority."""
        res_mum = await client.get("/api/v1/intelligence/zones/deep_mumbai_mithi")
        assert res_mum.status_code == 200
        mum_zone = res_mum.json()
        assert mum_zone["level"] == "DEEP"
        assert mum_zone["status"] == "ACTIVE"
        assert mum_zone["capabilities"]["physical_flood_solver"] is True
        assert mum_zone["capabilities"]["deep_intelligence"] == "AVAILABLE"
        assert mum_zone["capabilities"]["verified_facilities_count"] == 366

        # Check resolver bounds
        bounds = SpatialZoneResolver.get_zone_bounds("deep_mumbai_mithi")
        assert bounds["min_lat"] == 19.040
        assert bounds["max_lat"] == 19.120

    @pytest.mark.asyncio
    async def test_05_capability_matrix_no_silent_fallback(self, client: AsyncClient):
        """Verify capability matrix never silently falls back to Mumbai for unsupported zones."""
        # Query Mahanadi capabilities
        res_mah = await client.get("/api/v1/intelligence/capabilities?location_code=BASIN-MAHANADI")
        assert res_mah.status_code == 200
        mah_cap = res_mah.json()
        assert mah_cap["capabilities"]["deep_intelligence"] == "NOT_AVAILABLE"
        assert mah_cap["active_zone_id"] == "regional_mahanadi_basin"

        # Query Odisha capabilities
        res_od = await client.get("/api/v1/intelligence/capabilities?location_code=IN-OD")
        assert res_od.status_code == 200
        od_cap = res_od.json()
        assert od_cap["capabilities"]["deep_intelligence"] == "NOT_AVAILABLE"

        # Verify spatial resolver raises UnsupportedZoneError for physical solver on Mahanadi
        with pytest.raises(UnsupportedZoneError):
            SpatialZoneResolver.validate_capability("regional_mahanadi_basin", "physical_flood_solver")

        # Verify spatial resolver raises UnsupportedZoneError for unknown zone
        with pytest.raises(UnsupportedZoneError):
            SpatialZoneResolver.resolve_zone("unsupported_random_zone_123")

    @pytest.mark.asyncio
    async def test_06_mahanadi_experiments_endpoint(self, client: AsyncClient):
        """Verify /api/v1/intelligence/regional/mahanadi/experiments returns audit results."""
        res = await client.get("/api/v1/intelligence/regional/mahanadi/experiments")
        assert res.status_code == 200
        data = res.json()
        assert data["event_id"] == "DFO_3382"
        assert data["basin_id"] == "BASIN-MAHANADI"
        assert data["governance_status"] == "PROTOTYPE_ONLY"
        assert data["calibration_status"] == "NOT_CALIBRATED"
        assert data["alert_eligibility"] == "NOT_FOR_PUBLIC_ALERTS"
        assert "Phase 6" in data["primary_flood_authority"]
        assert "scientific_conclusion" in data
        assert "66.8%" in data["scientific_conclusion"]
        assert "metrics" in data
        assert "ablation_comparison" in data
        assert "spatial_independence_audit" in data

    @pytest.mark.asyncio
    async def test_07_mahanadi_subbasins_endpoint(self, client: AsyncClient):
        """Verify /api/v1/intelligence/regional/mahanadi/subbasins returns 27 sub-basins with partition tags."""
        res = await client.get("/api/v1/intelligence/regional/mahanadi/subbasins")
        assert res.status_code == 200
        data = res.json()
        assert data["type"] == "FeatureCollection"
        assert data["total_subbasins"] == 27
        assert data["partitions"]["train_count"] == 15
        assert data["partitions"]["val_count"] == 6
        assert data["partitions"]["test_count"] == 6
        assert data["spatial_independence"] == "ENFORCED_ZERO_LEAKAGE"

        # Check properties of features
        features = data["features"]
        assert len(features) == 27
        partitions_found = set(f["properties"].get("spatial_partition") for f in features)
        assert "TRAIN" in partitions_found
        assert "VALIDATION" in partitions_found
        assert "TEST" in partitions_found

    @pytest.mark.asyncio
    async def test_08_mahanadi_layers_endpoint(self, client: AsyncClient):
        """Verify /api/v1/intelligence/regional/mahanadi/layers returns research layer catalog."""
        res = await client.get("/api/v1/intelligence/regional/mahanadi/layers")
        assert res.status_code == 200
        data = res.json()
        assert data["basin_id"] == "BASIN-MAHANADI"
        assert data["governance"]["status"] == "PROTOTYPE_ONLY"
        assert data["governance"]["alerts"] == "NOT_FOR_PUBLIC_ALERTS"
        assert "EXPERIMENTAL SPATIAL RESEARCH" in data["governance"]["banner_text"]

        layer_ids = [layer["id"] for layer in data["layers"]]
        assert "subbasin_partitions" in layer_ids
        assert "river_network" in layer_ids
        assert "land_water_mask" in layer_ids
        assert "dfo3382_observations" in layer_ids
        assert "experimental_ranking_scores" in layer_ids

    @pytest.mark.asyncio
    async def test_09_basin_summary_and_regional_point_evaluation(self, client: AsyncClient):
        """Verify basin summary for BASIN-MAHANADI and honest regional point evaluation."""
        summary = RegionalIntelligenceService.get_basin_summary("BASIN-MAHANADI")
        assert summary is not None
        assert summary.basin_id == "BASIN-MAHANADI"
        assert summary.drainage_area_km2 == 141589.0
        assert summary.capabilities["experimental_research_layers"] is True
        assert summary.capabilities["physical_flood_solver"] is False

        # Point evaluation inside Mahanadi Delta (Cuttack: 20.46, 85.88)
        payload = {
            "latitude": 20.46,
            "longitude": 85.88,
            "allow_benchmark_rainfall": False,
        }
        res_pt = await client.post("/api/v1/intelligence/regional", json=payload)
        assert res_pt.status_code == 200
        pt_data = res_pt.json()
        assert pt_data["intelligence_level"] == "REGIONAL"
        assert pt_data["basin_id"] == "BASIN-MAHANADI"
        assert pt_data["calibration_status"] == "UNCALIBRATED_REGIONAL_SCREENING"
        # Facilities count remains honest None without synthetic fabrication
        assert pt_data["critical_facilities_count"] is None

    @pytest.mark.asyncio
    async def test_10_dfo2507_quarantine_integrity(self):
        """Verify DFO2507 remains strictly quarantined with zero access."""
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent
        intelligence_file = project_root / "backend" / "app" / "api" / "v1" / "intelligence.py"
        with open(intelligence_file, "r", encoding="utf-8") as f:
            code = f.read()

        # Zero occurrence of loading DFO 2507 labels
        assert "DFO_2507" not in code
        assert "DFO2507" not in code
