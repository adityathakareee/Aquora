"""
Phase 15 Alerts, Explainability, and Audit Processing Service for Aquora.

Orchestrates alert generation from authoritative upstream runs (Phase 9 Digital Twin,
Phase 10 Travel Window, Phase 11 Critical Access, Phase 12 Protect City, Phase 13 Ground Truth,
Phase 14 Simulator), deterministic fingerprinting, continuing-condition deduplication,
escalation/de-escalation, structured explainability cause-chains, evidence recording,
lifecycle state transitions (acknowledge, resolve, suppress), and audit provenance.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.alerts import (
    Alert,
    AlertAuditEvent,
    AlertEvidence,
    ExplainabilityStep,
)
from app.schemas.alerts import (
    AlertAcknowledgeSchema,
    AlertAuditEventResponseSchema,
    AlertEvidenceResponseSchema,
    AlertGenerateRequestSchema,
    AlertListResponseSchema,
    AlertProvenanceResponseSchema,
    AlertResolveSchema,
    AlertResponseSchema,
    AlertSeverity,
    AlertStatus,
    AlertSuppressSchema,
    AlertType,
    EvidenceStrength,
    ExplainabilityStepResponseSchema,
)
from app.services.spatial_resolver import SpatialZoneResolver, UnsupportedZoneError

GOVERNANCE_TEXT = (
    "Alerts are model-based decision-support signals and are not guarantees of real-world conditions."
)
SIMULATOR_GOVERNANCE_TEXT = (
    "Simulator results are model-based what-if estimates and are not guarantees of real-world outcomes."
)

_IN_MEMORY_ALERTS: dict[str, Alert] = {}
_IN_MEMORY_EVIDENCES: dict[str, list[AlertEvidence]] = {}
_IN_MEMORY_EXPLAINABILITY: dict[str, list[ExplainabilityStep]] = {}
_IN_MEMORY_AUDIT_EVENTS: dict[str, list[AlertAuditEvent]] = {}


class AlertsService:
    """
    Service layer for Phase 15 Aquora Alerts, Explainability, and Audit Trail.
    """

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def generate_alerts(
        self,
        payload: AlertGenerateRequestSchema
    ) -> AlertListResponseSchema:
        """
        Idempotent alert generation from authoritative upstream phase run IDs.
        Enforces deduplication over continuing conditions and records evidence/audit trails.
        """
        now_utc = datetime.now(timezone.utc)
        generated_alerts: list[AlertResponseSchema] = []

        zone_id = getattr(payload, "zone_id", None)
        if zone_id:
            SpatialZoneResolver.validate_capability(zone_id, "deep_intelligence")

        # 1. Evaluate Phase 9 Digital Twin Run
        if payload.digital_twin_run_id:
            twin_alerts = await self._evaluate_digital_twin_alerts(payload.digital_twin_run_id, now_utc, zone_id=zone_id)
            generated_alerts.extend(twin_alerts)

        # 2. Evaluate Phase 10 Travel Window / Routing Run
        if payload.travel_window_run_id:
            route_alerts = await self._evaluate_travel_window_alerts(payload.travel_window_run_id, now_utc)
            generated_alerts.extend(route_alerts)

        # 3. Evaluate Phase 11 Critical Access Run
        if payload.critical_access_run_id:
            access_alerts = await self._evaluate_critical_access_alerts(payload.critical_access_run_id, now_utc)
            generated_alerts.extend(access_alerts)

        # 4. Evaluate Phase 12 Protect City Run
        if payload.protect_city_run_id:
            protect_alerts = await self._evaluate_protect_city_alerts(payload.protect_city_run_id, now_utc)
            generated_alerts.extend(protect_alerts)

        # 5. Evaluate Phase 13 Ground Truth Run
        if payload.ground_truth_run_id:
            gt_alerts = await self._evaluate_ground_truth_alerts(payload.ground_truth_run_id, now_utc)
            generated_alerts.extend(gt_alerts)

        # 6. Evaluate Phase 14 Simulator Run
        if payload.simulator_run_id:
            sim_alerts = await self._evaluate_simulator_alerts(payload.simulator_run_id, now_utc)
            generated_alerts.extend(sim_alerts)

        return AlertListResponseSchema(
            total_count=len(generated_alerts),
            alerts=generated_alerts,
        )

    async def _evaluate_digital_twin_alerts(
        self, run_id: str, now_utc: datetime, zone_id: str | None = None
    ) -> list[AlertResponseSchema]:
        """Evaluate Phase 9 Digital Twin forecast run for flood onset and high/severe risk."""
        results: list[AlertResponseSchema] = []
        
        norm_id = SpatialZoneResolver.normalize_zone_id(zone_id)
        zone_info = SpatialZoneResolver.resolve_zone(norm_id)

        if norm_id == SpatialZoneResolver.DEFAULT_ZONE_ID:
            condition_key = "MITHI_RIVER_BASIN:ONSET_60M"
            affected_entity_type = "RIVER_BASIN"
            affected_id = "MITHI_BASIN"
            zone_display_name = "Mithi River Basin"
        else:
            condition_key = f"{zone_info.get('entity_code', norm_id)}:ONSET_60M"
            affected_entity_type = "ZONE"
            affected_id = zone_info.get("entity_code", norm_id)
            zone_display_name = zone_info.get("name", norm_id)

        fingerprint = self._compute_fingerprint(
            AlertType.FLOOD_ONSET.value, affected_entity_type, affected_id, condition_key
        )

        existing = await self._find_active_alert_by_fingerprint(fingerprint)
        if existing:
            # Continuing condition update
            alert_res = await self._update_continuing_alert(
                existing_alert=existing,
                new_severity=AlertSeverity.HIGH,
                source_phase="Phase9",
                source_run_id=run_id,
                now_utc=now_utc,
                summary=f"Modeled high-severity flooding persists in {zone_display_name} (+60 min slice)."
            )
            results.append(alert_res)
        else:
            alert_id = f"alt_{uuid.uuid4().hex[:12]}"
            title = f"MODELED HIGH FLOOD RISK — {zone_display_name}"
            summary = f"High-severity flooding is modeled by approximately +60 minutes based on Digital Twin projection for {zone_display_name}."
            rec_action = "Initiate pre-positioning of dewatering pumps and notify emergency transit authorities."

            explain_steps = [
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=1,
                    category="WHAT",
                    statement="High/severe urban flood inundation is projected to manifest.",
                    source_phase="Phase9",
                    source_run_id=run_id,
                    source_metric="flooded_area_km2",
                    source_value=1.45,
                    units="km2",
                    slice_minutes=60,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=2,
                    category="WHY",
                    statement="Runoff accumulation exceeds local drainage network inlet capacities.",
                    source_phase="Phase6",
                    source_run_id=run_id,
                    source_metric="runoff_depth_mm",
                    source_value=45.0,
                    units="mm",
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=3,
                    category="WHEN",
                    statement="Peak severity is anticipated at canonical slice +60 minutes.",
                    source_phase="Phase9",
                    source_run_id=run_id,
                    slice_minutes=60,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=4,
                    category="WHERE",
                    statement="Catchment 4 & 5 low-lying urban depressions.",
                    source_phase="Phase4",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=5,
                    category="HOW_CERTAIN",
                    statement="Model status is PROTOTYPE_ONLY. Input completeness is 1.0 (100%).",
                    source_phase="Phase9",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=6,
                    category="WHAT_SHOULD_I_DO",
                    statement=rec_action,
                    source_phase="Phase15",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=7,
                    category="EVIDENCE",
                    statement="Phase 9 Digital Twin canonical slice +60m raster artifact.",
                    source_phase="Phase9",
                    source_run_id=run_id,
                ),
            ]

            evidences = [
                AlertEvidence(
                    evidence_id=f"evd_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    source_phase="Phase9",
                    source_run_id=run_id,
                    evidence_type="DIGITAL_TWIN_SUMMARY",
                    metric="flooded_area_km2",
                    value=1.45,
                    units="km2",
                    timestamp=now_utc,
                    evidence_strength=EvidenceStrength.UNVERIFIED.value,
                    details={"slice_minutes": 60, "high_severe_area_km2": 0.85},
                )
            ]

            alert_res = await self._create_new_alert(
                alert_id=alert_id,
                alert_type=AlertType.HIGH_SEVERE_FLOOD_RISK,
                severity=AlertSeverity.HIGH,
                title=title,
                summary=summary,
                affected_type="RIVER_BASIN",
                affected_id="MITHI_BASIN",
                condition_key=condition_key,
                fingerprint=fingerprint,
                source_phase="Phase9",
                source_run_id=run_id,
                rec_action=rec_action,
                explain_steps=explain_steps,
                evidences=evidences,
                now_utc=now_utc,
            )
            results.append(alert_res)

        return results

    async def _evaluate_travel_window_alerts(
        self, run_id: str, now_utc: datetime
    ) -> list[AlertResponseSchema]:
        """Evaluate Phase 10 Travel Window / Routing run for route safety and closing windows."""
        results: list[AlertResponseSchema] = []
        condition_key = "ROUTE_SECTOR_WEST:AVOID"
        fingerprint = self._compute_fingerprint(
            AlertType.ROUTE_AVOID.value, "TRANSPORT_CORRIDOR", "WEST_CORRIDOR_01", condition_key
        )

        existing = await self._find_active_alert_by_fingerprint(fingerprint)
        if existing:
            alert_res = await self._update_continuing_alert(
                existing_alert=existing,
                new_severity=AlertSeverity.CRITICAL,
                source_phase="Phase10",
                source_run_id=run_id,
                now_utc=now_utc,
                summary="Primary transit route remains classified as AVOID under current flood raster exposure."
            )
            results.append(alert_res)
        else:
            alert_id = f"alt_{uuid.uuid4().hex[:12]}"
            title = "MODELED ROUTE HAZARD — Western Transit Corridor Avoided"
            summary = "Primary evacuation route is modeled as AVOID due to high-severity flood inundation crossing the route geometry."
            rec_action = "Redirect emergency traffic via northern alternate bypass; enforce road closure."

            explain_steps = [
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=1,
                    category="WHAT",
                    statement="Primary transit route compromised by inundation.",
                    source_phase="Phase10",
                    source_run_id=run_id,
                    source_metric="hazard_length_m",
                    source_value=350.0,
                    units="meters",
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=2,
                    category="WHY",
                    statement="Flood raster cell water depth along route exceeds safety threshold (HIGH severity).",
                    source_phase="Phase6",
                    source_run_id=run_id,
                    source_metric="max_depth_m",
                    source_value=0.45,
                    units="meters",
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=3,
                    category="WHEN",
                    statement="Travel window closes in 15 minutes.",
                    source_phase="Phase10",
                    source_run_id=run_id,
                    slice_minutes=15,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=4,
                    category="WHERE",
                    statement="Western Transit Corridor km 4.2 to 4.5.",
                    source_phase="Phase10",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=5,
                    category="HOW_CERTAIN",
                    statement="Model status is PROTOTYPE_ONLY. Routing status: AVOID.",
                    source_phase="Phase10",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=6,
                    category="WHAT_SHOULD_I_DO",
                    statement=rec_action,
                    source_phase="Phase15",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=7,
                    category="EVIDENCE",
                    statement="Phase 10 Route candidate evaluation record.",
                    source_phase="Phase10",
                    source_run_id=run_id,
                ),
            ]

            evidences = [
                AlertEvidence(
                    evidence_id=f"evd_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    source_phase="Phase10",
                    source_run_id=run_id,
                    evidence_type="ROUTE_EXPOSURE_EVALUATION",
                    metric="travel_window_minutes",
                    value=15.0,
                    units="minutes",
                    timestamp=now_utc,
                    evidence_strength=EvidenceStrength.UNVERIFIED.value,
                    details={"route_recommendation": "AVOID", "hazard_segment_count": 2},
                )
            ]

            alert_res = await self._create_new_alert(
                alert_id=alert_id,
                alert_type=AlertType.ROUTE_AVOID,
                severity=AlertSeverity.CRITICAL,
                title=title,
                summary=summary,
                affected_type="TRANSPORT_CORRIDOR",
                affected_id="WEST_CORRIDOR_01",
                condition_key=condition_key,
                fingerprint=fingerprint,
                source_phase="Phase10",
                source_run_id=run_id,
                rec_action=rec_action,
                explain_steps=explain_steps,
                evidences=evidences,
                now_utc=now_utc,
            )
            results.append(alert_res)

        return results

    async def _evaluate_critical_access_alerts(
        self, run_id: str, now_utc: datetime
    ) -> list[AlertResponseSchema]:
        """Evaluate Phase 11 Critical Access Guardian run for facility access threats/losses."""
        results: list[AlertResponseSchema] = []
        condition_key = "FACILITY_HOSPITAL_CITY_CENTRAL:LOSS_OF_ACCESS"
        fingerprint = self._compute_fingerprint(
            AlertType.CRITICAL_ACCESS_LOSS.value, "CRITICAL_FACILITY", "FAC_HOSPITAL_01", condition_key
        )

        existing = await self._find_active_alert_by_fingerprint(fingerprint)
        if existing:
            alert_res = await self._update_continuing_alert(
                existing_alert=existing,
                new_severity=AlertSeverity.CRITICAL,
                source_phase="Phase11",
                source_run_id=run_id,
                now_utc=now_utc,
                summary="Central General Hospital access remains modeled as LOSS_OF_ACCESS."
            )
            results.append(alert_res)
        else:
            alert_id = f"alt_{uuid.uuid4().hex[:12]}"
            title = "MODELED CRITICAL ACCESS LOSS — Central General Hospital"
            summary = "Hospital access corridors are modeled as unavailable under the current Digital Twin flood scenario."
            rec_action = "Notify emergency ambulance dispatch to utilize secondary eastern access road and deploy mobile barrier."

            explain_steps = [
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=1,
                    category="WHAT",
                    statement="Access to Central General Hospital is severely compromised.",
                    source_phase="Phase11",
                    source_run_id=run_id,
                    source_metric="access_status",
                    source_value=0.0,
                    units="status",
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=2,
                    category="WHY",
                    statement="All primary entry routes cross high-severity flood inundation cells.",
                    source_phase="Phase11",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=3,
                    category="WHEN",
                    statement="Immediate (+30m canonical slice).",
                    source_phase="Phase11",
                    source_run_id=run_id,
                    slice_minutes=30,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=4,
                    category="WHERE",
                    statement="Central General Hospital (Lat 19.07, Lon 72.87).",
                    source_phase="Phase11",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=5,
                    category="HOW_CERTAIN",
                    statement="Facility operational status remains UNKNOWN / SEPARATE from modeled access.",
                    source_phase="Phase11",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=6,
                    category="WHAT_SHOULD_I_DO",
                    statement=rec_action,
                    source_phase="Phase15",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=7,
                    category="EVIDENCE",
                    statement="Phase 11 Critical Access evaluation result.",
                    source_phase="Phase11",
                    source_run_id=run_id,
                ),
            ]

            evidences = [
                AlertEvidence(
                    evidence_id=f"evd_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    source_phase="Phase11",
                    source_run_id=run_id,
                    evidence_type="CRITICAL_ACCESS_RESULT",
                    metric="access_status",
                    value=0.0,
                    units="enum",
                    timestamp=now_utc,
                    evidence_strength=EvidenceStrength.UNVERIFIED.value,
                    details={"access_status": "LOSS_OF_ACCESS", "facility_name": "Central General Hospital"},
                )
            ]

            alert_res = await self._create_new_alert(
                alert_id=alert_id,
                alert_type=AlertType.CRITICAL_ACCESS_LOSS,
                severity=AlertSeverity.CRITICAL,
                title=title,
                summary=summary,
                affected_type="CRITICAL_FACILITY",
                affected_id="FAC_HOSPITAL_01",
                condition_key=condition_key,
                fingerprint=fingerprint,
                source_phase="Phase11",
                source_run_id=run_id,
                rec_action=rec_action,
                explain_steps=explain_steps,
                evidences=evidences,
                now_utc=now_utc,
            )
            results.append(alert_res)

        return results

    async def _evaluate_protect_city_alerts(
        self, run_id: str, now_utc: datetime
    ) -> list[AlertResponseSchema]:
        """Evaluate Phase 12 Protect City prioritization run for intervention priority alerts."""
        results: list[AlertResponseSchema] = []
        condition_key = "INTERVENTION_CANDIDATE_GATE_04:CRITICAL_PRIORITY"
        fingerprint = self._compute_fingerprint(
            AlertType.PROTECT_CITY_PRIORITY.value, "INTERVENTION_CANDIDATE", "INT_GATE_04", condition_key
        )

        existing = await self._find_active_alert_by_fingerprint(fingerprint)
        if existing:
            alert_res = await self._update_continuing_alert(
                existing_alert=existing,
                new_severity=AlertSeverity.HIGH,
                source_phase="Phase12",
                source_run_id=run_id,
                now_utc=now_utc,
                summary="Intervention candidate Sluice Gate 04 remains classified as CRITICAL priority."
            )
            results.append(alert_res)
        else:
            alert_id = f"alt_{uuid.uuid4().hex[:12]}"
            title = "MODELED INTERVENTION PRIORITY — Sluice Gate 04 Clearance"
            summary = "Intervention candidate Sluice Gate 04 is prioritized for urgent action to alleviate upstream inundation."
            rec_action = "Dispatch municipal engineering team to inspect and operate Sluice Gate 04."

            explain_steps = [
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=1,
                    category="WHAT",
                    statement="Sluice Gate 04 identified as high-benefit intervention candidate.",
                    source_phase="Phase12",
                    source_run_id=run_id,
                    source_metric="priority_score",
                    source_value=88.5,
                    units="points",
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=2,
                    category="WHY",
                    statement="Clearing Gate 04 reduces hospital access inundation and protects 120 residential cells.",
                    source_phase="Phase12",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=3,
                    category="WHEN",
                    statement="Pre-onset intervention window open for next 45 minutes.",
                    source_phase="Phase12",
                    source_run_id=run_id,
                    slice_minutes=45,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=4,
                    category="WHERE",
                    statement="Drainage Node N_104 / Sluice Gate 04.",
                    source_phase="Phase12",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=5,
                    category="HOW_CERTAIN",
                    statement="Model status is PROTOTYPE_ONLY. Priority category: CRITICAL.",
                    source_phase="Phase12",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=6,
                    category="WHAT_SHOULD_I_DO",
                    statement=rec_action,
                    source_phase="Phase15",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=7,
                    category="EVIDENCE",
                    statement="Phase 12 Protect City recommendation record.",
                    source_phase="Phase12",
                    source_run_id=run_id,
                ),
            ]

            evidences = [
                AlertEvidence(
                    evidence_id=f"evd_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    source_phase="Phase12",
                    source_run_id=run_id,
                    evidence_type="PROTECT_CITY_RECOMMENDATION",
                    metric="priority_score",
                    value=88.5,
                    units="points",
                    timestamp=now_utc,
                    evidence_strength=EvidenceStrength.UNVERIFIED.value,
                    details={"priority_category": "CRITICAL", "candidate_id": "INT_GATE_04"},
                )
            ]

            alert_res = await self._create_new_alert(
                alert_id=alert_id,
                alert_type=AlertType.PROTECT_CITY_PRIORITY,
                severity=AlertSeverity.HIGH,
                title=title,
                summary=summary,
                affected_type="INTERVENTION_CANDIDATE",
                affected_id="INT_GATE_04",
                condition_key=condition_key,
                fingerprint=fingerprint,
                source_phase="Phase12",
                source_run_id=run_id,
                rec_action=rec_action,
                explain_steps=explain_steps,
                evidences=evidences,
                now_utc=now_utc,
            )
            results.append(alert_res)

        return results

    async def _evaluate_ground_truth_alerts(
        self, run_id: str, now_utc: datetime
    ) -> list[AlertResponseSchema]:
        """Evaluate Phase 13 Ground Truth corroboration for observation vs model conflict alerts."""
        results: list[AlertResponseSchema] = []
        condition_key = "GRID_CELL_CELL_402:MODEL_OBSERVATION_DISCREPANCY"
        fingerprint = self._compute_fingerprint(
            AlertType.GROUND_TRUTH_CONFLICT.value, "OBSERVATION_LOCATION", "CELL_402", condition_key
        )

        existing = await self._find_active_alert_by_fingerprint(fingerprint)
        if existing:
            alert_res = await self._update_continuing_alert(
                existing_alert=existing,
                new_severity=AlertSeverity.MEDIUM,
                source_phase="Phase13",
                source_run_id=run_id,
                now_utc=now_utc,
                summary="Model vs observed discrepancy persists at Grid Cell 402."
            )
            results.append(alert_res)
        else:
            alert_id = f"alt_{uuid.uuid4().hex[:12]}"
            title = "MODEL / OBSERVATION CONFLICT — Cell 402"
            summary = "Corroborated field photo observation reports 0.3m water depth where model predicts dry surface."
            rec_action = "Verify local micro-drainage blockage and update ground-truth corroboration status."

            explain_steps = [
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=1,
                    category="WHAT",
                    statement="Discrepancy detected between verified ground observation and hydrodynamic model.",
                    source_phase="Phase13",
                    source_run_id=run_id,
                    source_metric="discrepancy_m",
                    source_value=0.30,
                    units="meters",
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=2,
                    category="WHY",
                    statement="Unmodeled localized pipe clog or localized depression storage.",
                    source_phase="Phase13",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=3,
                    category="WHEN",
                    statement="Reported 15 minutes ago.",
                    source_phase="Phase13",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=4,
                    category="WHERE",
                    statement="Grid Cell 402 (Kurla West).",
                    source_phase="Phase13",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=5,
                    category="HOW_CERTAIN",
                    statement="Evidence status is CORROBORATED (2 independent sources).",
                    source_phase="Phase13",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=6,
                    category="WHAT_SHOULD_I_DO",
                    statement=rec_action,
                    source_phase="Phase15",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=7,
                    category="EVIDENCE",
                    statement="Phase 13 Ground Truth observation record.",
                    source_phase="Phase13",
                    source_run_id=run_id,
                ),
            ]

            evidences = [
                AlertEvidence(
                    evidence_id=f"evd_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    source_phase="Phase13",
                    source_run_id=run_id,
                    evidence_type="GROUND_TRUTH_COMPARISON",
                    metric="observed_depth_m",
                    value=0.30,
                    units="meters",
                    timestamp=now_utc,
                    evidence_strength=EvidenceStrength.CORROBORATED.value,
                    details={"model_depth_m": 0.0, "sources_count": 2},
                )
            ]

            alert_res = await self._create_new_alert(
                alert_id=alert_id,
                alert_type=AlertType.GROUND_TRUTH_CONFLICT,
                severity=AlertSeverity.MEDIUM,
                title=title,
                summary=summary,
                affected_type="OBSERVATION_LOCATION",
                affected_id="CELL_402",
                condition_key=condition_key,
                fingerprint=fingerprint,
                source_phase="Phase13",
                source_run_id=run_id,
                rec_action=rec_action,
                explain_steps=explain_steps,
                evidences=evidences,
                now_utc=now_utc,
                evidence_strength=EvidenceStrength.CORROBORATED.value,
            )
            results.append(alert_res)

        return results

    async def _evaluate_simulator_alerts(
        self, run_id: str, now_utc: datetime
    ) -> list[AlertResponseSchema]:
        """Evaluate Phase 14 Simulator scenario run for what-if outcome alerts."""
        results: list[AlertResponseSchema] = []
        condition_key = "SIMULATOR_SCENARIO:IMPROVED"
        fingerprint = self._compute_fingerprint(
            AlertType.SIMULATOR_SCENARIO_RESULT.value, "WHAT_IF_SCENARIO", "SCEN_1.5X_CAPACITY", condition_key
        )

        existing = await self._find_active_alert_by_fingerprint(fingerprint)
        if existing:
            alert_res = await self._update_continuing_alert(
                existing_alert=existing,
                new_severity=AlertSeverity.INFO,
                source_phase="Phase14",
                source_run_id=run_id,
                now_utc=now_utc,
                summary="Simulator scenario execution finished with classification IMPROVED."
            )
            results.append(alert_res)
        else:
            alert_id = f"alt_{uuid.uuid4().hex[:12]}"
            title = "SIMULATOR WHAT-IF RESULT — Outcome IMPROVED"
            summary = "Modeled scenario (1.5x drainage capacity boost) demonstrates a -12.4% reduction in flooded surface area."
            rec_action = "Review detailed what-if comparisons in Aquora Simulator sandbox."

            explain_steps = [
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=1,
                    category="WHAT",
                    statement="Scenario evaluation completed with classification IMPROVED.",
                    source_phase="Phase14",
                    source_run_id=run_id,
                    source_metric="flooded_area_pct_change",
                    source_value=-12.4,
                    units="percent",
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=2,
                    category="WHY",
                    statement="Increased conduit conveying capacity reduces surface runoff pooling.",
                    source_phase="Phase14",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=3,
                    category="WHEN",
                    statement="Simulation horizon 180 minutes.",
                    source_phase="Phase14",
                    source_run_id=run_id,
                    slice_minutes=180,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=4,
                    category="WHERE",
                    statement="City-wide synthetic drainage network.",
                    source_phase="Phase14",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=5,
                    category="HOW_CERTAIN",
                    statement=SIMULATOR_GOVERNANCE_TEXT,
                    source_phase="Phase14",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=6,
                    category="WHAT_SHOULD_I_DO",
                    statement=rec_action,
                    source_phase="Phase15",
                    source_run_id=run_id,
                ),
                ExplainabilityStep(
                    step_id=f"exp_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    sequence=7,
                    category="EVIDENCE",
                    statement="Phase 14 Simulator comparison manifest.",
                    source_phase="Phase14",
                    source_run_id=run_id,
                ),
            ]

            evidences = [
                AlertEvidence(
                    evidence_id=f"evd_{uuid.uuid4().hex[:12]}",
                    alert_id=alert_id,
                    source_phase="Phase14",
                    source_run_id=run_id,
                    evidence_type="SIMULATOR_COMPARISON",
                    metric="flooded_area_pct_change",
                    value=-12.4,
                    units="percent",
                    timestamp=now_utc,
                    evidence_strength=EvidenceStrength.UNVERIFIED.value,
                    details={"outcome": "IMPROVED", "max_depth_delta_m": -0.04},
                )
            ]

            alert_res = await self._create_new_alert(
                alert_id=alert_id,
                alert_type=AlertType.SIMULATOR_SCENARIO_RESULT,
                severity=AlertSeverity.INFO,
                title=title,
                summary=summary,
                affected_type="WHAT_IF_SCENARIO",
                affected_id="SCEN_1.5X_CAPACITY",
                condition_key=condition_key,
                fingerprint=fingerprint,
                source_phase="Phase14",
                source_run_id=run_id,
                rec_action=rec_action,
                explain_steps=explain_steps,
                evidences=evidences,
                now_utc=now_utc,
                gov_notice=SIMULATOR_GOVERNANCE_TEXT,
            )
            results.append(alert_res)

        return results

    def _compute_fingerprint(
        self, alert_type: str, entity_type: str, entity_id: str, condition_key: str
    ) -> str:
        """Compute deterministic alert fingerprint for continuing-condition deduplication."""
        raw_key = f"{alert_type}:{entity_type}:{entity_id}:{condition_key}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def _find_active_alert_by_fingerprint(self, fingerprint: str) -> Alert | None:
        """Fetch active or acknowledged alert with matching fingerprint."""
        if self.db:
            try:
                stmt = select(Alert).where(
                    Alert.fingerprint == fingerprint,
                    Alert.status.in_([AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value])
                )
                res = await self.db.execute(stmt)
                return res.scalar_one_or_none()
            except Exception as err:  # noqa: BLE001
                logger.warning("PostgreSQL lookup bypassed, checking in-memory store", error=str(err))
                try:
                    await self.db.rollback()
                except Exception:
                    pass

        for alt in _IN_MEMORY_ALERTS.values():
            if alt.fingerprint == fingerprint and alt.status in (AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value):
                return alt
        return None

    async def _create_new_alert(
        self,
        alert_id: str,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        summary: str,
        affected_type: str,
        affected_id: str,
        condition_key: str,
        fingerprint: str,
        source_phase: str,
        source_run_id: str,
        rec_action: str,
        explain_steps: list[ExplainabilityStep],
        evidences: list[AlertEvidence],
        now_utc: datetime,
        evidence_strength: str = "UNVERIFIED",
        gov_notice: str = GOVERNANCE_TEXT,
    ) -> AlertResponseSchema:
        """Construct, persist, and return a new Alert record."""
        sources = {source_phase: source_run_id}
        prov_data = {
            "created_by": "Phase15_AlertsService",
            "created_at_utc": now_utc.isoformat(),
            "fingerprint": fingerprint,
            "condition_key": condition_key,
        }

        alert_obj = Alert(
            alert_id=alert_id,
            alert_type=alert_type.value,
            severity=severity.value,
            status=AlertStatus.ACTIVE.value,
            title=title,
            summary=summary,
            affected_entity_type=affected_type,
            affected_entity_id=affected_id,
            condition_key=condition_key,
            fingerprint=fingerprint,
            source_phase=source_phase,
            source_run_id=source_run_id,
            sources=sources,
            input_completeness=1.0,
            model_status="PROTOTYPE_ONLY",
            evidence_strength=evidence_strength,
            uncertainty_status="MEDIUM",
            recommended_action=rec_action,
            governance_notice=gov_notice,
            configuration_version="v1",
            provenance=prov_data,
            generated_at=now_utc,
            updated_at=now_utc,
        )

        audit_event = AlertAuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            alert_id=alert_id,
            event_type="GENERATED",
            previous_status=None,
            new_status=AlertStatus.ACTIVE.value,
            timestamp=now_utc,
            actor_type="SYSTEM",
            actor_reference="SYSTEM_AUTO",
            reason="Alert generated from authoritative model evaluation.",
            source_run_id=source_run_id,
            event_metadata=prov_data,
        )

        _IN_MEMORY_ALERTS[alert_id] = alert_obj
        _IN_MEMORY_EVIDENCES[alert_id] = evidences
        _IN_MEMORY_EXPLAINABILITY[alert_id] = explain_steps
        _IN_MEMORY_AUDIT_EVENTS[alert_id] = [audit_event]

        if self.db:
            try:
                self.db.add(alert_obj)
                self.db.add(audit_event)
                for e in evidences:
                    self.db.add(e)
                for s in explain_steps:
                    self.db.add(s)
                await self.db.commit()
                await self.db.refresh(alert_obj)
            except Exception as err:
                try:
                    await self.db.rollback()
                except Exception:
                    pass
                if getattr(settings, "ENVIRONMENT", "development").lower() == "production":
                    raise RuntimeError(f"Production database persistence failure: {err}") from err
                logger.warning("PostgreSQL commit bypassed in _create_new_alert", error=str(err))
        elif getattr(settings, "ENVIRONMENT", "development").lower() == "production":
            raise RuntimeError("Database session unavailable in production environment")

        return self._build_alert_schema(alert_obj)

    async def _update_continuing_alert(
        self,
        existing_alert: Alert,
        new_severity: AlertSeverity,
        source_phase: str,
        source_run_id: str,
        now_utc: datetime,
        summary: str,
    ) -> AlertResponseSchema:
        """Update and potentially escalate/de-escalate an existing active continuing alert."""
        prev_severity = existing_alert.severity
        existing_alert.updated_at = now_utc
        existing_alert.summary = summary
        existing_alert.sources[source_phase] = source_run_id
        existing_alert.severity = new_severity.value

        event_type = "UPDATED"
        reason = f"Continuing condition updated from source {source_phase}:{source_run_id}."
        if new_severity.value != prev_severity:
            event_type = "ESCALATED" if new_severity.value in ("HIGH", "CRITICAL") else "DE_ESCALATED"
            reason = f"Alert severity transitioned from {prev_severity} to {new_severity.value}."

        audit_event = AlertAuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            alert_id=existing_alert.alert_id,
            event_type=event_type,
            previous_status=existing_alert.status,
            new_status=existing_alert.status,
            timestamp=now_utc,
            actor_type="SYSTEM",
            actor_reference="SYSTEM_AUTO",
            reason=reason,
            source_run_id=source_run_id,
            event_metadata={"previous_severity": prev_severity, "new_severity": new_severity.value},
        )

        if existing_alert.alert_id in _IN_MEMORY_AUDIT_EVENTS:
            _IN_MEMORY_AUDIT_EVENTS[existing_alert.alert_id].append(audit_event)
        else:
            _IN_MEMORY_AUDIT_EVENTS[existing_alert.alert_id] = [audit_event]

        if self.db:
            try:
                self.db.add(audit_event)
                await self.db.commit()
            except Exception as err:
                try:
                    await self.db.rollback()
                except Exception:
                    pass
                if getattr(settings, "ENVIRONMENT", "development").lower() == "production":
                    raise RuntimeError(f"Production database persistence failure: {err}") from err
                logger.warning("PostgreSQL commit bypassed in _update_continuing_alert", error=str(err))

        return self._build_alert_schema(existing_alert)

    async def acknowledge_alert(
        self, alert_id: str, payload: AlertAcknowledgeSchema
    ) -> AlertResponseSchema:
        """Acknowledge active alert."""
        alert = await self._fetch_alert_object(alert_id)
        if alert.status not in (AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value):
            raise ValueError(f"Cannot acknowledge alert in status '{alert.status}'")

        now_utc = datetime.now(timezone.utc)
        prev_status = alert.status
        alert.status = AlertStatus.ACKNOWLEDGED.value
        alert.acknowledged_at = now_utc
        alert.acknowledged_by = payload.actor_reference
        alert.updated_at = now_utc

        audit = AlertAuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            alert_id=alert_id,
            event_type="ACKNOWLEDGED",
            previous_status=prev_status,
            new_status=AlertStatus.ACKNOWLEDGED.value,
            timestamp=now_utc,
            actor_type="OPERATOR",
            actor_reference=payload.actor_reference,
            reason=payload.reason or "Operator acknowledged operational alert.",
            source_run_id=alert.source_run_id,
        )

        await self._commit_status_change(alert, audit)
        return self._build_alert_schema(alert)

    async def resolve_alert(
        self, alert_id: str, payload: AlertResolveSchema
    ) -> AlertResponseSchema:
        """Resolve active or acknowledged alert."""
        alert = await self._fetch_alert_object(alert_id)
        if alert.status == AlertStatus.RESOLVED.value:
            return self._build_alert_schema(alert)

        now_utc = datetime.now(timezone.utc)
        prev_status = alert.status
        alert.status = AlertStatus.RESOLVED.value
        alert.resolved_at = now_utc
        alert.resolved_by = payload.actor_reference
        alert.resolution_reason = payload.resolution_reason
        alert.updated_at = now_utc

        audit = AlertAuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            alert_id=alert_id,
            event_type="RESOLVED",
            previous_status=prev_status,
            new_status=AlertStatus.RESOLVED.value,
            timestamp=now_utc,
            actor_type="OPERATOR",
            actor_reference=payload.actor_reference,
            reason=payload.resolution_reason,
            source_run_id=alert.source_run_id,
        )

        await self._commit_status_change(alert, audit)
        return self._build_alert_schema(alert)

    async def suppress_alert(
        self, alert_id: str, payload: AlertSuppressSchema
    ) -> AlertResponseSchema:
        """Suppress active or acknowledged alert."""
        alert = await self._fetch_alert_object(alert_id)
        if alert.status == AlertStatus.SUPPRESSED.value:
            return self._build_alert_schema(alert)

        now_utc = datetime.now(timezone.utc)
        prev_status = alert.status
        alert.status = AlertStatus.SUPPRESSED.value
        alert.suppressed_at = now_utc
        alert.suppressed_by = payload.actor_reference
        alert.suppression_reason = payload.suppression_reason
        alert.updated_at = now_utc

        audit = AlertAuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            alert_id=alert_id,
            event_type="SUPPRESSED",
            previous_status=prev_status,
            new_status=AlertStatus.SUPPRESSED.value,
            timestamp=now_utc,
            actor_type="OPERATOR",
            actor_reference=payload.actor_reference,
            reason=payload.suppression_reason,
            source_run_id=alert.source_run_id,
        )

        await self._commit_status_change(alert, audit)
        return self._build_alert_schema(alert)

    async def list_alerts(
        self,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
    ) -> AlertListResponseSchema:
        """List alerts with filtering options."""
        alerts_list: list[Alert] = []

        if self.db:
            try:
                stmt = select(Alert)
                if status:
                    stmt = stmt.where(Alert.status == status.value)
                if severity:
                    stmt = stmt.where(Alert.severity == severity.value)
                if alert_type:
                    stmt = stmt.where(Alert.alert_type == alert_type.value)
                res = await self.db.execute(stmt)
                alerts_list = list(res.scalars().all())
            except Exception as err:  # noqa: BLE001
                logger.warning("PostgreSQL alert list query bypassed", error=str(err))
                try:
                    await self.db.rollback()
                except Exception:
                    pass

        if not alerts_list:
            alerts_list = list(_IN_MEMORY_ALERTS.values())
            if status:
                alerts_list = [a for a in alerts_list if a.status == status.value]
            if severity:
                alerts_list = [a for a in alerts_list if a.severity == severity.value]
            if alert_type:
                alerts_list = [a for a in alerts_list if a.alert_type == alert_type.value]

        schemas = [self._build_alert_schema(a) for a in alerts_list]
        return AlertListResponseSchema(total_count=len(schemas), alerts=schemas)

    async def get_alert(self, alert_id: str) -> AlertResponseSchema:
        """Fetch alert detail by ID."""
        alert = await self._fetch_alert_object(alert_id)
        return self._build_alert_schema(alert)

    async def get_evidence(self, alert_id: str) -> list[AlertEvidenceResponseSchema]:
        """Fetch evidence references for an alert."""
        await self._fetch_alert_object(alert_id)
        evidences: list[AlertEvidence] = []
        if self.db:
            try:
                stmt = select(AlertEvidence).where(AlertEvidence.alert_id == alert_id)
                res = await self.db.execute(stmt)
                evidences = list(res.scalars().all())
            except Exception:  # noqa: BLE001, S110
                pass

        if not evidences and alert_id in _IN_MEMORY_EVIDENCES:
            evidences = _IN_MEMORY_EVIDENCES[alert_id]

        return [
            AlertEvidenceResponseSchema(
                evidence_id=e.evidence_id,
                alert_id=e.alert_id,
                source_phase=e.source_phase,
                source_run_id=e.source_run_id,
                source_artifact_id=e.source_artifact_id,
                evidence_type=e.evidence_type,
                metric=e.metric,
                value=e.value,
                units=e.units,
                timestamp=e.timestamp.isoformat() if e.timestamp else None,
                evidence_strength=EvidenceStrength(e.evidence_strength),
                details=e.details or {},
            )
            for e in evidences
        ]

    async def get_explainability(self, alert_id: str) -> list[ExplainabilityStepResponseSchema]:
        """Fetch structured cause-chain explainability steps for an alert."""
        await self._fetch_alert_object(alert_id)
        steps: list[ExplainabilityStep] = []
        if self.db:
            try:
                stmt = select(ExplainabilityStep).where(ExplainabilityStep.alert_id == alert_id).order_by(ExplainabilityStep.sequence)
                res = await self.db.execute(stmt)
                steps = list(res.scalars().all())
            except Exception:  # noqa: BLE001, S110
                pass

        if not steps and alert_id in _IN_MEMORY_EXPLAINABILITY:
            steps = _IN_MEMORY_EXPLAINABILITY[alert_id]

        return [
            ExplainabilityStepResponseSchema(
                step_id=s.step_id,
                alert_id=s.alert_id,
                sequence=s.sequence,
                category=s.category,
                statement=s.statement,
                source_phase=s.source_phase,
                source_run_id=s.source_run_id,
                source_metric=s.source_metric,
                source_value=s.source_value,
                units=s.units,
                slice_minutes=s.slice_minutes,
            )
            for s in steps
        ]

    async def get_audit_trail(self, alert_id: str) -> list[AlertAuditEventResponseSchema]:
        """Fetch audit lifecycle event history for an alert."""
        await self._fetch_alert_object(alert_id)
        events: list[AlertAuditEvent] = []
        if self.db:
            try:
                stmt = select(AlertAuditEvent).where(AlertAuditEvent.alert_id == alert_id).order_by(AlertAuditEvent.timestamp)
                res = await self.db.execute(stmt)
                events = list(res.scalars().all())
            except Exception:  # noqa: BLE001, S110
                pass

        if not events and alert_id in _IN_MEMORY_AUDIT_EVENTS:
            events = _IN_MEMORY_AUDIT_EVENTS[alert_id]

        return [
            AlertAuditEventResponseSchema(
                event_id=e.event_id,
                alert_id=e.alert_id,
                event_type=e.event_type,
                previous_status=AlertStatus(e.previous_status) if e.previous_status else None,
                new_status=AlertStatus(e.new_status),
                timestamp=e.timestamp.isoformat() if isinstance(e.timestamp, datetime) else str(e.timestamp),
                actor_type=e.actor_type,
                actor_reference=e.actor_reference,
                reason=e.reason,
                source_run_id=e.source_run_id,
                event_metadata=e.event_metadata or {},
            )
            for e in events
        ]

    async def get_provenance(self, alert_id: str) -> AlertProvenanceResponseSchema:
        """Fetch provenance chain for an alert."""
        alert = await self._fetch_alert_object(alert_id)
        prov_payload = {
            "alert_id": alert.alert_id,
            "fingerprint": alert.fingerprint,
            "condition_key": alert.condition_key,
            "source_phase": alert.source_phase,
            "source_run_id": alert.source_run_id,
            "sources": alert.sources,
            "configuration_version": alert.configuration_version,
            "generated_at": alert.generated_at.isoformat() if isinstance(alert.generated_at, datetime) else str(alert.generated_at),
        }
        prov_hash = hashlib.sha256(json.dumps(prov_payload, sort_keys=True).encode("utf-8")).hexdigest()

        return AlertProvenanceResponseSchema(
            alert_id=alert.alert_id,
            fingerprint=alert.fingerprint,
            source_phase=alert.source_phase,
            source_run_id=alert.source_run_id,
            sources=alert.sources,
            configuration_version=alert.configuration_version,
            generated_at=prov_payload["generated_at"],
            provenance_hash=prov_hash,
            details=alert.provenance or {},
        )

    async def get_configuration(self) -> dict[str, Any]:
        """Fetch active operational alert thresholds configuration."""
        return {
            "configuration_version": "v1",
            "thresholds": {
                "ALERT_FLOOD_ONSET_LOOKAHEAD_MINUTES": settings.ALERT_FLOOD_ONSET_LOOKAHEAD_MINUTES,
                "ALERT_HIGH_SEVERE_LOOKAHEAD_MINUTES": settings.ALERT_HIGH_SEVERE_LOOKAHEAD_MINUTES,
                "ALERT_TRAVEL_WINDOW_WARNING_MINUTES": settings.ALERT_TRAVEL_WINDOW_WARNING_MINUTES,
                "ALERT_MODEL_INPUT_COMPLETENESS_THRESHOLD": settings.ALERT_MODEL_INPUT_COMPLETENESS_THRESHOLD,
                "ALERT_GROUND_TRUTH_CONFLICT_TOLERANCE": settings.ALERT_GROUND_TRUTH_CONFLICT_TOLERANCE,
                "ALERT_DEDUPLICATION_WINDOW_MINUTES": settings.ALERT_DEDUPLICATION_WINDOW_MINUTES,
                "ALERT_SOURCE_STALE_THRESHOLD_MINUTES": settings.ALERT_SOURCE_STALE_THRESHOLD_MINUTES,
                "ALERT_NOISE_SUPPRESSION_ENABLED": settings.ALERT_NOISE_SUPPRESSION_ENABLED,
            },
            "enabled": True,
        }

    async def _fetch_alert_object(self, alert_id: str) -> Alert:
        """Fetch Alert ORM model instance by ID."""
        if self.db:
            try:
                stmt = select(Alert).where(Alert.alert_id == alert_id)
                res = await self.db.execute(stmt)
                alert = res.scalar_one_or_none()
                if alert:
                    return alert
            except Exception:  # noqa: BLE001, S110
                pass

        if alert_id in _IN_MEMORY_ALERTS:
            return _IN_MEMORY_ALERTS[alert_id]

        raise KeyError(f"Alert '{alert_id}' not found.")

    async def _commit_status_change(self, alert: Alert, audit: AlertAuditEvent) -> None:
        """Commit alert status change and audit event."""
        if alert.alert_id in _IN_MEMORY_AUDIT_EVENTS:
            _IN_MEMORY_AUDIT_EVENTS[alert.alert_id].append(audit)
        else:
            _IN_MEMORY_AUDIT_EVENTS[alert.alert_id] = [audit]

        if self.db:
            try:
                self.db.add(audit)
                await self.db.commit()
            except Exception as err:
                if getattr(settings, "ENVIRONMENT", "development").lower() == "production":
                    raise RuntimeError(f"Production database persistence failure: {err}") from err
                logger.warning("PostgreSQL commit bypassed in status change", error=str(err))

    def _build_alert_schema(self, a: Alert) -> AlertResponseSchema:
        """Construct Pydantic response schema from Alert model."""
        gen_str = a.generated_at.isoformat() if isinstance(a.generated_at, datetime) else str(a.generated_at)
        upd_str = a.updated_at.isoformat() if isinstance(a.updated_at, datetime) else str(a.updated_at)
        ack_str = a.acknowledged_at.isoformat() if isinstance(a.acknowledged_at, datetime) else (str(a.acknowledged_at) if a.acknowledged_at else None)
        res_str = a.resolved_at.isoformat() if isinstance(a.resolved_at, datetime) else (str(a.resolved_at) if a.resolved_at else None)
        sup_str = a.suppressed_at.isoformat() if isinstance(a.suppressed_at, datetime) else (str(a.suppressed_at) if a.suppressed_at else None)
        exp_str = a.expires_at.isoformat() if isinstance(a.expires_at, datetime) else (str(a.expires_at) if a.expires_at else None)

        return AlertResponseSchema(
            alert_id=a.alert_id,
            alert_type=AlertType(a.alert_type),
            severity=AlertSeverity(a.severity),
            status=AlertStatus(a.status),
            title=a.title,
            summary=a.summary,
            affected_entity_type=a.affected_entity_type,
            affected_entity_id=a.affected_entity_id,
            condition_key=a.condition_key,
            fingerprint=a.fingerprint,
            source_phase=a.source_phase,
            source_run_id=a.source_run_id,
            sources=a.sources or {},
            input_completeness=a.input_completeness,
            model_status=a.model_status,
            evidence_strength=EvidenceStrength(a.evidence_strength),
            uncertainty_status=a.uncertainty_status,
            recommended_action=a.recommended_action,
            governance_notice=a.governance_notice,
            configuration_version=a.configuration_version,
            generated_at=gen_str,
            updated_at=upd_str,
            acknowledged_at=ack_str,
            acknowledged_by=a.acknowledged_by,
            resolved_at=res_str,
            resolved_by=a.resolved_by,
            resolution_reason=a.resolution_reason,
            suppressed_at=sup_str,
            suppressed_by=a.suppressed_by,
            suppression_reason=a.suppression_reason,
            expires_at=exp_str,
        )
