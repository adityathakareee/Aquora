"""
Pydantic v2 Schemas for Phase 9 Flood Digital Twin API.

Provides typed validation contracts for Digital Twin simulation runs,
0-180 minute time slices, map artifacts, cell inspections, and diagnostic summaries.
"""

from typing import Any

from pydantic import BaseModel, Field


class DigitalTwinRunRequestSchema(BaseModel):
    """Request payload to create a Flood Digital Twin run."""

    study_area_id: str | None = Field(default="mithi_catchment_mumbai", description="Target pilot study area ID")
    zone_id: str | None = Field(default=None, description="Optional target intelligence zone ID")
    start_time: str | None = Field(default=None, description="ISO8601 simulation start timestamp")
    horizon_minutes: int = Field(default=180, ge=30, le=360, description="Simulation horizon in minutes (default 180 min / 3 hours)")
    timestep_minutes: int = Field(default=30, description="Display timestep interval in minutes (default 30 min)")

    provider_mode: str | None = Field(default="REAL_DATA", description="Data provider mode ('REAL_DATA' or 'TEST')")
    use_forecast_provider: bool = Field(default=True, description="Whether to use forecast provider for rainfall forcing")
    rainfall_source: str = Field(default="GPM_IMERG_OBSERVATION", description="Rainfall observation source identifier")
    forecast_source: str = Field(default="OPEN_METEO_ECMWF", description="Rainfall forecast source identifier")
    terrain_dataset_id: str = Field(default="FABDEM_30M_MUMBAI", description="Terrain DEM dataset identifier")
    drainage_dataset_id: str = Field(default="OSM_MUMBAI_DRAINAGE", description="Drainage network dataset identifier")
    analysis_crs: str = Field(default="EPSG:32643", description="Configured projected metric Analysis CRS for Mumbai project")


class DigitalTwinTimeSliceSchema(BaseModel):
    """Data contract for a single canonical time slice in the Digital Twin horizon."""

    run_id: str = Field(description="Digital twin run identifier")
    timestamp_iso: str = Field(description="ISO8601 timestamp for this time slice")
    timestamp_ist: str = Field(description="Display timestamp in IST (Indian Standard Time)")
    minutes_from_start: int = Field(description="Minutes elapsed from simulation start (0, 30, 60, 90, 120, 150, 180)")
    slice_label: str = Field(description="Canonical display label (NOW, +30m, +60m, +90m, +120m, +150m, +180m)")

    affected_cells_count: int = Field(description="Total inundated grid cells (depth >= 0.05m)")
    affected_area_km2: float = Field(description="Total inundated surface area in square kilometers")
    peak_severity: str = Field(description="Maximum flood severity level across catchment (DRY, LOW, MODERATE, HIGH, SEVERE)")

    severity_distribution: dict[str, int] = Field(description="Cell count distribution across severity classes")

    onset_cells_count: int = Field(default=0, description="New cells reaching inundation onset during this slice")
    input_completeness: str = Field(default="HIGH", description="Input data completeness level (HIGH, MEDIUM, LOW)")
    uncertainty_level: str = Field(default="LOW", description="Qualitative model uncertainty level (LOW, MEDIUM, HIGH)")

    cause_explanation: str = Field(description="Explainable diagnostic summary for flood risk evolution")
    artifact_path: str = Field(description="Relative path to map raster/vector artifact")


class DigitalTwinSummarySchema(BaseModel):
    """Run-level summary for the Digital Twin simulation."""

    run_id: str = Field(description="Digital twin run identifier")
    study_area_id: str = Field(description="Study area identifier")
    status: str = Field(description="Execution status (QUEUED, RUNNING, COMPLETED, FAILED)")
    created_at: str = Field(description="Creation timestamp")
    simulation_start_time: str = Field(description="Simulation start timestamp UTC")
    horizon_minutes: int = Field(description="Total simulation horizon in minutes")
    timestep_minutes: int = Field(description="Timestep interval in minutes")
    total_timesteps: int = Field(description="Total canonical time slices available")
    available_slices: list[int] = Field(description="List of available minutes_from_start slices")

    max_water_depth_m: float = Field(description="Peak water depth recorded across all slices")
    peak_affected_area_km2: float = Field(description="Maximum affected area across horizon")
    peak_time_minutes: int = Field(description="Minutes from start when peak flooding occurs")

    physical_engine_version: str = Field(description="Phase 6 physical simulation engine version")
    ml_calibration_version: str | None = Field(default="Phase8_XGBoost_Prototype_V1", description="Phase 8 ML model version if used")
    ml_calibration_status: str = Field(default="PROTOTYPE_ONLY", description="Explicit non-validated prototype label")

    input_completeness: dict[str, Any] = Field(description="Component data completeness metadata")
    provenance: dict[str, Any] = Field(description="Cryptographic provenance and dataset versioning")


class DigitalTwinRunResponseSchema(BaseModel):
    """Full execution response schema for a Digital Twin run."""

    run_id: str = Field(description="Digital twin run identifier")
    study_area_id: str = Field(description="Study area identifier")
    status: str = Field(description="Execution status")
    started_at: str = Field(description="Started timestamp UTC")
    completed_at: str | None = Field(default=None, description="Completed timestamp UTC")
    simulation_start_time: str = Field(description="Simulation start timestamp UTC")
    horizon_minutes: int = Field(description="Horizon in minutes")
    timestep_minutes: int = Field(description="Timestep in minutes")
    total_timesteps: int = Field(description="Total time slices")

    available_slices: list[int] = Field(default_factory=lambda: [0, 30, 60, 90, 120, 150, 180])
    summary: DigitalTwinSummarySchema | None = Field(default=None, description="Run summary")
    time_slices: list[DigitalTwinTimeSliceSchema] = Field(default_factory=list, description="Canonical time slices")

    output_directory: str = Field(description="Output storage directory")
    error_message: str | None = Field(default=None, description="Error message if failed")


class CellInspectionRequestSchema(BaseModel):
    """Query schema to inspect a specific cell in the Digital Twin grid."""

    grid_cell_id: str = Field(description="Stable grid cell identifier (e.g. CELL_R0240_C0190)")
    minutes_from_start: int = Field(default=60, description="Time slice minutes from start (0, 30, 60, 90, 120, 150, 180)")


class CellInspectionResponseSchema(BaseModel):
    """Operational cell inspection card response (Zero training labels exposed)."""

    run_id: str = Field(description="Digital twin run ID")
    grid_cell_id: str = Field(description="Stable grid cell identifier")
    minutes_from_start: int = Field(description="Time slice minutes")
    timestamp_iso: str = Field(description="Slice timestamp ISO8601")

    latitude: float = Field(description="WGS84 latitude")
    longitude: float = Field(description="WGS84 longitude")
    elevation_m: float = Field(description="FABDEM terrain elevation in meters")

    water_depth_m: float = Field(description="Modelled surface water depth in meters")
    severity: str = Field(description="Modelled flood severity (DRY, LOW, MODERATE, HIGH, SEVERE)")

    rainfall_intensity_mm_hr: float = Field(description="Modelled peak rainfall intensity in mm/hr")
    drainage_proxy_score: float = Field(description="Urban stormwater drainage capacity score (0-1)")
    distance_to_waterway_m: float = Field(description="Distance to Mithi River / nalla channel in meters")

    physical_model_score: float = Field(description="Phase 6 pre-event hydrological physics score (0-1)")
    prototype_ml_score: float | None = Field(default=None, description="Phase 8 secondary prototype ML calibration score (0-1)")
    ml_status_tag: str = Field(default="PROTOTYPE_ONLY", description="Explicit prototype label tag")

    input_completeness: str = Field(default="HIGH", description="Input completeness tier")
    uncertainty_level: str = Field(default="LOW", description="Qualitative model uncertainty tier")
    disclaimer: str = Field(default="Modelled flood state — not an official emergency warning.", description="Operational disclaimer")


class DigitalTwinMapSliceResponseSchema(BaseModel):
    """Compact map artifact metadata response schema (no giant per-cell JSON)."""

    run_id: str = Field(description="Digital twin run identifier")
    minutes_from_start: int = Field(description="Minutes elapsed from start")
    timestamp_iso: str = Field(description="ISO8601 timestamp")
    timestamp_ist: str = Field(description="Display timestamp in IST")
    artifact_type: str = Field(default="MAP_RASTER", description="Artifact type (MAP_RASTER)")
    format: str = Field(default="GEOTIFF", description="Map artifact format (GEOTIFF)")
    relative_path: str = Field(description="Relative path to raster map artifact")
    checksum: str | None = Field(default=None, description="SHA256 checksum of artifact")
    crs: str = Field(default="EPSG:4326", description="Canonical storage CRS")
    bounds: list[float] = Field(default_factory=lambda: [72.840, 19.040, 72.910, 19.120], description="Bounding box [min_lon, min_lat, max_lon, max_lat]")
    available_status: str = Field(default="AVAILABLE", description="Artifact availability status")
    affected_area_km2: float = Field(description="Total inundated area in km2")
    peak_severity: str = Field(description="Peak severity for this slice")
    cause_explanation: str = Field(description="Explainable diagnostic summary")
    scenario_type: str = Field(default="DEVELOPMENT SCENARIO", description="Honest scenario classification")
