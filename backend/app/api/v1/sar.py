"""
AQUORA 2.0 — Sentinel-1 SAR REST API Endpoints.

Provides versioned endpoints (/api/v1/sar) for:
- Scene discovery & catalog search
- Asynchronous safe acquisition job submission & status polling
- Bitemporal SAR preprocessing and flood candidate evidence generation
- Pilot domain flood evidence retrieval
- Geographic coverage and readiness audit

Adheres to:
- FastAPI background job execution conventions
- Zero-fabrication error handling (HTTP 404 for unknown domains / missing scenes)
- Strict non-disclosure of provider authentication secrets
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.schemas.sar import (
    SARAcquisitionRequest,
    SARCoverageResponse,
    SARDiscoveryRequest,
    SARDiscoveryResponse,
    SAREvidenceResponse,
    SARJobResponse,
    SARProcessingRequest,
    SARSceneMetadata,
)
from app.services.india_sar_service import IndiaSARService

router = APIRouter(prefix="/sar", tags=["Sentinel-1 SAR Flood Ingestion"])
sar_service = IndiaSARService()


@router.get(
    "/scenes",
    response_model=SARDiscoveryResponse,
    summary="Discover Sentinel-1 Scenes (Query Params)",
)
async def list_sar_scenes(
    domain_id: Optional[str] = Query(None, description="Pilot river domain ID (e.g. ganga_patna, deep_mumbai_mithi)"),
    orbit_direction: Optional[str] = Query(None, description="Filter by orbit direction: DESCENDING or ASCENDING"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of scenes to return"),
) -> SARDiscoveryResponse:
    """Discover verified Sentinel-1 GRD IW scenes matching query filters."""
    try:
        req = SARDiscoveryRequest(domain_id=domain_id, orbit_direction=orbit_direction, limit=limit)
        return await sar_service.discover_scenes(req)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/discover",
    response_model=SARDiscoveryResponse,
    summary="Discover Sentinel-1 Scenes (POST Body)",
)
async def discover_sar_scenes_post(
    req: SARDiscoveryRequest,
) -> SARDiscoveryResponse:
    """Discover verified Sentinel-1 GRD IW scenes matching detailed spatial/temporal envelope."""
    try:
        return await sar_service.discover_scenes(req)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.post(
    "/acquire",
    response_model=SARJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Bounded SAR Acquisition Job",
)
async def submit_sar_acquisition(
    req: SARAcquisitionRequest,
    background_tasks: BackgroundTasks,
) -> SARJobResponse:
    """
    Submit an asynchronous acquisition job.
    In dry_run mode, validates targets against catalog without downloading binaries.
    """
    job_res = await sar_service.submit_acquisition_job(req)
    return job_res


@router.get(
    "/jobs/{job_id}",
    response_model=SARJobResponse,
    summary="Get SAR Job Status",
)
async def get_sar_job_status(
    job_id: str,
) -> SARJobResponse:
    """Poll execution status and scene results of an asynchronous acquisition or processing job."""
    res = sar_service.get_job_status(job_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"SAR job '{job_id}' not found")
    return res


@router.get(
    "/jobs",
    response_model=List[SARJobResponse],
    summary="List All SAR Jobs",
)
async def list_sar_jobs() -> List[SARJobResponse]:
    """List all tracked acquisition and processing jobs."""
    return sar_service.list_jobs()


@router.post(
    "/process",
    response_model=SAREvidenceResponse,
    summary="Process Bitemporal SAR Pair into Flood Evidence",
)
async def process_sar_bitemporal_pair(
    req: SARProcessingRequest,
) -> SAREvidenceResponse:
    """
    Process pre-event and co-event Sentinel-1 pair into candidate flood evidence.
    Enforces geometric compatibility and quality masking.
    """
    try:
        return await sar_service.process_bitemporal_pair(req)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get(
    "/evidence/{domain_id}",
    response_model=SAREvidenceResponse,
    summary="Get Flood Candidate Evidence for Domain",
)
async def get_domain_sar_evidence(
    domain_id: str,
) -> SAREvidenceResponse:
    """
    Fetch derived flood candidate evidence for a pilot domain.
    Returns explicit UNAVAILABLE state if unacquired or unverified (Zero Fabrication).
    """
    ev = sar_service.get_evidence(domain_id)
    if not ev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain '{domain_id}' not recognized. Supported: {sar_service.get_supported_domains()}",
        )
    return ev


@router.get(
    "/metadata/{scene_id}",
    response_model=SARSceneMetadata,
    summary="Get Scene Asset Metadata",
)
async def get_scene_metadata(
    scene_id: str,
) -> SARSceneMetadata:
    """Retrieve full metadata for a specific Sentinel-1 SAFE scene."""
    data = sar_service.provider.VERIFIED_CATALOGUE.get(scene_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene_id}' not found in verified catalogue",
        )

    # Check if file exists locally
    local_path = None
    status_val = "VERIFIED_TARGET"
    repo_root = Path(__file__).resolve().parents[4]
    candidate = repo_root / "data" / "raw" / "phase7" / "sentinel1" / data.get("event_id", "") / f"{scene_id}.zip"
    if candidate.exists() and candidate.stat().st_size > 100_000_000:
        is_valid, _, _ = sar_service.provider.validate_scene_archive(candidate)
        if is_valid:
            local_path = str(candidate)
            status_val = "ACQUIRED"

    return SARSceneMetadata(
        scene_id=scene_id,
        event_id=data.get("event_id"),
        domain_id=data.get("domain_id"),
        role=data.get("role", "OBSERVATION"),
        platform=data.get("platform", "Sentinel-1A"),
        product_type=data.get("product_type", "GRD"),
        sensor_mode=data.get("sensor_mode", "IW"),
        polarizations=data.get("polarizations", ["VV", "VH"]),
        orbit_direction=data["orbit_direction"],
        relative_orbit=data.get("relative_orbit"),
        start_time_utc=data["start_time_utc"],
        stop_time_utc=data["stop_time_utc"],
        bbox=data["bbox"],
        download_url=data.get("download_url"),
        file_size_bytes=data.get("file_size_bytes"),
        sha256=data.get("sha256"),
        acquisition_status=status_val,
        local_path=local_path,
    )


@router.get(
    "/coverage",
    response_model=SARCoverageResponse,
    summary="Get India-Wide SAR Coverage Overview",
)
async def get_sar_coverage_overview() -> SARCoverageResponse:
    """Overview of supported river domains, bounding boxes, and scene catalog status."""
    return sar_service.get_coverage_overview()
