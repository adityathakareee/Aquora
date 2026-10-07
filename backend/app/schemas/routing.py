"""
Pydantic v2 Schemas for Phase 10 Flood-Aware Routing & Travel Window API.

Provides typed validation contracts for route requests, candidate geometries,
time-slice spatial exposure timeline, travel window calculations, recommendations,
and explainable diagnostics.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class RouteLocationSchema(BaseModel):
    """Geographic coordinate location contract (EPSG:4326 / WGS84)."""

    latitude: float = Field(ge=-90.0, le=90.0, description="WGS84 Latitude (-90 to +90)")
    longitude: float = Field(ge=-180.0, le=180.0, description="WGS84 Longitude (-180 to +180)")
    label: str | None = Field(default=None, description="Human-readable location label or landmark")

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def validate_finite_coords(cls, v: Any) -> float:
        if v is None or not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v):
            raise ValueError("Coordinates must be valid finite numeric values")
        return float(v)


import math


class RouteAnalysisRequestSchema(BaseModel):
    """Request payload for flood-aware route analysis and travel window calculation."""

    origin: RouteLocationSchema = Field(description="Origin location (lat, lon)")
    destination: RouteLocationSchema = Field(description="Destination location (lat, lon)")
    digital_twin_run_id: str | None = Field(default=None, description="Optional target Digital Twin run ID (defaults to latest completed)")
    departure_time: str | None = Field(default=None, description="Optional ISO8601 departure reference time")
    max_acceptable_severity: str = Field(default="HIGH", description="Maximum acceptable flood severity threshold before route hazard")
    max_alternatives: int = Field(default=3, ge=1, le=5, description="Maximum number of candidate routes to evaluate")
    provider_mode: str | None = Field(default=None, description="Optional routing provider mode: REAL_DATA (OSRM only), SYNTHETIC (dev/test only), or None (defaults to settings.ROUTING_PROVIDER)")
    zone_id: str | None = Field(default=None, description="Optional intelligence zone identifier (defaults to deep_mumbai_mithi)")


class RoutePointExposureSchema(BaseModel):
    """Spatial exposure at a single route sample point for a time slice."""

    distance_m: float = Field(description="Cumulative route distance from origin in meters")
    longitude: float = Field(description="WGS84 longitude")
    latitude: float = Field(description="WGS84 latitude")
    grid_cell_id: str = Field(description="Associated Phase 9 Digital Twin grid cell ID")
    water_depth_m: float = Field(description="Modelled surface water depth in meters")
    severity: str = Field(description="Modelled flood severity (DRY, LOW, MODERATE, HIGH, SEVERE, UNKNOWN)")
    minutes_from_start: int = Field(description="Time slice minutes from simulation start")


class TimeSliceExposureSchema(BaseModel):
    """Route exposure summary for a single canonical Digital Twin time slice."""

    minutes_from_start: int = Field(description="Minutes elapsed from simulation start (0, 30, 60, 90, 120, 150, 180)")
    status: str = Field(description="Route status (CLEAR, LOW_EXPOSURE, MODERATE_EXPOSURE, HIGH_RISK, SEVERE_RISK, UNKNOWN)")
    affected_distance_m: float = Field(description="Total route distance meeting or exceeding hazard threshold in meters")
    affected_percentage: float = Field(description="Percentage of route distance affected by flood hazard (0-100%)")
    peak_severity: str = Field(description="Peak flood severity class encountered along route")
    peak_water_depth_m: float = Field(description="Peak water depth encountered along route in meters")
    first_affected_km: float | None = Field(default=None, description="Distance from origin to first affected point in km")
    unknown_percentage: float = Field(default=0.0, description="Percentage of route with unmapped/unknown flood state")


class TravelWindowSchema(BaseModel):
    """Usable Travel Window calculation and status."""

    estimated_travel_time_min: float = Field(description="Estimated routing travel duration in minutes (no live traffic)")
    route_flood_onset_min: int | None = Field(default=None, description="Earliest Digital Twin slice minutes when route impact occurs")
    safety_buffer_min: int = Field(default=15, description="Configurable safety buffer in minutes subtracted from onset")
    usable_travel_window_min: int | None = Field(default=None, description="Usable window before flood onset in minutes (clamped at 0)")
    status: str = Field(description="Travel window status (SAFE_WINDOW, LIMITED_WINDOW, NO_SAFE_WINDOW, UNKNOWN, NO_MODELED_ONSET_WITHIN_HORIZON)")


class RouteSegmentSchema(BaseModel):
    """Route geometry line segment tagged with flood severity for map visualization."""

    segment_id: str = Field(description="Segment identifier")
    start_coordinates: list[float] = Field(description="[lon, lat] start coordinate")
    end_coordinates: list[float] = Field(description="[lon, lat] end coordinate")
    severity: str = Field(description="Segment flood severity (DRY, LOW, MODERATE, HIGH, SEVERE, UNKNOWN)")
    water_depth_m: float = Field(description="Peak water depth along segment in meters")
    grid_cell_id: str = Field(description="Associated grid cell ID")
    is_unknown: bool = Field(default=False, description="True if flood state is unknown/nodata")


class RouteCandidateSchema(BaseModel):
    """Full candidate route result with spatial geometry, exposure timeline, and travel window."""

    route_id: str = Field(description="Candidate route identifier")
    summary: str = Field(description="Short route label or landmark description")
    provider: str = Field(description="Routing provider identifier (SYNTHETIC_ROUTER, OSRM_ROUTER)")
    provider_mode: str = Field(description="Provider mode (SYNTHETIC, LIVE_OSRM)")
    distance_m: float = Field(description="Total route distance in meters")
    estimated_duration_s: float = Field(description="Estimated route travel duration in seconds")
    geometry_geojson: dict[str, Any] = Field(description="GeoJSON LineString geometry contract")
    travel_window: TravelWindowSchema = Field(description="Calculated travel window metrics")
    recommendation: str = Field(description="Route recommendation (GO_NOW, ALTERNATE_RECOMMENDED, AVOID, UNKNOWN)")
    explanation: str = Field(description="Human-readable explainable causal rationale")
    time_slice_exposures: list[TimeSliceExposureSchema] = Field(default_factory=list, description="7-slice route exposure timeline")
    segments: list[RouteSegmentSchema] = Field(default_factory=list, description="Visualization segments for map rendering")


class RouteAnalysisResponseSchema(BaseModel):
    """Top-level route analysis response schema for Phase 10 API."""

    run_id: str = Field(description="Routing run identifier")
    digital_twin_run_id: str = Field(description="Selected Digital Twin run ID")
    recommended_route_id: str = Field(description="ID of primary recommended candidate route")
    recommendation: str = Field(description="Top-level recommendation (GO_NOW, ALTERNATE_RECOMMENDED, AVOID, UNKNOWN)")
    explanation: str = Field(description="Top-level causal explanation text")
    travel_window: TravelWindowSchema = Field(description="Primary route travel window metrics")
    candidates: list[RouteCandidateSchema] = Field(default_factory=list, description="All evaluated candidate routes")
    warnings: list[str] = Field(default_factory=list, description="Data quality, synthetic provider, and uncertainty warnings")
    provenance: dict[str, Any] = Field(description="Full routing provenance and dataset version metadata")
