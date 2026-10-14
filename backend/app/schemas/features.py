"""
AQUORA Phase 2E — National Flood Feature Pipeline Schemas.

Defines request, response, and export schemas for multiscale flood feature generation,
strictly adhering to ml/aquora_ml_feature_schema_v1.json (v1.0.0).

INVARIANTS:
1. Exact 20 feature names, types, and constraints matching schema v1.0.0.
2. Separation of predictor features from candidate flood labels and SAR metadata (Zero Leakage).
3. Explicit nulls for unavailable observations; authentic zero rainfall preserved as 0.0.
4. Strict tier gating: Core National, Regional Expansion, Deep Zone Exclusive.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class FeatureTier(str, Enum):
    CORE_NATIONAL = "CORE_NATIONAL"
    REGIONAL_EXPANSION = "REGIONAL_EXPANSION"
    DEEP_ZONE_EXCLUSIVE = "DEEP_ZONE_EXCLUSIVE"


class FeatureVectorNational(BaseModel):
    """
    11 Core National Predictor Features.
    Must be structurally present for all national extraction queries.
    Values are None if the authoritative observation is unavailable.
    """
    rainfall_1h_mm: Optional[float] = Field(None, ge=0.0, description="1-hour accumulated precipitation in mm")
    rainfall_3h_mm: Optional[float] = Field(None, ge=0.0, description="3-hour accumulated precipitation in mm")
    rainfall_6h_mm: Optional[float] = Field(None, ge=0.0, description="6-hour accumulated precipitation in mm")
    rainfall_24h_mm: Optional[float] = Field(None, ge=0.0, description="24-hour antecedent rainfall in mm")
    rainfall_72h_mm: Optional[float] = Field(None, ge=0.0, description="72-hour antecedent rainfall in mm")
    rainfall_anomaly_index: Optional[float] = Field(None, description="Normalized rainfall anomaly against baseline")
    elevation_m: Optional[float] = Field(None, description="Terrain surface elevation in meters")
    slope_deg: Optional[float] = Field(None, ge=0.0, le=90.0, description="Terrain surface slope in degrees [0, 90]")
    distance_to_river_m: Optional[float] = Field(None, ge=0.0, description="Distance to nearest major river reach in meters")
    historical_flood_frequency: Optional[float] = Field(None, ge=0.0, le=1.0, description="Historical flood occurrence probability index [0, 1]")
    landcover_class: Optional[int] = Field(None, description="Discrete land cover classification code (e.g. WorldCover)")


class FeatureVectorRegional(FeatureVectorNational):
    """
    Regional Expansion: Extends Core National with 3 catchment & exposure features.
    """
    basin_drainage_area_km2: Optional[float] = Field(None, gt=0.0, description="Upstream catchment drainage area in km2")
    soil_saturation_index: Optional[float] = Field(None, ge=0.0, le=1.0, description="Antecedent soil moisture saturation score [0, 1]")
    population_density_per_km2: Optional[float] = Field(None, ge=0.0, description="Human settlement exposure density per km2")


class FeatureVectorDeep(FeatureVectorRegional):
    """
    Deep Zone Exclusive: Extends Regional with 6 micro-scale hydrodynamic and urban features.
    Strictly isolated to verified Deep Intelligence Zones.
    """
    flow_accumulation_cells: Optional[int] = Field(None, ge=0, description="D8 flow accumulation upstream cell count")
    drainage_proxy_score: Optional[float] = Field(None, ge=0.0, description="Stormwater drainage sink / conveyance proxy")
    built_up_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Impervious built-up surface fraction [0, 1]")
    distance_to_road_m: Optional[float] = Field(None, ge=0.0, description="Fine-resolution proximity to road network in meters")
    distance_to_waterway_m: Optional[float] = Field(None, ge=0.0, description="Proximity to urban stormwater channel/nalla in meters")
    tide_level_m: Optional[float] = Field(None, description="Water level from coastal tide gauge in meters")


class CandidateLabelMetadata(BaseModel):
    """
    Zero-Leakage Target Candidate Evidence Boundary.
    Stores SAR or ground-truth evidence strictly separate from predictor features.
    """
    flood_label: int = Field(-1, description="Target label: 1=flood candidate, 0=dry negative, -1=unobserved/unknown")
    sar_scene_id: Optional[str] = Field(None, description="Intersecting Sentinel-1 SAR scene ID if present")
    sar_delta_vv_db: Optional[float] = Field(None, description="Backscatter delta in dB (evidence only, never a feature)")
    label_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score of candidate label")
    provenance: str = Field("UNAVAILABLE", description="Label provenance classification")


class PointFeatureExtractionRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    timestamp: Optional[datetime] = Field(None, description="Observation timestamp (ISO-8601)")
    allow_benchmark_rainfall: bool = Field(False, description="Whether non-operational benchmark rainfall fixtures are permitted")
    include_candidate_target: bool = Field(False, description="Whether to evaluate candidate SAR target label (stored in separate metadata)")


class PointFeatureExtractionResponse(BaseModel):
    zone_tier: str = Field(..., description="Resolved zone tier: NATIONAL, REGIONAL, or DEEP_ZONE")
    zone_name: str = Field(..., description="Resolved zone name")
    zone_id: Optional[str] = Field(None, description="Zone identifier if registered")
    coordinates: Dict[str, float] = Field(..., description="Latitude and Longitude")
    timestamp: Optional[datetime] = Field(None, description="Extraction timestamp")
    features: Dict[str, Optional[Any]] = Field(..., description="Extracted feature vector adhering to aquora_ml_feature_schema_v1")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Dataset provenance and source traceability")
    candidate_target: Optional[CandidateLabelMetadata] = Field(None, description="Candidate flood label metadata (isolated from features)")
    schema_version: str = Field("1.0.0", description="Validated schema version")
    schema_validated: bool = Field(True, description="Whether the record passed strict JSON Schema validation")


class BatchGridFeatureExtractionRequest(BaseModel):
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Southern bounding latitude")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Northern bounding latitude")
    min_lon: float = Field(..., ge=-180.0, le=180.0, description="Western bounding longitude")
    max_lon: float = Field(..., ge=-180.0, le=180.0, description="Eastern bounding longitude")
    grid_resolution_deg: float = Field(0.05, gt=0.0, le=1.0, description="Sampling step size in degrees (default 0.05 deg ~ 5 km)")
    timestamp: Optional[datetime] = Field(None, description="Observation timestamp")
    allow_benchmark_rainfall: bool = Field(False, description="Permit non-operational benchmark fixtures")
    export_format: str = Field("json", description="Export format: 'json' or 'parquet_base64'")

    @field_validator("max_lat")
    @classmethod
    def validate_latitude_order(cls, v: float, info) -> float:
        min_lat = info.data.get("min_lat")
        if min_lat is not None and v < min_lat:
            raise ValueError("max_lat must be greater than or equal to min_lat")
        return v

    @field_validator("max_lon")
    @classmethod
    def validate_longitude_order(cls, v: float, info) -> float:
        min_lon = info.data.get("min_lon")
        if min_lon is not None and v < min_lon:
            raise ValueError("max_lon must be greater than or equal to min_lon")
        return v


class BatchGridFeatureExtractionResponse(BaseModel):
    point_count: int = Field(..., description="Total points sampled")
    bounding_box: Dict[str, float] = Field(..., description="Requested bounding box")
    grid_resolution_deg: float = Field(..., description="Grid step size")
    records: Optional[List[Dict[str, Any]]] = Field(None, description="List of feature records if JSON format requested")
    parquet_base64: Optional[str] = Field(None, description="Base64-encoded Parquet buffer if requested")
    parquet_byte_size: Optional[int] = Field(None, description="Parquet buffer size in bytes")
    schema_version: str = Field("1.0.0", description="Schema version")


class FeatureSchemaMetadataResponse(BaseModel):
    schema_name: str
    schema_version: str
    created_at: str
    governance: Dict[str, str]
    tiers: Dict[str, Dict[str, Any]]
    total_features: int
