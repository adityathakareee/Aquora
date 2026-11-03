"""
AQUORA 2.0 Intelligence Tier, Capability & Governance API Endpoints.

Exposes:
- Operational Intelligence Zones (National, Regional, Deep)
- Location capability matrix (AVAILABLE / FUTURE / NOT_AVAILABLE)
- Versioned ML feature governance schema (aquora_ml_feature_schema_v1)
- Model registry catalog
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[4]
PHASE7_EXPERIMENTS = PROJECT_ROOT / "data" / "processed" / "phase7" / "experiments"
PHASE7_BOUNDARIES = PROJECT_ROOT / "data" / "processed" / "phase7" / "boundaries"

from app.schemas.intelligence_contracts import (
    AQUORA_ML_FEATURE_SCHEMA_V1,
    CapabilityStatus,
    IntelligenceLevel,
    ZoneStatus,
)
from app.schemas.screening import (
    NationalScreeningBatchRequest,
    NationalScreeningBatchResponse,
    NationalScreeningRequest,
    NationalScreeningResponse,
    ScreeningStatus,
)
from app.schemas.regional import (
    BasinSummaryResponse,
    RegionalBatchRequest,
    RegionalBatchResponse,
    RegionalIntelligenceRequest,
    RegionalIntelligenceResponse,
)
from app.schemas.deep import (
    DeepIntelligenceRequest,
    DeepIntelligenceResponse,
    DeepSimulationRequest,
)
from app.services.india_feature_pipeline import IndiaFeaturePipelineService
from app.services.ml_model_registry import FloodModelRegistry
from app.services.regional_intelligence_service import RegionalIntelligenceService
from app.services.deep_intelligence_service import DeepIntelligenceService

router = APIRouter(prefix="/intelligence", tags=["Intelligence Tiers & Capabilities"])
feature_pipeline_service = IndiaFeaturePipelineService()
regional_intelligence_service = RegionalIntelligenceService()
deep_intelligence_service = DeepIntelligenceService()


# Registered operational intelligence zones
REGISTERED_ZONES: Dict[str, Dict[str, Any]] = {
    "deep_mumbai_mithi": {
        "zone_id": "deep_mumbai_mithi",
        "name": "Mumbai Mithi River Basin Deep Zone",
        "entity_code": "CATCH-MITHI-01",
        "level": IntelligenceLevel.DEEP.value,
        "status": ZoneStatus.ACTIVE.value,
        "spatial_bounds": {
            "min_lat": 19.03,
            "max_lat": 19.13,
            "min_lon": 72.83,
            "max_lon": 72.93,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.AVAILABLE.value,
            "regional_intelligence": CapabilityStatus.AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.AVAILABLE.value,
            "physical_flood_solver": True,
            "high_resolution_dem": True,
            "real_radar_corroboration": True,
            "critical_facility_routing": True,
            "drainage_loss_proxy": True,
            "verified_facilities_count": 366,
        },
        "governance_note": "AQUORA 1.0 foundational pilot. Full hydraulic depth & route optimization active.",
    },
    "regional_maharashtra": {
        "zone_id": "regional_maharashtra",
        "name": "Maharashtra State Regional Corridor",
        "entity_code": "IN-MH",
        "level": IntelligenceLevel.REGIONAL.value,
        "status": ZoneStatus.PLANNED.value,
        "spatial_bounds": {
            "min_lat": 15.6,
            "max_lat": 22.0,
            "min_lon": 72.6,
            "max_lon": 80.9,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.FUTURE.value,
            "regional_intelligence": CapabilityStatus.FUTURE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": False,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
        },
        "governance_note": "Regional intelligence zone planned for Phase 2 data engineering.",
    },
    "national_india": {
        "zone_id": "national_india",
        "name": "India National Screening Extent",
        "entity_code": "IN",
        "level": IntelligenceLevel.NATIONAL.value,
        "status": ZoneStatus.PLANNED.value,
        "spatial_bounds": {
            "min_lat": 6.5,
            "max_lat": 37.5,
            "min_lon": 68.0,
            "max_lon": 97.5,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.FUTURE.value,
            "regional_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": False,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
        },
        "governance_note": "National screening model scheduled for Phase 2/3 Kaggle training.",
    },
    "regional_ganga_basin": {
        "zone_id": "regional_ganga_basin",
        "name": "Ganga River Basin Regional Zone",
        "entity_code": "BASIN-GANGA",
        "level": IntelligenceLevel.REGIONAL.value,
        "status": ZoneStatus.ACTIVE.value,
        "spatial_bounds": {
            "min_lat": 21.8,
            "max_lat": 31.5,
            "min_lon": 73.0,
            "max_lon": 89.0,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.AVAILABLE.value,
            "regional_intelligence": CapabilityStatus.AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": True,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
        },
        "governance_note": "Phase 2B regional intelligence foundation: 30m DEM, HydroRIVERS, and HydroBASINS active.",
    },
    "regional_brahmaputra_basin": {
        "zone_id": "regional_brahmaputra_basin",
        "name": "Brahmaputra River Basin Regional Zone",
        "entity_code": "BASIN-BRAHMAPUTRA",
        "level": IntelligenceLevel.REGIONAL.value,
        "status": ZoneStatus.ACTIVE.value,
        "spatial_bounds": {
            "min_lat": 24.5,
            "max_lat": 29.5,
            "min_lon": 88.0,
            "max_lon": 96.5,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.AVAILABLE.value,
            "regional_intelligence": CapabilityStatus.AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": True,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
        },
        "governance_note": "Phase 2B regional intelligence foundation active.",
    },
    "regional_godavari_basin": {
        "zone_id": "regional_godavari_basin",
        "name": "Godavari River Basin Regional Zone",
        "entity_code": "BASIN-GODAVARI",
        "level": IntelligenceLevel.REGIONAL.value,
        "status": ZoneStatus.ACTIVE.value,
        "spatial_bounds": {
            "min_lat": 17.0,
            "max_lat": 22.7,
            "min_lon": 73.4,
            "max_lon": 82.6,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.AVAILABLE.value,
            "regional_intelligence": CapabilityStatus.AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": True,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
        },
        "governance_note": "Phase 2B regional intelligence foundation active.",
    },
    "regional_krishna_basin": {
        "zone_id": "regional_krishna_basin",
        "name": "Krishna River Basin Regional Zone",
        "entity_code": "BASIN-KRISHNA",
        "level": IntelligenceLevel.REGIONAL.value,
        "status": ZoneStatus.ACTIVE.value,
        "spatial_bounds": {
            "min_lat": 13.1,
            "max_lat": 19.4,
            "min_lon": 73.3,
            "max_lon": 81.2,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.AVAILABLE.value,
            "regional_intelligence": CapabilityStatus.AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": True,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
        },
        "governance_note": "Phase 2B regional intelligence foundation active.",
    },
    "regional_narmada_basin": {
        "zone_id": "regional_narmada_basin",
        "name": "Narmada River Basin Regional Zone",
        "entity_code": "BASIN-NARMADA",
        "level": IntelligenceLevel.REGIONAL.value,
        "status": ZoneStatus.ACTIVE.value,
        "spatial_bounds": {
            "min_lat": 21.3,
            "max_lat": 22.6,
            "min_lon": 72.5,
            "max_lon": 81.8,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.AVAILABLE.value,
            "regional_intelligence": CapabilityStatus.AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": True,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
        },
        "governance_note": "Phase 2B regional intelligence foundation active.",
    },
    "regional_sabarmati_basin": {
        "zone_id": "regional_sabarmati_basin",
        "name": "Sabarmati River Basin Regional Zone",
        "entity_code": "BASIN-SABARMATI",
        "level": IntelligenceLevel.REGIONAL.value,
        "status": ZoneStatus.ACTIVE.value,
        "spatial_bounds": {
            "min_lat": 22.0,
            "max_lat": 24.8,
            "min_lon": 71.0,
            "max_lon": 74.0,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.AVAILABLE.value,
            "regional_intelligence": CapabilityStatus.AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": True,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
        },
        "governance_note": "Phase 2B regional intelligence foundation active.",
    },
    "regional_mahanadi_basin": {
        "zone_id": "regional_mahanadi_basin",
        "name": "Mahanadi River Basin Regional Research Zone",
        "entity_code": "BASIN-MAHANADI",
        "level": IntelligenceLevel.REGIONAL.value,
        "status": ZoneStatus.PROTOTYPE.value,
        "spatial_bounds": {
            "min_lat": 19.3,
            "max_lat": 23.6,
            "min_lon": 80.4,
            "max_lon": 86.9,
        },
        "capabilities": {
            "national_screening": CapabilityStatus.AVAILABLE.value,
            "regional_intelligence": CapabilityStatus.AVAILABLE.value,
            "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            "physical_flood_solver": False,
            "high_resolution_dem": True,
            "real_radar_corroboration": False,
            "critical_facility_routing": False,
            "drainage_loss_proxy": False,
            "verified_facilities_count": 0,
            "experimental_research_layers": True,
        },
        "governance_note": (
            "Phase 7F regional experimental study (DFO 3382). "
            "PROTOTYPE_ONLY / NOT_CALIBRATED / NOT_FOR_PUBLIC_ALERTS. "
            "Phase 6 deterministic physics engine is the sole primary flood authority."
        ),
    },
}


class IntelligenceZoneResponse(BaseModel):
    zone_id: str
    name: str
    entity_code: str
    level: str
    status: str
    spatial_bounds: Dict[str, float]
    capabilities: Dict[str, Any]
    governance_note: str


class LocationCapabilityResponse(BaseModel):
    entity_code: str
    name: str
    intelligence_level: str
    capabilities: Dict[str, str]
    deep_zone_ids: List[str]
    active_zone_id: Optional[str]


@router.get("/zones", response_model=List[IntelligenceZoneResponse], summary="List Operational Intelligence Zones")
async def list_intelligence_zones(
    level: Optional[str] = Query(None, description="Filter by level: NATIONAL, REGIONAL, DEEP"),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, PROTOTYPE, PLANNED")
) -> List[IntelligenceZoneResponse]:
    """Retrieve operational and planned AQUORA Intelligence Zones."""
    results = []
    for zone in REGISTERED_ZONES.values():
        if level and zone["level"].upper() != level.upper():
            continue
        if status and zone["status"].upper() != status.upper():
            continue

        results.append(IntelligenceZoneResponse(**zone))
    return results


@router.get("/zones/{zone_id}", response_model=IntelligenceZoneResponse, summary="Get Intelligence Zone Details")
async def get_intelligence_zone(zone_id: str) -> IntelligenceZoneResponse:
    """Retrieve details for a specific intelligence zone."""
    zone = REGISTERED_ZONES.get(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail=f"Intelligence Zone '{zone_id}' not found.")
    return IntelligenceZoneResponse(**zone)


@router.get("/capabilities", response_model=LocationCapabilityResponse, summary="Query Location Capabilities")
async def get_capabilities_by_location(
    location_code: str = Query("IN-MH-MUMBAI", description="Target location code (e.g. IN, IN-MH, IN-MH-MUMBAI, CATCH-MITHI-01)")
) -> LocationCapabilityResponse:
    """
    Return trustworthy capability status for any location across India.
    Never fabricates unsupported deep capabilities.
    """
    norm = location_code.upper()
    if norm in ["MUMBAI", "CITY_MUMBAI", "IN-MH-MUMBAI"]:
        return LocationCapabilityResponse(
            entity_code="IN-MH-MUMBAI",
            name="Mumbai",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.AVAILABLE.value,
            },
            deep_zone_ids=["deep_mumbai_mithi"],
            active_zone_id="deep_mumbai_mithi",
        )
    elif norm in ["MITHI", "CATCH-MITHI-01"]:
        return LocationCapabilityResponse(
            entity_code="CATCH-MITHI-01",
            name="Mithi Urban Catchment",
            intelligence_level=IntelligenceLevel.DEEP.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.AVAILABLE.value,
            },
            deep_zone_ids=["deep_mumbai_mithi"],
            active_zone_id="deep_mumbai_mithi",
        )
    elif norm in ["IN-MH", "MAHARASHTRA"]:
        return LocationCapabilityResponse(
            entity_code="IN-MH",
            name="Maharashtra",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.FUTURE.value,
                "regional_intelligence": CapabilityStatus.FUTURE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=["deep_mumbai_mithi"],
            active_zone_id=None,
        )
    elif norm in ["IN", "INDIA"]:
        return LocationCapabilityResponse(
            entity_code="IN",
            name="India",
            intelligence_level=IntelligenceLevel.NATIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.FUTURE.value,
                "regional_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=["deep_mumbai_mithi"],
            active_zone_id=None,
        )
    elif norm in ["BASIN-GANGA", "GANGA", "BASIN_GANGA"]:
        return LocationCapabilityResponse(
            entity_code="BASIN-GANGA",
            name="Ganga River Basin",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id="regional_ganga_basin",
        )
    elif norm in ["BASIN-BRAHMAPUTRA", "BRAHMAPUTRA", "BASIN_BRAHMAPUTRA"]:
        return LocationCapabilityResponse(
            entity_code="BASIN-BRAHMAPUTRA",
            name="Brahmaputra River Basin",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id="regional_brahmaputra_basin",
        )
    elif norm in ["BASIN-GODAVARI", "GODAVARI", "BASIN_GODAVARI"]:
        return LocationCapabilityResponse(
            entity_code="BASIN-GODAVARI",
            name="Godavari River Basin",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id="regional_godavari_basin",
        )
    elif norm in ["BASIN-NARMADA", "NARMADA", "BASIN_NARMADA"]:
        return LocationCapabilityResponse(
            entity_code="BASIN-NARMADA",
            name="Narmada River Basin",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id="regional_narmada_basin",
        )
    elif norm in ["BASIN-MAHANADI", "MAHANADI", "BASIN_MAHANADI"]:
        return LocationCapabilityResponse(
            entity_code="BASIN-MAHANADI",
            name="Mahanadi River Basin",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id="regional_mahanadi_basin",
        )
    elif norm in ["BASIN-KRISHNA", "KRISHNA", "BASIN_KRISHNA"]:
        return LocationCapabilityResponse(
            entity_code="BASIN-KRISHNA",
            name="Krishna River Basin",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id="regional_krishna_basin",
        )
    elif norm in ["BASIN-SABARMATI", "SABARMATI", "BASIN_SABARMATI"]:
        return LocationCapabilityResponse(
            entity_code="BASIN-SABARMATI",
            name="Sabarmati River Basin",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id="regional_sabarmati_basin",
        )
    elif norm in ["BASIN-WEST_COAST", "WEST_COAST", "BASIN_WEST_COAST"]:
        return LocationCapabilityResponse(
            entity_code="BASIN-WEST_COAST",
            name="West Coast & Western Ghats Drainage Basin",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.AVAILABLE.value,
            },
            deep_zone_ids=["deep_mumbai_mithi"],
            active_zone_id="deep_mumbai_mithi",
        )
    elif norm in ["IN-OD", "ODISHA", "ORISSA"]:
        return LocationCapabilityResponse(
            entity_code="IN-OD",
            name="Odisha",
            intelligence_level=IntelligenceLevel.REGIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.AVAILABLE.value,
                "regional_intelligence": CapabilityStatus.AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id="regional_mahanadi_basin",
        )
    else:
        # Generic unsupported entity
        return LocationCapabilityResponse(
            entity_code=location_code,
            name=location_code,
            intelligence_level=IntelligenceLevel.NATIONAL.value,
            capabilities={
                "national_screening": CapabilityStatus.FUTURE.value,
                "regional_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
                "deep_intelligence": CapabilityStatus.NOT_AVAILABLE.value,
            },
            deep_zone_ids=[],
            active_zone_id=None,
        )


@router.get("/feature-schema", summary="Get Versioned ML Feature Schema")
async def get_feature_schema() -> Dict[str, Any]:
    """Retrieve the authoritative versioned ML predictor schema (aquora_ml_feature_schema_v1)."""
    return AQUORA_ML_FEATURE_SCHEMA_V1


@router.get("/models", summary="List Registered Flood Models")
async def list_models() -> List[Dict[str, Any]]:
    """Retrieve registered models across all intelligence tiers from FloodModelRegistry."""
    return FloodModelRegistry.list_models()


def is_within_national_bounds(lat: float, lon: float) -> bool:
    """Validate whether coordinate lies within the India national extent [6.5-37.5°N, 68.0-97.5°E]."""
    bounds = REGISTERED_ZONES["national_india"]["spatial_bounds"]
    return (
        bounds["min_lat"] <= lat <= bounds["max_lat"]
        and bounds["min_lon"] <= lon <= bounds["max_lon"]
    )


@router.post(
    "/screening/national",
    response_model=NationalScreeningResponse,
    summary="National Flood Risk Screening (Macro Scale)",
    description=(
        "Evaluates the 11 Core National ML features for macro flood susceptibility across India. "
        "Strictly decoupled from Phase 6 physical hydraulic simulation. "
        "Reports explicit MODEL_NOT_TRAINED status when model artifact is unverified/untrained; "
        "never fabricates predictions or synthetic scores."
    ),
)
async def screen_national_point(request: NationalScreeningRequest) -> NationalScreeningResponse:
    # 1. Retrieve the national screening model from the registry
    model = FloodModelRegistry.get_model(IntelligenceLevel.NATIONAL, "national_india")

    # 2. Check national extent bounds
    if not is_within_national_bounds(request.latitude, request.longitude):
        return NationalScreeningResponse(
            status=ScreeningStatus.OUTSIDE_COVERAGE.value,
            is_ready=False,
            model_id=model.model_id,
            model_version=model.model_version,
            resolved_zone="OUTSIDE_INDIA_EXTENT",
            coordinates={"latitude": request.latitude, "longitude": request.longitude},
            features_used=None,
            feature_values=None,
            susceptibility_probability=None,
            susceptibility_grade=None,
            calibration_status="UNCALIBRATED_MACRO_SCREENING",
            provenance={"domain": "NATIONAL_INDIA", "error": "OUTSIDE_SPATIAL_EXTENT"},
            message=(
                f"Coordinates ({request.latitude}, {request.longitude}) fall outside the "
                "supported India National Screening extent [6.5-37.5°N, 68.0-97.5°E]. "
                "No synthetic spatial fallback is permitted."
            ),
        )

    # 3. Extract 11 Core National features via Phase 2E pipeline
    try:
        extraction = feature_pipeline_service.extract_point_features(
            latitude=request.latitude,
            longitude=request.longitude,
            timestamp=request.timestamp,
            allow_benchmark_rainfall=request.allow_benchmark_rainfall,
            include_candidate_target=False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"National feature pipeline extraction failed: {str(e)}",
        )

    tier = extraction.zone_tier
    resolved_zone = extraction.zone_name
    extracted_features = extraction.features

    # Filter to exact 11 core national features in governed order
    core_features: Dict[str, Optional[float]] = {}
    for feat_name in IndiaFeaturePipelineService.CORE_NATIONAL_FEATURES:
        val = extracted_features.get(feat_name)
        core_features[feat_name] = float(val) if val is not None else None

    # 4. Predict via registered national model
    prediction_result = model.predict_risk(core_features)

    # 5. Assemble response adhering to schema
    if prediction_result.get("model_status") == ScreeningStatus.INSUFFICIENT_INPUT_DATA.value:
        status_val = ScreeningStatus.INSUFFICIENT_INPUT_DATA.value
        is_ready = False
    elif prediction_result.get("is_ready"):
        status_val = ScreeningStatus.READY.value
        is_ready = True
    else:
        status_val = ScreeningStatus.MODEL_NOT_TRAINED.value
        is_ready = False

    return NationalScreeningResponse(
        status=status_val,
        is_ready=is_ready,
        model_id=model.model_id,
        model_version=model.model_version,
        resolved_zone=resolved_zone,
        coordinates={"latitude": request.latitude, "longitude": request.longitude},
        features_used=prediction_result.get("features_evaluated", IndiaFeaturePipelineService.CORE_NATIONAL_FEATURES),
        feature_values=core_features,
        susceptibility_probability=prediction_result.get("predicted_probability"),
        susceptibility_grade=prediction_result.get("susceptibility_grade"),
        calibration_status=prediction_result.get("calibration_status", "UNCALIBRATED_MACRO_SCREENING"),
        governance_status="PROTOTYPE_ONLY",
        operational_readiness="NOT_FOR_PUBLIC_ALERTS",
        physics_engine_primacy="Phase 6 deterministic physics engine remains primary authority",
        hydrorivers_reach_distance_m=extraction.provenance.get("hydrorivers_reach_distance_m"),
        provenance={
            "tier": tier,
            "pipeline_version": "1.0.0",
            "governance_status": "PROTOTYPE_ONLY",
            "calibration_status": "NOT_CALIBRATED",
            "operational_readiness": "NOT_FOR_PUBLIC_ALERTS",
            "physics_engine_primacy": "Phase 6 deterministic physics engine remains primary authority",
            "model_status": prediction_result.get("model_status", model.status),
            "input_validity": prediction_result.get("input_validity"),
            "available_predictors": prediction_result.get("available_predictors"),
            "missing_predictors": prediction_result.get("missing_predictors"),
            "feature_provenance": extraction.provenance,
        },
        message=prediction_result.get("message"),
    )


@router.post(
    "/screening/national/batch",
    response_model=NationalScreeningBatchResponse,
    summary="Batch National Flood Risk Screening",
    description="Bounded batch screening for up to 250 points across India.",
)
async def screen_national_batch(request: NationalScreeningBatchRequest) -> NationalScreeningBatchResponse:
    if len(request.points) > 250:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(request.points)} exceeds maximum allowed limit of 250 points.",
        )

    model = FloodModelRegistry.get_model(IntelligenceLevel.NATIONAL, "national_india")
    results: List[NationalScreeningResponse] = []

    for pt in request.points:
        single_req = NationalScreeningRequest(
            latitude=pt.latitude,
            longitude=pt.longitude,
            timestamp=pt.timestamp,
            allow_benchmark_rainfall=request.allow_benchmark_rainfall,
        )
        res = await screen_national_point(single_req)
        results.append(res)

    return NationalScreeningBatchResponse(
        total_requested=len(request.points),
        results=results,
        model_id=model.model_id,
        model_version=model.model_version,
    )


# ==============================================================================
# PHASE 4: LEVEL 2 REGIONAL INTELLIGENCE ENDPOINTS
# ==============================================================================


@router.post(
    "/regional",
    response_model=RegionalIntelligenceResponse,
    summary="Regional Flood Intelligence & Watershed Risk",
    description=(
        "Level 2 Regional flood intelligence across supported Indian river basins. "
        "Evaluates the 14 authorized features (11 Core National + 3 Regional Expansion). "
        "Never fabricates values for uningested features or outside supported basins."
    ),
)
async def get_regional_intelligence(
    request: RegionalIntelligenceRequest,
) -> RegionalIntelligenceResponse:
    return regional_intelligence_service.evaluate_point(request)


@router.post(
    "/regional/batch",
    response_model=RegionalBatchResponse,
    summary="Batch Regional Flood Intelligence",
    description="Bounded batch regional flood intelligence for up to 250 points across India.",
)
async def get_regional_intelligence_batch(
    request: RegionalBatchRequest,
) -> RegionalBatchResponse:
    if len(request.points) > 250:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(request.points)} exceeds maximum allowed limit of 250 points.",
        )
    return regional_intelligence_service.evaluate_batch(request)


@router.get(
    "/regional/basins/{basin_id}",
    response_model=BasinSummaryResponse,
    summary="River Basin Hydrographic Summary",
    description="Get metadata, boundaries, drainage area, and operational capabilities for an Indian river basin.",
)
async def get_basin_summary(basin_id: str) -> BasinSummaryResponse:
    summary = RegionalIntelligenceService.get_basin_summary(basin_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"River basin '{basin_id}' not found in canonical HydroBASINS hierarchy.",
        )
    return summary


@router.get(
    "/regional/mahanadi/experiments",
    summary="Mahanadi Experimental Exploration Metrics & Robustness Review",
    description=(
        "Returns Phase 7F Stage 4 and Stage 4.1 experimental results for the DFO 3382 Mahanadi regional study. "
        "Strictly governance-bounded: PROTOTYPE_ONLY, NOT_CALIBRATED, NOT_FOR_PUBLIC_ALERTS. "
        "Phase 6 deterministic physics engine remains the primary operational flood authority."
    ),
)
async def get_mahanadi_experiments() -> Dict[str, Any]:
    metrics_path = PHASE7_EXPERIMENTS / "dfo3382_robustness_metrics.json"
    ablation_path = PHASE7_EXPERIMENTS / "dfo3382_feature_ablation.csv"
    spatial_audit_path = PHASE7_EXPERIMENTS / "dfo3382_spatial_independence_audit.json"
    importance_path = PHASE7_EXPERIMENTS / "dfo3382_feature_importance.csv"

    metrics: Dict[str, Any] = {}
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    elif (PHASE7_EXPERIMENTS / "dfo3382_model_metrics.json").exists():
        with open(PHASE7_EXPERIMENTS / "dfo3382_model_metrics.json", "r", encoding="utf-8") as f:
            metrics = json.load(f)

    ablation_records: List[Dict[str, Any]] = []
    if ablation_path.exists():
        with open(ablation_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            ablation_records = list(reader)

    spatial_audit: Dict[str, Any] = {}
    if spatial_audit_path.exists():
        with open(spatial_audit_path, "r", encoding="utf-8") as f:
            spatial_audit = json.load(f)

    feature_importance: List[Dict[str, Any]] = []
    if importance_path.exists():
        with open(importance_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            feature_importance = list(reader)

    return {
        "event_id": "DFO_3382",
        "basin_id": "BASIN-MAHANADI",
        "basin_name": "Mahanadi River Basin",
        "governance_status": "PROTOTYPE_ONLY",
        "calibration_status": "NOT_CALIBRATED",
        "alert_eligibility": "NOT_FOR_PUBLIC_ALERTS",
        "primary_flood_authority": "Phase 6 2D Hydrodynamic Physics Solver (engines/flood/solver.py)",
        "scientific_conclusion": (
            "DFO 3382 label distribution is strongly coupled with optical water boundary margins "
            "(66.8% flood cells in dry_fraction < 0.70). On high-quality terrestrial cells away from water bodies, "
            "model collapses near baseline prevalence. Models serve as uncalibrated experimental exploratory ranking, "
            "not operational flood predictions."
        ),
        "metrics": metrics,
        "ablation_comparison": ablation_records,
        "spatial_independence_audit": spatial_audit,
        "feature_importance": feature_importance,
    }


@router.get(
    "/regional/mahanadi/subbasins",
    summary="Mahanadi HydroBASINS Sub-basins with Spatial Partitions",
    description="Returns the 27 Level 8 HydroBASINS sub-basins in the Mahanadi study extent with spatial partition tags.",
)
async def get_mahanadi_subbasins() -> Dict[str, Any]:
    subbasin_geojson_path = PHASE7_BOUNDARIES / "mahanadi_hydrobasins" / "mahanadi_hydrobasins_lev08.geojson"
    splits_path = PHASE7_EXPERIMENTS / "dfo3382_spatial_splits.json"

    if not subbasin_geojson_path.exists():
        raise HTTPException(status_code=404, detail="Mahanadi sub-basin boundaries not found.")

    with open(subbasin_geojson_path, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    splits_data: Dict[str, Any] = {}
    if splits_path.exists():
        with open(splits_path, "r", encoding="utf-8") as f:
            splits_data = json.load(f)

    partitions = splits_data.get("partitions", {})
    train_ids = set(partitions.get("TRAIN", {}).get("subbasin_ids", []))
    val_ids = set(partitions.get("VAL", {}).get("subbasin_ids", []))
    test_ids = set(partitions.get("TEST", {}).get("subbasin_ids", []))
    study_ids = train_ids | val_ids | test_ids

    study_features = []
    for feat in geojson_data.get("features", []):
        props = feat.setdefault("properties", {})
        h_id = props.get("HYBAS_ID")
        if h_id in study_ids:
            if h_id in train_ids:
                props["spatial_partition"] = "TRAIN"
            elif h_id in val_ids:
                props["spatial_partition"] = "VALIDATION"
            elif h_id in test_ids:
                props["spatial_partition"] = "TEST"
            study_features.append(feat)

    return {
        "type": geojson_data.get("type", "FeatureCollection"),
        "total_subbasins": len(study_features),
        "partitions": {
            "train_count": len(train_ids),
            "val_count": len(val_ids),
            "test_count": len(test_ids),
        },
        "spatial_independence": "ENFORCED_ZERO_LEAKAGE",
        "features": study_features,
    }


@router.get(
    "/regional/mahanadi/layers",
    summary="Mahanadi Regional Research Layer Manifest",
    description="Returns catalog of regional exploratory geospatial and ML layers for the Mahanadi study extent.",
)
async def get_mahanadi_layers() -> Dict[str, Any]:
    return {
        "basin_id": "BASIN-MAHANADI",
        "basin_name": "Mahanadi River Basin",
        "governance": {
            "status": "PROTOTYPE_ONLY",
            "calibration": "NOT_CALIBRATED",
            "alerts": "NOT_FOR_PUBLIC_ALERTS",
            "primary_authority": "Phase 6 2D Hydrodynamic Physics Solver",
            "banner_text": "EXPERIMENTAL SPATIAL RESEARCH — NOT AN OPERATIONAL FLOOD FORECAST",
        },
        "layers": [
            {
                "id": "subbasin_partitions",
                "name": "Sub-basin Partitions (HydroBASINS Lev08)",
                "type": "vector",
                "visible_default": True,
                "description": "15 Train, 6 Validation, 6 Test sub-basins partitioned to prevent spatial autocorrelation leakage.",
                "color_map": {"TRAIN": "#3b82f6", "VALIDATION": "#f59e0b", "TEST": "#10b981"},
            },
            {
                "id": "river_network",
                "name": "HydroRIVERS Drainage Network",
                "type": "vector",
                "visible_default": True,
                "description": "Canonical vector stream network and distributaries (Devi, Daya, Bhargavi, Kushabhadra).",
                "color": "#06b6d4",
            },
            {
                "id": "land_water_mask",
                "name": "Land/Water Mask & Margin Uncertainty",
                "type": "raster",
                "visible_default": False,
                "description": "Copernicus/ESA Land-Water. Highlights MIXED_WATER_MARGIN (<0.70 dry) where 66.8% flood observations concentrate.",
                "color": "#6366f1",
            },
            {
                "id": "dfo3382_observations",
                "name": "DFO 3382 MODIS Observed Inundation (Sept 2008)",
                "type": "observation",
                "visible_default": True,
                "description": "Satellite-derived coarse optical flood extent from Dartmouth Flood Observatory.",
                "color": "#ef4444",
            },
            {
                "id": "experimental_ranking_scores",
                "name": "Experimental ML Ranking Scores (Ablated XGBoost)",
                "type": "experimental_ml",
                "visible_default": False,
                "description": "Diagnostic spatial rankings. Not calibrated probabilities; not evaluated on real-time rainfall.",
                "color": "#8b5cf6",
            },
        ],
    }


# ==============================================================================
# PHASE 5: LEVEL 3 DEEP INTELLIGENCE & PHYSICAL ENGINE FEDERATION
# ==============================================================================


@router.post(
    "/deep",
    response_model=DeepIntelligenceResponse,
    summary="Deep Intelligence Point Inspection",
    description=(
        "Level 3 Deep Intelligence point inspection across the verified Mumbai Mithi Deep Zone. "
        "Samples high-resolution 30m terrain rasters (elevation, slope, aspect, flow accumulation, drainage proxy) "
        "using EPSG:32643 projection. Simulation is opt-in and not launched automatically."
    ),
)
async def inspect_deep_point(
    request: DeepIntelligenceRequest,
) -> DeepIntelligenceResponse:
    return await deep_intelligence_service.evaluate_point(request)


@router.post(
    "/deep/simulate",
    response_model=DeepIntelligenceResponse,
    summary="Explicit Deep Zone Physical Flood Simulation",
    description=(
        "Executes deterministic 2D hydrodynamic simulation for the Mumbai Mithi Deep Zone. "
        "Enforces mass balance conservation and evaluates flood depth impacts on verified critical facilities."
    ),
)
async def simulate_deep_zone(
    request: DeepSimulationRequest,
) -> DeepIntelligenceResponse:
    return await deep_intelligence_service.run_simulation(request)
