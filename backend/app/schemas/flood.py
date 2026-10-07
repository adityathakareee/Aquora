"""
Pydantic v2 Schemas for Phase 6 Flood Simulation Engine API.

Provides typed validation for simulation execution requests, hydrologic parameters,
coupling policies, simulation run status, diagnostics, and output artifact metadata.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.geospatial.flood import (
    RainfallResamplingMethod,
    RainfallSourceType,
    RunoffModel,
)


class RunoffParametersSchema(BaseModel):
    """Hydrologic parameters for rainfall-to-runoff generation."""

    model: RunoffModel = Field(default=RunoffModel.IMPERVIOUS_LOSS, description="Runoff model formulation")
    runoff_coefficient: float = Field(default=0.7, ge=0.0, le=1.0, description="Runoff coefficient C (0.0 to 1.0)")
    infiltration_rate_mm_hr: float = Field(default=5.0, ge=0.0, description="Soil infiltration rate in mm/hr")
    initial_loss_mm: float = Field(default=2.0, ge=0.0, description="Initial abstraction/wetting loss in mm")
    depression_storage_m3_per_m2: float = Field(default=0.05, ge=0.0, description="Depression storage per m2 cell area")


class DrainageCouplingPolicySchema(BaseModel):
    """Policy for unknown drainage capacity, direction, and catchment association."""

    unknown_capacity_policy: str = Field(default="EXCLUDE", description="Policy for missing pipe capacity ('EXCLUDE', 'CONSERVATIVE_ASSUMPTION', 'SCENARIO')")
    unknown_direction_policy: str = Field(default="EXCLUDE", description="Policy for unknown link direction ('EXCLUDE', 'SCENARIO')")
    unknown_association_policy: str = Field(default="EXCLUDE", description="Policy for unassociated catchments ('EXCLUDE', 'NEAREST_VALID')")
    max_association_distance_m: float = Field(default=200.0, ge=0.0, description="Maximum association distance in meters")


class FloodSimulationRequestSchema(BaseModel):
    """Request payload to trigger a physical flood simulation run."""

    provider_mode: str = Field(
        default="REAL_DATA",
        description="Provider execution mode ('REAL_DATA' for real Mithi DEM & IMERG rainfall, 'TEST' for unit test fixtures)"
    )
    event_id: str | None = Field(
        default="E05",
        description="Historical flood event identifier for REAL_DATA mode ('E01' to 'E07')"
    )
    study_area_id: str | None = Field(default="mithi_urban_catchment", description="Optional study area ID")
    zone_id: str | None = Field(default=None, description="Optional target intelligence zone ID")
    start_time: str | None = Field(default="2020-08-05T08:00:00Z", description="ISO timestamp for simulation start time")
    horizon_minutes: int = Field(default=180, ge=10, le=300, description="Simulation horizon in minutes (up to 3 hours / 300 min)")
    timestep_minutes: int = Field(default=10, description="Simulation timestep in minutes (5, 10, 15, 30, 60)")

    rainfall_source_type: RainfallSourceType = Field(default=RainfallSourceType.OBSERVATION, description="Rainfall data source type")
    rainfall_resampling_method: RainfallResamplingMethod = Field(default=RainfallResamplingMethod.HOLD, description="Temporal resampling method")
    synthetic_rainfall_mm_hr: float | None = Field(default=30.0, ge=0.0, description="Rainfall intensity in mm/hr if using synthetic rainfall in TEST mode")
    use_forecast_provider: bool = Field(default=False, description="Whether to use real Open-Meteo ECMWF forecast provider for simulation rainfall series")
    forecast_dataset_id: str | None = Field(default=None, description="Optional forecast model ID or dataset identifier (e.g. 'ECMWF_IFS_GLOBAL' or 'OPEN_METEO_ECMWF')")

    terrain_dataset_id: str | None = Field(default="elevation_30m", description="Terrain DEM dataset ID or file basename")
    drainage_dataset_id: str | None = Field(default="synthetic_simple_chain", description="Drainage dataset ID")

    runoff_parameters: RunoffParametersSchema = Field(default_factory=RunoffParametersSchema, description="Runoff parameters")
    coupling_policy: DrainageCouplingPolicySchema = Field(default_factory=DrainageCouplingPolicySchema, description="Drainage coupling policy")
    analysis_crs: str = Field(default="EPSG:32643", description="Configurable projected metric Analysis CRS")


class MassBalanceDiagnosticSchema(BaseModel):
    """Timestep mass balance accounting record."""

    timestep_index: int
    timestamp_iso: str
    previous_storage_m3: float
    rainfall_input_m3: float
    runoff_generated_m3: float
    surface_inflow_m3: float
    surface_outflow_m3: float
    drainage_inflow_m3: float
    drainage_outflow_m3: float
    infiltration_losses_m3: float
    current_storage_m3: float
    mass_balance_error_m3: float
    is_valid: bool
    warnings: list[str] = []


class FloodSimulationArtifactSchema(BaseModel):
    """Metadata container for file-backed simulation artifact outputs."""

    artifact_id: str
    simulation_id: str
    artifact_type: str  # 'MANIFEST', 'TIMESTEP_RASTER', 'DIAGNOSTICS_JSON'
    relative_path: str
    format: str  # 'GeoTIFF', 'JSON'
    created_at: str


class FloodSimulationRunResponseSchema(BaseModel):
    """Full summary response for a flood simulation run."""

    simulation_id: str
    study_area_id: str | None = None
    provider_mode: str = "REAL_DATA"
    status: str  # 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    started_at: str
    completed_at: str | None = None
    start_time: str
    horizon_minutes: int
    timestep_minutes: int
    total_timesteps: int

    rainfall_source_id: str | None = None
    terrain_dataset_id: str | None = None
    drainage_dataset_id: str | None = None

    configuration_hash: str
    engine_version: str

    input_completeness: dict[str, Any]
    mass_balance_totals: dict[str, Any]
    overall_mass_balance_error_m3: float
    is_mass_balance_valid: bool

    output_manifest_path: str
    provenance: dict[str, Any] = {}
    warnings: list[dict[str, str]] = []
    error_message: str | None = None

