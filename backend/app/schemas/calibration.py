"""
Pydantic Schemas for Phase 8 Prototype ML Calibration.
Strictly adheres to PROTOTYPE_ONLY status metadata requirements.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CalibrationEvaluationRequest(BaseModel):
    simulation_run_id: Optional[str] = Field(
        default=None,
        description="ID of physical simulation run (e.g., Phase 6 E05 run)"
    )
    event_id: Optional[str] = Field(
        default="E05",
        description="Hydro-meteorological event identifier (e.g., 'E05')"
    )
    provider_mode: str = Field(
        default="REAL_DATA",
        description="Data acquisition mode ('REAL_DATA' or 'SYNTHETIC')"
    )
    sample_limit: Optional[int] = Field(
        default=10,
        description="Number of sample predictions to return in summary"
    )
    zone_id: Optional[str] = Field(
        default=None,
        description="Optional target intelligence zone ID"
    )


class PredictionSummary(BaseModel):
    input_row_count: int = Field(..., description="Total input grid cells evaluated")
    prediction_count: int = Field(..., description="Total valid predictions produced")
    min_score: float = Field(..., description="Minimum prototype ML score")
    max_score: float = Field(..., description="Maximum prototype ML score")
    mean_score: float = Field(..., description="Mean prototype ML score")
    std_score: float = Field(..., description="Standard deviation of prototype ML score")
    high_risk_cell_count: int = Field(..., description="Count of grid cells with ML score >= 0.5")


class CalibrationEvaluationResponse(BaseModel):
    run_id: str = Field(..., description="Unique ID for this calibration evaluation execution")
    simulation_run_id: Optional[str] = Field(default=None, description="Source physical simulation run ID")
    event_id: Optional[str] = Field(default=None, description="Hydro-meteorological event ID")
    model_artifact: str = Field(default="aquora_xgboost_prototype.joblib", description="Model filename")
    model_status: str = Field(default="PROTOTYPE_ONLY", description="Explicit prototype model status")
    calibration_status: str = Field(default="NOT_CALIBRATED", description="Explicit prototype calibration status")
    provider_mode: str = Field(default="REAL_DATA", description="Data provider mode")
    feature_schema: List[str] = Field(..., description="List of 12 approved model features in exact expected order")
    feature_count: int = Field(default=12, description="Number of approved model features")
    prediction_summary: PredictionSummary = Field(..., description="Statistical summary of predictions")
    provenance: Dict[str, Any] = Field(..., description="Execution provenance and audit metadata")
    sample_scores: Optional[List[float]] = Field(default=None, description="Sample top/representative prototype ML scores")

