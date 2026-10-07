"""
Pydantic v2 Schemas for Phase 12 Protect the City API.

Defines strict input request and output response validation contracts for:
- InterventionCandidateSchema
- PriorityComponentBreakdownSchema
- ProtectCityRecommendationSchema
- ProtectCityRequestSchema
- ProtectCityResponseSchema
"""

import math
from typing import Any

from pydantic import BaseModel, Field, field_validator

INTERVENTION_TAXONOMY = [
    "DRAINAGE_CLEARANCE",
    "DRAINAGE_CAPACITY_REVIEW",
    "PUMP_OR_DEWATERING_REVIEW",
    "TEMPORARY_BARRIER_REVIEW",
    "ROAD_ACCESS_PROTECTION",
    "CRITICAL_FACILITY_ACCESS_PROTECTION",
    "TRAFFIC_CONTROL_REVIEW",
    "OUTFALL_CAPACITY_REVIEW",
    "STORAGE_REVIEW",
    "SITE_INSPECTION",
    "OTHER_REVIEW",
]

PRIORITY_CATEGORIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
EXPECTED_BENEFIT_CATEGORIES = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
FEASIBILITY_CATEGORIES = ["FEASIBLE_REVIEW", "UNKNOWN", "NOT_ASSESSED"]
UNCERTAINTY_CATEGORIES = ["HIGH", "MEDIUM", "LOW", "UNKNOWN"]


class InterventionCandidateSchema(BaseModel):
    """Intervention opportunity candidate schema representation."""

    candidate_id: str = Field(description="Unique intervention candidate identifier")
    name: str = Field(description="Intervention candidate asset or corridor name")
    candidate_type: str = Field(description="Intervention category taxonomy (DRAINAGE_CLEARANCE, ROAD_ACCESS_PROTECTION, etc.)")
    latitude: float = Field(description="Candidate latitude in EPSG:4326")
    longitude: float = Field(description="Candidate longitude in EPSG:4326")
    source: str = Field(description="Data source name")
    source_id: str | None = Field(default=None, description="Source-specific record ID")
    source_type: str = Field(default="SYNTHETIC", description="Source type (AUTHORITATIVE, INSTITUTIONAL, OPEN_GOVERNMENT, OSM, SYNTHETIC)")
    verification_status: str = Field(default="UNVERIFIED", description="Verification status")
    provider_mode: str = Field(default="SYNTHETIC", description="Provider mode (SYNTHETIC, LOCAL_VERIFIED)")
    environment: str = Field(default="DEVELOPMENT_ONLY", description="Environment mode ('DEVELOPMENT_ONLY', 'TEST_ONLY', 'PRODUCTION')")
    affected_asset_type: str | None = Field(default=None, description="Type of affected municipal asset if known")
    affected_asset_id: str | None = Field(default=None, description="ID of affected municipal asset if known")
    summary: str = Field(default="", description="Short candidate description")
    provenance: dict[str, Any] = Field(default_factory=dict, description="Full source provenance metadata")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if v is None or math.isnan(v) or math.isinf(v) or not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude must be finite value between -90 and +90, got {v}")
        return float(v)

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if v is None or math.isnan(v) or math.isinf(v) or not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude must be finite value between -180 and +180, got {v}")
        return float(v)

    @field_validator("candidate_type")
    @classmethod
    def validate_candidate_type(cls, v: str) -> str:
        type_upper = v.upper()
        if type_upper not in INTERVENTION_TAXONOMY:
            raise ValueError(f"Candidate type '{v}' not recognized in intervention taxonomy. Expected one of {INTERVENTION_TAXONOMY}")
        return type_upper


class PriorityComponentBreakdownSchema(BaseModel):
    """Decomposable priority components breakdown for explainable decision support."""

    flood_severity_score: float = Field(description="Flood severity component contribution (0-30)")
    time_to_threat_score: float = Field(description="Threat onset timing component contribution (0-25)")
    critical_access_score: float = Field(description="Phase 11 critical facility access contribution (0-25)")
    route_impact_score: float = Field(description="Phase 10 route disruption contribution (0-20)")
    terrain_drainage_score: float = Field(description="Phase 4/5 terrain & drainage evidence contribution (0-15)")
    evidence_completeness_score: float = Field(description="Data completeness & verification penalty/bonus (-10 to +10)")
    raw_priority_score: float = Field(description="Unclamped raw priority score sum (-10 to 125)")
    final_priority_score: float = Field(description="Clamped operational priority score (0 to 125)")
    total_score: float = Field(description="Total bounded priority score (0-125)")
    ranking_category: str = Field(description="Resulting priority category (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN)")


class ProtectCityRecommendationSchema(BaseModel):
    """Prioritized intervention opportunity recommendation schema."""

    candidate: InterventionCandidateSchema = Field(description="Target intervention candidate metadata")
    priority: str = Field(description="Priority category (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN)")
    raw_priority_score: float = Field(default=0.0, description="Unclamped raw priority score (-10 to 125)")
    final_priority_score: float = Field(default=0.0, description="Clamped operational priority score (0 to 125)")
    priority_score: float = Field(description="Bounded numerical priority score for deterministic ranking (0 to 125)")
    priority_component_breakdown: PriorityComponentBreakdownSchema = Field(description="Decomposable component breakdown")
    intervention_type: str = Field(description="Recommended intervention category from controlled taxonomy")
    first_threat_minutes: int | None = Field(default=None, description="Earliest Digital Twin slice (min) when flood threat emerges")
    first_high_severity_minutes: int | None = Field(default=None, description="Earliest slice (min) when HIGH/SEVERE flood occurs")
    peak_severity: str = Field(description="Peak flood severity class encountered (DRY, LOW, MODERATE, HIGH, SEVERE, UNKNOWN)")
    peak_severity_minutes: int | None = Field(default=None, description="Time slice (min) of peak flood severity")
    expected_benefit: str = Field(description="Qualitative expected benefit category (HIGH, MEDIUM, LOW, UNKNOWN)")
    feasibility_status: str = Field(description="Operational engineering feasibility status (FEASIBLE_REVIEW, UNKNOWN, NOT_ASSESSED)")
    uncertainty_status: str = Field(description="Evidence uncertainty category (HIGH, MEDIUM, LOW, UNKNOWN)")
    affected_route_count: int = Field(default=0, description="Number of Phase 10 candidate routes impacted")
    affected_critical_facility_count: int = Field(default=0, description="Number of Phase 11 critical facilities impacted")
    affected_facility_ids: list[str] = Field(default_factory=list, description="IDs of affected critical facilities")
    route_impact_context: str = Field(default="", description="Phase 10 route impact explanation note")
    critical_access_context: str = Field(default="", description="Phase 11 critical access explanation note")
    drainage_context: str = Field(default="", description="Phase 5 drainage network explanation note")
    terrain_context: str = Field(default="", description="Phase 4 terrain flow accumulation explanation note")
    explanation: str = Field(description="Full cause-chain explanation (PREDICTION -> IMPACT -> CRITICALITY -> DECISION -> ACTION)")
    warnings: list[str] = Field(default_factory=list, description="Quality, synthetic fixture, and uncertainty warnings")
    provenance: dict[str, Any] = Field(description="Full audit provenance and dataset version metadata")


class ProtectCityRequestSchema(BaseModel):
    """Input request schema for Protect the City intervention analysis."""

    digital_twin_run_id: str | None = Field(default=None, description="Optional Digital Twin run ID (defaults to latest completed run)")
    routing_run_id: str | None = Field(default=None, description="Optional Phase 10 routing run ID for route context")
    critical_access_run_id: str | None = Field(default=None, description="Optional Phase 11 critical access run ID for facility context")
    minimum_priority: str = Field(default="LOW", description="Minimum priority threshold filter ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')")
    candidate_types: list[str] | None = Field(default=None, description="Optional filter by intervention candidate categories")
    priority_limit: int = Field(default=20, ge=1, le=100, description="Maximum number of recommendations to return")
    time_horizon_minutes: int | None = Field(default=180, description="Optional time horizon filter in minutes (30, 60, 120, 180)")
    zone_id: str | None = Field(default=None, description="Optional intelligence zone identifier (defaults to deep_mumbai_mithi)")


class ProtectCityResponseSchema(BaseModel):
    """Top-level response schema for Phase 12 Protect the City API."""

    run_id: str = Field(description="Unique Protect the City run identifier")
    digital_twin_run_id: str = Field(description="Selected Phase 9 Digital Twin run ID")
    routing_run_id: str | None = Field(default=None, description="Phase 10 routing run ID if used")
    critical_access_run_id: str | None = Field(default=None, description="Phase 11 critical access run ID if used")
    generated_at: str = Field(description="ISO8601 generation timestamp")
    total_candidates: int = Field(description="Total candidate opportunities evaluated")
    recommendations: list[ProtectCityRecommendationSchema] = Field(default_factory=list, description="Prioritized recommendations")
    priority_counts: dict[str, int] = Field(description="Counts per priority level (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN)")
    warnings: list[str] = Field(default_factory=list, description="Data completeness, synthetic, and governance warnings")
    provenance: dict[str, Any] = Field(description="Full audit provenance and governance metadata")
    uncertainty_summary: dict[str, Any] = Field(description="Overall evidence uncertainty summary")
