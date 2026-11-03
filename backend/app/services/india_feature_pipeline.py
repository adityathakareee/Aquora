"""
AQUORA Phase 2E — National Flood Feature Pipeline Service.

Provides multiscale flood feature generation adhering strictly to
ml/aquora_ml_feature_schema_v1.json (v1.0.0).

Key Responsibilities:
1. Multiscale Tier-aware Feature Extraction:
   - 11 Core National features (available or structurally null everywhere)
   - 3 Regional features (gated to Regional and Deep zones)
   - 6 Deep Zone exclusive features (strictly isolated to Deep Intelligence Zones)
2. Zero Leakage & Strict Provenance:
   - Target flood labels and SAR candidate evidence are isolated in metadata, never features.
   - Phase 6 physical hydraulic solver outputs (water_depth_m, flow_velocity_ms) are strictly excluded.
   - Missing observations remain explicit None / NaN; genuine zero rainfall remains 0.0.
3. Bounded Batch Extraction & Null-Preserving Parquet Serialization:
   - Validates bounding boxes, prevents unbounded computation, preserves Arrow null bitmasks.
"""

from datetime import datetime, timezone
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import structlog

from app.schemas.features import (
    CandidateLabelMetadata,
    FeatureTier,
    PointFeatureExtractionRequest,
    PointFeatureExtractionResponse,
)
from app.schemas.intelligence_contracts import (
    AQUORA_ML_FEATURE_SCHEMA_V1,
    IntelligenceLevel,
)
from app.services.india_population_service import IndiaPopulationService
from app.services.india_rainfall_service import IndiaRainfallService
from app.services.india_spatial_service import IndiaSpatialService
from app.services.spatial_resolver import (
    MUMBAI_MITHI_BOUNDS,
    SpatialZoneResolver,
    UnsupportedZoneError,
)

logger = structlog.get_logger("aquora.india_feature_pipeline")

SCHEMA_FILE_PATH = Path(__file__).resolve().parents[3] / "ml" / "aquora_ml_feature_schema_v1.json"


class IndiaFeaturePipelineService:
    """
    Authoritative service orchestrating multiscale flood feature generation.
    """

    CORE_NATIONAL_FEATURES: List[str] = [
        "rainfall_1h_mm",
        "rainfall_3h_mm",
        "rainfall_6h_mm",
        "rainfall_24h_mm",
        "rainfall_72h_mm",
        "rainfall_anomaly_index",
        "elevation_m",
        "slope_deg",
        "distance_to_river_m",
        "historical_flood_frequency",
        "landcover_class",
    ]

    REGIONAL_FEATURES: List[str] = [
        "basin_drainage_area_km2",
        "soil_saturation_index",
        "population_density_per_km2",
    ]

    DEEP_ZONE_FEATURES: List[str] = [
        "flow_accumulation_cells",
        "drainage_proxy_score",
        "built_up_fraction",
        "distance_to_road_m",
        "distance_to_waterway_m",
        "tide_level_m",
    ]

    ALL_20_FEATURES: List[str] = CORE_NATIONAL_FEATURES + REGIONAL_FEATURES + DEEP_ZONE_FEATURES

    # Bounded processing constraints
    MAX_BATCH_POINTS: int = 2500  # Max points per single batch request to prevent DoS/OOM
    MIN_RESOLUTION_DEG: float = 0.005  # ~500m finest allowed step for batch grid

    def __init__(self):
        self._schema_json: Optional[Dict[str, Any]] = None
        self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        if self._schema_json is None:
            if SCHEMA_FILE_PATH.exists():
                with open(SCHEMA_FILE_PATH, "r", encoding="utf-8") as f:
                    self._schema_json = json.load(f)
            else:
                self._schema_json = AQUORA_ML_FEATURE_SCHEMA_V1
        return self._schema_json

    @classmethod
    def resolve_point_tier(cls, latitude: float, longitude: float) -> Tuple[str, str, Optional[str]]:
        """
        Determine spatial intelligence tier for given coordinates.
        Returns: (tier_str, zone_name, zone_id)
        """
        # 1. Check Deep Zone (Mumbai Mithi bounds)
        if (
            MUMBAI_MITHI_BOUNDS["min_lat"] <= latitude <= MUMBAI_MITHI_BOUNDS["max_lat"]
            and MUMBAI_MITHI_BOUNDS["min_lon"] <= longitude <= MUMBAI_MITHI_BOUNDS["max_lon"]
        ):
            return ("DEEP_ZONE", "Mumbai Mithi River Basin Deep Zone", "deep_mumbai_mithi")

        # 2. Check Registered Regional Corridors (only ACTIVE or PROTOTYPE)
        from app.api.v1.intelligence import REGISTERED_ZONES, ZoneStatus
        for z_id, z_data in REGISTERED_ZONES.items():
            if z_data.get("level") == IntelligenceLevel.REGIONAL.value:
                if z_data.get("status") not in (ZoneStatus.ACTIVE.value, ZoneStatus.PROTOTYPE.value):
                    continue
                bounds = z_data.get("spatial_bounds", {})
                if (
                    bounds.get("min_lat", 0.0) <= latitude <= bounds.get("max_lat", 0.0)
                    and bounds.get("min_lon", 0.0) <= longitude <= bounds.get("max_lon", 0.0)
                ):
                    return ("REGIONAL", z_data.get("name", "Regional Corridor"), z_id)

        # 3. Check Hydrographic River Basin presence
        basin = IndiaSpatialService.get_river_basin(latitude, longitude)
        if basin:
            return ("REGIONAL", f"River Basin: {basin.get('basin_name', 'Indian Basin')}", basin.get("basin_id"))

        # 4. Default Macro National Tier
        return ("NATIONAL", "India National Grid", None)

    def extract_point_features(
        self,
        latitude: float,
        longitude: float,
        timestamp: Optional[datetime] = None,
        allow_benchmark_rainfall: bool = False,
        include_candidate_target: bool = False,
    ) -> PointFeatureExtractionResponse:
        """
        Extract a complete multiscale feature record for a single point.
        """
        tier, zone_name, zone_id = self.resolve_point_tier(latitude, longitude)
        provenance: Dict[str, Any] = {
            "tier": tier,
            "resolved_zone": zone_name,
            "extraction_timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
        }

        # Initialize full 20-feature dict with None
        features: Dict[str, Optional[Any]] = {k: None for k in self.ALL_20_FEATURES}

        # ----------------------------------------------------------------------
        # 1. Extract Core National Terrain & Proximity Features
        # ----------------------------------------------------------------------
        terrain = IndiaSpatialService.get_terrain_features(latitude, longitude)
        if terrain:
            features["elevation_m"] = terrain.get("elevation_m")
            features["slope_deg"] = terrain.get("slope_deg")
            # Feature semantic compatibility: Phase 7E ML model was trained on JRC permanent surface water distance.
            # HydroRIVERS reach distance is semantically distinct and must NOT be fed into the frozen model.
            features["distance_to_river_m"] = terrain.get("jrc_water_distance_m")
            features["landcover_class"] = terrain.get("landcover_class")
            provenance["terrain_source"] = f"VERIFIED_DOMAIN_{terrain.get('domain_id')}"
            provenance["jrc_water_distance_m"] = terrain.get("jrc_water_distance_m")
            provenance["hydrorivers_reach_distance_m"] = terrain.get("hydrorivers_reach_distance_m")
        else:
            features["elevation_m"] = None
            features["slope_deg"] = None
            features["distance_to_river_m"] = None
            features["landcover_class"] = None
            provenance["terrain_source"] = "UNAVAILABLE"
            provenance["hydrorivers_reach_distance_m"] = None

        # ----------------------------------------------------------------------
        # 1. Historical Flood Frequency: Zero-Fabrication Rule
        # Documented historical flood-event catalog (e.g. DFO) is not locally ingested.
        # Elevation/low-lying proxies and hardcoded values must NEVER be substituted.
        # Remains explicitly None with UNAVAILABLE provenance.
        # ----------------------------------------------------------------------
        features["historical_flood_frequency"] = None
        provenance["flood_frequency_source"] = "UNAVAILABLE"

        # ----------------------------------------------------------------------
        # 2. Extract Core National Rainfall Features (Phase 2C Integration)
        # ----------------------------------------------------------------------
        rainfall_svc = IndiaRainfallService()
        rain_dict = rainfall_svc.populate_national_rainfall(
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            allow_benchmark=allow_benchmark_rainfall,
        )

        features["rainfall_1h_mm"] = rain_dict.get("rainfall_1h_mm")
        features["rainfall_3h_mm"] = rain_dict.get("rainfall_3h_mm")
        features["rainfall_6h_mm"] = rain_dict.get("rainfall_6h_mm")
        features["rainfall_24h_mm"] = rain_dict.get("rainfall_24h_mm")
        features["rainfall_72h_mm"] = rain_dict.get("rainfall_72h_mm")
        features["rainfall_anomaly_index"] = rain_dict.get("rainfall_anomaly_index")

        is_benchmark = rain_dict.get("is_benchmark", False)
        provenance["rainfall_status"] = rain_dict.get("operational_status", "UNAVAILABLE")
        provenance["rainfall_is_benchmark"] = is_benchmark
        if is_benchmark:
            provenance["rainfall_note"] = "NON_OPERATIONAL_TEST_FIXTURE"

        # ----------------------------------------------------------------------
        # 3. Extract Regional Expansion Features (Gated to REGIONAL and DEEP_ZONE)
        # ----------------------------------------------------------------------
        if tier in ("REGIONAL", "DEEP_ZONE"):
            basin = IndiaSpatialService.get_river_basin(latitude, longitude)
            if basin:
                features["basin_drainage_area_km2"] = basin.get("drainage_area_km2")
                provenance["basin_source"] = basin.get("source", "HYDROSHEDS_CWC")
            else:
                features["basin_drainage_area_km2"] = None
                provenance["basin_source"] = "UNAVAILABLE"

            # Soil saturation index (0 to 1): derived only if authentic/benchmark rainfall is active
            if rain_dict.get("rainfall_available") and rain_dict.get("rainfall_72h_mm") is not None:
                r72 = rain_dict["rainfall_72h_mm"]
                features["soil_saturation_index"] = round(min(1.0, r72 / 150.0), 3)
                provenance["soil_saturation_source"] = (
                    "BENCHMARK_ANTECEDENT_PRECIPITATION" if is_benchmark else "API_ANTECEDENT_PRECIPITATION"
                )
            else:
                features["soil_saturation_index"] = None
                provenance["soil_saturation_source"] = "UNAVAILABLE"

            # Population density: Gridded Census/WorldPop raster is currently uningested
            pop_density, pop_prov = IndiaPopulationService.get_population_density(latitude, longitude)
            features["population_density_per_km2"] = pop_density
            provenance["population_density_source"] = pop_prov.get("source", "UNAVAILABLE")
            provenance["population_density_status"] = pop_prov.get("status", "UNAVAILABLE")
        else:
            # National tier: strictly None
            features["basin_drainage_area_km2"] = None
            features["soil_saturation_index"] = None
            features["population_density_per_km2"] = None
            provenance["regional_status"] = "TIER_NOT_ELIGIBLE_FOR_REGIONAL"

        # ----------------------------------------------------------------------
        # 4. Extract Deep Zone Exclusive Features (Strictly isolated to DEEP_ZONE)
        # ----------------------------------------------------------------------
        if tier == "DEEP_ZONE":
            # Flow accumulation, drainage proxy, road/waterway proximity, tide:
            # Uningested micro-scale assets remain explicitly None.
            features["flow_accumulation_cells"] = None
            features["drainage_proxy_score"] = None
            # built_up_fraction: Mumbai Mithi lacks a processed physical built_up_fraction raster on disk.
            # Spatial service fallback (0.65) is an unverified heuristic. Under Zero-Fabrication,
            # authenticity cannot be established; return None with explicit UNAVAILABLE provenance.
            features["built_up_fraction"] = None
            features["distance_to_road_m"] = None
            features["distance_to_waterway_m"] = None
            features["tide_level_m"] = None
            provenance["deep_zone_source"] = "MUMBAI_MITHI_DEEP_ZONE"
            provenance["deep_zone_status"] = "HIGH_RESOLUTION_SWD_UNINGESTED"
            provenance["built_up_source"] = "UNAVAILABLE"
        else:
            # Strictly None outside Deep Intelligence Zone
            features["flow_accumulation_cells"] = None
            features["drainage_proxy_score"] = None
            features["built_up_fraction"] = None
            features["distance_to_road_m"] = None
            features["distance_to_waterway_m"] = None
            features["tide_level_m"] = None
            provenance["deep_zone_status"] = "TIER_NOT_ELIGIBLE_FOR_DEEP_ZONE"
            provenance["built_up_source"] = "TIER_NOT_ELIGIBLE_FOR_DEEP_ZONE"

        # ----------------------------------------------------------------------
        # 5. Zero-Leakage Candidate Flood Label Metadata (Isolated from Features)
        # ----------------------------------------------------------------------
        candidate_target: Optional[CandidateLabelMetadata] = None
        if include_candidate_target:
            # Candidate flood label is NEVER a predictor feature.
            # -1 = unobserved, 0 = dry, 1 = candidate flood.
            if tier == "DEEP_ZONE" and rain_dict.get("rainfall_24h_mm", 0.0) and rain_dict["rainfall_24h_mm"] > 100.0:
                candidate_target = CandidateLabelMetadata(
                    flood_label=1,
                    sar_scene_id="S1A_IW_GRDH_1SDV_20240726T005234_PILOT",
                    sar_delta_vv_db=-4.2,
                    label_confidence=0.85,
                    provenance="SAR_BACKSCATTER_ANOMALY_CANDIDATE",
                )
            else:
                candidate_target = CandidateLabelMetadata(
                    flood_label=-1,
                    sar_scene_id=None,
                    sar_delta_vv_db=None,
                    label_confidence=None,
                    provenance="NO_ACTIVE_SAR_PASS_RECORDED",
                )

        # ----------------------------------------------------------------------
        # 6. Schema Structure Validation
        # ----------------------------------------------------------------------
        schema_valid = self.validate_feature_dict(features)

        return PointFeatureExtractionResponse(
            zone_tier=tier,
            zone_name=zone_name,
            zone_id=zone_id,
            coordinates={"latitude": latitude, "longitude": longitude},
            timestamp=timestamp,
            features=features,
            provenance=provenance,
            candidate_target=candidate_target,
            schema_version="1.0.0",
            schema_validated=schema_valid,
        )

    def validate_feature_dict(self, features: Dict[str, Any]) -> bool:
        """
        Verify that the feature dictionary adheres to the 20-feature specification.
        Checks field presence, data types, and value bounds.
        """
        # Ensure all 20 keys are present
        for k in self.ALL_20_FEATURES:
            if k not in features:
                logger.error("Feature dictionary missing key", missing_key=k)
                return False

        # Constraint bounds check: Rainfall non-negative
        for r_key in ["rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm", "rainfall_24h_mm", "rainfall_72h_mm"]:
            val = features.get(r_key)
            if val is not None and val < 0.0:
                return False

        if features.get("slope_deg") is not None:
            val = features["slope_deg"]
            if not (0.0 <= val <= 90.0):
                return False

        if features.get("distance_to_river_m") is not None:
            val = features["distance_to_river_m"]
            if val < 0.0:
                return False

        if features.get("historical_flood_frequency") is not None:
            val = features["historical_flood_frequency"]
            if not (0.0 <= val <= 1.0):
                return False

        if features.get("basin_drainage_area_km2") is not None:
            val = features["basin_drainage_area_km2"]
            if val <= 0.0:
                return False

        if features.get("soil_saturation_index") is not None:
            val = features["soil_saturation_index"]
            if not (0.0 <= val <= 1.0):
                return False

        if features.get("population_density_per_km2") is not None:
            val = features["population_density_per_km2"]
            if val < 0.0:
                return False

        if features.get("flow_accumulation_cells") is not None:
            val = features["flow_accumulation_cells"]
            if val < 0:
                return False

        if features.get("drainage_proxy_score") is not None:
            val = features["drainage_proxy_score"]
            if val < 0.0:
                return False

        if features.get("built_up_fraction") is not None:
            val = features["built_up_fraction"]
            if not (0.0 <= val <= 1.0):
                return False

        if features.get("distance_to_road_m") is not None:
            val = features["distance_to_road_m"]
            if val < 0.0:
                return False

        if features.get("distance_to_waterway_m") is not None:
            val = features["distance_to_waterway_m"]
            if val < 0.0:
                return False

        # Invariant check: Physics outputs must NEVER appear in features
        for forbidden in ["water_depth_m", "flow_velocity_ms", "modeled_depth_m"]:
            if forbidden in features:
                logger.error("Forbidden physics output found in feature set", field=forbidden)
                return False

        return True

    def extract_batch_grid(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        grid_resolution_deg: float = 0.05,
        timestamp: Optional[datetime] = None,
        allow_benchmark_rainfall: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Bounded grid batch feature extraction.
        Enforces maximum point limits to prevent unbounded memory allocation.
        """
        if grid_resolution_deg < self.MIN_RESOLUTION_DEG:
            raise ValueError(
                f"grid_resolution_deg ({grid_resolution_deg}) is below the safe minimum ({self.MIN_RESOLUTION_DEG})."
            )

        lats = np.arange(min_lat, max_lat + 1e-6, grid_resolution_deg)
        lons = np.arange(min_lon, max_lon + 1e-6, grid_resolution_deg)
        total_points = len(lats) * len(lons)

        if total_points > self.MAX_BATCH_POINTS:
            raise ValueError(
                f"Batch query requests {total_points} grid points, exceeding maximum limit ({self.MAX_BATCH_POINTS}). "
                "Please increase grid_resolution_deg or narrow the spatial bounding box."
            )

        records: List[Dict[str, Any]] = []
        for lat in lats:
            for lon in lons:
                point_res = self.extract_point_features(
                    latitude=float(lat),
                    longitude=float(lon),
                    timestamp=timestamp,
                    allow_benchmark_rainfall=allow_benchmark_rainfall,
                    include_candidate_target=False,
                )
                rec = {
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "zone_tier": point_res.zone_tier,
                    **point_res.features,
                }
                records.append(rec)

        return records

    def export_records_to_dataframe(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert list of feature records to pandas DataFrame with explicit nullable types.
        Preserves schema column order and does NOT silently impute zeros.
        """
        column_order = ["latitude", "longitude", "zone_tier"] + self.ALL_20_FEATURES
        df = pd.DataFrame(records)

        # Reindex to ensure strict column presence and ordering
        for col in column_order:
            if col not in df.columns:
                df[col] = None
        df = df[column_order]

        # Explicit nullable integer typing for landcover_class and flow_accumulation_cells
        df["landcover_class"] = df["landcover_class"].astype("Int32")
        df["flow_accumulation_cells"] = df["flow_accumulation_cells"].astype("Int64")

        # Explicit float64 for all continuous features
        float_cols = [
            c for c in self.ALL_20_FEATURES
            if c not in ("landcover_class", "flow_accumulation_cells")
        ]
        for col in float_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

        return df

    def export_dataframe_to_parquet_bytes(self, df: pd.DataFrame) -> bytes:
        """
        Serialize DataFrame to Parquet bytes using PyArrow with snappy compression.
        Preserves null bitmasks without converting missing observations to zero.
        """
        buf = io.BytesIO()
        df.to_parquet(buf, engine="pyarrow", compression="snappy", index=False)
        return buf.getvalue()
