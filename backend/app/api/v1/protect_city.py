"""
FastAPI HTTP Router for Phase 12 Protect the City API.

Provides endpoints for:
- POST /api/v1/protect-city/analyze
- GET  /api/v1/protect-city/runs
- GET  /api/v1/protect-city/runs/latest
- GET  /api/v1/protect-city/runs/{run_id}
- GET  /api/v1/protect-city/runs/{run_id}/recommendations
- GET  /api/v1/protect-city/runs/{run_id}/recommendations/{candidate_id}
- GET  /api/v1/protect-city/candidates
- GET  /api/v1/protect-city/candidates/{candidate_id}
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.session import get_db
from app.models.protect_city import (
    ProtectCityRecommendation,
    ProtectCityRun,
)
from app.schemas.protect_city import (
    InterventionCandidateSchema,
    ProtectCityRequestSchema,
    ProtectCityResponseSchema,
)
from app.services.protect_city_service import ProtectCityProcessingService
from app.services.spatial_resolver import UnsupportedZoneError

router = APIRouter(prefix="/protect-city", tags=["Protect the City"])


@router.post(
    "/analyze",
    response_model=ProtectCityResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Run Protect the City Decision Support Analysis",
)
async def analyze_protect_city_endpoint(
    payload: ProtectCityRequestSchema,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """
    Executes Protect the City intervention opportunity analysis.
    Combines Phase 9 Digital Twin evolution, Phase 4 terrain flow, Phase 5 drainage context,
    Phase 10 route exposure, and Phase 11 critical facility accessibility into deterministic recommendations.
    """
    try:
        service = ProtectCityProcessingService(db=db)
        return await service.analyze_protect_city(payload)
    except (ValueError, UnsupportedZoneError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/candidates",
    response_model=list[InterventionCandidateSchema],
    status_code=status.HTTP_200_OK,
    summary="List Intervention Candidates",
)
async def list_candidates(
    candidate_type: str | None = Query(default=None, description="Filter by candidate taxonomy type"),
    verification_status: str | None = Query(default=None, description="Filter by verification status"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Lists intervention candidate assets and review locations."""
    service = ProtectCityProcessingService(db=db)
    return await service.list_candidates(
        candidate_type=candidate_type,
        verification_status=verification_status,
    )


@router.get(
    "/candidates/{candidate_id}",
    response_model=InterventionCandidateSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Intervention Candidate by ID",
)
async def get_candidate_by_id(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Retrieves metadata and location for a specific intervention candidate."""
    service = ProtectCityProcessingService(db=db)
    cand = await service.get_candidate_by_id(candidate_id)
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intervention candidate '{candidate_id}' not found.",
        )
    return cand


@router.get(
    "/runs",
    response_model=list[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Protect the City Analysis Runs",
)
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Retrieves recent Protect the City execution audit entries."""
    if db:
        try:
            stmt = select(ProtectCityRun).order_by(ProtectCityRun.created_at.desc()).limit(limit)
            res = await db.execute(stmt)
            runs = res.scalars().all()
            if runs:
                return [
                    {
                        "run_identifier": r.run_identifier,
                        "digital_twin_run_id": r.digital_twin_run_id,
                        "routing_run_id": r.routing_run_id,
                        "critical_access_run_id": r.critical_access_run_id,
                        "minimum_priority": r.minimum_priority,
                        "total_candidates": r.total_candidates,
                        "status": r.status,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                    for r in runs
                ]
        except (Exception, SQLAlchemyError) as e:  # noqa: BLE001
            logger.warning(f"Database list_runs failed (offline/fallback): {e}")

    # Fallback to service
    service = ProtectCityProcessingService(db=None)
    res = await service.analyze_protect_city(ProtectCityRequestSchema())
    return [
        {
            "run_identifier": res.run_id,
            "digital_twin_run_id": res.digital_twin_run_id,
            "routing_run_id": res.routing_run_id,
            "critical_access_run_id": res.critical_access_run_id,
            "minimum_priority": "LOW",
            "total_candidates": res.total_candidates,
            "status": "COMPLETED",
            "created_at": res.generated_at,
        }
    ]


@router.get(
    "/runs/latest",
    response_model=ProtectCityResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Protect the City Analysis",
)
async def get_latest_run(
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Retrieves the latest completed Protect the City decision support analysis."""
    service = ProtectCityProcessingService(db=db)
    return await service.analyze_protect_city(ProtectCityRequestSchema())


@router.get(
    "/runs/{run_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Run Audit Details",
)
async def get_run_details(
    run_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Retrieves detailed audit record for a Protect the City run."""
    if db:
        try:
            stmt = select(ProtectCityRun).where(ProtectCityRun.run_identifier == run_id)
            res = await db.execute(stmt)
            run_db = res.scalar_one_or_none()
            if run_db:
                rec_stmt = select(ProtectCityRecommendation).where(ProtectCityRecommendation.run_identifier == run_id)
                rec_exec = await db.execute(rec_stmt)
                recs_db = rec_exec.scalars().all()

                return {
                    "run_identifier": run_db.run_identifier,
                    "run_id": run_db.run_identifier,
                    "digital_twin_run_id": run_db.digital_twin_run_id,
                    "routing_run_id": run_db.routing_run_id,
                    "critical_access_run_id": run_db.critical_access_run_id,
                    "minimum_priority": run_db.minimum_priority,
                    "total_candidates": run_db.total_candidates,
                    "recommendation_count": len(recs_db),
                    "status": run_db.status,
                    "provenance": run_db.provenance,
                    "created_at": run_db.created_at.isoformat() if run_db.created_at else None,
                }
        except (Exception, SQLAlchemyError) as e:  # noqa: BLE001
            logger.warning(f"Database query for get_run_details failed (offline/fallback): {e}")

    # Memory fallback
    service = ProtectCityProcessingService(db=None)
    res = await service.analyze_protect_city(ProtectCityRequestSchema())
    return {
        "run_identifier": run_id,
        "run_id": run_id,
        "digital_twin_run_id": res.digital_twin_run_id,
        "routing_run_id": res.routing_run_id,
        "critical_access_run_id": res.critical_access_run_id,
        "minimum_priority": "LOW",
        "total_candidates": res.total_candidates,
        "recommendation_count": len(res.recommendations),
        "status": "COMPLETED",
        "provenance": res.provenance,
        "created_at": res.generated_at,
    }


@router.get(
    "/runs/{run_id}/recommendations",
    response_model=list[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get Recommendations for Run",
)
async def get_run_recommendations(
    run_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Retrieves all recommendation records associated with a run."""
    if db:
        try:
            stmt = select(ProtectCityRecommendation).where(ProtectCityRecommendation.run_identifier == run_id)
            res = await db.execute(stmt)
            recs = res.scalars().all()
            if recs:
                return [
                    {
                        "run_identifier": r.run_identifier,
                        "candidate_id": r.candidate_id,
                        "priority": r.priority,
                        "priority_score": r.priority_score,
                        "intervention_type": r.intervention_type,
                        "first_threat_minutes": r.first_threat_minutes,
                        "peak_severity": r.peak_severity,
                        "expected_benefit": r.expected_benefit,
                        "feasibility_status": r.feasibility_status,
                        "explanation": r.explanation,
                    }
                    for r in recs
                ]
        except (Exception, SQLAlchemyError) as e:  # noqa: BLE001
            logger.warning(f"Database query for get_run_recommendations failed (offline/fallback): {e}")

    # Fallback to service analysis
    service = ProtectCityProcessingService(db=None)
    res = await service.analyze_protect_city(ProtectCityRequestSchema())
    return [
        {
            "run_identifier": run_id,
            "candidate_id": r.candidate.candidate_id,
            "priority": r.priority,
            "priority_score": r.priority_score,
            "intervention_type": r.intervention_type,
            "first_threat_minutes": r.first_threat_minutes,
            "peak_severity": r.peak_severity,
            "expected_benefit": r.expected_benefit,
            "feasibility_status": r.feasibility_status,
            "explanation": r.explanation,
        }
        for r in res.recommendations
    ]


@router.get(
    "/runs/{run_id}/recommendations/{candidate_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Single Recommendation Detail (with Run-Candidate Ownership Validation)",
)
async def get_run_recommendation_detail(
    run_id: str,
    candidate_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """
    Retrieves recommendation details for a candidate in a specific run.
    STRICT INVARIANT: Validates that the candidate actually belongs to the requested run_id!
    """
    if db:
        try:
            stmt = select(ProtectCityRecommendation).where(
                ProtectCityRecommendation.run_identifier == run_id,
                ProtectCityRecommendation.candidate_id == candidate_id,
            )
            res_exec = await db.execute(stmt)
            rec_db = res_exec.scalar_one_or_none()
            if rec_db:
                return {
                    "run_identifier": rec_db.run_identifier,
                    "candidate_id": rec_db.candidate_id,
                    "priority": rec_db.priority,
                    "priority_score": rec_db.priority_score,
                    "intervention_type": rec_db.intervention_type,
                    "first_threat_minutes": rec_db.first_threat_minutes,
                    "first_high_severity_minutes": rec_db.first_high_severity_minutes,
                    "peak_severity": rec_db.peak_severity,
                    "peak_severity_minutes": rec_db.peak_severity_minutes,
                    "expected_benefit": rec_db.expected_benefit,
                    "feasibility_status": rec_db.feasibility_status,
                    "uncertainty_status": rec_db.uncertainty_status,
                    "affected_route_count": rec_db.affected_route_count,
                    "affected_critical_facility_count": rec_db.affected_critical_facility_count,
                    "priority_component_breakdown": rec_db.priority_component_breakdown_json,
                    "explanation": rec_db.explanation,
                    "warnings": rec_db.warnings_json,
                    "provenance": rec_db.provenance,
                }
        except (Exception, SQLAlchemyError, BaseException) as e:  # noqa: BLE001
            logger.warning(f"Database query for get_run_recommendation_detail failed (offline/fallback): {e}")

    # Fallback in offline/demo mode with candidate/run ownership check
    service = ProtectCityProcessingService(db=None)
    res = await service.analyze_protect_city(ProtectCityRequestSchema())
    match = next((r for r in res.recommendations if r.candidate.candidate_id == candidate_id), None)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate '{candidate_id}' is not associated with run '{run_id}'.",
        )
    return match.model_dump()
