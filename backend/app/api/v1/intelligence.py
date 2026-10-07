"""
AQUORA 2.0 Intelligence Tier, Capability & Governance API Endpoints.

Exposes:
- Operational Intelligence Zones (National, Regional, Deep)
- Location capability matrix (AVAILABLE / FUTURE / NOT_AVAILABLE)
- Versioned ML feature governance schema (aquora_ml_feature_schema_v1)
- Model registry catalog
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.schemas.intelligence_contracts import (
    AQUORA_ML_FEATURE_SCHEMA_V1,
    CapabilityStatus,
    IntelligenceLevel,
    ZoneStatus,
)
from app.services.ml_model_registry import FloodModelRegistry

router = APIRouter(prefix="/intelligence", tags=["Intelligence Tiers & Capabilities"])

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
