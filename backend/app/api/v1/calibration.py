"""
Phase 8 Prototype ML Calibration Router.
Exposes read-only XGBoost model metadata and evaluation endpoints.

All responses explicitly carry `model_status: PROTOTYPE_ONLY` and `calibration_status: PROTOTYPE_ONLY`.
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from app.schemas.intelligence_contracts import IntelligenceLevel
from app.schemas.calibration import (
    CalibrationEvaluationRequest,
    CalibrationEvaluationResponse,
)
from app.services.calibration_service import CalibrationService
from app.services.ml_model_registry import FloodModelRegistry
from app.services.spatial_resolver import SpatialZoneResolver, UnsupportedZoneError

router = APIRouter(prefix="/calibration", tags=["Phase 8 — Calibration Prototype"])


@router.get(
    "/metadata",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get XGBoost Prototype Calibration Model Metadata",
    description="Returns read-only metadata, feature schema (16 features), and sha256 checksum for prototype model."
)
def get_calibration_metadata() -> Dict[str, Any]:
    try:
        service = CalibrationService()
        return service.get_model_metadata()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load calibration metadata: {str(e)}"
        ) from e


@router.post(
    "/evaluate",
    response_model=CalibrationEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Read-Only Prototype Calibration Inference",
    description="Evaluates Kaggle-trained XGBoost prototype model against real Mithi features. Explicit status: PROTOTYPE_ONLY."
)
def evaluate_calibration(payload: CalibrationEvaluationRequest) -> CalibrationEvaluationResponse:
    try:
        if payload.zone_id is not None:
            norm_id = SpatialZoneResolver.normalize_zone_id(payload.zone_id)
            SpatialZoneResolver.resolve_zone(norm_id)
            SpatialZoneResolver.validate_capability(norm_id, "deep_intelligence")

        service = CalibrationService()
        features_df = service.prepare_features_for_event(
            event_id=payload.event_id or "E05"
        )
        res = service.evaluate(
            features_df=features_df,
            simulation_run_id=payload.simulation_run_id,
            event_id=payload.event_id or "E05",
            provider_mode=payload.provider_mode
        )
        return CalibrationEvaluationResponse(**res)
    except UnsupportedZoneError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calibration evaluation failed: {str(e)}"
        ) from e
