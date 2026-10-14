"""
AQUORA Phase 4 — India Population Exposure Ingestion & Resolution Service.

Provides demographic population density resolution across Indian administrative
and watershed regions under strict Zero-Fabrication principles.

INVARIANTS:
1. Zero Fabrication: If authentic, locally ingested gridded Census or WorldPop
   demographic data is not present on disk, returns None with explicit UNAVAILABLE provenance.
2. No Synthetic Fallback: Never synthesizes fake population numbers or assigns
   arbitrary national averages to unverified locations.
3. Traceability: Provenance explicitly details dataset status and source attribution.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import structlog

logger = structlog.get_logger("aquora.india_population_service")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RAW_DEMOGRAPHICS_DIR = PROJECT_ROOT / "data" / "raw" / "demographics"
PROCESSED_DEMOGRAPHICS_DIR = PROJECT_ROOT / "data" / "processed" / "demographics"


class IndiaPopulationService:
    """
    Authoritative service resolving authentic population exposure data across India.
    Implements honest, un-fabricated demographic queries.
    """

    @classmethod
    def is_available(cls) -> bool:
        """
        Check if authentic gridded demographic datasets (WorldPop 1km or Census tables)
        are ingested and available locally on disk.
        """
        # Neither raw nor processed demographic directories have authentic gridded rasters.
        if not PROCESSED_DEMOGRAPHICS_DIR.exists():
            return False

        # Check for verified raster files
        rasters = list(PROCESSED_DEMOGRAPHICS_DIR.glob("*.tif"))
        return len(rasters) > 0

    @classmethod
    def get_population_density(
        cls, latitude: float, longitude: float
    ) -> Tuple[Optional[float], Dict[str, Any]]:
        """
        Query population density in persons/km2 for a given geographic coordinate.

        Returns:
            Tuple of (population_density_per_km2, provenance_dict)
            If data is not locally ingested, returns (None, provenance).
        """
        # Validate coordinates within Indian bounding box [6.5-37.5°N, 68.0-97.5°E]
        if not (6.5 <= latitude <= 37.5 and 68.0 <= longitude <= 97.5):
            return None, {
                "status": "OUTSIDE_INDIA_EXTENT",
                "source": "UNAVAILABLE",
                "details": f"Coordinates ({latitude}, {longitude}) are outside Indian extent.",
            }

        # Check local authentic dataset availability
        if not cls.is_available():
            return None, {
                "status": "UNAVAILABLE",
                "source": "UNINGESTED_WORLDPOP_CENSUS",
                "details": (
                    "Authentic gridded population data (WorldPop / Census of India) "
                    "is not locally ingested. Zero-fabrication invariant enforced: value is None."
                ),
            }

        # Placeholder for future local raster sampling when authentic GeoTIFFs are ingested
        return None, {
            "status": "UNAVAILABLE",
            "source": "UNINGESTED_WORLDPOP_CENSUS",
            "details": "Population dataset not yet activated on local disk.",
        }
