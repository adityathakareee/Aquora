"""
Unit and Integration Tests for Phase 6 Real Mithi Data Wiring & Provider Mode (Step 3).
"""

import pytest
import os
import numpy as np
from pathlib import Path

from app.schemas.flood import FloodSimulationRequestSchema
from app.services.flood_service import FloodProcessingService
from app.providers.terrain import LocalDEMTerrainProvider
from app.providers.rainfall import IMERGRainfallProvider


@pytest.mark.asyncio
async def test_real_data_mode_selects_local_dem_and_imerg():
    """Verify REAL_DATA mode loads real Copernicus DEM and real IMERG E02 rainfall."""
    service = FloodProcessingService()
    req = FloodSimulationRequestSchema(
        provider_mode="REAL_DATA",
        event_id="E02",
        horizon_minutes=30,
        timestep_minutes=10
    )
    res = await service.execute_simulation(req)
    
    assert res.status == "COMPLETED"
    assert res.provider_mode == "REAL_DATA"
    assert "EPSG" in str(res.provenance["dem_crs"])
    assert res.provenance["dem_dimensions"] == [476, 392]
    assert "elevation_30m.tif" in res.provenance["dem_source"]
    assert "E02_rainfall_30m.tif" in res.provenance["rainfall_source"]
    assert res.provenance["is_synthetic_fallback"] is False


@pytest.mark.asyncio
async def test_real_data_mode_missing_dem_fails_clearly():
    """Verify missing DEM in REAL_DATA mode raises FileNotFoundError (no synthetic fallback)."""
    service = FloodProcessingService()
    req = FloodSimulationRequestSchema(
        provider_mode="REAL_DATA",
        terrain_dataset_id="non_existent_dem_file_99999.tif",
        event_id="E05"
    )
    with pytest.raises(FileNotFoundError) as exc_info:
        await service.execute_simulation(req)
    assert "REAL_DATA mode requires real Copernicus DEM" in str(exc_info.value) or "file not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_real_data_mode_missing_rainfall_fails_clearly():
    """Verify missing event rainfall in REAL_DATA mode raises FileNotFoundError."""
    service = FloodProcessingService()
    req = FloodSimulationRequestSchema(
        provider_mode="REAL_DATA",
        event_id="E999_NON_EXISTENT_EVENT"
    )
    with pytest.raises(FileNotFoundError) as exc_info:
        await service.execute_simulation(req)
    assert "REAL_DATA mode requires real NASA IMERG rainfall file" in str(exc_info.value) or "file not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_synthetic_test_fixtures_still_work():
    """Verify TEST mode still executes using synthetic fixtures for unit testing."""
    service = FloodProcessingService()
    req = FloodSimulationRequestSchema(
        provider_mode="TEST",
        terrain_dataset_id="synthetic_v_valley",
        horizon_minutes=30,
        timestep_minutes=10
    )
    res = await service.execute_simulation(req)
    assert res.status == "COMPLETED"
    assert res.provider_mode == "TEST"
    assert res.provenance["dem_source"] == "TEST FIXTURE ONLY — Synthetic Terrain Generator"
