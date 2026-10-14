"""
AQUORA 2.0 Standardized Multi-Tier Data Contracts & Versioned ML Feature Schema.

Defines schemas for:
1. National Data Contract (Country-wide screening)
2. Regional Data Contract (State/District/Basin/City intelligence)
3. Deep Data Contract (High-resolution physical solver + local drainage + SAR)
4. Versioned ML Feature Schema (aquora_ml_feature_schema_v1)
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IntelligenceLevel(str, Enum):
    NATIONAL = "NATIONAL"
    REGIONAL = "REGIONAL"
    DEEP = "DEEP"


class CapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    FUTURE = "FUTURE"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class EntityType(str, Enum):
    COUNTRY = "COUNTRY"
    STATE = "STATE"
    DISTRICT = "DISTRICT"
    BASIN = "BASIN"
    CITY = "CITY"
    CATCHMENT = "CATCHMENT"
    GRID_CELL = "GRID_CELL"


class ZoneStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PROTOTYPE = "PROTOTYPE"
    PLANNED = "PLANNED"


# ==============================================================================
# MULTI-TIER DATA CONTRACTS
# ==============================================================================

class NationalDataContract(BaseModel):
    """
    Standardized payload contract for Level 1: National Flood Risk Screening.
    Available uniformly across the Indian subcontinent using macro-scale datasets.
    """
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    elevation_m: float = Field(..., description="Copernicus 30m terrain elevation in meters")
    slope_deg: float = Field(..., ge=0.0, le=90.0, description="Terrain surface slope in degrees")
    distance_to_river_m: float = Field(..., ge=0.0, description="Distance to nearest major river channel in meters")
    rainfall_1h_mm: Optional[float] = Field(None, ge=0.0, description="1-hour accumulated precipitation in mm")
    rainfall_3h_mm: Optional[float] = Field(None, ge=0.0, description="3-hour accumulated precipitation in mm")
    rainfall_6h_mm: Optional[float] = Field(None, ge=0.0, description="6-hour accumulated precipitation in mm")
    rainfall_24h_mm: Optional[float] = Field(None, ge=0.0, description="24-hour accumulated precipitation in mm")
    rainfall_72h_mm: Optional[float] = Field(None, ge=0.0, description="72-hour accumulated precipitation in mm")
    rainfall_anomaly_index: Optional[float] = Field(None, description="Normalized rainfall deviation against 10-year climatological baseline")
    historical_flood_frequency_score: float = Field(..., ge=0.0, le=1.0, description="Historical multi-decadal flood occurrence probability")
    landcover_class: int = Field(..., description="ESA WorldCover 2021 land cover classification code")

    # Rainfall availability & provenance status
    rainfall_available: bool = Field(True, description="Whether rainfall observations are available for this contract")
    rainfall_operational_status: Optional[str] = Field(None, description="Operational availability status or reason why unavailable")
    rainfall_provenance: Optional[str] = Field(None, description="Provenance classification of rainfall metrics (e.g. AUTHENTIC_OBSERVATION, OPERATIONAL_FORECAST, LITERATURE_DERIVED_BENCHMARK, UNAVAILABLE)")



class RegionalDataContract(NationalDataContract):
    """
    Standardized payload contract for Level 2: Regional Intelligence.
    Extends National Data Contract with administrative and watershed attributes.
    """
    basin_id: Optional[str] = Field(None, description="HydroSHEDS / CWC river basin identifier")
    basin_name: Optional[str] = Field(None, description="Official river basin name")
    sub_catchment_id: Optional[str] = Field(None, description="Sub-basin / catchment code")
    soil_saturation_index: Optional[float] = Field(None, ge=0.0, le=1.0, description="Antecedent moisture condition score (0=dry, 1=saturated)")
    basin_drainage_area_km2: Optional[float] = Field(None, ge=0.0, description="Contributing upstream catchment drainage area in km2")
    population_density_per_km2: Optional[float] = Field(None, ge=0.0, description="Census-derived population exposure per square km")
    critical_facilities_count: Optional[int] = Field(None, ge=0, description="Number of hospitals, fire stations, and substations in region")


class DeepDataContract(RegionalDataContract):
    """
    Standardized payload contract for Level 3: Deep Intelligence Zone.
    Supports high-resolution hydrodynamic modeling, physical loss solvers, and radar corroboration.
    Currently operational exclusively in the Mumbai / Mithi Deep Intelligence Zone.
    """
    flow_accumulation_cells: Optional[int] = Field(None, ge=0, description="D8 deterministic flow accumulation count")
    drainage_proxy_score: Optional[float] = Field(None, ge=0.0, description="High-resolution DEM sink and conveyance bottleneck proxy")
    built_up_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Impervious surface fraction from building vector footprints")
    distance_to_road_m: Optional[float] = Field(None, ge=0.0, description="Fine-resolution distance to navigable street network in meters")
    distance_to_waterway_m: Optional[float] = Field(None, ge=0.0, description="Distance to local nalla / urban stormwater canal in meters")
    tide_level_m: Optional[float] = Field(None, description="Real-time or harmonic tide water level in meters (coastal zones only)")
    sar_delta_vv_db: Optional[float] = Field(None, description="Sentinel-1 GRD VV bitemporal backscatter delta in dB")
    modeled_depth_m: Optional[float] = Field(None, ge=0.0, description="Phase 6 deterministic hydraulic water depth in meters")
    sar_available: bool = Field(False, description="Whether SAR backscatter observations are available for this contract")
    sar_operational_status: Optional[str] = Field("OPERATIONAL_OBSERVATION_UNAVAILABLE", description="Operational availability status for SAR")
    sar_provenance: Optional[str] = Field("UNAVAILABLE", description="Provenance classification of SAR backscatter observation")


# ==============================================================================
# VERSIONED ML FEATURE GOVERNANCE SCHEMA
# ==============================================================================

class MLFeatureTier(str, Enum):
    CORE_NATIONAL = "CORE_NATIONAL"
    REGIONAL_EXPANSION = "REGIONAL_EXPANSION"
    DEEP_ZONE_EXCLUSIVE = "DEEP_ZONE_EXCLUSIVE"


class MLFeatureAvailability(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    UNAVAILABLE = "UNAVAILABLE"


class MLFeatureDefinition(BaseModel):
    name: str = Field(..., description="Feature field name")
    tier: MLFeatureTier = Field(..., description="Feature hierarchy tier")
    availability_national: MLFeatureAvailability = Field(..., description="Availability at National scale")
    availability_regional: MLFeatureAvailability = Field(..., description="Availability at Regional scale")
    availability_deep: MLFeatureAvailability = Field(..., description="Availability in Deep Zone")
    dtype: str = Field(..., description="Data type (float32, int32, etc.)")
    description: str = Field(..., description="Scientific feature description")
    governance_note: Optional[str] = Field(None, description="Leakage or provenance constraint")


AQUORA_ML_FEATURE_SCHEMA_V1: Dict[str, Any] = {
    "schema_name": "aquora_ml_feature_schema_v1",
    "schema_version": "1.0.0",
    "created_at": "2026-10-07T00:00:00Z",
    "governance": {
        "status": "APPROVED",
        "description": "Standardized India-ready ML predictor schema enforcing strict tier isolation."
    },
    "features": [
        # --- CORE NATIONAL PREDICTORS (Always required across India) ---
        {
            "name": "rainfall_1h_mm",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "1-hour accumulated precipitation in mm (IMERG / ECMWF)",
        },
        {
            "name": "rainfall_3h_mm",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "3-hour accumulated precipitation in mm",
        },
        {
            "name": "rainfall_6h_mm",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "6-hour accumulated precipitation in mm",
        },
        {
            "name": "rainfall_24h_mm",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "24-hour antecedent rainfall in mm",
        },
        {
            "name": "rainfall_72h_mm",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "72-hour antecedent rainfall in mm",
        },
        {
            "name": "rainfall_anomaly_index",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Normalized rainfall anomaly against 10-year GPM baseline",
        },
        {
            "name": "elevation_m",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Terrain surface elevation from Copernicus 30m DEM in meters",
        },
        {
            "name": "slope_deg",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Surface terrain slope in degrees",
        },
        {
            "name": "distance_to_river_m",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Planar metric distance to nearest major HydroSHEDS/OSM river channel",
        },
        {
            "name": "historical_flood_frequency",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Historical multi-decadal flood occurrence probability index (0-1)",
        },
        {
            "name": "landcover_class",
            "tier": MLFeatureTier.CORE_NATIONAL.value,
            "availability_national": MLFeatureAvailability.REQUIRED.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "int32",
            "description": "ESA WorldCover 2021 discrete integer class code",
        },

        # --- REGIONAL EXPANSION PREDICTORS ---
        {
            "name": "basin_drainage_area_km2",
            "tier": MLFeatureTier.REGIONAL_EXPANSION.value,
            "availability_national": MLFeatureAvailability.OPTIONAL.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Contributing upstream catchment drainage area in km2",
        },
        {
            "name": "soil_saturation_index",
            "tier": MLFeatureTier.REGIONAL_EXPANSION.value,
            "availability_national": MLFeatureAvailability.OPTIONAL.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Antecedent moisture condition score (0=dry, 1=saturated)",
        },
        {
            "name": "population_density_per_km2",
            "tier": MLFeatureTier.REGIONAL_EXPANSION.value,
            "availability_national": MLFeatureAvailability.OPTIONAL.value,
            "availability_regional": MLFeatureAvailability.REQUIRED.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "District-level population exposure density",
        },

        # --- DEEP ZONE EXCLUSIVE PREDICTORS (Not available at national scale) ---
        {
            "name": "flow_accumulation_cells",
            "tier": MLFeatureTier.DEEP_ZONE_EXCLUSIVE.value,
            "availability_national": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_regional": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "int32",
            "description": "High-resolution D8 flow accumulation cells count",
            "governance_note": "Do not train national screening model on this feature.",
        },
        {
            "name": "drainage_proxy_score",
            "tier": MLFeatureTier.DEEP_ZONE_EXCLUSIVE.value,
            "availability_national": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_regional": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Micro-catchment drainage sink and conveyance bottleneck proxy",
            "governance_note": "Exclusive to verified deep zones with high-res urban sinks.",
        },
        {
            "name": "built_up_fraction",
            "tier": MLFeatureTier.DEEP_ZONE_EXCLUSIVE.value,
            "availability_national": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_regional": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Building footprint impervious surface coverage fraction",
            "governance_note": "Requires verified urban building vector geometry layer.",
        },
        {
            "name": "distance_to_road_m",
            "tier": MLFeatureTier.DEEP_ZONE_EXCLUSIVE.value,
            "availability_national": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_regional": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Fine-scale street network proximity in meters",
        },
        {
            "name": "distance_to_waterway_m",
            "tier": MLFeatureTier.DEEP_ZONE_EXCLUSIVE.value,
            "availability_national": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_regional": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_deep": MLFeatureAvailability.REQUIRED.value,
            "dtype": "float32",
            "description": "Local stormwater channel / nalla network proximity in meters",
        },
        {
            "name": "tide_level_m",
            "tier": MLFeatureTier.DEEP_ZONE_EXCLUSIVE.value,
            "availability_national": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_regional": MLFeatureAvailability.UNAVAILABLE.value,
            "availability_deep": MLFeatureAvailability.OPTIONAL.value,
            "dtype": "float32",
            "description": "Observed water level from local coastal tide gauge in meters",
            "governance_note": "Coastal zones only. Unavailable in inland river catchments.",
        },
    ],
}
