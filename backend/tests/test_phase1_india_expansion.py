"""
AQUORA 2.0 Phase 1 India-Wide Expansion Automated Test Suite.

Verifies:
1. Multi-tier Geographic Hierarchy (India -> State -> City -> Catchment)
2. Intelligence Zones and capability reporting (AVAILABLE, FUTURE, NOT_AVAILABLE)
3. Standardized Multi-tier Data Contracts (National, Regional, Deep)
4. Versioned ML Feature Schema (aquora_ml_feature_schema_v1)
5. ML Model Registry abstraction and Mumbai XGBoost model preservation
6. API Endpoints (/api/v1/locations and /api/v1/intelligence)
7. Non-fabrication invariants
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.geographic import GeographicEntity, IntelligenceZone
from app.schemas.intelligence_contracts import (
    AQUORA_ML_FEATURE_SCHEMA_V1,
    CapabilityStatus,
    DeepDataContract,
    EntityType,
    IntelligenceLevel,
    MLFeatureTier,
    NationalDataContract,
    RegionalDataContract,
)
from app.services.ml_model_registry import (
    BaseFloodModel,
    FloodModelRegistry,
    MumbaiMithiDeepModel,
    NationalScreeningModelPlaceholder,
)


# ==============================================================================
# 1. DATA CONTRACTS & VALIDATION
# ==============================================================================

def test_national_data_contract_validation():
    """Verify National Data Contract enforces required macro-scale predictors."""
    payload = {
        "latitude": 19.076,
        "longitude": 72.8777,
        "elevation_m": 12.5,
        "slope_deg": 2.1,
        "distance_to_river_m": 450.0,
        "rainfall_1h_mm": 15.0,
        "rainfall_3h_mm": 35.0,
        "rainfall_6h_mm": 60.0,
        "rainfall_24h_mm": 120.0,
        "rainfall_72h_mm": 250.0,
        "rainfall_anomaly_index": 2.4,
        "historical_flood_frequency_score": 0.85,
        "landcover_class": 50,
    }
    contract = NationalDataContract(**payload)
    assert contract.elevation_m == 12.5
    assert contract.rainfall_24h_mm == 120.0


def test_regional_data_contract_inheritance():
    """Verify Regional Data Contract extends National contract with basin fields."""
    payload = {
        "latitude": 19.076,
        "longitude": 72.8777,
        "elevation_m": 12.5,
        "slope_deg": 2.1,
        "distance_to_river_m": 450.0,
        "rainfall_1h_mm": 15.0,
        "rainfall_3h_mm": 35.0,
        "rainfall_6h_mm": 60.0,
        "rainfall_24h_mm": 120.0,
        "rainfall_72h_mm": 250.0,
        "rainfall_anomaly_index": 2.4,
        "historical_flood_frequency_score": 0.85,
        "landcover_class": 50,
        "basin_id": "BASIN-MITHI",
        "basin_name": "Mithi River Basin",
        "soil_saturation_index": 0.78,
        "population_density_per_km2": 21000.0,
    }
    contract = RegionalDataContract(**payload)
    assert contract.basin_name == "Mithi River Basin"
    assert contract.soil_saturation_index == 0.78


def test_deep_data_contract_inheritance():
    """Verify Deep Data Contract supports micro-scale physical attributes."""
    payload = {
        "latitude": 19.076,
        "longitude": 72.8777,
        "elevation_m": 12.5,
        "slope_deg": 2.1,
        "distance_to_river_m": 450.0,
        "rainfall_1h_mm": 15.0,
        "rainfall_3h_mm": 35.0,
        "rainfall_6h_mm": 60.0,
        "rainfall_24h_mm": 120.0,
        "rainfall_72h_mm": 250.0,
        "rainfall_anomaly_index": 2.4,
        "historical_flood_frequency_score": 0.85,
        "landcover_class": 50,
        "basin_id": "BASIN-MITHI",
        "flow_accumulation_cells": 12400,
        "drainage_proxy_score": 3.8,
        "built_up_fraction": 0.92,
        "distance_to_road_m": 15.0,
        "distance_to_waterway_m": 85.0,
        "tide_level_m": 4.1,
        "modeled_depth_m": 0.65,
    }
    contract = DeepDataContract(**payload)
    assert contract.flow_accumulation_cells == 12400
    assert contract.modeled_depth_m == 0.65


# ==============================================================================
# 2. VERSIONED ML FEATURE GOVERNANCE SCHEMA
# ==============================================================================

def test_ml_feature_schema_integrity():
    """Verify versioned schema distinguishes core national vs deep features."""
    schema = AQUORA_ML_FEATURE_SCHEMA_V1
    assert schema["schema_name"] == "aquora_ml_feature_schema_v1"
    assert schema["schema_version"] == "1.0.0"

    features = schema["features"]
    feature_names = [f["name"] for f in features]
    assert "rainfall_1h_mm" in feature_names
    assert "elevation_m" in feature_names
    assert "flow_accumulation_cells" in feature_names

    # Check tier categorization
    deep_exclusive = [
        f for f in features if f["tier"] == MLFeatureTier.DEEP_ZONE_EXCLUSIVE.value
    ]
    deep_names = [f["name"] for f in deep_exclusive]
    assert "flow_accumulation_cells" in deep_names
    assert "drainage_proxy_score" in deep_names
    for f in deep_exclusive:
        assert f["availability_national"] == "UNAVAILABLE"


# ==============================================================================
# 3. MODEL REGISTRY & ABSTRACTION
# ==============================================================================

def test_model_registry_initialization_and_dispatch():
    """Verify FloodModelRegistry routes models without assuming single-model."""
    FloodModelRegistry.initialize()
    models = FloodModelRegistry.list_models()
    assert len(models) >= 2

    # Verify Deep Model retrieval for Mumbai
    deep_model = FloodModelRegistry.get_model(
        level=IntelligenceLevel.DEEP,
        zone_id="deep_mumbai_mithi"
    )
    assert isinstance(deep_model, BaseFloodModel)
    assert deep_model.status == "PROTOTYPE_ONLY"
    assert deep_model.intelligence_level == IntelligenceLevel.DEEP

    # Verify National Model slot exists and operates safely without fabrication
    national_model = FloodModelRegistry.get_model(level=IntelligenceLevel.NATIONAL)
    assert national_model.status in ("PLANNED", "OPERATIONAL")
    with pytest.raises((NotImplementedError, ValueError)):
        national_model.predict_risk({})


# ==============================================================================
# 4. LOCATIONS API ENDPOINTS
# ==============================================================================

@pytest.mark.asyncio
async def test_locations_api_list():
    """Verify /api/v1/locations returns geographic hierarchy entities."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/locations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 4

        codes = [item["entity_code"] for item in data]
        assert "IN" in codes
        assert "IN-MH" in codes
        assert "IN-MH-MUMBAI" in codes
        assert "CATCH-MITHI-01" in codes


@pytest.mark.asyncio
async def test_locations_api_detail_and_404():
    """Verify /api/v1/locations/{code} returns details and 404 for unknown codes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid code
        resp = await client.get("/api/v1/locations/IN-MH-MUMBAI")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Mumbai"
        assert data["entity_type"] == "CITY"
        assert "CATCH-MITHI-01" in data["child_codes"]

        # 404 for unknown
        resp_404 = await client.get("/api/v1/locations/UNKNOWN_PLACE")
        assert resp_404.status_code == 404


# ==============================================================================
# 5. INTELLIGENCE API ENDPOINTS & ZERO FABRICATION
# ==============================================================================

@pytest.mark.asyncio
async def test_intelligence_zones_endpoint():
    """Verify /api/v1/intelligence/zones lists active Mumbai deep zone and planned zones."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/intelligence/zones")
        assert resp.status_code == 200
        zones = resp.json()
        zone_ids = [z["zone_id"] for z in zones]
        assert "deep_mumbai_mithi" in zone_ids
        assert "national_india" in zone_ids

        mumbai_zone = next(z for z in zones if z["zone_id"] == "deep_mumbai_mithi")
        assert mumbai_zone["status"] == "ACTIVE"
        assert mumbai_zone["capabilities"]["physical_flood_solver"] is True


@pytest.mark.asyncio
async def test_intelligence_capabilities_endpoint():
    """Verify /api/v1/intelligence/capabilities returns trustworthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Mumbai -> Full capabilities AVAILABLE
        resp_mum = await client.get("/api/v1/intelligence/capabilities?location_code=IN-MH-MUMBAI")
        assert resp_mum.status_code == 200
        mum_data = resp_mum.json()
        assert mum_data["capabilities"]["deep_intelligence"] == "AVAILABLE"
        assert mum_data["active_zone_id"] == "deep_mumbai_mithi"

        # 2. Unsupported city -> Deep is NOT_AVAILABLE
        resp_other = await client.get("/api/v1/intelligence/capabilities?location_code=IN-KA-BLR")
        assert resp_other.status_code == 200
        other_data = resp_other.json()
        assert other_data["capabilities"]["deep_intelligence"] == "NOT_AVAILABLE"
        assert other_data["active_zone_id"] is None


@pytest.mark.asyncio
async def test_intelligence_feature_schema_and_models_endpoints():
    """Verify feature-schema and models endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_schema = await client.get("/api/v1/intelligence/feature-schema")
        assert resp_schema.status_code == 200
        assert resp_schema.json()["schema_name"] == "aquora_ml_feature_schema_v1"

        resp_models = await client.get("/api/v1/intelligence/models")
        assert resp_models.status_code == 200
        assert len(resp_models.json()) >= 2
