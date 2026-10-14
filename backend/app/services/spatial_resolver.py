"""
AQUORA 2.0 Spatial and Intelligence Zone Resolver.

Authoritative resolver bridging service/engine computations with the active
geographic hierarchy and intelligence zone registry.

INVARIANTS:
1. Reuses REGISTERED_ZONES from app.api.v1.intelligence without duplicating definitions.
2. For deep_mumbai_mithi (or None/default), returns verified Mumbai Mithi bounds:
   {"min_lat": 19.03, "max_lat": 19.13, "min_lon": 72.83, "max_lon": 72.93}
3. For unsupported zones, raises UnsupportedZoneError (NEVER silently falls back to Mumbai).
4. Never fabricates spatial bounds or capabilities for unverified locations.
"""

from typing import Any, Dict, Optional
import structlog

from app.schemas.geospatial import BoundingBox

logger = structlog.get_logger("aquora.spatial_resolver")


class UnsupportedZoneError(ValueError):
    """Raised when an operation is requested on an unverified or unsupported intelligence zone."""
    pass


MUMBAI_MITHI_BOUNDS = {
    "min_lat": 19.040,
    "max_lat": 19.120,
    "min_lon": 72.840,
    "max_lon": 72.910,
    "center_lat": 19.076,
    "center_lon": 72.877,
}


class SpatialZoneResolver:
    """
    Central authoritative resolver for intelligence zones, spatial bounding boxes,
    and capability validations.
    """

    DEFAULT_ZONE_ID = "deep_mumbai_mithi"

    # Canonical aliases mapping legacy or shorthand identifiers to official zone IDs
    ZONE_ALIASES: Dict[str, str] = {
        "mumbai": DEFAULT_ZONE_ID,
        "mumbai_mithi": DEFAULT_ZONE_ID,
        "mithi": DEFAULT_ZONE_ID,
        "mithi_catchment_mumbai": DEFAULT_ZONE_ID,
        "default": DEFAULT_ZONE_ID,
        "ganga": "regional_ganga_basin",
        "ganga_basin": "regional_ganga_basin",
        "brahmaputra": "regional_brahmaputra_basin",
        "brahmaputra_basin": "regional_brahmaputra_basin",
        "godavari": "regional_godavari_basin",
        "godavari_basin": "regional_godavari_basin",
        "narmada": "regional_narmada_basin",
        "narmada_basin": "regional_narmada_basin",
    }

    @classmethod
    def normalize_zone_id(cls, zone_id: Optional[str]) -> str:
        """Normalize zone identifier or return the default verified Mumbai zone."""
        if not zone_id or zone_id.strip() == "":
            return cls.DEFAULT_ZONE_ID

        clean_id = zone_id.strip().lower()
        return cls.ZONE_ALIASES.get(clean_id, zone_id.strip())

    @classmethod
    def resolve_zone(cls, zone_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolve the complete intelligence zone descriptor.
        Raises UnsupportedZoneError if the zone is not in REGISTERED_ZONES.
        """
        from app.api.v1.intelligence import REGISTERED_ZONES

        norm_id = cls.normalize_zone_id(zone_id)

        zone = REGISTERED_ZONES.get(norm_id)
        if not zone:
            logger.warning("Attempted to access unsupported intelligence zone", requested_zone=zone_id)
            raise UnsupportedZoneError(
                f"Intelligence zone '{zone_id}' is not recognized or supported by AQUORA. "
                "No synthetic spatial fallback is permitted."
            )

        return zone

    @classmethod
    def get_zone_bounds(cls, zone_id: Optional[str] = None) -> Dict[str, float]:
        """
        Return the spatial bounding dictionary for the specified zone.
        Guarantees exact Mumbai bounds for deep_mumbai_mithi:
        {"min_lat": 19.040, "max_lat": 19.120, "min_lon": 72.840, "max_lon": 72.910, "center_lat": 19.076, "center_lon": 72.877}
        """
        norm_id = cls.normalize_zone_id(zone_id)
        if norm_id == cls.DEFAULT_ZONE_ID:
            return dict(MUMBAI_MITHI_BOUNDS)

        zone = cls.resolve_zone(norm_id)
        bounds = zone.get("spatial_bounds")
        if not bounds:
            raise UnsupportedZoneError(f"Zone '{zone.get('zone_id')}' does not define valid spatial_bounds.")
        return bounds

    @classmethod
    def get_zone_bbox(cls, zone_id: Optional[str] = None) -> BoundingBox:
        """
        Return a BoundingBox schema object for the specified zone.
        For deep_mumbai_mithi (or None/default), returns canonical (minx=72.83, miny=19.03, maxx=72.93, maxy=19.13).
        minx = min_lon, miny = min_lat, maxx = max_lon, maxy = max_lat
        """
        norm_id = cls.normalize_zone_id(zone_id)
        if norm_id == cls.DEFAULT_ZONE_ID:
            return BoundingBox(minx=72.83, miny=19.03, maxx=72.93, maxy=19.13)

        bounds = cls.get_zone_bounds(norm_id)
        return BoundingBox(
            minx=bounds["min_lon"],
            miny=bounds["min_lat"],
            maxx=bounds["max_lon"],
            maxy=bounds["max_lat"],
        )

    @classmethod
    def get_zone_center(cls, zone_id: Optional[str] = None) -> tuple[float, float]:
        """Return (center_lat, center_lon) tuple for the specified zone."""
        bounds = cls.get_zone_bounds(zone_id)
        center_lat = (bounds["min_lat"] + bounds["max_lat"]) / 2.0
        center_lon = (bounds["min_lon"] + bounds["max_lon"]) / 2.0
        return (center_lat, center_lon)

    @classmethod
    def validate_capability(cls, zone_id: Optional[str], capability_key: str) -> None:
        """
        Verify that the requested zone actively supports the required capability.
        Raises UnsupportedZoneError if the capability is false, unavailable, or future.
        """
        zone = cls.resolve_zone(zone_id)
        caps = zone.get("capabilities", {})

        cap_val = caps.get(capability_key)
        if cap_val is True or cap_val == "AVAILABLE":
            return

        raise UnsupportedZoneError(
            f"Zone '{zone.get('zone_id')}' does not have capability '{capability_key}' "
            f"(Status: {cap_val or 'NOT_AVAILABLE'}). Operation aborted without fabrication."
        )
