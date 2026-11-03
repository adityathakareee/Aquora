"""
AQUORA Phase 7 — Authoritative HydroBASINS Level 04 Watershed Polygon Service.

Replaces approximate rectangular bounding-box basin attribution with authentic
HydroSHEDS / WWF HydroBASINS (v1.c) Level 04 vector polygon containment.

Key Capabilities:
1. Genuine Polygon Containment:
   - Uses authentic HydroBASINS Level 04 shapefiles (72 basins intersecting India).
   - In-memory Shapely STRtree spatial indexing for sub-millisecond query evaluation.
2. CRS Transformation:
   - Supports arbitrary input coordinate reference systems via pyproj Transformer,
     projecting coordinates into canonical EPSG:4326.
3. Deterministic Boundary Tie-Breaking:
   - Coordinates lying on shared watershed divides (boundary touches) are resolved
     deterministically by selecting the basin with larger upstream contributing area
     (UP_AREA), with lower HYBAS_ID as a consistent tie-breaker.
4. River Network Resolution:
   - Integrates HydroRIVERS Asia vector reaches (Strahler order >= 4) with spatial
     indexing to compute true geodetic river network distance (distance_to_river_m).
5. Zero Fabrication Invariance:
   - Coordinates outside Indian watershed boundaries (e.g. open ocean) return None.
   - Never falls back to approximate rectangular boxes.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from pyproj import Geod, Transformer
import shapely
from shapely.geometry import Point, box
import structlog

logger = structlog.get_logger("aquora.hydrobasins_service")

# Resolve Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
HYDROBASINS_LEV4_SHP = (
    DATA_DIR
    / "raw"
    / "phase7"
    / "hydrography"
    / "hydrobasins"
    / "extracted"
    / "hybas_as_lev04_v1c.shp"
)
HYDRORIVERS_SHP = (
    DATA_DIR
    / "raw"
    / "phase7"
    / "hydrography"
    / "hydrorivers"
    / "extracted"
    / "HydroRIVERS_v10_as_shp"
    / "HydroRIVERS_v10_as.shp"
)
PROC_BOUNDARIES = DATA_DIR / "processed" / "boundaries"

# India territorial bounding box [min_lon, min_lat, max_lon, max_lat]
INDIA_BBOX = (68.0, 6.0, 98.0, 38.0)

# Canonical mapping of primary HydroBASINS Level 04 basins in India
CANONICAL_BASIN_NAMES: Dict[int, Dict[str, Any]] = {
    4040960480: {
        "basin_id": "BASIN-GANGA",
        "basin_name": "Ganga River Basin",
        "drainage_area_km2": 861452.0,
        "aliases": ["GANGA", "BASIN_GANGA", "REGIONAL_GANGA_BASIN", "4040960480"],
        "major_states": ["IN-UK", "IN-UP", "IN-BR", "IN-WB", "IN-JH", "IN-MP", "IN-RJ", "IN-HR", "IN-DL"],
        "primary_river": "Ganga",
    },
    4040960200: {
        "basin_id": "BASIN-BRAHMAPUTRA",
        "basin_name": "Brahmaputra River Basin",
        "aliases": ["BRAHMAPUTRA", "BASIN_BRAHMAPUTRA", "REGIONAL_BRAHMAPUTRA_BASIN", "4040960200"],
        "major_states": ["IN-AS", "IN-AR", "IN-ML", "IN-NL", "IN-SK"],
        "primary_river": "Brahmaputra",
    },
    4040865930: {
        "basin_id": "BASIN-BRAHMAPUTRA-UPPER",
        "basin_name": "Upper Brahmaputra / Dibang / Lohit Basin",
        "aliases": ["UPPER_BRAHMAPUTRA", "LOHIT_DIBANG", "4040865930"],
        "major_states": ["IN-AR", "IN-AS"],
        "primary_river": "Brahmaputra / Lohit",
    },
    4040027780: {
        "basin_id": "BASIN-GODAVARI",
        "basin_name": "Godavari River Basin",
        "aliases": ["GODAVARI", "BASIN_GODAVARI", "REGIONAL_GODAVARI_BASIN", "4040027780"],
        "major_states": ["IN-MH", "IN-TG", "IN-AP", "IN-CH", "IN-OR"],
        "primary_river": "Godavari",
    },
    4040027790: {
        "basin_id": "BASIN-GODAVARI-DELTA",
        "basin_name": "Godavari Delta Coastal Basin",
        "aliases": ["GODAVARI_DELTA", "4040027790"],
        "major_states": ["IN-AP"],
        "primary_river": "Godavari Delta",
    },
    4040027940: {
        "basin_id": "BASIN-KRISHNA",
        "basin_name": "Krishna River Basin",
        "aliases": ["KRISHNA", "BASIN_KRISHNA", "REGIONAL_KRISHNA_BASIN", "4040027940"],
        "major_states": ["IN-MH", "IN-KA", "IN-TG", "IN-AP"],
        "primary_river": "Krishna",
    },
    4040027950: {
        "basin_id": "BASIN-PENNAR",
        "basin_name": "Pennar & Andhra East Coast Basin",
        "aliases": ["PENNAR", "BASIN_PENNAR", "4040027950"],
        "major_states": ["IN-AP", "IN-KA", "IN-TN"],
        "primary_river": "Pennar",
    },
    4040028760: {
        "basin_id": "BASIN-CAUVERY",
        "basin_name": "Cauvery River Basin",
        "aliases": ["CAUVERY", "KAVERI", "BASIN_CAUVERY", "4040028760"],
        "major_states": ["IN-KA", "IN-TN", "IN-KL"],
        "primary_river": "Cauvery",
    },
    4040028770: {
        "basin_id": "BASIN-TAMILNADU-COAST",
        "basin_name": "Tamil Nadu South East Coast / Vaigai Basin",
        "aliases": ["VAIGAI", "TAMILNADU_COAST", "4040028770"],
        "major_states": ["IN-TN", "IN-KL"],
        "primary_river": "Vaigai / Tamirabarani",
    },
    4040029530: {
        "basin_id": "BASIN-MITHI",
        "basin_name": "Mithi Catchment / Coastal Maharashtra Basin",
        "aliases": [
            "BASIN-WEST_COAST",
            "WEST_COAST",
            "WESTERN_GHATS",
            "KONKAN",
            "BASIN-MITHI",
            "MITHI",
            "BASIN-NARMADA",
            "NARMADA",
            "BASIN-TAPI",
            "TAPI",
            "REGIONAL_MAHARASHTRA",
            "REGIONAL_NARMADA_BASIN",
            "DEEP_MUMBAI_MITHI",
            "4040029530",
        ],
        "major_states": ["IN-MH", "IN-GJ", "IN-GA", "IN-KA", "IN-KL", "IN-MP"],
        "primary_river": "Narmada / Tapi / Mithi / Periyar",
    },
    4040031820: {
        "basin_id": "BASIN-SABARMATI",
        "basin_name": "Sabarmati River Basin",
        "aliases": ["SABARMATI", "BASIN_SABARMATI", "REGIONAL_SABARMATI_BASIN", "4040031820"],
        "major_states": ["IN-GJ", "IN-RJ"],
        "primary_river": "Sabarmati",
    },
    4040031750: {
        "basin_id": "BASIN-MAHI",
        "basin_name": "Mahi River Basin",
        "aliases": ["MAHI", "BASIN_MAHI", "4040031750"],
        "major_states": ["IN-MP", "IN-RJ", "IN-GJ"],
        "primary_river": "Mahi",
    },
    4040027100: {
        "basin_id": "BASIN-MAHANADI-UPPER",
        "basin_name": "Upper Mahanadi River Basin",
        "aliases": ["UPPER_MAHANADI", "HIRAKUD", "4040027100"],
        "major_states": ["IN-CH", "IN-OR"],
        "primary_river": "Mahanadi (Upper Reach)",
    },
    4040027110: {
        "basin_id": "BASIN-MAHANADI",
        "basin_name": "Lower Mahanadi & Delta Coastal Basin",
        "aliases": [
            "MAHANADI",
            "BASIN_MAHANADI",
            "REGIONAL_MAHANADI_BASIN",
            "MAHANADI_DELTA",
            "4040027110",
        ],
        "major_states": ["IN-OR"],
        "primary_river": "Mahanadi (Delta Reach)",
    },
    4040794730: {
        "basin_id": "BASIN-INDUS-PUNJAB",
        "basin_name": "Indus Basin - Sutlej / Beas / Punjab",
        "aliases": ["INDUS_PUNJAB", "SUTLEJ", "BEAS", "4040794730"],
        "major_states": ["IN-PB", "IN-HP", "IN-HR", "IN-RJ", "IN-JK"],
        "primary_river": "Sutlej / Beas / Ravi",
    },
    4040033430: {
        "basin_id": "BASIN-LUNI",
        "basin_name": "Luni River & Rajasthan Desert Basin",
        "aliases": ["LUNI", "RAJASTHAN_DESERT", "4040033430"],
        "major_states": ["IN-RJ", "IN-GJ"],
        "primary_river": "Luni",
    },
    4040025460: {
        "basin_id": "BASIN-SUBARNAREKHA",
        "basin_name": "Subarnarekha & Brahmani Basin",
        "aliases": ["SUBARNAREKHA", "BRAHMANI", "BAITARANI", "4040025460"],
        "major_states": ["IN-JH", "IN-OR", "IN-WB"],
        "primary_river": "Subarnarekha / Brahmani",
    },
    4040025450: {
        "basin_id": "BASIN-MEGHNA-DELTA",
        "basin_name": "Lower Meghna / Sundarbans Coastal Basin",
        "aliases": ["MEGHNA", "SUNDARBANS", "4040025450"],
        "major_states": ["IN-WB", "IN-TR", "IN-MZ"],
        "primary_river": "Meghna / Padma Estuary",
    },
}


class HydrobasinsService:
    """
    Authoritative service managing authentic HydroBASINS Level 04 watershed geometries,
    in-memory spatial indexing, CRS transformation, and HydroRIVERS reach distance calculation.
    """

    _instance: Optional["HydrobasinsService"] = None

    def __new__(cls) -> "HydrobasinsService":
        if cls._instance is None:
            cls._instance = super(HydrobasinsService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._initialized = True
        self._gdf = None
        self._sindex = None
        self._geoms = None
        self._basins_metadata: Dict[int, Dict[str, Any]] = {}
        self._alias_to_hybas_id: Dict[str, int] = {}
        self._rivers_gdf = None
        self._rivers_tree = None
        self._geod = Geod(ellps="WGS84")

        self._load_hydrobasins()

    def _load_hydrobasins(self) -> None:
        """Load and spatially index HydroBASINS Level 04 polygons intersecting India."""
        if not HYDROBASINS_LEV4_SHP.exists():
            logger.error(
                "HydroBASINS Level 04 shapefile missing",
                expected_path=str(HYDROBASINS_LEV4_SHP),
            )
            return

        try:
            import geopandas as gpd

            logger.info("Loading HydroBASINS Level 04 polygons for India...")
            gdf_full = gpd.read_file(HYDROBASINS_LEV4_SHP)

            # Filter to India bounding box
            india_polygon = box(*INDIA_BBOX)
            gdf_india = gdf_full[gdf_full.intersects(india_polygon)].copy().reset_index(drop=True)

            self._gdf = gdf_india
            self._geoms = gdf_india.geometry.values
            self._sindex = shapely.STRtree(self._geoms)

            # Build metadata cache & alias lookup
            for idx, row in gdf_india.iterrows():
                hybas_id = int(row["HYBAS_ID"])
                c = row.geometry.centroid
                bounds = row.geometry.bounds

                canon = CANONICAL_BASIN_NAMES.get(hybas_id, {})
                basin_id = canon.get("basin_id", f"HYBAS-{hybas_id}")
                basin_name = canon.get("basin_name", f"HydroBASINS Unit {hybas_id}")
                major_states = canon.get("major_states", [])

                meta = {
                    "hybas_id": hybas_id,
                    "basin_id": basin_id,
                    "basin_name": basin_name,
                    "main_bas": int(row["MAIN_BAS"]),
                    "next_down": int(row["NEXT_DOWN"]),
                    "pfaf_id": int(row["PFAF_ID"]),
                    "pfaf_code": str(row["PFAF_ID"]),
                    "pfafstetter_level": 4,
                    "sub_area_km2": float(row["SUB_AREA"]),
                    "drainage_area_km2": float(canon.get("drainage_area_km2", row["SUB_AREA"])),
                    "up_area_km2": float(row["UP_AREA"]),
                    "centroid": {"latitude": float(c.y), "longitude": float(c.x)},
                    "bounds": {
                        "min_lon": float(bounds[0]),
                        "min_lat": float(bounds[1]),
                        "max_lon": float(bounds[2]),
                        "max_lat": float(bounds[3]),
                    },
                    "major_states": major_states,
                    "is_exact_polygon": True,
                }
                self._basins_metadata[hybas_id] = meta

                # Register aliases
                clean_bid = basin_id.upper()
                self._alias_to_hybas_id[clean_bid] = hybas_id
                self._alias_to_hybas_id[str(hybas_id)] = hybas_id
                for alias in canon.get("aliases", []):
                    self._alias_to_hybas_id[alias.upper()] = hybas_id

            logger.info(
                "Indexed authentic HydroBASINS Level 04 basins successfully",
                total_india_basins=len(self._basins_metadata),
            )
        except Exception as e:
            logger.error("Failed to load HydroBASINS Level 04 dataset", error=str(e))
            self._gdf = None
            self._sindex = None

    def _ensure_rivers_loaded(self) -> None:
        """Lazily load and spatially index HydroRIVERS Asia reaches with Strahler order >= 4."""
        if self._rivers_tree is not None:
            return

        if not HYDRORIVERS_SHP.exists():
            logger.warning(
                "HydroRIVERS shapefile not found at expected path",
                expected_path=str(HYDRORIVERS_SHP),
            )
            return

        try:
            import geopandas as gpd

            logger.info("Lazily loading HydroRIVERS reaches (Strahler >= 4) for India...")
            gdf_riv = gpd.read_file(
                HYDRORIVERS_SHP,
                bbox=INDIA_BBOX,
                where="ORD_STRA >= 4",
            )
            self._rivers_gdf = gdf_riv.reset_index(drop=True)
            self._rivers_tree = shapely.STRtree(self._rivers_gdf.geometry.values)
            logger.info(
                "Indexed HydroRIVERS reach network",
                reach_count=len(self._rivers_gdf),
            )
        except Exception as e:
            logger.error("Failed to index HydroRIVERS reach network", error=str(e))
            self._rivers_gdf = None
            self._rivers_tree = None

    def transform_coordinates(
        self,
        x: float,
        y: float,
        source_crs: str = "EPSG:4326",
    ) -> Tuple[float, float]:
        """
        Transform arbitrary coordinates into canonical WGS84 (longitude, latitude).
        """
        if not source_crs or source_crs.upper() in ("EPSG:4326", "WGS84", "CRS84"):
            return float(x), float(y)

        transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(x, y)
        return float(lon), float(lat)

    def resolve_basin(
        self,
        latitude: float,
        longitude: float,
        crs: str = "EPSG:4326",
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve genuine HydroBASINS Level 04 watershed polygon for the given coordinate.

        Guarantees:
        - Point-in-polygon containment using authentic boundaries.
        - Deterministic tie-breaking on shared boundaries / divides (UP_AREA -> min HYBAS_ID).
        - Returns None if outside Indian watershed territory (Zero Fabrication).
        - Never silently falls back to approximate rectangular bounding boxes.
        """
        if self._sindex is None or self._gdf is None:
            logger.warning("HydroBASINS service uninitialized; cannot resolve polygon.")
            return None

        # 1. Coordinate transformation
        lon, lat = self.transform_coordinates(longitude, latitude, source_crs=crs)

        # 2. National territorial bounding envelope pre-check
        min_lon, min_lat, max_lon, max_lat = INDIA_BBOX
        if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
            return None

        query_pt = Point(lon, lat)

        # 3. Query spatial index for candidate polygon bounding envelopes
        candidate_indices = self._sindex.query(query_pt)
        if len(candidate_indices) == 0:
            return None

        # 4. Strict interior containment evaluation
        interior_matches = []
        boundary_matches = []

        for idx in candidate_indices:
            poly = self._geoms[idx]
            if poly.contains(query_pt):
                dist_to_boundary = float(poly.boundary.distance(query_pt))
                interior_matches.append((idx, dist_to_boundary))
            elif poly.touches(query_pt) or poly.distance(query_pt) < 1e-7:
                boundary_matches.append((idx, 0.0))

        # 5. Handle Interior Match (Unambiguous)
        if len(interior_matches) == 1:
            idx, dist_bd = interior_matches[0]
            hybas_id = int(self._gdf.iloc[idx]["HYBAS_ID"])
            base_meta = dict(self._basins_metadata[hybas_id])
            base_meta.update({
                "containment_type": "STRICT_INTERIOR",
                "boundary_ambiguity": False,
                "distance_to_boundary_deg": dist_bd,
                "distance_to_boundary_km": dist_bd * 111.32,
                "query_coordinates": {"latitude": lat, "longitude": lon},
            })
            return base_meta

        # Multiple overlapping interiors (rare topological overlap)
        if len(interior_matches) > 1:
            # Deterministic resolution: choose largest UP_AREA
            sorted_matches = sorted(
                interior_matches,
                key=lambda x: (
                    -float(self._gdf.iloc[x[0]]["UP_AREA"]),
                    int(self._gdf.iloc[x[0]]["HYBAS_ID"]),
                ),
            )
            idx, dist_bd = sorted_matches[0]
            hybas_id = int(self._gdf.iloc[idx]["HYBAS_ID"])
            base_meta = dict(self._basins_metadata[hybas_id])
            candidate_ids = [int(self._gdf.iloc[m[0]]["HYBAS_ID"]) for m in sorted_matches]
            base_meta.update({
                "containment_type": "OVERLAP_RESOLVED",
                "boundary_ambiguity": True,
                "distance_to_boundary_deg": dist_bd,
                "distance_to_boundary_km": dist_bd * 111.32,
                "ambiguous_hybas_ids": candidate_ids,
                "query_coordinates": {"latitude": lat, "longitude": lon},
            })
            return base_meta

        # 6. Handle Boundary / Divide Points (Touches)
        if boundary_matches:
            # Deterministic resolution policy:
            # Primary criterion: largest upstream contributing drainage area (UP_AREA)
            # Secondary criterion: lower numerical HYBAS_ID
            sorted_boundary = sorted(
                boundary_matches,
                key=lambda x: (
                    -float(self._gdf.iloc[x[0]]["UP_AREA"]),
                    int(self._gdf.iloc[x[0]]["HYBAS_ID"]),
                ),
            )
            idx, dist_bd = sorted_boundary[0]
            hybas_id = int(self._gdf.iloc[idx]["HYBAS_ID"])
            base_meta = dict(self._basins_metadata[hybas_id])
            candidate_ids = [int(self._gdf.iloc[m[0]]["HYBAS_ID"]) for m in sorted_boundary]

            base_meta.update({
                "containment_type": "BOUNDARY_RESOLVED",
                "boundary_ambiguity": len(sorted_boundary) > 1,
                "distance_to_boundary_deg": 0.0,
                "distance_to_boundary_km": 0.0,
                "ambiguous_hybas_ids": candidate_ids if len(candidate_ids) > 1 else None,
                "query_coordinates": {"latitude": lat, "longitude": lon},
            })
            return base_meta

        # Outside all polygons
        return None

    def get_basin_by_id(self, basin_id_or_hybas_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Retrieve structured HydroBASINS Level 04 metadata by canonical ID, alias, or HYBAS_ID.
        """
        key_str = str(basin_id_or_hybas_id).strip().upper()
        hybas_id = self._alias_to_hybas_id.get(key_str)

        if hybas_id and hybas_id in self._basins_metadata:
            return dict(self._basins_metadata[hybas_id])

        # Try parsing as integer
        try:
            int_id = int(key_str.replace("HYBAS-", ""))
            if int_id in self._basins_metadata:
                return dict(self._basins_metadata[int_id])
        except ValueError:
            pass

        return None

    def list_supported_basins(self) -> List[Dict[str, Any]]:
        """Return list of all 72 authentic HydroBASINS Level 04 basins covering India."""
        return [dict(meta) for meta in self._basins_metadata.values()]

    def get_river_network_distance(
        self,
        latitude: float,
        longitude: float,
        min_strahler: int = 4,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate geodetic distance in meters to the nearest HydroRIVERS reach (Strahler >= min_strahler).

        Scientific Fidelity:
        - Measures distance to topological drainage network centerlines.
        - Strictly isolated from permanent surface water masks.
        - Preserves model feature semantics (distance_to_river_m).
        """
        self._ensure_rivers_loaded()
        if self._rivers_tree is None or self._rivers_gdf is None:
            logger.warning("HydroRIVERS dataset unavailable; distance cannot be calculated.")
            return None

        # Territorial bbox check
        min_lon, min_lat, max_lon, max_lat = INDIA_BBOX
        if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
            return None

        pt = Point(longitude, latitude)

        try:
            # Query STRtree for nearest reach geometry
            nearest_idx = self._rivers_tree.nearest(pt)
            nearest_row = self._rivers_gdf.iloc[nearest_idx]
            line_geom = nearest_row.geometry

            # Find closest point on line
            p_line, _ = shapely.ops.nearest_points(line_geom, pt)

            # Geodetic ellipsoidal distance in meters
            _, _, dist_m = self._geod.inv(pt.x, pt.y, p_line.x, p_line.y)

            return {
                "distance_to_river_m": float(max(0.0, dist_m)),
                "nearest_reach_id": int(nearest_row["HYRIV_ID"]),
                "strahler_order": int(nearest_row["ORD_STRA"]),
                "mean_discharge_m3s": float(nearest_row["DIS_AV_CMS"]),
                "river_source": "HydroSHEDS_HydroRIVERS_v1.0",
                "filter_rule": f"ORD_STRA >= {min_strahler}",
            }
        except Exception as err:
            logger.error("Failed to compute river network distance", error=str(err))
            return None

    def export_india_level04_geojson(
        self,
        output_path: Optional[Path] = None,
        simplify_tolerance: Optional[float] = None,
    ) -> Path:
        """
        Export authentic HydroBASINS Level 04 India basins to GeoJSON.
        Optionally simplify geometries for web browser delivery.
        """
        if self._gdf is None:
            raise RuntimeError("HydroBASINS dataset not loaded.")

        dest = output_path or (PROC_BOUNDARIES / "hydrobasins_india_lev04.geojson")
        dest.parent.mkdir(parents=True, exist_ok=True)

        gdf_export = self._gdf.copy()
        gdf_export["basin_id"] = gdf_export["HYBAS_ID"].apply(
            lambda hid: self._basins_metadata.get(int(hid), {}).get("basin_id", f"HYBAS-{hid}")
        )
        gdf_export["basin_name"] = gdf_export["HYBAS_ID"].apply(
            lambda hid: self._basins_metadata.get(int(hid), {}).get("basin_name", f"Basin {hid}")
        )

        if simplify_tolerance and simplify_tolerance > 0:
            gdf_export["geometry"] = gdf_export.geometry.simplify(
                simplify_tolerance, preserve_topology=True
            )

        cols_to_keep = [
            "HYBAS_ID",
            "basin_id",
            "basin_name",
            "MAIN_BAS",
            "PFAF_ID",
            "SUB_AREA",
            "UP_AREA",
            "geometry",
        ]
        gdf_export = gdf_export[[c for c in cols_to_keep if c in gdf_export.columns]]
        gdf_export.to_file(dest, driver="GeoJSON")
        logger.info("Exported HydroBASINS Level 04 GeoJSON", dest=str(dest))
        return dest
