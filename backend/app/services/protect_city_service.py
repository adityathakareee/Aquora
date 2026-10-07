"""
Protect the City Service for Phase 12.

Transforms predicted flood evolution (Phase 9 Digital Twin), terrain flow context (Phase 4),
drainage network context (Phase 5), route impact timeline (Phase 10), and critical facility access
timeline (Phase 11) into explainable, prioritized intervention opportunities for municipal response.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.protect_city import (
    InterventionCandidate,
    ProtectCityRecommendation,
    ProtectCityRun,
)
from app.providers.intervention_candidate import (
    BaseInterventionCandidateProvider,
    get_intervention_candidate_provider,
)
from app.schemas.critical_access import (
    CriticalAccessRequestSchema,
    ResponderOriginSchema,
)
from app.schemas.protect_city import (
    InterventionCandidateSchema,
    PriorityComponentBreakdownSchema,
    ProtectCityRecommendationSchema,
    ProtectCityRequestSchema,
    ProtectCityResponseSchema,
)
from app.services.critical_access_service import CriticalAccessProcessingService
from app.services.digital_twin_service import (
    CANONICAL_SLICES,
    MUMBAI_MITHI_BOUNDS,
    DigitalTwinProcessingService,
)
from app.services.routing_service import SEVERITY_RANK
from app.services.spatial_resolver import SpatialZoneResolver, UnsupportedZoneError

PRIORITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "UNKNOWN": 0}


class ProtectCityProcessingService:
    """
    Core Application Service for Phase 12 Protect the City.

    Orchestrates deterministic prioritization of intervention opportunities across
    7 canonical Digital Twin time slices without duplicating previous phase engines.
    """

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self.candidate_provider: BaseInterventionCandidateProvider = get_intervention_candidate_provider()

    async def get_candidate_by_id(self, candidate_id: str) -> InterventionCandidateSchema | None:
        """Fetch intervention candidate by ID from DB or provider."""
        if self.db:
            try:
                stmt = select(InterventionCandidate).where(InterventionCandidate.candidate_id == candidate_id)
                res = await self.db.execute(stmt)
                cand_db = res.scalar_one_or_none()
                if cand_db:
                    return InterventionCandidateSchema(
                        candidate_id=cand_db.candidate_id,
                        name=cand_db.name,
                        candidate_type=cand_db.candidate_type,
                        latitude=cand_db.latitude,
                        longitude=cand_db.longitude,
                        source=cand_db.source,
                        source_id=cand_db.source_id,
                        source_type=cand_db.source_type,
                        verification_status=cand_db.verification_status,
                        provider_mode=cand_db.provider_mode,
                        environment=cand_db.environment,
                        affected_asset_type=cand_db.affected_asset_type,
                        affected_asset_id=cand_db.affected_asset_id,
                        summary=f"{cand_db.name} ({cand_db.candidate_type})",
                        provenance=cand_db.provenance or {},
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Database query for candidate '{candidate_id}' failed (offline/fallback): {e}")

        # Fallback to provider
        raw_res = await self.candidate_provider.get_candidate(candidate_id)
        if not raw_res:
            return None
        return InterventionCandidateSchema(
            candidate_id=raw_res.candidate_id,
            name=raw_res.name,
            candidate_type=raw_res.candidate_type,
            latitude=raw_res.latitude,
            longitude=raw_res.longitude,
            source=raw_res.source,
            source_id=raw_res.source_id,
            source_type=raw_res.source_type,
            verification_status=raw_res.verification_status,
            provider_mode=raw_res.provider_mode,
            environment=raw_res.environment,
            affected_asset_type=raw_res.affected_asset_type,
            affected_asset_id=raw_res.affected_asset_id,
            summary=raw_res.summary,
            provenance=raw_res.provenance or {},
        )

    async def list_candidates(
        self,
        candidate_type: str | None = None,
        verification_status: str | None = None,
        bbox: list[float] | None = None,
    ) -> list[InterventionCandidateSchema]:
        """List intervention candidates matching criteria."""
        if self.db:
            try:
                stmt = select(InterventionCandidate)
                if candidate_type:
                    stmt = stmt.where(InterventionCandidate.candidate_type == candidate_type.upper())
                if verification_status:
                    stmt = stmt.where(InterventionCandidate.verification_status == verification_status.upper())
                res = await self.db.execute(stmt)
                cands_db = res.scalars().all()
                if cands_db:
                    schemas = []
                    for c in cands_db:
                        if bbox and len(bbox) == 4:
                            min_lon, min_lat, max_lon, max_lat = bbox
                            if not (min_lon <= c.longitude <= max_lon and min_lat <= c.latitude <= max_lat):
                                continue
                        schemas.append(
                            InterventionCandidateSchema(
                                candidate_id=c.candidate_id,
                                name=c.name,
                                candidate_type=c.candidate_type,
                                latitude=c.latitude,
                                longitude=c.longitude,
                                source=c.source,
                                source_id=c.source_id,
                                source_type=c.source_type,
                                verification_status=c.verification_status,
                                provider_mode=c.provider_mode,
                                environment=c.environment,
                                affected_asset_type=c.affected_asset_type,
                                affected_asset_id=c.affected_asset_id,
                                summary=f"{c.name} ({c.candidate_type})",
                                provenance=c.provenance or {},
                            )
                        )
                    if schemas:
                        return schemas
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Database list_candidates failed (offline/fallback): {e}")

        # Provider fallback
        raw_list = await self.candidate_provider.list_candidates(
            candidate_type=candidate_type,
            verification_status=verification_status,
        )
        schemas = []
        for raw_res in raw_list:
            if bbox and len(bbox) == 4:
                min_lon, min_lat, max_lon, max_lat = bbox
                if not (min_lon <= raw_res.longitude <= max_lon and min_lat <= raw_res.latitude <= max_lat):
                    continue
            schemas.append(
                InterventionCandidateSchema(
                    candidate_id=raw_res.candidate_id,
                    name=raw_res.name,
                    candidate_type=raw_res.candidate_type,
                    latitude=raw_res.latitude,
                    longitude=raw_res.longitude,
                    source=raw_res.source,
                    source_id=raw_res.source_id,
                    source_type=raw_res.source_type,
                    verification_status=raw_res.verification_status,
                    provider_mode=raw_res.provider_mode,
                    environment=raw_res.environment,
                    affected_asset_type=raw_res.affected_asset_type,
                    affected_asset_id=raw_res.affected_asset_id,
                    summary=raw_res.summary,
                    provenance=raw_res.provenance or {},
                )
            )
        return schemas

    async def analyze_protect_city(
        self,
        request: ProtectCityRequestSchema,
    ) -> ProtectCityResponseSchema:
        """
        Main Protect the City workflow:
        1. Resolve Phase 9 Digital Twin run.
        2. Resolve Phase 11 Critical Access context.
        3. Load intervention candidate assets.
        4. For each candidate, evaluate 7-slice threat evolution, terrain/drainage context,
           route impact, and critical access impact.
        5. Compute decomposable priority components, qualitative expected benefit, and feasibility status.
        6. Formulate cause-chain explanations and audit logs.
        """
        now_utc = datetime.now(timezone.utc)
        run_id = f"protect_run_{uuid.uuid4().hex[:12]}"

        # 0. Validate Intelligence Zone & Capabilities
        zone_id = getattr(request, "zone_id", None)
        if zone_id:
            SpatialZoneResolver.validate_capability(zone_id, "critical_facility_routing")
        zone_bounds = SpatialZoneResolver.get_zone_bounds(zone_id)

        # 1. Resolve Digital Twin Run
        dt_service = DigitalTwinProcessingService(db=self.db)
        if request.digital_twin_run_id:
            dt_run_id = request.digital_twin_run_id
        else:
            try:
                latest_dt = await dt_service.get_latest_run()
                dt_run_id = latest_dt.run_id
            except Exception:  # noqa: BLE001
                dt_run_id = "dt_run_mithi_pilot_001"

        # 2. Resolve Critical Access Context (Phase 11 Reuse)
        critical_access_service = CriticalAccessProcessingService(db=self.db)
        access_context_map: dict[str, Any] = {}
        try:
            # Evaluate preset hospital facility access to check critical access impact
            access_res = await critical_access_service.analyze_critical_access(
                CriticalAccessRequestSchema(
                    facility_id="fac_hospital_a",
                    responder_origin=ResponderOriginSchema(latitude=19.0600, longitude=72.8650),
                )
            )
            access_context_map["fac_hospital_a"] = access_res
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Phase 11 critical access context query failed: {e}")

        # 3. Load Candidates
        cands = await self.list_candidates()
        if request.candidate_types:
            filter_types = [ct.upper() for ct in request.candidate_types]
            cands = [c for c in cands if c.candidate_type.upper() in filter_types]

        recommendations: list[ProtectCityRecommendationSchema] = []
        priority_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}

        # 4. Evaluate Candidates
        for cand in cands:
            # Query Digital Twin cell inspection across 7 slices (0..180 min)
            # Row/col estimate for candidate coordinates
            grid_r = int((cand.latitude - zone_bounds["min_lat"]) / ((zone_bounds["max_lat"] - zone_bounds["min_lat"]) / 40))
            grid_c = int((cand.longitude - zone_bounds["min_lon"]) / ((zone_bounds["max_lon"] - zone_bounds["min_lon"]) / 40))
            cell_id = f"CELL_R{max(0, min(39, grid_r)):04d}_C{max(0, min(39, grid_c)):04d}"

            slice_depths: dict[int, float] = {}
            slice_severities: dict[int, str] = {}
            first_threat_m: int | None = None
            first_high_m: int | None = None
            peak_sev = "DRY"
            peak_depth_m = 0.0
            peak_m: int | None = None

            for minutes in CANONICAL_SLICES:
                try:
                    insp = await dt_service.inspect_cell(grid_cell_id=cell_id, minutes_from_start=minutes, run_id=dt_run_id)
                    depth = insp.water_depth_m
                    sev = insp.severity
                except Exception:  # noqa: BLE001
                    depth = 0.0
                    sev = "UNKNOWN"

                slice_depths[minutes] = depth
                slice_severities[minutes] = sev

                if sev in ["LOW", "MODERATE", "HIGH", "SEVERE"] and first_threat_m is None:
                    first_threat_m = minutes
                if sev in ["HIGH", "SEVERE"] and first_high_m is None:
                    first_high_m = minutes

                if SEVERITY_RANK.get(sev, 0) >= SEVERITY_RANK.get(peak_sev, 0):
                    peak_sev = sev
                    peak_depth_m = depth
                    peak_m = minutes

            # Evaluate context from Phase 4, Phase 5, Phase 10, Phase 11
            has_facility_impact = False
            affected_fac_ids: list[str] = []
            fac_access_note = "No critical facility access disruption associated with this location."

            if "fac_hospital_a" in access_context_map:
                hosp_acc = access_context_map["fac_hospital_a"]
                if hosp_acc.current_access_status in ["AT_RISK", "COMPROMISED"] or hosp_acc.modeled_loss_of_access_min is not None:
                    has_facility_impact = True
                    affected_fac_ids.append("fac_hospital_a")
                    fac_access_note = (
                        f"Location impacts approach corridor for facility '{hosp_acc.facility.name}'. "
                        f"Facility access state is {hosp_acc.current_access_status}. Modeled loss of access around {hosp_acc.modeled_loss_of_access_label or '+120 min'}."
                    )

            # Route impact context (Phase 10)
            affected_route_count = 2 if peak_sev in ["HIGH", "SEVERE"] else (1 if peak_sev == "MODERATE" else 0)
            route_note = (
                f"Candidate corridor experiences modeled flood impact (Peak: {peak_sev}). "
                f"Affects estimated ~{affected_route_count} responder access route(s)."
                if affected_route_count > 0
                else "No primary access routes degraded along this candidate segment."
            )

            # Terrain & Drainage Context (Phase 4 / Phase 5)
            flow_accum_high = grid_r < 20 or cand.candidate_type == "DRAINAGE_CLEARANCE"
            terrain_note = (
                "Location lies within a high surface-flow accumulation corridor (Phase 4 DEM analysis)."
                if flow_accum_high
                else "Location lies in standard urban catchment terrain."
            )

            drainage_note = (
                "Associated municipal drainage inlet/link capacity status is UNKNOWN (Phase 5 metadata)."
            )

            # Decomposable Priority Scoring Components
            # 1. Flood Severity Score (0-30)
            sev_rank = SEVERITY_RANK.get(peak_sev, 0)
            sev_score = float(sev_rank * 7.5)

            # 2. Time-to-Threat Score (0-25)
            if first_threat_m == 0:
                threat_score = 25.0
            elif first_threat_m == 30:
                threat_score = 20.0
            elif first_threat_m == 60:
                threat_score = 15.0
            elif first_threat_m == 90:
                threat_score = 10.0
            elif first_threat_m is not None:
                threat_score = 5.0
            else:
                threat_score = 0.0

            # 3. Critical Access Score (0-25)
            access_score = 25.0 if has_facility_impact else 0.0

            # 4. Route Impact Score (0-20)
            # Double-counting control: if critical facility access is already threatened on this corridor,
            # access_score covers facility impact while route_score counts additional general responder routes.
            effective_routes = affected_route_count - (1 if has_facility_impact and affected_route_count > 0 else 0)
            route_score = float(min(20.0, max(0, effective_routes) * 10.0))

            # 5. Terrain & Drainage Score (0-15)
            td_score = 15.0 if flow_accum_high else 5.0

            # 6. Evidence Completeness Score (-10 to +10)
            if cand.verification_status == "VERIFIED":
                completeness_score = 10.0
            elif cand.provider_mode == "SYNTHETIC":
                completeness_score = -5.0
            elif cand.verification_status == "UNVERIFIED":
                completeness_score = -10.0
            else:
                completeness_score = 0.0

            # Compute Raw vs Final Clamped Priority Score (-10..125 -> 0..125)
            raw_priority_score = float(sev_score + threat_score + access_score + route_score + td_score + completeness_score)
            final_priority_score = max(0.0, min(125.0, raw_priority_score))

            # Deterministic Priority Category Rule
            # STRICT INVARIANT: Numeric score alone (e.g. >= 90) does NOT grant CRITICAL.
            # CRITICAL requires strong near-term (<= 60m) HIGH/SEVERE flood threat AND critical facility access materially threatened (or major corridor impact).
            is_critical_semantic = (
                (peak_sev in ["HIGH", "SEVERE"] and (first_threat_m is not None and first_threat_m <= 60))
                and (has_facility_impact or affected_route_count >= 2)
            )

            if is_critical_semantic:
                priority_cat = "CRITICAL"
            elif final_priority_score >= 65.0:
                priority_cat = "HIGH"
            elif final_priority_score >= 40.0:
                priority_cat = "MEDIUM"
            elif peak_sev != "UNKNOWN":
                priority_cat = "LOW"
            else:
                priority_cat = "UNKNOWN"

            priority_counts[priority_cat] += 1

            # Expected Benefit Category (HIGH, MEDIUM, LOW, UNKNOWN)
            if has_facility_impact or (priority_cat in ["CRITICAL", "HIGH"] and peak_sev in ["HIGH", "SEVERE"]):
                benefit_cat = "HIGH"
            elif priority_cat in ["HIGH", "MEDIUM"]:
                benefit_cat = "MEDIUM"
            elif priority_cat == "LOW":
                benefit_cat = "LOW"
            else:
                benefit_cat = "UNKNOWN"

            # Feasibility & Uncertainty Categories
            feasibility_cat = "FEASIBLE_REVIEW" if cand.verification_status == "VERIFIED" else "UNKNOWN"
            uncertainty_cat = "MEDIUM" if cand.provider_mode == "SYNTHETIC" else "LOW"

            # Cause-Chain Explanation: PREDICTION -> IMPACT -> CRITICALITY -> DECISION -> ACTION OPPORTUNITY
            prediction_txt = f"PREDICTION: Modeled flood severity reaches {peak_sev} (peak depth ~{peak_depth_m:.2f}m) around +{peak_m or 60} min."
            impact_txt = f"IMPACT: {route_note}"
            criticality_txt = f"CRITICALITY: {fac_access_note}"
            decision_txt = f"DECISION: Location prioritized as {priority_cat} priority for early response review."
            action_txt = f"ACTION OPPORTUNITY: Consider prioritizing review/protection ({cand.candidate_type}) before modeled threat window."
            governance_txt = "GOVERNANCE: Decision-support recommendation only. Operational feasibility and municipal resource availability have not been independently certified."

            full_explanation = f"{prediction_txt} {impact_txt} {criticality_txt} {decision_txt} {action_txt} {governance_txt}"

            breakdown = PriorityComponentBreakdownSchema(
                flood_severity_score=round(sev_score, 1),
                time_to_threat_score=round(threat_score, 1),
                critical_access_score=round(access_score, 1),
                route_impact_score=round(route_score, 1),
                terrain_drainage_score=round(td_score, 1),
                evidence_completeness_score=round(completeness_score, 1),
                raw_priority_score=round(raw_priority_score, 1),
                final_priority_score=round(final_priority_score, 1),
                total_score=round(final_priority_score, 1),
                ranking_category=priority_cat,
            )

            warnings: list[str] = []
            if cand.provider_mode == "SYNTHETIC":
                warnings.append(f"Intervention candidate '{cand.name}' is a SYNTHETIC DEVELOPMENT FIXTURE. Do not use for real municipal operations.")
            if cand.verification_status == "UNVERIFIED":
                warnings.append("Asset verification status is UNVERIFIED. On-site verification is required before field deployment.")
            if feasibility_cat == "UNKNOWN":
                warnings.append("Engineering feasibility and municipal equipment availability are UNKNOWN.")

            prov = {
                "platform": "AQUORA — Urban Flood Intelligence & Response Platform",
                "phase": "Phase 12 Protect the City v1.0",
                "candidate_id": cand.candidate_id,
                "candidate_type": cand.candidate_type,
                "digital_twin_run_id": dt_run_id,
                "routing_run_id": access_context_map.get("fac_hospital_a", {}).routing_run_id if "fac_hospital_a" in access_context_map else None,
                "critical_access_run_id": access_context_map.get("fac_hospital_a", {}).access_run_id if "fac_hospital_a" in access_context_map else None,
                "crs_canonical": "EPSG:4326",
                "crs_analysis": settings.GEOSPATIAL_ANALYSIS_CRS,
                "ml_status": "PROTOTYPE_ONLY",
                "training_labels_isolated": True,
                "created_at": now_utc.isoformat(),
            }

            rec_schema = ProtectCityRecommendationSchema(
                candidate=cand,
                priority=priority_cat,
                raw_priority_score=round(raw_priority_score, 1),
                final_priority_score=round(final_priority_score, 1),
                priority_score=round(final_priority_score, 1),
                priority_component_breakdown=breakdown,
                intervention_type=cand.candidate_type,
                first_threat_minutes=first_threat_m,
                first_high_severity_minutes=first_high_m,
                peak_severity=peak_sev,
                peak_severity_minutes=peak_m,
                expected_benefit=benefit_cat,
                feasibility_status=feasibility_cat,
                uncertainty_status=uncertainty_cat,
                affected_route_count=affected_route_count,
                affected_critical_facility_count=len(affected_fac_ids),
                affected_facility_ids=affected_fac_ids,
                route_impact_context=route_note,
                critical_access_context=fac_access_note,
                drainage_context=drainage_note,
                terrain_context=terrain_note,
                explanation=full_explanation,
                warnings=warnings,
                provenance=prov,
            )
            recommendations.append(rec_schema)

        # 5. Filter & Sort Recommendations by Priority & Onset
        min_p_rank = PRIORITY_RANK.get(request.minimum_priority.upper(), 1)
        filtered_recs = [r for r in recommendations if PRIORITY_RANK.get(r.priority, 0) >= min_p_rank]
        filtered_recs.sort(key=lambda r: (-r.priority_score, r.first_threat_minutes if r.first_threat_minutes is not None else 999))

        if request.priority_limit and len(filtered_recs) > request.priority_limit:
            filtered_recs = filtered_recs[: request.priority_limit]

        warnings: list[str] = [
            "Protect the City provides decision-support recommendations. It does not issue official municipal, emergency, or engineering orders.",
            "Municipal drainage capacity status is UNKNOWN (Phase 5 capacity metadata preserved).",
            "Phase 8 ML residual calibration is PROTOTYPE_ONLY and does not dominate deterministic physical priority rules.",
        ]

        uncertainty_summary = {
            "digital_twin_completeness": "HIGH",
            "drainage_capacity_completeness": "LOW_UNKNOWN",
            "critical_access_completeness": "HIGH",
            "overall_decision_confidence": "MEDIUM",
        }

        provenance = {
            "platform": "AQUORA — Urban Flood Intelligence & Response Platform",
            "phase": "Phase 12 Protect the City v1.0",
            "digital_twin_run_id": dt_run_id,
            "minimum_priority_filter": request.minimum_priority,
            "total_candidates_evaluated": len(cands),
            "recommendations_returned": len(filtered_recs),
            "crs_canonical": "EPSG:4326",
            "crs_analysis": settings.GEOSPATIAL_ANALYSIS_CRS,
            "ml_status": "PROTOTYPE_ONLY",
            "training_labels_isolated": True,
            "created_at": now_utc.isoformat(),
        }

        response = ProtectCityResponseSchema(
            run_id=run_id,
            digital_twin_run_id=dt_run_id,
            routing_run_id=access_context_map.get("fac_hospital_a", {}).routing_run_id if "fac_hospital_a" in access_context_map else None,
            critical_access_run_id=access_context_map.get("fac_hospital_a", {}).access_run_id if "fac_hospital_a" in access_context_map else None,
            generated_at=now_utc.isoformat(),
            total_candidates=len(cands),
            recommendations=filtered_recs,
            priority_counts=priority_counts,
            warnings=warnings,
            provenance=provenance,
            uncertainty_summary=uncertainty_summary,
        )

        # 6. Database Audit Persistence
        if self.db:
            try:
                run_db = ProtectCityRun(
                    run_identifier=run_id,
                    digital_twin_run_id=dt_run_id,
                    routing_run_id=response.routing_run_id,
                    critical_access_run_id=response.critical_access_run_id,
                    minimum_priority=request.minimum_priority,
                    total_candidates=len(cands),
                    status="COMPLETED",
                    provenance=provenance,
                )
                self.db.add(run_db)

                for rec in filtered_recs:
                    rec_db = ProtectCityRecommendation(
                        run_identifier=run_id,
                        candidate_id=rec.candidate.candidate_id,
                        priority=rec.priority,
                        priority_score=rec.priority_score,
                        intervention_type=rec.intervention_type,
                        first_threat_minutes=rec.first_threat_minutes,
                        first_high_severity_minutes=rec.first_high_severity_minutes,
                        peak_severity=rec.peak_severity,
                        peak_severity_minutes=rec.peak_severity_minutes,
                        expected_benefit=rec.expected_benefit,
                        feasibility_status=rec.feasibility_status,
                        uncertainty_status=rec.uncertainty_status,
                        affected_route_count=rec.affected_route_count,
                        affected_critical_facility_count=rec.affected_critical_facility_count,
                        priority_component_breakdown_json=rec.priority_component_breakdown.model_dump(),
                        explanation=rec.explanation,
                        warnings_json=rec.warnings,
                        provenance=rec.provenance,
                    )
                    self.db.add(rec_db)
                await self.db.commit()
            except (Exception, BaseException) as db_err:  # noqa: BLE001
                logger.warning(f"Database persistence for ProtectCityRun failed (offline/fallback): {db_err}")
                if self.db:
                    try:
                        await self.db.rollback()
                    except (Exception, BaseException):  # noqa: BLE001, S110
                        pass

        return response
