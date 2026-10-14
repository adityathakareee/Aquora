"""
AQUORA Phase 4 — Regional Flood Intelligence & Watershed Risk Schemas.

Defines API data contracts for Level 2 (Regional) flood intelligence across
supported Indian river basins and administrative corridors.
Adheres strictly to ml/aquora_ml_feature_schema_v1.json (v1.0.0).

INVARIANTS:
1. Exact 14 features evaluated: 11 CORE_NATIONAL + 3 REGIONAL_EXPANSION.
2. Deep-zone-exclusive features (flow_accumulation_cells, drainage_proxy_score,
   built_up_fraction, tide_level_m, etc.) are strictly prohibited from regional predictors.
3. Zero-Fabrication: If population data or facilities are missing, they remain None.
   No synthetic demographic or facility numbers.
4. Bounded Execution: Batch size capped strictly at 250 points.
5. Heuristic Clarification: Uncalibrated watershed screening index is strictly labeled
   as an uncalibrated heuristic, never as a calibrated probability or hydraulic depth.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class RegionalStatus(str, Enum):
    READY = "READY"
    HEURISTIC_AVAILABLE = "HEURISTIC_AVAILABLE"
    MODEL_NOT_TRAINED = "MODEL_NOT_TRAINED"
    OUTSIDE_REGIONAL_COVERAGE = "OUTSIDE_REGIONAL_COVERAGE"
    FEATURE_ERROR = "FEATURE_ERROR"


class RegionalExposureGrade(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNCALIBRATED = "UNCALIBRATED"


class RegionalIntelligenceRequest(BaseModel):
    """Request for Level 2 Regional flood intelligence at a single coordinate."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    timestamp: Optional[datetime] = Field(None, description="Observation timestamp")
    basin_id: Optional[str] = Field(None, description="Optional explicit basin identifier hint")
    allow_benchmark_rainfall: bool = Field(False, description="Whether non-operational benchmark fixtures are permitted (dev/test only)")


class RegionalIntelligenceResponse(BaseModel):
    """Authoritative response for Level 2 Regional flood intelligence."""
    status: str = Field(..., description="Regional status: READY, HEURISTIC_AVAILABLE, MODEL_NOT_TRAINED, or OUTSIDE_REGIONAL_COVERAGE")
    is_ready: bool = Field(..., description="Whether a trained, certified ML model artifact is active")
    model_id: str = Field(..., description="Model identifier")
    model_version: str = Field(..., description="Model version string")
    intelligence_level: str = Field("REGIONAL", description="AQUORA intelligence tier: REGIONAL")
    basin_id: Optional[str] = Field(None, description="HydroSHEDS/CWC River Basin identifier (e.g. BASIN-GANGA)")
    basin_name: Optional[str] = Field(None, description="Official river basin name")
    resolved_zone: str = Field(..., description="Resolved geographic zone or corridor name")
    coordinates: Dict[str, float] = Field(..., description="Query latitude and longitude")
    features_used: Optional[List[str]] = Field(None, description="The 14 authorized features (11 Core National + 3 Regional)")
    feature_values: Optional[Dict[str, Optional[float]]] = Field(None, description="Evaluated feature dictionary")
    watershed_exposure_index: Optional[float] = Field(None, ge=0.0, le=1.0, description="Dimensionless uncalibrated watershed exposure screening index [0, 1]")
    exposure_grade: Optional[str] = Field(None, description="Exposure grade: LOW (<0.33), MEDIUM (0.33-0.66), HIGH (>=0.66), or UNCALIBRATED")
    calibration_status: str = Field(
        "UNCALIBRATED_REGIONAL_SCREENING",
        description="Calibration disclaimer: uncalibrated meso-scale screening index, not a hydraulic depth or forecast",
    )
    critical_facilities_count: Optional[int] = Field(None, ge=0, description="Verified critical facility count within basin/zone")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Traceability provenance")
    message: Optional[str] = Field(None, description="Descriptive status or diagnostic message")


class RegionalBatchItem(BaseModel):
    """Single item within a batch regional intelligence request."""
    point_id: str = Field(..., description="Client-provided unique identifier for this point")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    timestamp: Optional[datetime] = Field(None, description="Observation timestamp")
    basin_id: Optional[str] = Field(None, description="Optional basin hint")


class RegionalBatchRequest(BaseModel):
    """Bounded batch request for regional flood intelligence (max 250 points)."""
    points: List[RegionalBatchItem] = Field(..., max_length=250, description="Batch points (max 250)")
    allow_benchmark_rainfall: bool = Field(False, description="Allow benchmark rainfall fixtures")

    @field_validator("points")
    @classmethod
    def validate_batch_size(cls, v: List[RegionalBatchItem]) -> List[RegionalBatchItem]:
        if len(v) > 250:
            raise ValueError(f"Batch size {len(v)} exceeds maximum allowed limit of 250 points.")
        if len(v) == 0:
            raise ValueError("Batch must contain at least 1 point.")
        return v


class RegionalBatchResponse(BaseModel):
    """Batch response for regional flood intelligence."""
    total_requested: int
    results: List[RegionalIntelligenceResponse]
    model_id: str
    model_version: str


class BasinSummaryResponse(BaseModel):
    """Summary metadata and operational status for an Indian river basin."""
    basin_id: str = Field(..., description="HydroBASINS identifier (e.g. BASIN-GANGA)")
    basin_name: str = Field(..., description="Official river basin name")
    pfaf_code: Optional[str] = Field(None, description="Pfafstetter hydrologic basin code")
    pfafstetter_level: Optional[int] = Field(None, description="Pfafstetter hierarchy level")
    drainage_area_km2: Optional[float] = Field(None, description="Contributing upstream catchment drainage area in km2")
    major_states: List[str] = Field(default_factory=list, description="State codes intersected by basin")
    centroid: Dict[str, float] = Field(..., description="Basin centroid latitude and longitude")
    bounds: Dict[str, float] = Field(..., description="Bounding box (min_lon, min_lat, max_lon, max_lat)")
    operational_status: str = Field(..., description="Operational status: ACTIVE or PLANNED")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Tier capability flags")
    governance_note: str = Field(..., description="Data provenance and governance statement")
