"""
AQUORA Phase 5 — Deep Intelligence & Physical Engine Federation Schemas.

Defines API data contracts for Level 3 (Deep Intelligence) flood intelligence
operating in the Mumbai / Mithi River Deep Intelligence Zone.
Reuses existing DeepDataContract and adheres to ml/aquora_ml_feature_schema_v1.json.

INVARIANTS:
1. Reuses DeepDataContract from app.schemas.intelligence_contracts without duplicating.
2. Strict Zone Isolation: Operates exclusively within the verified deep_mumbai_mithi extent.
   Outside this zone, returns OUTSIDE_DEEP_ZONE_COVERAGE.
3. Zero-Fabrication: built_up_fraction, distance_to_road_m, distance_to_waterway_m,
   tide_level_m, and SAR observations remain None if unavailable on disk.
4. Physical Engine Primacy: Deterministic hydraulic water depth is strictly distinguished
   from ML susceptibility scores.
5. Opt-in Simulation: Point inspection (/intelligence/deep) does NOT automatically launch
   a physical simulation. Physical simulation is triggered only on explicit request.
6. Rigorous Facility Coverage: Facilities are aligned to the simulation raster grid via
   projected CRS (EPSG:32643); flood impacts are evaluated only where grid coverage exists.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class DeepStatus(str, Enum):
    READY = "READY"
    POINT_INSPECTED = "POINT_INSPECTED"
    SIMULATION_COMPLETED = "SIMULATION_COMPLETED"
    SIMULATION_FAILED = "SIMULATION_FAILED"
    SOLVER_ERROR = "SOLVER_ERROR"
    OUTSIDE_DEEP_ZONE_COVERAGE = "OUTSIDE_DEEP_ZONE_COVERAGE"
    FEATURE_ERROR = "FEATURE_ERROR"


class PhysicalSeverity(str, Enum):
    DRY = "DRY"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"
    UNCOVERED = "UNCOVERED"


class DeepIntelligenceRequest(BaseModel):
    """
    Request payload for Level 3 Deep Intelligence point inspection.
    By default, performs high-resolution raster feature extraction without launching
    a hydrodynamic simulation.
    """
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    timestamp: Optional[datetime] = Field(None, description="Observation timestamp")
    allow_benchmark_rainfall: bool = Field(
        False,
        description="Whether non-operational benchmark rainfall fixtures are permitted (dev/test only)"
    )
    run_simulation: bool = Field(
        False,
        description="Explicit opt-in to launch the Phase 6 hydrodynamic simulation; False by default"
    )
    simulation_horizon_minutes: Optional[int] = Field(
        180,
        ge=10,
        le=300,
        description="Simulation horizon in minutes if simulation is explicitly enabled (10 to 300)"
    )
    simulation_timestep_minutes: Optional[int] = Field(
        10,
        description="Simulation timestep in minutes if simulation is enabled"
    )


class DeepSimulationRequest(BaseModel):
    """
    Request payload for explicit physical flood simulation execution (POST /intelligence/deep/simulate).
    """
    latitude: Optional[float] = Field(
        None,
        ge=-90.0,
        le=90.0,
        description="Optional inspection latitude within the Deep Zone to sample depth"
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180.0,
        le=180.0,
        description="Optional inspection longitude within the Deep Zone to sample depth"
    )
    horizon_minutes: int = Field(
        180,
        ge=10,
        le=300,
        description="Simulation horizon in minutes (up to 300 min / 5 hours)"
    )
    timestep_minutes: int = Field(
        10,
        description="Simulation timestep in minutes (5, 10, 15, 30)"
    )
    start_time: Optional[str] = Field(
        None,
        description="ISO timestamp for simulation start time. Defaults to current UTC time for live NWP."
    )
    use_live_forecast: bool = Field(
        True,
        description="Whether to use live ECMWF NWP forecast forcing from Open-Meteo"
    )
    runoff_model: str = Field(
        "RATIONAL_COEFFICIENT",
        description="Hydrologic runoff model ('RATIONAL_COEFFICIENT', 'IMPERVIOUS_LOSS', 'INITIAL_DEPRESSION_LOSS')"
    )
    rational_c: float = Field(
        0.75,
        ge=0.0,
        le=1.0,
        description="Runoff coefficient for Rational model (0.0 to 1.0)"
    )
    evaluate_facility_impacts: bool = Field(
        True,
        description="Whether to evaluate flood depth impacts across verified critical facilities"
    )


class FacilityImpactItem(BaseModel):
    """Individual critical facility with verified raster grid alignment and depth impact."""
    facility_id: str = Field(..., description="Unique facility identifier")
    name: str = Field(..., description="Facility name")
    category: str = Field(..., description="Facility category (e.g. HOSPITAL, POLICE, FIRE_STATION)")
    latitude: float = Field(..., description="WGS84 latitude")
    longitude: float = Field(..., description="WGS84 longitude")
    raster_col: Optional[int] = Field(None, description="Grid column in projected EPSG:32643 raster")
    raster_row: Optional[int] = Field(None, description="Grid row in projected EPSG:32643 raster")
    raster_covered: bool = Field(..., description="Whether facility coordinates fall inside the raster grid")
    modeled_water_depth_m: Optional[float] = Field(None, ge=0.0, description="Physically modeled water depth at facility cell in meters")
    flood_severity: Optional[str] = Field(None, description="Severity grade: DRY, LOW, MODERATE, HIGH, SEVERE, or UNCOVERED")
    impact_status: str = Field(..., description="Operational impact status (e.g. ACCESSIBLE, INUNDATED, OUT_OF_RASTER_BOUNDS)")


class FacilityImpactSummary(BaseModel):
    """Aggregate flood impact summary across verified facilities in the Deep Intelligence Zone."""
    total_facilities_in_zone: int = Field(..., description="Total verified facilities within zone boundary")
    facilities_covered_by_raster: int = Field(..., description="Facilities falling within raster bounds")
    facilities_outside_raster: int = Field(..., description="Facilities outside raster bounds (no proximity inference applied)")
    impacted_facilities_count: int = Field(..., description="Count of facilities with water depth >= 0.05m")
    severity_breakdown: Dict[str, int] = Field(..., description="Counts per severity category")
    top_impacted_facilities: List[FacilityImpactItem] = Field(
        default_factory=list,
        description="Detailed items for facilities experiencing water depth > 0 or highest severity"
    )


class DeepSimulationSummary(BaseModel):
    """Summary of deterministic hydrodynamic simulation execution."""
    simulation_id: str = Field(..., description="Unique simulation identifier")
    provider_mode: str = Field(..., description="Data provider execution mode (REAL_DATA or TEST)")
    status: str = Field(..., description="Simulation status (e.g. COMPLETED, FAILED)")
    started_at: str = Field(..., description="Execution start timestamp")
    completed_at: str = Field(..., description="Execution completion timestamp")
    horizon_minutes: int = Field(..., description="Horizon in minutes")
    timestep_minutes: int = Field(..., description="Timestep in minutes")
    total_timesteps: int = Field(..., description="Total timesteps executed")
    rainfall_source: str = Field(..., description="Rainfall forcing provider and model identity")
    mean_rainfall_intensity_mm_hr: float = Field(..., description="Mean rainfall rate across horizon")
    max_rainfall_intensity_mm_hr: float = Field(..., description="Peak rainfall rate across horizon")
    peak_water_depth_m: float = Field(..., description="Maximum water depth recorded across the entire grid")
    overall_mass_balance_error_m3: float = Field(..., description="Overall mass balance error in cubic meters")
    is_mass_balance_valid: bool = Field(..., description="Whether mass balance error meets tolerance (<= 1e-4)")
    output_manifest_path: str = Field(..., description="Path to file-backed output manifest")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Solver execution provenance")
    limitations: List[str] = Field(default_factory=list, description="Documented model limitations and caveats")


class DeepIntelligenceResponse(BaseModel):
    """
    Authoritative response for Level 3 Deep Intelligence & Physical Engine Federation.
    """
    status: str = Field(..., description="Evaluation status (e.g. READY, POINT_INSPECTED, OUTSIDE_DEEP_ZONE_COVERAGE)")
    intelligence_level: str = Field("DEEP", description="AQUORA intelligence tier: DEEP")
    zone_id: Optional[str] = Field(None, description="Resolved Deep Intelligence Zone identifier")
    zone_name: Optional[str] = Field(None, description="Resolved zone name")
    coordinates: Dict[str, float] = Field(..., description="Query latitude and longitude")
    point_in_zone: bool = Field(..., description="Whether query point is within verified Deep Zone bounds")
    raster_sampled: bool = Field(..., description="Whether 30m high-resolution terrain rasters were sampled")

    # High-resolution physical features
    elevation_m: Optional[float] = Field(None, description="Copernicus 30m elevation in meters")
    slope_degrees: Optional[float] = Field(None, description="Terrain slope in degrees")
    aspect_degrees: Optional[float] = Field(None, description="Terrain aspect in degrees")
    flow_accumulation_cells: Optional[int] = Field(None, ge=0, description="D8 deterministic flow accumulation count (rounded integer cells)")
    drainage_proxy_score: Optional[float] = Field(None, ge=0.0, description="High-resolution DEM sink and conveyance bottleneck proxy")

    # Uningested / missing features strictly preserved as None under zero-fabrication
    built_up_fraction: Optional[float] = Field(None, description="Built-up fraction (None: uningested on disk)")
    distance_to_road_m: Optional[float] = Field(None, description="Distance to road network (None: uningested on disk)")
    distance_to_waterway_m: Optional[float] = Field(None, description="Distance to waterway canal (None: uningested on disk)")
    tide_level_m: Optional[float] = Field(None, description="Tide level (None: gauge CSV uningested on disk)")

    # Physical vs ML distinction
    modeled_water_depth_m: Optional[float] = Field(
        None,
        ge=0.0,
        description="Deterministic hydraulic water depth from Phase 6 hydrodynamic solver in meters"
    )
    physical_severity: Optional[str] = Field(
        None,
        description="Physical depth classification: DRY (<0.05m), LOW (0.05-0.15m), MODERATE (0.15-0.3m), HIGH (0.3-0.6m), SEVERE (>=0.6m)"
    )
    ml_susceptibility_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Supplementary prototype ML susceptibility score [0, 1]. Strictly separate from physical depth."
    )
    calibration_status: str = Field(
        "PHYSICAL_HYDRODYNAMIC_SOLVER_PRIMARY",
        description="Authority model note: Physical 2D hydrodynamic solver is primary truth; ML score is supplementary."
    )

    # Corroboration & Facilities
    sar_corroboration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sentinel-1 SAR radar evidence status"
    )
    critical_facilities_count: Optional[int] = Field(
        None,
        ge=0,
        description="Total verified critical facilities in zone"
    )

    # Simulation and facility impacts (populated when simulation is executed or available)
    simulation: Optional[DeepSimulationSummary] = Field(
        None,
        description="Details of physical flood simulation run if executed or requested"
    )
    facility_impacts: Optional[FacilityImpactSummary] = Field(
        None,
        description="Impact breakdown on verified facilities if simulation was executed"
    )

    provenance: Dict[str, Any] = Field(default_factory=dict, description="Complete end-to-end provenance")
    limitations: List[str] = Field(default_factory=list, description="Documented limitations and uningested data notices")
    message: Optional[str] = Field(None, description="Descriptive status or diagnostic message")
