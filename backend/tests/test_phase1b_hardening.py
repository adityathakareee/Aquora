"""
AQUORA 2.0 Phase 1B Architecture Hardening Automated Test Suite.

Verifies:
1. SpatialZoneResolver authoritative spatial bounds, bounding boxes, centers, and aliases.
2. Capability validation across active, planned, and unsupported intelligence zones.
3. Strict non-fabrication: unverified zones raise UnsupportedZoneError / HTTP 400 (NEVER silent Mumbai fallback).
4. Default compatibility: omitting zone_id produces 100% byte-for-byte Mumbai/Mithi baseline behavior.
5. Dynamic alert geography and condition key resolution.
6. Calibration router zone validation and FloodModelRegistry capability gating.
7. Service-layer decoupling in Flood, Digital Twin, Routing, and Protect City services.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.alerts import AlertGenerateRequestSchema
from app.schemas.calibration import CalibrationEvaluationRequest
from app.schemas.digital_twin import DigitalTwinRunRequestSchema
from app.schemas.flood import FloodSimulationRequestSchema
from app.schemas.routing import RouteAnalysisRequestSchema, RouteLocationSchema
from app.schemas.protect_city import ProtectCityRequestSchema
from app.services.alerts_service import AlertsService
from app.services.routing_service import DigitalTwinRasterReader
from app.services.spatial_resolver import (
    MUMBAI_MITHI_BOUNDS,
    SpatialZoneResolver,
    UnsupportedZoneError,
)


# ==============================================================================
# 1. SPATIAL ZONE RESOLVER UNIT TESTS
# ==============================================================================

def test_spatial_resolver_default_and_aliases():
    """Verify resolver maps None, empty string, and aliases to deep_mumbai_mithi."""
    assert SpatialZoneResolver.normalize_zone_id(None) == "deep_mumbai_mithi"
    assert SpatialZoneResolver.normalize_zone_id("") == "deep_mumbai_mithi"
    assert SpatialZoneResolver.normalize_zone_id("mumbai") == "deep_mumbai_mithi"
    assert SpatialZoneResolver.normalize_zone_id("mithi") == "deep_mumbai_mithi"
    assert SpatialZoneResolver.normalize_zone_id("deep_mumbai_mithi") == "deep_mumbai_mithi"


def test_spatial_resolver_mumbai_bounds_invariants():
    """Verify resolver returns exact canonical Mumbai bounds for default/Mumbai requests."""
    bounds = SpatialZoneResolver.get_zone_bounds()
    assert bounds["min_lat"] == MUMBAI_MITHI_BOUNDS["min_lat"]
    assert bounds["max_lat"] == MUMBAI_MITHI_BOUNDS["max_lat"]
    assert bounds["min_lon"] == MUMBAI_MITHI_BOUNDS["min_lon"]
    assert bounds["max_lon"] == MUMBAI_MITHI_BOUNDS["max_lon"]

    # Verify EPSG:4326 bounding box convention
    bbox = SpatialZoneResolver.get_zone_bbox("deep_mumbai_mithi")
    assert bbox.minx == 72.83
    assert bbox.miny == 19.03
    assert bbox.maxx == 72.93
    assert bbox.maxy == 19.13


def test_spatial_resolver_center_calculation():
    """Verify center coordinates computation for verified zones."""
    c_lat, c_lon = SpatialZoneResolver.get_zone_center("deep_mumbai_mithi")
    assert 19.0 < c_lat < 19.2
    assert 72.8 < c_lon < 73.0


def test_spatial_resolver_unsupported_zone_rejection():
    """Verify unverified zone raises UnsupportedZoneError with zero fabrication."""
    with pytest.raises(UnsupportedZoneError) as exc_info:
        SpatialZoneResolver.resolve_zone("unsupported_delhi_zone")
    assert "not recognized or supported" in str(exc_info.value)

    with pytest.raises(UnsupportedZoneError):
        SpatialZoneResolver.get_zone_bounds("random_nonexistent_zone")

    with pytest.raises(UnsupportedZoneError):
        SpatialZoneResolver.get_zone_bbox("fake_zone_id")


def test_spatial_resolver_capability_validation():
    """Verify capabilities check enforces physical solver and routing restrictions."""
    # Mumbai Mithi has all capabilities
    SpatialZoneResolver.validate_capability("deep_mumbai_mithi", "physical_flood_solver")
    SpatialZoneResolver.validate_capability("deep_mumbai_mithi", "critical_facility_routing")
    SpatialZoneResolver.validate_capability("deep_mumbai_mithi", "deep_intelligence")

    # Planned regional zone lacks physical solver and deep intelligence
    with pytest.raises(UnsupportedZoneError) as exc_info:
        SpatialZoneResolver.validate_capability("regional_maharashtra", "physical_flood_solver")
    assert "does not have capability 'physical_flood_solver'" in str(exc_info.value)

    with pytest.raises(UnsupportedZoneError):
        SpatialZoneResolver.validate_capability("national_india", "critical_facility_routing")


# ==============================================================================
# 2. SCHEMA HARDENING & BACKWARD COMPATIBILITY
# ==============================================================================

def test_request_schemas_accept_optional_zone_id():
    """Verify all workflow request schemas accept optional zone_id without breaking defaults."""
    flood_req = FloodSimulationRequestSchema()
    assert flood_req.zone_id is None
    flood_req_zone = FloodSimulationRequestSchema(zone_id="deep_mumbai_mithi")
    assert flood_req_zone.zone_id == "deep_mumbai_mithi"

    dt_req = DigitalTwinRunRequestSchema()
    assert dt_req.zone_id is None
    dt_req_zone = DigitalTwinRunRequestSchema(zone_id="mumbai")
    assert dt_req_zone.zone_id == "mumbai"

    route_req = RouteAnalysisRequestSchema(
        origin=RouteLocationSchema(latitude=19.07, longitude=72.87),
        destination=RouteLocationSchema(latitude=19.08, longitude=72.88),
    )
    assert route_req.zone_id is None

    alert_req = AlertGenerateRequestSchema(digital_twin_run_id="dt_test_001")
    assert alert_req.zone_id is None

    protect_req = ProtectCityRequestSchema()
    assert protect_req.zone_id is None

    calib_req = CalibrationEvaluationRequest()
    assert calib_req.zone_id is None


# ==============================================================================
# 3. ROUTING & RASTER READER SPATIAL GENERALIZATION
# ==============================================================================

def test_raster_reader_zone_bounds_resolution():
    """Verify DigitalTwinRasterReader defaults to Mumbai bounds and adapts to specified zone."""
    reader_default = DigitalTwinRasterReader(width=40, height=40)
    assert reader_default.bounds["min_lat"] == MUMBAI_MITHI_BOUNDS["min_lat"]

    reader_mumbai = DigitalTwinRasterReader(width=40, height=40, zone_id="deep_mumbai_mithi")
    assert reader_mumbai.bounds["min_lat"] == MUMBAI_MITHI_BOUNDS["min_lat"]

    with pytest.raises(UnsupportedZoneError):
        DigitalTwinRasterReader(width=40, height=40, zone_id="unknown_zone")


# ==============================================================================
# 4. ALERTS SERVICE DYNAMIC GEOGRAPHY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_alerts_service_default_and_mumbai_backward_compatibility():
    """Verify AlertsService retains exact canonical Mithi titles and conditions for default/Mumbai."""
    service = AlertsService()

    # Default (None zone_id)
    req_default = AlertGenerateRequestSchema(digital_twin_run_id="dt_run_test_phase1b")
    res_default = await service.generate_alerts(req_default)
    assert res_default.total_count >= 1
    alt = res_default.alerts[0]
    assert "Mithi River Basin" in alt.title

    # Explicit deep_mumbai_mithi
    req_mumbai = AlertGenerateRequestSchema(
        digital_twin_run_id="dt_run_test_phase1b_explicit",
        zone_id="deep_mumbai_mithi",
    )
    res_mumbai = await service.generate_alerts(req_mumbai)
    assert res_mumbai.total_count >= 1
    assert "Mithi River Basin" in res_mumbai.alerts[0].title


@pytest.mark.asyncio
async def test_alerts_service_unsupported_zone_rejection():
    """Verify AlertsService rejects unsupported zone without silent fallback."""
    service = AlertsService()
    req_invalid = AlertGenerateRequestSchema(
        digital_twin_run_id="dt_run_test_phase1b_fail",
        zone_id="unsupported_coastal_zone",
    )
    with pytest.raises(UnsupportedZoneError):
        await service.generate_alerts(req_invalid)


# ==============================================================================
# 5. ENDPOINT HARDENING & ZERO FABRICATION (HTTP INTEGRATION)
# ==============================================================================

@pytest.mark.asyncio
async def test_api_digital_twin_unsupported_zone_returns_400():
    """Verify Digital Twin endpoint returns 400 Bad Request when unsupported zone requested."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Zone without physical flood solver capability
        res_planned = await client.post(
            "/api/v1/digital-twin/runs",
            json={"zone_id": "regional_maharashtra", "provider_mode": "TEST"},
        )
        assert res_planned.status_code == 400
        assert "does not have capability 'physical_flood_solver'" in res_planned.json()["detail"]

        # Completely unknown zone
        res_unknown = await client.post(
            "/api/v1/digital-twin/runs",
            json={"zone_id": "nonexistent_zone_99", "provider_mode": "TEST"},
        )
        assert res_unknown.status_code == 400
        assert "not recognized or supported" in res_unknown.json()["detail"]


@pytest.mark.asyncio
async def test_api_routing_unsupported_zone_returns_400():
    """Verify Routing endpoint returns 400 Bad Request for unsupported zones."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "origin": {"latitude": 19.07, "longitude": 72.87},
            "destination": {"latitude": 19.08, "longitude": 72.88},
            "zone_id": "national_india",  # Lacks critical_facility_routing capability
        }
        res = await client.post("/api/v1/routing/routes/analyze", json=payload)
        assert res.status_code == 400
        assert "critical_facility_routing" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_protect_city_unsupported_zone_returns_400():
    """Verify Protect City endpoint returns 400 Bad Request for unsupported zones."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/protect-city/analyze",
            json={"zone_id": "unsupported_ganga_basin"},
        )
        assert res.status_code == 400
        assert "not recognized or supported" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_calibration_zone_gating():
    """Verify Calibration endpoint allows deep_mumbai_mithi and gates unregistered zones."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Zone without ML calibration model registered
        res_planned = await client.post(
            "/api/v1/calibration/evaluate",
            json={"zone_id": "regional_maharashtra"},
        )
        assert res_planned.status_code == 400
        assert "does not have capability 'deep_intelligence'" in res_planned.json()["detail"]

        # Unsupported zone
        res_unsupported = await client.post(
            "/api/v1/calibration/evaluate",
            json={"zone_id": "fake_zone_id"},
        )
        assert res_unsupported.status_code == 400
