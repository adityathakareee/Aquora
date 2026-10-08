"""
AQUORA 2.0 — Phase 2B India Geographic + Terrain Foundation Test Suite.

Automated verification of:
1. Administrative hierarchy (India, 36 States/UTs, key districts)
2. HydroBASINS basin hierarchy (8 major Indian river basins)
3. Copernicus DEM GLO-30 elevation ranges and nodata
4. Terrain slope units (degrees [0, 90]) and derivation method
5. HydroRIVERS channel vectors, Strahler order, and metric distance-to-river (>= 0m)
6. ESA WorldCover categorical mapping and built_up_fraction [0, 1]
7. 5-basin smoke tests (Ganga, Brahmaputra, Godavari, Narmada, Mithi)
8. Multi-tier data contract instantiation (NationalDataContract & RegionalDataContract)
9. Zero-fabrication and non-fallback guarantees
10. SpatialZoneResolver regional zone capability gating
"""

import json
from pathlib import Path
import numpy as np
import pytest
import yaml

from app.schemas.intelligence_contracts import (
    NationalDataContract,
    RegionalDataContract,
)
from app.services.india_spatial_service import IndiaSpatialService, VERIFIED_DOMAINS
from app.services.spatial_resolver import SpatialZoneResolver, UnsupportedZoneError

# Resolve Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROC_BOUNDARIES = DATA_DIR / "processed" / "boundaries"
PROC_DEM = DATA_DIR / "processed" / "dem"
PROC_TERRAIN = DATA_DIR / "processed" / "terrain"
PROC_HYDRO = DATA_DIR / "processed" / "hydrography"
PROC_LANDCOVER = DATA_DIR / "processed" / "landcover"
MANIFESTS_DIR = DATA_DIR / "manifests"


# ==============================================================================
# 1. ADMINISTRATIVE HIERARCHY TESTS
# ==============================================================================

def test_administrative_hierarchy_completeness():
    """Verify India, 36 States/UTs, and key districts in administrative hierarchy."""
    admin_path = PROC_BOUNDARIES / "india_administrative_hierarchy.json"
    assert admin_path.exists(), "Administrative hierarchy JSON must exist."

    with open(admin_path, "r", encoding="utf-8") as f:
        admin = json.load(f)

    # 1. Country validation
    country = admin["country"]
    assert country["entity_code"] == "IN"
    assert country["name"] == "India"
    assert country["entity_type"] == "COUNTRY"
    assert country["parent_id"] is None
    assert country["bounds"]["min_lon"] < country["bounds"]["max_lon"]
    assert country["bounds"]["min_lat"] < country["bounds"]["max_lat"]

    # 2. States / UTs validation
    states = admin["states"]
    assert len(states) == 36, f"Expected 36 States and UTs, found {len(states)}"
    state_codes = {s["entity_code"] for s in states}
    assert "IN-MH" in state_codes
    assert "IN-AS" in state_codes
    assert "IN-BR" in state_codes
    assert "IN-GJ" in state_codes
    assert "IN-DL" in state_codes

    for s in states:
        assert s["parent_code"] == "IN"
        assert s["entity_type"] == "STATE"
        assert "latitude" in s["centroid"]
        assert "longitude" in s["centroid"]

    # 3. Key Districts validation
    districts = admin["districts"]
    assert len(districts) >= 8
    dist_codes = {d["entity_code"] for d in districts}
    assert "DIST-BR-PAT" in dist_codes
    assert "DIST-AS-KAM" in dist_codes
    assert "DIST-MH-NAS" in dist_codes
    assert "DIST-GJ-BHA" in dist_codes
    assert "DIST-MH-MUM-SUB" in dist_codes

    # Verify parent links
    patna = next(d for d in districts if d["entity_code"] == "DIST-BR-PAT")
    assert patna["parent_code"] == "IN-BR"
    assert patna["basin_code"] == "BASIN-GANGA"


# ==============================================================================
# 2. HYDROBASINS HIERARCHY TESTS
# ==============================================================================

def test_hydrobasins_hierarchy_integrity():
    """Verify 8 major Indian river basins in HydroBASINS hierarchy."""
    basins_path = PROC_BOUNDARIES / "hydrobasins_india.json"
    assert basins_path.exists(), "HydroBASINS hierarchy JSON must exist."

    with open(basins_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    basins = data["basins"]
    assert len(basins) == 8, f"Expected 8 basins, found {len(basins)}"

    basin_ids = {b["basin_id"] for b in basins}
    assert "BASIN-GANGA" in basin_ids
    assert "BASIN-BRAHMAPUTRA" in basin_ids
    assert "BASIN-GODAVARI" in basin_ids
    assert "BASIN-KRISHNA" in basin_ids
    assert "BASIN-NARMADA" in basin_ids
    assert "BASIN-TAPI" in basin_ids
    assert "BASIN-MAHANADI" in basin_ids
    assert "BASIN-MITHI" in basin_ids

    ganga = next(b for b in basins if b["basin_id"] == "BASIN-GANGA")
    assert ganga["drainage_area_km2"] > 800000.0
    assert ganga["pfafstetter_level"] == 4
    assert "IN-BR" in ganga["major_states"]
    assert "IN-UP" in ganga["major_states"]


# ==============================================================================
# 3. TERRAIN & SLOPE DERIVATION TESTS
# ==============================================================================

@pytest.mark.parametrize("domain_id,min_elev,max_elev", [
    ("ganga_patna", 40.0, 75.0),
    ("brahmaputra_guwahati", 45.0, 160.0),
    ("godavari_nashik", 540.0, 680.0),
    ("narmada_bharuch", 10.0, 50.0),
])
def test_dem_elevation_and_slope_ranges(domain_id, min_elev, max_elev):
    """Verify DEM elevation and slope derivation across regional domains."""
    elev_file = PROC_DEM / f"{domain_id}_elevation_30m.tif"
    slope_file = PROC_TERRAIN / f"{domain_id}_slope_30m.tif"

    assert elev_file.exists(), f"Elevation file missing for {domain_id}"
    assert slope_file.exists(), f"Slope file missing for {domain_id}"

    import rasterio
    with rasterio.open(elev_file) as src:
        elev_arr = src.read(1)
        assert src.crs.to_string() == "EPSG:4326"
        assert src.nodata == -9999.0
        valid_elev = elev_arr[elev_arr != src.nodata]
        assert np.all(valid_elev >= min_elev), f"Elevation below {min_elev}m in {domain_id}"
        assert np.all(valid_elev <= max_elev), f"Elevation above {max_elev}m in {domain_id}"

    with rasterio.open(slope_file) as src:
        slope_arr = src.read(1)
        valid_slope = slope_arr[slope_arr != src.nodata]
        # Slope in degrees must strictly be [0, 90]
        assert np.all(valid_slope >= 0.0), f"Negative slope in {domain_id}"
        assert np.all(valid_slope <= 90.0), f"Slope > 90 deg in {domain_id}"


# ==============================================================================
# 4. HYDRORIVERS & METRIC DISTANCE TO RIVER TESTS
# ==============================================================================

@pytest.mark.parametrize("domain_id,expected_strahler", [
    ("ganga_patna", 8),
    ("brahmaputra_guwahati", 8),
    ("godavari_nashik", 6),
    ("narmada_bharuch", 7),
])
def test_hydrorivers_attributes_and_metric_distance(domain_id, expected_strahler):
    """Verify HydroRIVERS channel vectors and non-negative metric distance grids."""
    river_file = PROC_HYDRO / f"hydrorivers_{domain_id}.geojson"
    dist_file = PROC_TERRAIN / f"{domain_id}_distance_to_river_30m.tif"

    assert river_file.exists(), f"River vector missing for {domain_id}"
    assert dist_file.exists(), f"Distance raster missing for {domain_id}"

    # Verify vector attributes
    with open(river_file, "r", encoding="utf-8") as f:
        river_data = json.load(f)
    feat = river_data["features"][0]
    props = feat["properties"]
    assert props["strahler_order"] == expected_strahler
    assert props["upstream_drainage_area_km2"] > 0.0

    # Verify distance raster
    import rasterio
    with rasterio.open(dist_file) as src:
        dist_arr = src.read(1)
        assert np.all(dist_arr >= 0.0), "distance_to_river_m must be non-negative"
        # Minimum distance near the channel should be close to 0m (< 100m)
        assert np.min(dist_arr) < 100.0, "Minimum river distance should approach zero near channel"
        # Maximum distance in a 20 km domain should be > 2000m
        assert np.max(dist_arr) > 2000.0, "Maximum river distance should be significant away from channel"


# ==============================================================================
# 5. ESA WORLDCOVER LAND COVER & BUILT-UP FRACTION TESTS
# ==============================================================================

@pytest.mark.parametrize("domain_id", [
    "ganga_patna", "brahmaputra_guwahati", "godavari_nashik", "narmada_bharuch"
])
def test_worldcover_landcover_and_builtup_fraction(domain_id):
    """Verify 30m aggregated land cover class and built_up_fraction [0, 1]."""
    lc_file = PROC_LANDCOVER / f"{domain_id}_landcover_30m.tif"
    bu_file = PROC_LANDCOVER / f"{domain_id}_built_up_fraction_30m.tif"

    assert lc_file.exists()
    assert bu_file.exists()

    import rasterio
    with rasterio.open(lc_file) as src:
        lc_arr = src.read(1)
        unique_classes = set(np.unique(lc_arr))
        # Valid classes: 10 (Tree), 40 (Cropland), 50 (Built-up), 80 (Water)
        assert unique_classes.issubset({10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100, -1})

    with rasterio.open(bu_file) as src:
        bu_arr = src.read(1)
        assert np.all(bu_arr >= 0.0), "built_up_fraction must be >= 0.0"
        assert np.all(bu_arr <= 1.0), "built_up_fraction must be <= 1.0"


# ==============================================================================
# 6. FIVE-BASIN SMOKE TESTS (IndiaSpatialService)
# ==============================================================================

@pytest.mark.parametrize("basin_name,lat,lon,expected_domain", [
    ("Ganga", 25.62, 85.12, "ganga_patna"),
    ("Brahmaputra", 26.18, 91.73, "brahmaputra_guwahati"),
    ("Godavari", 19.98, 73.78, "godavari_nashik"),
    ("Narmada", 21.72, 73.00, "narmada_bharuch"),
    ("Mithi", 19.076, 72.877, "mumbai_mithi"),
])
def test_five_basin_spatial_service_smoke(basin_name, lat, lon, expected_domain):
    """Smoke test 30m terrain extraction across 5 major Indian river basins."""
    features = IndiaSpatialService.get_terrain_features(lat, lon)
    assert features is not None, f"Terrain lookup failed for {basin_name} at ({lat}, {lon})"
    assert features["domain_id"] == expected_domain
    assert features["elevation_m"] is not None
    assert 0.0 <= features["slope_deg"] <= 90.0
    assert features["distance_to_river_m"] >= 0.0
    assert features["landcover_class"] > 0
    assert 0.0 <= features["built_up_fraction"] <= 1.0


# ==============================================================================
# 7. DATA CONTRACT INSTANTIATION FROM REAL TERRAIN
# ==============================================================================

def test_national_data_contract_instantiation():
    """Verify NationalDataContract creation from real physical terrain."""
    contract = IndiaSpatialService.build_national_data_contract(
        latitude=25.62,
        longitude=85.12,
        rainfall_1h_mm=10.0,
        rainfall_24h_mm=80.0,
    )
    assert isinstance(contract, NationalDataContract)
    assert contract.latitude == 25.62
    assert contract.longitude == 85.12
    assert contract.elevation_m > 40.0
    assert contract.slope_deg >= 0.0
    assert contract.distance_to_river_m >= 0.0
    assert contract.rainfall_24h_mm == 80.0


def test_regional_data_contract_instantiation():
    """Verify RegionalDataContract creation extending national contract with basin info."""
    contract = IndiaSpatialService.build_regional_data_contract(
        latitude=25.62,
        longitude=85.12,
        rainfall_24h_mm=80.0,
    )
    assert isinstance(contract, RegionalDataContract)
    assert contract.basin_id == "BASIN-GANGA"
    assert contract.basin_name == "Ganga River Basin"
    assert contract.basin_drainage_area_km2 > 800000.0


# ==============================================================================
# 8. ZERO-FABRICATION AND NON-FALLBACK GUARANTEES
# ==============================================================================

def test_zero_fabrication_outside_coverage():
    """Verify points outside verified domains return None (Zero Fabrication)."""
    # Point in the Arabian Sea
    sea_features = IndiaSpatialService.get_terrain_features(15.0, 65.0)
    assert sea_features is None, "Ocean point must not return fabricated terrain"

    # Point in Rajasthan desert (outside the 5 target domains)
    desert_features = IndiaSpatialService.get_terrain_features(27.0, 71.5)
    assert desert_features is None, "Unverified point must return None, not synthetic fallback"

    # Building contract for unverified point returns None
    contract = IndiaSpatialService.build_national_data_contract(15.0, 65.0)
    assert contract is None


# ==============================================================================
# 9. SPATIAL RESOLVER REGIONAL ZONES & CAPABILITY GATING
# ==============================================================================

@pytest.mark.parametrize("zone_alias,expected_zone_id", [
    ("ganga", "regional_ganga_basin"),
    ("brahmaputra", "regional_brahmaputra_basin"),
    ("godavari", "regional_godavari_basin"),
    ("narmada", "regional_narmada_basin"),
    ("mumbai", "deep_mumbai_mithi"),
])
def test_spatial_resolver_regional_zones(zone_alias, expected_zone_id):
    """Verify SpatialZoneResolver normalizes and resolves regional basin zones."""
    zone = SpatialZoneResolver.resolve_zone(zone_alias)
    assert zone["zone_id"] == expected_zone_id

    # Regional zones have high_resolution_dem
    if expected_zone_id != "deep_mumbai_mithi":
        assert zone["capabilities"]["high_resolution_dem"] is True
        # But they do NOT support deep physical flood solver
        with pytest.raises(UnsupportedZoneError):
            SpatialZoneResolver.validate_capability(zone_alias, "physical_flood_solver")


# ==============================================================================
# 10. MANIFEST & PROVENANCE VALIDATION
# ==============================================================================

def test_manifest_provenance_validation():
    """Verify Phase 2B dataset manifest has complete metadata entries."""
    manifest_file = MANIFESTS_DIR / "phase2b_dataset_manifest.yaml"
    assert manifest_file.exists()

    with open(manifest_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    datasets = data["datasets"]
    assert len(datasets) >= 7

    dataset_ids = {d["dataset_id"] for d in datasets}
    assert "P2B-ADMIN-001" in dataset_ids
    assert "P2B-BASIN-001" in dataset_ids
    assert "P2B-DEM-001" in dataset_ids
    assert "P2B-SLOPE-001" in dataset_ids
    assert "P2B-HYDRO-001" in dataset_ids
    assert "P2B-DIST-001" in dataset_ids
    assert "P2B-LC-001" in dataset_ids

    for d in datasets:
        assert d["license"] is not None
        assert d["provider"] is not None
        assert d["crs"] == "EPSG:4326"
