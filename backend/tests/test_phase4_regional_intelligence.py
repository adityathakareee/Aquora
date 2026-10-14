"""
AQUORA Phase 4 — Regional Flood Intelligence & Watershed Risk Test Suite.

Comprehensive verification of:
1. Exact 14-feature regional governance (11 Core National + 3 Regional Expansion).
2. Deep-zone feature isolation & rejection of prohibited hydraulic leakage columns.
3. Zero-fabrication demographic resolution via IndiaPopulationService.
4. Authentic critical facility counts (366 for Mumbai/Mithi; None with provenance elsewhere).
5. RegionalBasinModel registry integration, untrained PLANNED status, and uncalibrated screening index calculation.
6. API Endpoints:
   - POST /api/v1/intelligence/regional (single-point evaluation)
   - POST /api/v1/intelligence/regional/batch (bounded batch processing, 250 max limit)
   - GET /api/v1/intelligence/regional/basins/{basin_id} (basin metadata & capabilities)
7. Strict Phase 6 physical hydraulic solver isolation.
8. Compatibility with National (Level 1) and Deep (Level 3) registries.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.schemas.intelligence_contracts import IntelligenceLevel
from app.schemas.regional import (
    BasinSummaryResponse,
    RegionalBatchItem,
    RegionalBatchRequest,
    RegionalIntelligenceRequest,
    RegionalStatus,
)
from app.services.india_population_service import IndiaPopulationService
from app.services.india_spatial_service import IndiaSpatialService
from app.services.ml_model_registry import FloodModelRegistry, RegionalBasinModel
from app.services.regional_intelligence_service import RegionalIntelligenceService

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_registry():
    FloodModelRegistry._registry.clear()
    FloodModelRegistry._initialized = False
    FloodModelRegistry.initialize()
    yield
    FloodModelRegistry._registry.clear()
    FloodModelRegistry._initialized = False
    FloodModelRegistry.initialize()


EXPECTED_14_FEATURES = [
    "rainfall_1h_mm",
    "rainfall_3h_mm",
    "rainfall_6h_mm",
    "rainfall_24h_mm",
    "rainfall_72h_mm",
    "rainfall_anomaly_index",
    "elevation_m",
    "slope_deg",
    "distance_to_river_m",
    "historical_flood_frequency",
    "landcover_class",
    "basin_drainage_area_km2",
    "soil_saturation_index",
    "population_density_per_km2",
]

PROHIBITED_COLUMNS = [
    "flow_accumulation_cells",
    "drainage_proxy_score",
    "built_up_fraction",
    "distance_to_road_m",
    "distance_to_waterway_m",
    "tide_level_m",
    "water_depth_m",
    "flow_velocity_ms",
    "modeled_depth_m",
    "sar_delta_vv_db",
    "flood_label",
    "candidate_flood_label",
]


class TestPhase4RegionalIntelligence:
    """Test suite for Level 2 Regional Flood Intelligence."""

    def test_regional_14_features_governance(self):
        """Verify that RegionalBasinModel evaluates exactly the 14 authorized features."""
        model = RegionalBasinModel()
        assert model.FEATURE_NAMES == EXPECTED_14_FEATURES
        assert len(model.FEATURE_NAMES) == 14

    @pytest.mark.parametrize("col", PROHIBITED_COLUMNS)
    def test_rejection_of_leakage_and_deep_zone_columns(self, col):
        """RegionalBasinModel must strictly raise ValueError if forbidden columns are provided."""
        model = RegionalBasinModel()
        features = {f: 1.0 for f in EXPECTED_14_FEATURES}
        features[col] = 42.0

        with pytest.raises(ValueError, match="Forbidden columns detected"):
            model.predict_risk(features)

    def test_zero_fabrication_population_service(self):
        """Confirm IndiaPopulationService returns None with explicit provenance when uningested."""
        assert IndiaPopulationService.is_available() is False

        # In-extent query (Ganga basin)
        density, prov = IndiaPopulationService.get_population_density(25.6, 85.1)
        assert density is None
        assert prov["status"] == "UNAVAILABLE"
        assert "UNINGESTED" in prov["source"]

        # Out-of-extent query
        density_out, prov_out = IndiaPopulationService.get_population_density(0.0, 0.0)
        assert density_out is None
        assert prov_out["status"] == "OUTSIDE_INDIA_EXTENT"

    def test_zero_fabrication_critical_facilities(self):
        """Mumbai/Mithi reports authentic 366 facilities; other basins report None with provenance."""
        service = RegionalIntelligenceService()

        # 1. Ganga basin point (Patna)
        req_ganga = RegionalIntelligenceRequest(
            latitude=25.6,
            longitude=85.1,
            allow_benchmark_rainfall=True,
        )
        res_ganga = service.evaluate_point(req_ganga)
        assert res_ganga.basin_id == "BASIN-GANGA"
        assert res_ganga.critical_facilities_count is None
        assert res_ganga.provenance["critical_facilities_provenance"] == "CRITICAL_FACILITIES_UNINGESTED"

        # 2. Mumbai Mithi basin point
        req_mithi = RegionalIntelligenceRequest(
            latitude=19.076,
            longitude=72.877,
            allow_benchmark_rainfall=True,
        )
        res_mithi = service.evaluate_point(req_mithi)
        assert res_mithi.basin_id == "BASIN-MITHI"
        assert res_mithi.critical_facilities_count == 366
        assert "AUTHENTIC" in res_mithi.provenance["critical_facilities_provenance"]

    def test_regional_model_untrained_status(self):
        """Default RegionalBasinModel must be untrained with is_ready=False and None probability."""
        model = FloodModelRegistry.get_model(IntelligenceLevel.REGIONAL)
        assert model.status == "PLANNED"
        assert model.intelligence_level == IntelligenceLevel.REGIONAL

        features = {f: 1.0 for f in EXPECTED_14_FEATURES}
        result = model.predict_risk(features)
        assert result["is_ready"] is False
        assert result["predicted_probability"] is None
        assert result["calibration_status"] == "UNCALIBRATED_REGIONAL_SCREENING"

    def test_regional_model_heuristic_screening_computation(self):
        """Calculates bounded uncalibrated watershed exposure screening index when inputs exist."""
        model = RegionalBasinModel()
        features = {
            "rainfall_24h_mm": 50.0,
            "soil_saturation_index": 0.5,
            "distance_to_river_m": 500.0,
            "slope_deg": 2.0,
        }
        res = model.predict_risk(features)
        assert res["is_ready"] is False
        assert res["predicted_probability"] is None
        assert res["watershed_exposure_index"] is not None
        assert 0.0 <= res["watershed_exposure_index"] <= 1.0
        assert res["exposure_grade"] in ["LOW", "MEDIUM", "HIGH"]
        assert "uncalibrated" in res["message"].lower()

    def test_regional_model_heuristic_missing_rainfall(self):
        """When rainfall is missing (None), index must be None and grade UNCALIBRATED."""
        model = RegionalBasinModel()
        features = {
            "rainfall_24h_mm": None,
            "soil_saturation_index": None,
            "distance_to_river_m": 500.0,
            "slope_deg": 2.0,
        }
        res = model.predict_risk(features)
        assert res["watershed_exposure_index"] is None
        assert res["exposure_grade"] == "UNCALIBRATED"

    def test_api_regional_point_in_ganga(self):
        """POST /api/v1/intelligence/regional for Patna point returns valid response."""
        response = client.post(
            "/api/v1/intelligence/regional",
            json={
                "latitude": 25.6,
                "longitude": 85.1,
                "allow_benchmark_rainfall": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["basin_id"] == "BASIN-GANGA"
        assert data["intelligence_level"] == "REGIONAL"
        assert len(data["features_used"]) == 14
        assert "flow_accumulation_cells" not in data["feature_values"]
        assert data["status"] in [RegionalStatus.READY.value, RegionalStatus.HEURISTIC_AVAILABLE.value]

    def test_api_regional_point_outside_coverage(self):
        """POST /api/v1/intelligence/regional for point in sea returns OUTSIDE_REGIONAL_COVERAGE."""
        response = client.post(
            "/api/v1/intelligence/regional",
            json={
                "latitude": 10.0,
                "longitude": 60.0,  # Arabian Sea outside Indian river basins
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == RegionalStatus.OUTSIDE_REGIONAL_COVERAGE.value
        assert data["basin_id"] is None
        assert data["feature_values"] is None

    def test_api_regional_batch_limit_250_accepted(self):
        """POST /api/v1/intelligence/regional/batch with exactly 250 points is accepted."""
        points = [
            {"point_id": f"pt_{i}", "latitude": 25.6, "longitude": 85.1}
            for i in range(250)
        ]
        response = client.post(
            "/api/v1/intelligence/regional/batch",
            json={"points": points, "allow_benchmark_rainfall": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 250
        assert len(data["results"]) == 250

    def test_api_regional_batch_limit_251_rejected(self):
        """POST /api/v1/intelligence/regional/batch with 251 points is rejected with HTTP 422/400."""
        points = [
            {"point_id": f"pt_{i}", "latitude": 25.6, "longitude": 85.1}
            for i in range(251)
        ]
        response = client.post(
            "/api/v1/intelligence/regional/batch",
            json={"points": points},
        )
        assert response.status_code in [400, 422]

    def test_api_basin_summary_success(self):
        """GET /api/v1/intelligence/regional/basins/BASIN-GANGA returns verified summary."""
        response = client.get("/api/v1/intelligence/regional/basins/BASIN-GANGA")
        assert response.status_code == 200
        data = response.json()
        assert data["basin_id"] == "BASIN-GANGA"
        assert data["basin_name"] == "Ganga River Basin"
        assert data["operational_status"] == "ACTIVE"
        assert data["drainage_area_km2"] == 861452.0
        assert "IN-UP" in data["major_states"]
        assert data["capabilities"]["regional_intelligence"] == "AVAILABLE"

    def test_api_basin_summary_not_found(self):
        """GET /api/v1/intelligence/regional/basins/NONEXISTENT returns HTTP 404."""
        response = client.get("/api/v1/intelligence/regional/basins/BASIN-UNKNOWN-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_physics_engine_isolation(self):
        """Confirm Phase 6 deterministic physical solver is NEVER invoked during regional intelligence."""
        import inspect
        from app.services.regional_intelligence_service import RegionalIntelligenceService
        service_src = inspect.getsource(RegionalIntelligenceService)
        model = RegionalBasinModel()

        # Prohibited hydraulic variables must never be in predictor feature names
        assert "water_depth_m" not in model.FEATURE_NAMES
        assert "flow_velocity_ms" not in model.FEATURE_NAMES
        assert "modeled_depth_m" not in model.FEATURE_NAMES

        # Physics solver classes must never be referenced or imported
        assert "WeshFluidEngine" not in service_src
        assert "HydrodynamicEngine" not in service_src
        assert "MithiPhysicsEngine" not in service_src

    def test_national_and_deep_model_isolation_in_registry(self):
        """Ensure registering RegionalBasinModel preserves National and Mumbai/Mithi routing."""
        mumbai_model = FloodModelRegistry.get_model(IntelligenceLevel.DEEP, "deep_mumbai_mithi")
        assert mumbai_model.intelligence_level == IntelligenceLevel.DEEP

        national_model = FloodModelRegistry.get_model(IntelligenceLevel.NATIONAL, "national_india")
        assert national_model.intelligence_level == IntelligenceLevel.NATIONAL

        regional_model = FloodModelRegistry.get_model(IntelligenceLevel.REGIONAL, "regional_ganga_basin")
        assert regional_model.intelligence_level == IntelligenceLevel.REGIONAL

        models = FloodModelRegistry.list_models()
        levels = {m["intelligence_level"] for m in models}
        assert "NATIONAL" in levels
        assert "REGIONAL" in levels
        assert "DEEP" in levels
