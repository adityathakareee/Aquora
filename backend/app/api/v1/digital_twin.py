"""
FastAPI HTTP API Router for Phase 9 Flood Digital Twin (/api/v1/digital-twin).

Provides endpoints for creating Digital Twin simulation runs, listing runs,
inspecting time slices (0, 30, 60, 90, 120, 150, 180 min), retrieving map-ready spatial layers,
getting run summaries, and inspecting operational cell diagnostics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.digital_twin import (
    CellInspectionResponseSchema,
    DigitalTwinMapSliceResponseSchema,
    DigitalTwinRunRequestSchema,
    DigitalTwinRunResponseSchema,
    DigitalTwinSummarySchema,
    DigitalTwinTimeSliceSchema,
)
from app.services.digital_twin_service import DigitalTwinProcessingService
from app.services.spatial_resolver import UnsupportedZoneError

router = APIRouter(prefix="/digital-twin", tags=["Flood Digital Twin"])


@router.post(
    "/runs",
    response_model=DigitalTwinRunResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create & Execute 0-180 Min Flood Digital Twin Simulation Run"
)
async def create_digital_twin_run(
    payload: DigitalTwinRunRequestSchema,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger end-to-end 0-180 minute Digital Twin run for Mithi River catchment pilot.
    Couples Phase 6 physics engine, Phase 3 rainfall, Phase 4 terrain, Phase 5 drainage, and Phase 8 prototype ML score.
    """
    try:
        service = DigitalTwinProcessingService(db=db)
        return await service.create_run(payload)
    except (UnsupportedZoneError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/runs",
    response_model=list[DigitalTwinRunResponseSchema],
    summary="List Recent Digital Twin Simulation Runs"
)
async def list_digital_twin_runs(db: AsyncSession = Depends(get_db)):
    """List recent Digital Twin simulation runs."""
    service = DigitalTwinProcessingService(db=db)
    run = await service.get_latest_run()
    return [run]


@router.get(
    "/runs/latest",
    response_model=DigitalTwinRunResponseSchema,
    summary="Get Latest Usable Digital Twin Simulation Run"
)
async def get_latest_digital_twin_run(db: AsyncSession = Depends(get_db)):
    """Retrieve the latest completed Digital Twin run for Mithi River catchment."""
    service = DigitalTwinProcessingService(db=db)
    return await service.get_latest_run()


@router.get(
    "/runs/{run_id}",
    response_model=DigitalTwinRunResponseSchema,
    summary="Get Digital Twin Run Metadata by ID"
)
async def get_digital_twin_run_by_id(run_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve Digital Twin run execution details by run ID."""
    service = DigitalTwinProcessingService(db=db)
    return await service.get_run_by_id(run_id)


@router.get(
    "/runs/{run_id}/timeslices",
    response_model=list[DigitalTwinTimeSliceSchema],
    summary="Get All 7 Canonical Time Slices (0 to 180 min)"
)
async def get_digital_twin_timeslices(run_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve the 7 canonical time slices (0, 30, 60, 90, 120, 150, 180 min) with metrics and artifact pointers."""
    service = DigitalTwinProcessingService(db=db)
    run = await service.get_run_by_id(run_id)
    return run.time_slices


@router.get(
    "/runs/{run_id}/summary",
    response_model=DigitalTwinSummarySchema,
    summary="Get Digital Twin Summary & Provenance Metadata"
)
async def get_digital_twin_summary(run_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve summary metrics, peak affected area, max depth, and provenance metadata."""
    service = DigitalTwinProcessingService(db=db)
    run = await service.get_run_by_id(run_id)
    if not run.summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Summary not found for run {run_id}"
        )
    return run.summary


@router.get(
    "/runs/{run_id}/map/{minutes_from_start}",
    response_model=DigitalTwinMapSliceResponseSchema,
    summary="Get Compact Map Raster Artifact Metadata"
)
async def get_digital_twin_map_slice(
    run_id: str,
    minutes_from_start: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve map raster artifact metadata for a specific time slice (0, 30, 60, 90, 120, 150, 180 min).
    No giant per-cell JSON response is produced.
    """
    if minutes_from_start not in [0, 30, 60, 90, 120, 150, 180]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported time slice: {minutes_from_start}. Must be one of [0, 30, 60, 90, 120, 150, 180]."
        )

    service = DigitalTwinProcessingService(db=db)
    run = await service.get_run_by_id(run_id)

    slice_item = next((s for s in run.time_slices if s.minutes_from_start == minutes_from_start), None)
    if not slice_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time slice +{minutes_from_start}m not found."
        )

    return DigitalTwinMapSliceResponseSchema(
        run_id=run_id,
        minutes_from_start=minutes_from_start,
        timestamp_iso=slice_item.timestamp_iso,
        timestamp_ist=slice_item.timestamp_ist,
        artifact_type="MAP_RASTER",
        format="GEOTIFF",
        relative_path=slice_item.artifact_path,
        checksum=None,
        crs="EPSG:4326",
        bounds=[72.840, 19.040, 72.910, 19.120],
        available_status="AVAILABLE",
        affected_area_km2=slice_item.affected_area_km2,
        peak_severity=slice_item.peak_severity,
        cause_explanation=slice_item.cause_explanation,
        scenario_type="DEVELOPMENT SCENARIO",
    )


@router.get(
    "/runs/{run_id}/inspect",
    response_model=CellInspectionResponseSchema,
    summary="Inspect Cell-Level Diagnostics (Zero Training Labels Exposed)"
)
async def inspect_digital_twin_cell(
    run_id: str,
    grid_cell_id: str = Query(..., description="Stable grid cell identifier"),
    minutes_from_start: int = Query(default=60, description="Time slice minutes from start"),
    db: AsyncSession = Depends(get_db)
):
    """
    Inspect operational cell diagnostics (elevation, depth, severity, rainfall, drainage, physical score, prototype ML score, input completeness, uncertainty).
    Strictly isolated from Phase 7 training target labels.
    """
    if not grid_cell_id or not grid_cell_id.startswith("CELL_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid grid_cell_id: {grid_cell_id}. Must start with 'CELL_'."
        )

    service = DigitalTwinProcessingService(db=db)
    return await service.inspect_cell(
        grid_cell_id=grid_cell_id,
        minutes_from_start=minutes_from_start,
        run_id=run_id,
    )
