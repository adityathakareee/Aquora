"""
Phase 15 Alerts, Explainability, and Audit Pydantic Schemas.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AlertType(str, Enum):
    FLOOD_ONSET = "FLOOD_ONSET"
    FLOOD_SEVERITY_ESCALATION = "FLOOD_SEVERITY_ESCALATION"
    HIGH_SEVERE_FLOOD_RISK = "HIGH_SEVERE_FLOOD_RISK"
    TRAVEL_WINDOW_CLOSING = "TRAVEL_WINDOW_CLOSING"
    ROUTE_AVOID = "ROUTE_AVOID"
    CRITICAL_ACCESS_THREAT = "CRITICAL_ACCESS_THREAT"
    CRITICAL_ACCESS_LOSS = "CRITICAL_ACCESS_LOSS"
    PROTECT_CITY_PRIORITY = "PROTECT_CITY_PRIORITY"
    GROUND_TRUTH_CONFLICT = "GROUND_TRUTH_CONFLICT"
    MODEL_INPUT_DEGRADED = "MODEL_INPUT_DEGRADED"
    MODEL_UNCERTAINTY = "MODEL_UNCERTAINTY"
    SIMULATOR_SCENARIO_RESULT = "SIMULATOR_SCENARIO_RESULT"
    SYSTEM_DATA_QUALITY = "SYSTEM_DATA_QUALITY"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    EXPIRED = "EXPIRED"
    SUPPRESSED = "SUPPRESSED"
    FAILED = "FAILED"


class EvidenceStrength(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    CORROBORATED = "CORROBORATED"
    CONFIRMED = "CONFIRMED"


class AlertGenerateRequestSchema(BaseModel):
    digital_twin_run_id: str | None = Field(None, description="Authoritative Phase 9 Digital Twin Run ID")
    travel_window_run_id: str | None = Field(None, description="Authoritative Phase 10 Travel Window / Routing Run ID")
    critical_access_run_id: str | None = Field(None, description="Authoritative Phase 11 Critical Access Run ID")
    protect_city_run_id: str | None = Field(None, description="Authoritative Phase 12 Protect City Run ID")
    ground_truth_run_id: str | None = Field(None, description="Authoritative Phase 13 Ground Truth Verification Run ID")
    simulator_run_id: str | None = Field(None, description="Authoritative Phase 14 Simulator Run ID")
    zone_id: str | None = Field(None, description="Optional target intelligence zone ID (defaults to Mumbai Deep Zone)")

    @model_validator(mode="after")
    def validate_at_least_one_source(self) -> "AlertGenerateRequestSchema":
        sources = [
            self.digital_twin_run_id,
            self.travel_window_run_id,
            self.critical_access_run_id,
            self.protect_city_run_id,
            self.ground_truth_run_id,
            self.simulator_run_id,
        ]
        if not any(sources):
            raise ValueError("At least one valid authoritative source run_id must be provided for alert generation.")
        return self


class AlertAcknowledgeSchema(BaseModel):
    actor_reference: str = Field("OPERATOR_PRIMARY", description="Actor identifier acknowledging the alert")
    reason: str | None = Field(None, description="Optional acknowledgement rationale note")


class AlertResolveSchema(BaseModel):
    actor_reference: str = Field("OPERATOR_PRIMARY", description="Actor identifier resolving the alert")
    resolution_reason: str = Field(..., min_length=3, description="Mandatory resolution reason")


class AlertSuppressSchema(BaseModel):
    actor_reference: str = Field("OPERATOR_PRIMARY", description="Actor identifier suppressing the alert")
    suppression_reason: str = Field(..., min_length=3, description="Mandatory suppression rationale")


class AlertEvidenceResponseSchema(BaseModel):
    evidence_id: str
    alert_id: str
    source_phase: str
    source_run_id: str
    source_artifact_id: str | None = None
    evidence_type: str
    metric: str
    value: float | None = None
    units: str | None = None
    timestamp: str | None = None
    evidence_strength: EvidenceStrength
    details: dict[str, Any] = Field(default_factory=dict)


class ExplainabilityStepResponseSchema(BaseModel):
    step_id: str
    alert_id: str
    sequence: int
    category: str  # WHAT, WHY, WHEN, WHERE, HOW_CERTAIN, WHAT_SHOULD_I_DO, EVIDENCE
    statement: str
    source_phase: str
    source_run_id: str
    source_metric: str | None = None
    source_value: float | None = None
    units: str | None = None
    slice_minutes: int | None = None


class AlertAuditEventResponseSchema(BaseModel):
    event_id: str
    alert_id: str
    event_type: str
    previous_status: AlertStatus | None = None
    new_status: AlertStatus
    timestamp: str
    actor_type: str
    actor_reference: str
    reason: str | None = None
    source_run_id: str | None = None
    event_metadata: dict[str, Any] = Field(default_factory=dict)


class AlertProvenanceResponseSchema(BaseModel):
    alert_id: str
    fingerprint: str
    source_phase: str
    source_run_id: str
    sources: dict[str, Any]
    configuration_version: str
    generated_at: str
    provenance_hash: str
    details: dict[str, Any] = Field(default_factory=dict)


class AlertConfigurationSchema(BaseModel):
    configuration_id: str
    configuration_version: str
    thresholds: dict[str, Any]
    enabled: bool
    created_at: str


class AlertResponseSchema(BaseModel):
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    summary: str
    affected_entity_type: str
    affected_entity_id: str
    condition_key: str
    fingerprint: str
    source_phase: str
    source_run_id: str
    sources: dict[str, Any]
    input_completeness: float
    model_status: str
    evidence_strength: EvidenceStrength
    uncertainty_status: str
    recommended_action: str
    governance_notice: str
    configuration_version: str
    generated_at: str
    updated_at: str
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None
    resolution_reason: str | None = None
    suppressed_at: str | None = None
    suppressed_by: str | None = None
    suppression_reason: str | None = None
    expires_at: str | None = None


class AlertListResponseSchema(BaseModel):
    total_count: int
    alerts: list[AlertResponseSchema]
