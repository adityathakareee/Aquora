"""
AQUORA Phase 4 — Regional Watershed Intelligence Service (Level 2).

Orchestrates meso-scale flood risk and watershed exposure evaluation across
supported Indian river basins (Ganga, Brahmaputra, Godavari, Narmada, Mithi, etc.).
Adheres strictly to ml/aquora_ml_feature_schema_v1.json (v1.0.0).

INVARIANTS:
1. Exact 14 Predictors: Evaluates strictly the 11 CORE_NATIONAL plus 3 REGIONAL_EXPANSION features.
2. Deep Zone Isolation: Deep-zone exclusive features (flow_accumulation_cells,
   drainage_proxy_score, built_up_fraction, tide_level_m, etc.) are strictly prohibited.
3. Zero-Fabrication: Population density and critical facilities are never synthesized.
   If uningested, they remain None with explicit provenance.
4. Physical Engine Primacy: The Phase 6 deterministic hydraulic solver is never invoked or imitated.
5. Heuristic Clarification: Uncalibrated screening index is explicitly labeled as a dimensionless
   heuristic, never as a calibrated probability or hydraulic depth.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import structlog

from app.schemas.intelligence_contracts import IntelligenceLevel
from app.schemas.regional import (
    BasinSummaryResponse,
    RegionalBatchItem,
    RegionalBatchRequest,
    RegionalBatchResponse,
    RegionalExposureGrade,
    RegionalIntelligenceRequest,
    RegionalIntelligenceResponse,
    RegionalStatus,
)
from app.services.india_feature_pipeline import IndiaFeaturePipelineService
from app.services.india_spatial_service import IndiaSpatialService
from app.services.ml_model_registry import FloodModelRegistry

logger = structlog.get_logger("aquora.regional_intelligence_service")


class RegionalIntelligenceService:
    """
    Authoritative application service for Level 2 Regional flood intelligence.
    """

    # Exact 14 features authorized for Regional Level 2 intelligence
    REGIONAL_14_FEATURES: List[str] = (
        IndiaFeaturePipelineService.CORE_NATIONAL_FEATURES
        + IndiaFeaturePipelineService.REGIONAL_FEATURES
    )

    def __init__(self):
        self._feature_service = IndiaFeaturePipelineService()

    def evaluate_point(
        self,
        request: RegionalIntelligenceRequest,
    ) -> RegionalIntelligenceResponse:
        """
        Evaluate regional flood intelligence for a single coordinate point.
        """
        lat, lon = request.latitude, request.longitude

        # 1. Spatial validation: resolve river basin boundary from authentic hydrography
        basin = IndiaSpatialService.get_river_basin(lat, lon)
        basin_id = basin.get("basin_id") if basin else None
        basin_name = basin.get("basin_name") if basin else None

        # 2. Out of coverage gate: must fall within supported Indian river basins
        if not basin or not basin_id:
            logger.info("Regional query outside supported river basin coverage", lat=lat, lon=lon)
            return RegionalIntelligenceResponse(
                status=RegionalStatus.OUTSIDE_REGIONAL_COVERAGE.value,
                is_ready=False,
                model_id="aquora_regional_basin_model_v1",
                model_version="1.0.0-regional",
                intelligence_level="REGIONAL",
                basin_id=None,
                basin_name=None,
                resolved_zone="OUTSIDE_REGIONAL_BASIN_COVERAGE",
                coordinates={"latitude": lat, "longitude": lon},
                features_used=None,
                feature_values=None,
                watershed_exposure_index=None,
                exposure_grade=RegionalExposureGrade.UNCALIBRATED.value,
                calibration_status="UNCALIBRATED_REGIONAL_SCREENING",
                critical_facilities_count=None,
                provenance={
                    "domain": "REGIONAL_INDIA",
                    "error": "OUTSIDE_SUPPORTED_BASIN_GEOMETRY",
                },
                message=(
                    f"Coordinates ({lat}, {lon}) do not intersect any verified Indian river basin boundary. "
                    "Level 2 Regional Intelligence requires verified HydroBASINS watershed coverage. "
                    "Zero-fabrication invariant enforced: no synthetic fallback."
                ),
            )

        # 3. Extract features via IndiaFeaturePipelineService
        try:
            extraction = self._feature_service.extract_point_features(
                latitude=lat,
                longitude=lon,
                timestamp=request.timestamp,
                allow_benchmark_rainfall=request.allow_benchmark_rainfall,
                include_candidate_target=False,
            )
        except Exception as e:
            logger.error("Regional feature extraction failed", error=str(e), lat=lat, lon=lon)
            return RegionalIntelligenceResponse(
                status=RegionalStatus.FEATURE_ERROR.value,
                is_ready=False,
                model_id="aquora_regional_basin_model_v1",
                model_version="1.0.0-regional",
                intelligence_level="REGIONAL",
                basin_id=basin_id,
                basin_name=basin_name,
                resolved_zone=basin.get("basin_name", "UNKNOWN_BASIN"),
                coordinates={"latitude": lat, "longitude": lon},
                features_used=None,
                feature_values=None,
                watershed_exposure_index=None,
                exposure_grade=RegionalExposureGrade.UNCALIBRATED.value,
                calibration_status="UNCALIBRATED_REGIONAL_SCREENING",
                critical_facilities_count=None,
                provenance={"error": str(e)},
                message=f"Regional feature extraction failed: {str(e)}",
            )

        extracted = extraction.features
        tier = extraction.zone_tier
        resolved_zone = extraction.zone_name

        # 4. Strict Governance: Filter strictly to the 14 authorized features
        feature_values_14: Dict[str, Optional[float]] = {}
        for feat in self.REGIONAL_14_FEATURES:
            val = extracted.get(feat)
            feature_values_14[feat] = float(val) if val is not None else None

        # 5. Resolve critical facilities count honestly
        # Mumbai/Mithi has 366 authentic facilities; other basins currently have uningested facility catalogs.
        critical_facilities: Optional[int] = None
        facility_provenance: str = "UNAVAILABLE"
        if basin_id == "BASIN-MITHI" or "mithi" in resolved_zone.lower():
            critical_facilities = 366
            facility_provenance = "AUTHENTIC_OSM_MCGM_VERIFIED_BASELINE"
        else:
            critical_facilities = None
            facility_provenance = "CRITICAL_FACILITIES_UNINGESTED"

        # 6. Dispatch to registered Regional model in FloodModelRegistry
        model = FloodModelRegistry.get_model(IntelligenceLevel.REGIONAL, basin_id)
        prediction = model.predict_risk(feature_values_14)

        # 7. Formulate authoritative response
        if prediction.get("is_ready"):
            status_val = RegionalStatus.READY.value
        elif prediction.get("watershed_exposure_index") is not None:
            status_val = RegionalStatus.HEURISTIC_AVAILABLE.value
        else:
            status_val = RegionalStatus.MODEL_NOT_TRAINED.value

        provenance = {
            "tier": tier,
            "pipeline_version": "1.0.0",
            "basin_id": basin_id,
            "basin_source": "HYDROSHEDS_HYDROBASINS_V1C",
            "model_status": prediction.get("model_status", model.status),
            "critical_facilities_provenance": facility_provenance,
            "feature_provenance": extraction.provenance,
        }

        return RegionalIntelligenceResponse(
            status=status_val,
            is_ready=prediction.get("is_ready", False),
            model_id=model.model_id,
            model_version=model.model_version,
            intelligence_level="REGIONAL",
            basin_id=basin_id,
            basin_name=basin_name,
            resolved_zone=resolved_zone,
            coordinates={"latitude": lat, "longitude": lon},
            features_used=self.REGIONAL_14_FEATURES,
            feature_values=feature_values_14,
            watershed_exposure_index=prediction.get("watershed_exposure_index"),
            exposure_grade=prediction.get("exposure_grade"),
            calibration_status=prediction.get("calibration_status", "UNCALIBRATED_REGIONAL_SCREENING"),
            critical_facilities_count=critical_facilities,
            provenance=provenance,
            message=prediction.get("message"),
        )

    def evaluate_batch(
        self,
        request: RegionalBatchRequest,
    ) -> RegionalBatchResponse:
        """
        Evaluate regional flood intelligence for a bounded batch of points (max 250).
        """
        results: List[RegionalIntelligenceResponse] = []
        model = FloodModelRegistry.get_model(IntelligenceLevel.REGIONAL, "default")

        for item in request.points:
            pt_req = RegionalIntelligenceRequest(
                latitude=item.latitude,
                longitude=item.longitude,
                timestamp=item.timestamp,
                basin_id=item.basin_id,
                allow_benchmark_rainfall=request.allow_benchmark_rainfall,
            )
            res = self.evaluate_point(pt_req)
            results.append(res)

        return RegionalBatchResponse(
            total_requested=len(request.points),
            results=results,
            model_id=model.model_id,
            model_version=model.model_version,
        )

    @classmethod
    def get_basin_summary(cls, basin_id: str) -> Optional[BasinSummaryResponse]:
        """
        Retrieve structured metadata and capabilities for a specific Indian river basin.
        First checks authentic HydroBASINS Level 04 service, then legacy hierarchy.
        Returns None if basin_id is unknown.
        """
        from app.services.hydrobasins_service import HydrobasinsService
        matched = HydrobasinsService().get_basin_by_id(basin_id)

        if not matched:
            basins = IndiaSpatialService._load_basins_hierarchy().get("basins", [])
            for b in basins:
                if b.get("basin_id", "").upper() == basin_id.upper():
                    matched = b
                    break

        if not matched:
            return None

        # Determine capabilities
        is_mahanadi = matched.get("basin_id") in ["BASIN-MAHANADI", "BASIN-MAHANADI-UPPER", "BASIN-MAHANADI-LOWER"]
        is_active = matched.get("basin_id") in [
            "BASIN-GANGA",
            "BASIN-BRAHMAPUTRA",
            "BASIN-GODAVARI",
            "BASIN-KRISHNA",
            "BASIN-NARMADA",
            "BASIN-SABARMATI",
            "BASIN-MAHANADI",
            "BASIN-MITHI",
            "BASIN-WEST_COAST",
        ]

        capabilities = {
            "national_screening": "AVAILABLE",
            "regional_intelligence": "AVAILABLE" if is_active else "PLANNED",
            "deep_intelligence": "AVAILABLE" if matched.get("basin_id") in ["BASIN-MITHI", "CATCH-MITHI-01"] else "NOT_AVAILABLE",
            "high_resolution_dem": is_active,
            "hydrography_channels": is_active,
            "physical_flood_solver": matched.get("basin_id") in ["BASIN-MITHI", "CATCH-MITHI-01"],
            "experimental_research_layers": is_mahanadi,
        }

        gov_note = (
            "Phase 7F DFO 3382 regional research study. PROTOTYPE_ONLY / NOT_CALIBRATED / NOT_FOR_PUBLIC_ALERTS. Physics engine primary authority."
            if is_mahanadi
            else "HydroSHEDS / HydroBASINS v1.c canonical boundary. Copernicus GLO-30 DEM reference."
        )

        return BasinSummaryResponse(
            basin_id=matched["basin_id"],
            basin_name=matched["basin_name"],
            pfaf_code=matched.get("pfaf_code"),
            pfafstetter_level=matched.get("pfafstetter_level"),
            drainage_area_km2=matched.get("drainage_area_km2"),
            major_states=matched.get("major_states", []),
            centroid=matched.get("centroid", {"latitude": 0.0, "longitude": 0.0}),
            bounds=matched.get("bounds", {"min_lon": 0.0, "min_lat": 0.0, "max_lon": 0.0, "max_lat": 0.0}),
            operational_status="ACTIVE" if is_active else "PLANNED",
            capabilities=capabilities,
            governance_note=gov_note,
        )
