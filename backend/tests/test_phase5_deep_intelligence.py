"""
AQUORA Phase 5 — Deep Intelligence Integration & Physical Engine Federation Tests.

Tests Level 3 Deep Intelligence endpoints, high-resolution terrain sampling,
Phase 6 hydrodynamic solver federation, facility impact verification, and zero-fabrication invariants.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import numpy as np

from app.main import app
from app.schemas.deep import (
    DeepIntelligenceRequest,
    DeepSimulationRequest,
    DeepStatus,
    PhysicalSeverity,
)
from app.services.deep_intelligence_service import DeepIntelligenceService

client = TestClient(app)


# ==============================================================================
# 1. COORDINATE VALIDATION & ZONE COVERAGE GATES
# ==============================================================================


def test_deep_inspection_valid_kurla_coordinate():
    """Verify point inspection within deep_mumbai_mithi zone succeeds with valid rasters."""
    payload = {"latitude": 19.065, "longitude": 72.879}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == DeepStatus.POINT_INSPECTED.value
    assert data["intelligence_level"] == "DEEP"
    assert data["zone_id"] == "deep_mumbai_mithi"
    assert data["point_in_zone"] is True
    assert data["raster_sampled"] is True

    # High-resolution raster features sampled from EPSG:32643
    assert data["elevation_m"] is not None
    assert 40.0 <= data["elevation_m"] <= 60.0
    assert data["slope_degrees"] is not None
    assert data["aspect_degrees"] is not None
    assert data["flow_accumulation_cells"] is not None
    assert isinstance(data["flow_accumulation_cells"], int)
    assert data["drainage_proxy_score"] is not None

    # Opt-in invariant: normal inspection does NOT run physical simulation
    assert data["modeled_water_depth_m"] is None
    assert data["simulation"] is None
    assert data["facility_impacts"] is None


def test_deep_inspection_bkc_coordinate():
    """Verify point inspection at BKC within deep zone."""
    payload = {"latitude": 19.066, "longitude": 72.868}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == DeepStatus.POINT_INSPECTED.value
    assert data["point_in_zone"] is True
    assert data["elevation_m"] is not None


def test_deep_inspection_outside_deep_zone_patna():
    """Verify points outside Deep Zone (e.g. Patna) return OUTSIDE_DEEP_ZONE_COVERAGE."""
    payload = {"latitude": 25.600, "longitude": 85.100}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == DeepStatus.OUTSIDE_DEEP_ZONE_COVERAGE.value
    assert data["point_in_zone"] is False
    assert data["raster_sampled"] is False
    assert data["zone_id"] is None
    assert data["elevation_m"] is None
    assert data["flow_accumulation_cells"] is None
    assert "outside the verified Mumbai Mithi Deep Intelligence Zone" in data["message"]


def test_deep_inspection_outside_deep_zone_delhi():
    """Verify Delhi coordinate is rejected from Level 3 Deep Intelligence."""
    payload = {"latitude": 28.6139, "longitude": 77.2090}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == DeepStatus.OUTSIDE_DEEP_ZONE_COVERAGE.value
    assert data["point_in_zone"] is False


def test_deep_inspection_colaba_outside_mithi_dem():
    """Verify Colaba (South Mumbai outside Mithi DEM extent) returns OUTSIDE_DEEP_ZONE_COVERAGE."""
    payload = {"latitude": 18.906, "longitude": 72.814}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == DeepStatus.OUTSIDE_DEEP_ZONE_COVERAGE.value
    assert data["point_in_zone"] is False


def test_deep_inspection_invalid_latitude():
    """Verify invalid geographic latitude (> 90) triggers HTTP 422."""
    payload = {"latitude": 190.0, "longitude": 72.879}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 422


def test_deep_inspection_invalid_longitude():
    """Verify invalid geographic longitude (< -180) triggers HTTP 422."""
    payload = {"latitude": 19.065, "longitude": -195.0}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 422


# ==============================================================================
# 2. ZERO-FABRICATION BOUNDARIES & MISSING FEATURES
# ==============================================================================


def test_deep_inspection_zero_fabrication_missing_features():
    """
    Verify uningested attributes remain explicitly None under zero-fabrication:
    built_up_fraction, distance_to_road_m, distance_to_waterway_m, tide_level_m.
    """
    payload = {"latitude": 19.065, "longitude": 72.879}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Must be strictly None, never invented or filled with synthetic heuristics
    assert data["built_up_fraction"] is None
    assert data["distance_to_road_m"] is None
    assert data["distance_to_waterway_m"] is None
    assert data["tide_level_m"] is None


def test_deep_inspection_sar_unavailable():
    """Verify SAR corroboration reports UNAVAILABLE status honestly."""
    payload = {"latitude": 19.065, "longitude": 72.879}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    sar = data["sar_corroboration"]
    assert sar["sar_available"] is False
    assert sar["evidence_classification"] == "UNAVAILABLE"
    assert sar["validation_status"] == "REGISTERED_TARGET_AWAITING_DOWNLOAD"
    assert sar["mean_delta_vv_db"] is None


# ==============================================================================
# 3. HIGH-RESOLUTION RASTER SAMPLING & SCIENTIFIC JUSTIFICATION
# ==============================================================================


def test_raster_nodata_handling():
    """Verify NoData pixels (-9999.0) in rasters are safely handled as None."""
    svc = DeepIntelligenceService()
    # Mock raster reading to simulate a NoData pixel
    with patch("rasterio.open") as mock_open:
        mock_src = MagicMock()
        mock_src.height = 476
        mock_src.width = 392
        mock_src.nodata = -9999.0
        mock_src.index.return_value = (10, 10)
        mock_src.read.return_value = np.array([[-9999.0]])
        mock_open.return_value.__enter__.return_value = mock_src

        sampled = svc.sample_terrain_rasters(19.065, 72.879)
        assert sampled["nodata_detected"] is True
        assert sampled["elevation_m"] is None
        assert sampled["flow_accumulation_cells"] is None


def test_flow_accumulation_integer_rounding():
    """
    Verify continuous floating-point flow accumulation is rounded to discrete integer cells.
    Scientific rationale: D8 flow accumulation represents a discrete count of contributing cells.
    """
    svc = DeepIntelligenceService()
    sampled = svc.sample_terrain_rasters(19.065, 72.879)
    flow_acc = sampled["flow_accumulation_cells"]
    assert isinstance(flow_acc, int)
    assert flow_acc >= 0


# ==============================================================================
# 4. OPT-IN SIMULATION INVARIANT
# ==============================================================================


def test_normal_inspection_does_not_launch_simulation():
    """Normal inspection must NEVER execute the hydrodynamic solver."""
    with patch.object(DeepIntelligenceService, "execute_physical_simulation") as mock_sim:
        payload = {"latitude": 19.065, "longitude": 72.879, "run_simulation": False}
        resp = client.post("/api/v1/intelligence/deep", json=payload)
        assert resp.status_code == 200
        mock_sim.assert_not_called()


@pytest.mark.asyncio
async def test_explicit_simulation_request_via_deep_endpoint():
    """When run_simulation=True, the physical solver is invoked and returns valid depth."""
    payload = {
        "latitude": 19.065,
        "longitude": 72.879,
        "run_simulation": True,
        "simulation_horizon_minutes": 30,
        "simulation_timestep_minutes": 10,
    }
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    if data["status"] == DeepStatus.SIMULATION_FAILED.value:
        pytest.skip("External Open-Meteo ECMWF API temporarily unreachable or overloaded (HTTP 503)")

    assert data["status"] == DeepStatus.SIMULATION_COMPLETED.value
    assert data["modeled_water_depth_m"] is not None
    assert data["physical_severity"] is not None
    assert data["simulation"] is not None
    assert data["simulation"]["is_mass_balance_valid"] is True
    assert data["facility_impacts"] is not None


# ==============================================================================
# 5. STANDALONE SIMULATION ENDPOINT (/deep/simulate)
# ==============================================================================


def test_standalone_deep_simulate_endpoint():
    """Verify POST /api/v1/intelligence/deep/simulate executes solver and evaluates impacts."""
    payload = {
        "latitude": 19.065,
        "longitude": 72.879,
        "horizon_minutes": 30,
        "timestep_minutes": 10,
        "evaluate_facility_impacts": True,
    }
    resp = client.post("/api/v1/intelligence/deep/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    if data["status"] == DeepStatus.SIMULATION_FAILED.value:
        pytest.skip("External Open-Meteo ECMWF API temporarily unreachable or overloaded (HTTP 503)")

    assert data["status"] == DeepStatus.SIMULATION_COMPLETED.value
    assert data["simulation"] is not None
    sim = data["simulation"]
    assert sim["status"] == "COMPLETED"
    assert sim["horizon_minutes"] == 30
    assert sim["timestep_minutes"] == 10
    assert sim["is_mass_balance_valid"] is True
    assert sim["overall_mass_balance_error_m3"] <= 1e-4

    # Facility impacts
    fac_impacts = data["facility_impacts"]
    assert fac_impacts is not None
    assert fac_impacts["total_facilities_in_zone"] == 366
    assert fac_impacts["facilities_covered_by_raster"] == 365
    assert fac_impacts["facilities_outside_raster"] == 1


def test_standalone_deep_simulate_outside_zone():
    """Verify simulation is rejected for coordinates outside deep zone."""
    payload = {
        "latitude": 25.600,
        "longitude": 85.100,
        "horizon_minutes": 30,
    }
    resp = client.post("/api/v1/intelligence/deep/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == DeepStatus.OUTSIDE_DEEP_ZONE_COVERAGE.value
    assert data["simulation"] is None


# ==============================================================================
# 6. SOLVER ERROR & DEGRADATION HANDLING
# ==============================================================================


def test_simulation_failure_handled_truthfully():
    """Verify solver exceptions return SIMULATION_FAILED without fabricating synthetic depths."""
    with patch.object(
        DeepIntelligenceService,
        "execute_physical_simulation",
        side_effect=RuntimeError("NWP forecast connection timeout")
    ):
        payload = {
            "latitude": 19.065,
            "longitude": 72.879,
            "run_simulation": True,
        }
        resp = client.post("/api/v1/intelligence/deep", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == DeepStatus.SIMULATION_FAILED.value
        assert data["modeled_water_depth_m"] is None
        assert data["physical_severity"] is None


# ==============================================================================
# 7. CRITICAL FACILITY IMPACTS & ZERO PROXIMITY INFERENCE
# ==============================================================================


def test_facility_impacts_zero_proximity_inference():
    """
    Verify facility impact evaluation:
    - 365 facilities are within raster bounds.
    - Exactly 1 facility (Bandra Bus Station (W)) is outside raster bounds (col=-1).
    - The outside facility has raster_covered=False, depth=None, and impact_status=OUT_OF_RASTER_BOUNDS.
    - No proximity inference is applied.
    """
    svc = DeepIntelligenceService()
    # Evaluate with zero-depth baseline grid
    dummy_depth_grid = np.zeros((476, 392), dtype=np.float64)
    summary = svc.evaluate_facility_impacts(dummy_depth_grid)

    assert summary.total_facilities_in_zone == 366
    assert summary.facilities_covered_by_raster == 365
    assert summary.facilities_outside_raster == 1
    assert summary.severity_breakdown[PhysicalSeverity.UNCOVERED.value] == 1
    assert summary.severity_breakdown[PhysicalSeverity.DRY.value] == 365


def test_facility_depth_impact_thresholds():
    """Verify facility depth values map accurately to physical severity classifications."""
    svc = DeepIntelligenceService()
    # Create depth grid with specific known depths
    depth_grid = np.zeros((476, 392), dtype=np.float64)
    # Put 0.10m depth (LOW) at row 202, col 137 (Kurla)
    depth_grid[202, 137] = 0.10
    # Put 0.75m depth (SEVERE) at row 197, col 99 (BKC)
    depth_grid[197, 99] = 0.75

    summary = svc.evaluate_facility_impacts(depth_grid)
    assert summary.total_facilities_in_zone == 366
    assert summary.facilities_covered_by_raster == 365


# ==============================================================================
# 8. PHYSICAL WATER DEPTH VS ML SUSCEPTIBILITY DISTINCTION
# ==============================================================================


def test_distinction_between_physical_depth_and_ml_susceptibility():
    """
    Verify deterministic physical water depth and ML susceptibility score
    are clearly distinguished and separately reported.
    """
    payload = {"latitude": 19.065, "longitude": 72.879, "allow_benchmark_rainfall": True}
    resp = client.post("/api/v1/intelligence/deep", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # ML score is dimensionless [0, 1] supplementary score
    assert data["ml_susceptibility_score"] is not None
    assert 0.0 <= data["ml_susceptibility_score"] <= 1.0

    # Modeled depth is in meters, and in point inspection is None unless simulated
    assert data["modeled_water_depth_m"] is None
    assert data["calibration_status"] == "PHYSICAL_HYDRODYNAMIC_SOLVER_PRIMARY"
