"""
AQUORA 2.0 Geographic Hierarchy API Endpoints.

Provides discovery of Indian administrative and hydrological entities:
    COUNTRY -> STATE -> DISTRICT -> BASIN -> CITY -> CATCHMENT -> GRID_CELL

Preserves backward compatibility while paving the way for India-wide scale.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.schemas.intelligence_contracts import EntityType, IntelligenceLevel

router = APIRouter(prefix="/locations", tags=["Locations & Hierarchy"])

# Canonical in-memory hierarchy seed fixtures ensuring deterministic responses
# across development, testing, and production environments without raw scraping.
BASELINE_LOCATIONS: Dict[str, Dict[str, Any]] = {
    "IN": {
        "entity_code": "IN",
        "name": "India",
        "entity_type": EntityType.COUNTRY.value,
        "parent_code": None,
        "intelligence_level": IntelligenceLevel.NATIONAL.value,
        "centroid_lat": 20.5937,
        "centroid_lon": 78.9629,
        "default_zoom": 5,
        "child_codes": ["IN-MH"],
        "metadata": {
            "iso_code": "IND",
            "coverage": "Subcontinent",
            "tier": "National Screening Baseline",
        },
    },
    "IN-MH": {
        "entity_code": "IN-MH",
        "name": "Maharashtra",
        "entity_type": EntityType.STATE.value,
        "parent_code": "IN",
        "intelligence_level": IntelligenceLevel.REGIONAL.value,
        "centroid_lat": 19.7515,
        "centroid_lon": 75.7139,
        "default_zoom": 7,
        "child_codes": ["IN-MH-MUMBAI"],
        "metadata": {
            "state_code": "27",
            "capital": "Mumbai",
            "tier": "Regional Intelligence",
        },
    },
    "IN-MH-MUMBAI": {
        "entity_code": "IN-MH-MUMBAI",
        "name": "Mumbai",
        "entity_type": EntityType.CITY.value,
        "parent_code": "IN-MH",
        "intelligence_level": IntelligenceLevel.REGIONAL.value,
        "centroid_lat": 19.0760,
        "centroid_lon": 72.8777,
        "default_zoom": 11,
        "child_codes": ["CATCH-MITHI-01"],
        "metadata": {
            "municipal_body": "MCGM",
            "coastal": True,
            "tier": "Regional + Deep Zone Anchor",
        },
    },
    "CATCH-MITHI-01": {
        "entity_code": "CATCH-MITHI-01",
        "name": "Mithi Urban Catchment",
        "entity_type": EntityType.CATCHMENT.value,
        "parent_code": "IN-MH-MUMBAI",
        "intelligence_level": IntelligenceLevel.DEEP.value,
        "centroid_lat": 19.0800,
        "centroid_lon": 72.8750,
        "default_zoom": 13,
        "child_codes": [],
        "metadata": {
            "river": "Mithi River",
            "area_km2": 72.4,
            "outfall": "Mahim Creek / Arabian Sea",
            "tier": "Deep Intelligence Zone (Phase 1 Validated)",
        },
    },
}


class LocationSummary(BaseModel):
    entity_code: str
    name: str
    entity_type: str
    parent_code: Optional[str]
    intelligence_level: str
    centroid_lat: float
    centroid_lon: float
    default_zoom: int
    has_children: bool


class LocationDetail(LocationSummary):
    child_codes: List[str]
    metadata: Dict[str, Any]


@router.get("", response_model=List[LocationSummary], summary="List Geographic Entities")
async def list_locations(
    parent_code: Optional[str] = Query(None, description="Filter by parent entity code"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (COUNTRY, STATE, CITY, etc.)"),
    intelligence_level: Optional[str] = Query(None, description="Filter by level (NATIONAL, REGIONAL, DEEP)")
) -> List[LocationSummary]:
    """Retrieve geographic entities supporting navigation from India down to catchments."""
    results = []
    for loc in BASELINE_LOCATIONS.values():
        if parent_code is not None and loc["parent_code"] != parent_code:
            continue
        if entity_type is not None and loc["entity_type"].upper() != entity_type.upper():
            continue
        if intelligence_level is not None and loc["intelligence_level"].upper() != intelligence_level.upper():
            continue

        results.append(
            LocationSummary(
                entity_code=loc["entity_code"],
                name=loc["name"],
                entity_type=loc["entity_type"],
                parent_code=loc["parent_code"],
                intelligence_level=loc["intelligence_level"],
                centroid_lat=loc["centroid_lat"],
                centroid_lon=loc["centroid_lon"],
                default_zoom=loc["default_zoom"],
                has_children=len(loc["child_codes"]) > 0,
            )
        )
    return results


@router.get("/{entity_code}", response_model=LocationDetail, summary="Get Location Details")
async def get_location_by_code(entity_code: str) -> LocationDetail:
    """Retrieve details for a specific geographic entity in the hierarchy."""
    norm_code = entity_code.upper()
    # Normalize aliases
    if norm_code in ["MUMBAI", "CITY_MUMBAI"]:
        norm_code = "IN-MH-MUMBAI"
    elif norm_code in ["MITHI", "MITHI_CATCHMENT"]:
        norm_code = "CATCH-MITHI-01"
    elif norm_code in ["INDIA"]:
        norm_code = "IN"

    loc = BASELINE_LOCATIONS.get(norm_code)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Geographic entity '{entity_code}' not found.")

    return LocationDetail(
        entity_code=loc["entity_code"],
        name=loc["name"],
        entity_type=loc["entity_type"],
        parent_code=loc["parent_code"],
        intelligence_level=loc["intelligence_level"],
        centroid_lat=loc["centroid_lat"],
        centroid_lon=loc["centroid_lon"],
        default_zoom=loc["default_zoom"],
        has_children=len(loc["child_codes"]) > 0,
        child_codes=loc["child_codes"],
        metadata=loc["metadata"],
    )
