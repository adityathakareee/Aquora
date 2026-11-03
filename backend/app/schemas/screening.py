"""
AQUORA Phase 3 — National Flood Screening Schemas.

Defines API data contracts for macro-scale national flood screening.
Adheres strictly to ml/aquora_ml_feature_schema_v1.json (v1.0.0).

INVARIANTS:
1. Exact 11 CORE_NATIONAL features used for screening.
2. Macro susceptibility score is strictly separated from Phase 6 physical water depths.
3. Untrained models report explicit NOT_TRAINED status; never fabricates fake scores.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ScreeningStatus(str, Enum):
    READY = "READY"
    INSUFFICIENT_INPUT_DATA = "INSUFFICIENT_INPUT_DATA"
    MODEL_NOT_TRAINED = "MODEL_NOT_TRAINED"
    OUTSIDE_COVERAGE = "OUTSIDE_COVERAGE"
    FEATURE_ERROR = "FEATURE_ERROR"


class SusceptibilityGrade(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class NationalScreeningRequest(BaseModel):
    """Request for macro-scale national flood screening at a single coordinate."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    timestamp: Optional[datetime] = Field(None, description="Observation timestamp")
    allow_benchmark_rainfall: bool = Field(False, description="Whether non-operational benchmark fixtures are permitted (dev/test only)")


class NationalScreeningResponse(BaseModel):
    """Authoritative response for national macro screening."""
    status: str = Field(..., description="Screening status: READY, MODEL_NOT_TRAINED, or OUTSIDE_COVERAGE")
    is_ready: bool = Field(..., description="Whether a trained, verified model artifact is active")
    model_id: str = Field(..., description="Model identifier")
    model_version: str = Field(..., description="Model version string")
    intelligence_level: str = Field("NATIONAL", description="AQUORA intelligence tier: NATIONAL")
    resolved_zone: str = Field(..., description="Geographic zone or basin name")
    coordinates: Dict[str, float] = Field(..., description="Query latitude and longitude")
    features_used: Optional[List[str]] = Field(None, description="Exact 11 features evaluated")
    feature_values: Optional[Dict[str, Optional[float]]] = Field(None, description="Evaluated feature dictionary")
    susceptibility_probability: Optional[float] = Field(None, ge=0.0, le=1.0, description="Predicted macro susceptibility probability [0, 1]")
    susceptibility_grade: Optional[str] = Field(None, description="Susceptibility grade: LOW (<0.33), MEDIUM (0.33-0.66), HIGH (>=0.66)")
    calibration_status: str = Field("UNCALIBRATED_MACRO_SCREENING", description="Calibration disclaimer: macro screening susceptibility, not physical depth")
    governance_status: str = Field("PROTOTYPE_ONLY", description="Model governance status: PROTOTYPE_ONLY")
    operational_readiness: str = Field("NOT_FOR_PUBLIC_ALERTS", description="Operational readiness: NOT_FOR_PUBLIC_ALERTS")
    physics_engine_primacy: str = Field("Phase 6 deterministic physics engine remains primary authority", description="Primary simulation authority disclaimer")
    hydrorivers_reach_distance_m: Optional[float] = Field(None, description="Authentic HydroRIVERS reach centerline distance in meters")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Traceability provenance")
    message: Optional[str] = Field(None, description="Descriptive status or diagnostic message")


class NationalScreeningBatchItem(BaseModel):
    point_id: str
    latitude: float
    longitude: float
    timestamp: Optional[datetime] = None


class NationalScreeningBatchRequest(BaseModel):
    points: List[NationalScreeningBatchItem] = Field(..., max_length=250, description="Batch points (max 250)")
    allow_benchmark_rainfall: bool = Field(False, description="Allow benchmark rainfall fixtures")


class NationalScreeningBatchResponse(BaseModel):
    total_requested: int
    results: List[NationalScreeningResponse]
    model_id: str
    model_version: str
