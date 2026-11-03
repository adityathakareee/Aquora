"""
AQUORA Phase 6C.2F: Hydrological Conditioning Design and Controlled Delineation Readiness Tests.

Verifies:
1. Working DEM and Raw DEM immutability, provenance, CRS, dimensions, and transform.
2. Proposed outlet pixel mapping, elevation, and road-deck obstacle detection at Mahim Causeway.
3. CSMIA airport barrier detection, culvert evidence audit, and strict refusal to guess/burn trenches.
4. Conditioning comparison metrics (unconditioned vs priority-flood vs lake-preserved).
5. D8 flow direction validity, flat routing, accumulation, and non-forced exploratory area observation.
6. Detection of unresolved sinks, flow disconnection, and urban pooling artifacts.
7. Manifest completeness, governance invariants, and EXPLORATORY ONLY acceptance decision.
"""

import hashlib
from pathlib import Path
import numpy as np
import pyproj
import pytest
import rasterio
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2f_delineation_manifest.yaml"
SCRATCH_DIR = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "scratch"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_working_dem_immutability_and_provenance():
    """Verify raw DEM and working DEM are present, untouched, and match exact SHA-256."""
    assert RAW_DEM_PATH.exists(), f"Raw DEM missing: {RAW_DEM_PATH}"
    assert WORKING_DEM_PATH.exists(), f"Working DEM missing: {WORKING_DEM_PATH}"

    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256, "Raw DEM checksum modified!"
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256, "Working DEM modified!"

    with rasterio.open(WORKING_DEM_PATH) as ds:
        assert ds.crs.to_string() == "EPSG:32643"
        assert ds.width == 536
        assert ds.height == 746
        assert ds.res == (30.0, 30.0)
        assert ds.nodata == -9999.0
        assert ds.bounds.left == 269460.0
        assert ds.bounds.right == 285540.0
        assert ds.bounds.bottom == 2104260.0
        assert ds.bounds.top == 2126640.0


def test_proposed_outlet_mapping_and_road_deck_detection():
    """Verify coordinate-to-pixel mapping for Mahim Causeway and detect elevated road deck."""
    with rasterio.open(WORKING_DEM_PATH) as ds:
        dem = ds.read(1)
        transformer = pyproj.Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
        x_proj, y_proj = transformer.transform(72.840, 19.040)
        row, col = ds.index(x_proj, y_proj)

        assert row == 666, f"Expected row 666, got {row}"
        assert col == 107, f"Expected col 107, got {col}"

        elev_causeway = float(dem[row, col])
        # The Mahim Causeway road deck sits at ~9.95m MSL
        assert elev_causeway > 8.0, f"Expected elevated causeway > 8m, got {elev_causeway}m"
        assert abs(elev_causeway - 9.95) < 0.1, f"Expected ~9.95m, got {elev_causeway}m"

        # Check true water channel cell in Mahim Creek (Row 655, Col 100)
        elev_creek = float(dem[655, 100])
        assert elev_creek < 1.0, f"Expected creek bed/water < 1m MSL, got {elev_creek}m"

        # Check Mahim Bay receiving water (Row 635, Col 84)
        elev_bay = float(dem[635, 84])
        assert elev_bay == 0.0, f"Expected sea level 0.0m MSL, got {elev_bay}m"


def test_csmia_airport_barrier_and_culvert_evidence_discipline():
    """Verify airport runway barrier in DSM and confirm zero guessed culverts."""
    with rasterio.open(WORKING_DEM_PATH) as ds:
        dem = ds.read(1)
        transformer = pyproj.Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
        x_csmia, y_csmia = transformer.transform(72.875, 19.090)
        csmia_r, csmia_c = ds.index(x_csmia, y_csmia)

        assert csmia_r == 483
        assert csmia_c == 232

        runway_elev = float(dem[csmia_r, csmia_c])
        marol_elev = float(dem[450, 246])

        # Runway is higher than upstream riverbed entry point at Marol
        assert runway_elev > marol_elev, (
            f"Expected runway ({runway_elev}m) to form an adverse barrier over Marol ({marol_elev}m)"
        )

    # Verify that manifest classifies culvert centerline as MISSING and enforces zero fabrication
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    culvert_info = manifest["hydraulic_structures_audit"]["csmia_culvert_audit"]
    assert "MISSING" in culvert_info["evidence_tiers"]["georeferenced_centerline_geometry"]
    assert "ZERO FABRICATION ENFORCED" in culvert_info["governance_action"]


def test_conditioning_methods_comparison_and_lake_preservation():
    """Verify conditioning metrics, sink detection, and lake preservation."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    cond = manifest["conditioning_evaluation"]

    # 1. Unconditioned
    assert cond["unconditioned_dem"]["true_sinks_detected"] == 12405
    assert abs(cond["unconditioned_dem"]["sink_percentage"] - 3.10) < 0.1
    assert "DISCONNECTED" in cond["unconditioned_dem"]["flow_connectivity"]
    assert cond["unconditioned_dem"]["delineated_catchment_causeway_km2"] < 0.01

    # 2. Global Priority-Flood
    assert cond["global_priority_flood_filling"]["affected_cell_count"] > 80000
    assert cond["global_priority_flood_filling"]["max_elevation_increase_m"] > 10.0
    # Powai lake artifact: raised by ~3.76m
    powai_delta = cond["global_priority_flood_filling"]["unphysical_pooling_artifacts"]["powai_lake"]["elevation_delta_m"]
    assert abs(powai_delta - 3.76) < 0.1

    # 3. Lake Preservation
    assert cond["lake_preservation_evaluation"]["vihar_lake_cells_protected"] > 3000
    assert cond["lake_preservation_evaluation"]["powai_lake_cells_protected"] > 400


def test_d8_flow_routing_and_non_forcing_governance():
    """Verify D8 exploratory catchment area is observed, not forced to Chitale benchmark."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    benchmark_comp = manifest["conditioning_evaluation"]["global_priority_flood_filling"]["reference_benchmark_comparison"]
    observed_area = benchmark_comp["observed_exploratory_area_km2"]
    chitale_area = benchmark_comp["chitale_committee_stated_area_km2"]

    # Observed area is ~75.37 km2, chitale is 72.95 km2
    assert chitale_area == 72.95
    assert abs(observed_area - 75.37) < 0.1
    # Verify non-forcing
    assert observed_area != chitale_area, "CRITICAL FLAW: Catchment was artificially forced to match reference!"
    assert "NOT A TARGET" in benchmark_comp["evaluation"]


def test_temporary_scratch_rasters_reproducibility():
    """Verify temporary rasters were generated in scratch directory and source remains untouched."""
    temp_filled = SCRATCH_DIR / "elevation_30m_exploratory_filled.tif"
    temp_fdir = SCRATCH_DIR / "elevation_30m_exploratory_fdir.tif"

    assert temp_filled.exists(), "Temporary filled raster missing"
    assert temp_fdir.exists(), "Temporary flow direction raster missing"

    with rasterio.open(temp_filled) as ds:
        assert ds.crs.to_string() == "EPSG:32643"
        assert ds.width == 536
        assert ds.height == 746

    with rasterio.open(temp_fdir) as ds:
        assert ds.crs.to_string() == "EPSG:32643"
        data = ds.read(1)
        # Directions must be -1 or 0..7
        unique_dirs = set(np.unique(data))
        valid_dirs = set(range(-1, 8))
        assert unique_dirs.issubset(valid_dirs), f"Invalid flow directions detected: {unique_dirs - valid_dirs}"


def test_manifest_phase6c2f_governance_and_acceptance_decision():
    """Verify manifest governance invariants, blocked status, and final EXPLORATORY ONLY decision."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["status"] == "DELINEATION_READINESS_AUDIT_COMPLETED"
    assert gov["readiness_decision"] == "EXPLORATORY_ONLY"
    assert gov["historical_simulation_permitted"] is False
    assert gov["zero_culvert_fabrication_enforced"] is True
    assert gov["synthetic_box_retired"] is True
    assert gov["working_dem_immutable"] is True

    # Check criteria status
    criteria = manifest["acceptance_criteria"]
    assert criteria["criterion_1_preflight_and_dem_immutability"]["status"] == "PASS"
    assert criteria["criterion_2_outlet_and_drainage_route_verification"]["status"] == "BLOCKED"
    assert criteria["criterion_3_culvert_evidence_discipline"]["status"] == "BLOCKED"
    assert criteria["criterion_4_conditioning_methods_evaluated"]["status"] == "PASS"
    assert criteria["criterion_5_controlled_d8_evaluation"]["status"] == "PASS"
    assert criteria["criterion_6_independent_evaluation"]["status"] == "PASS"
    assert criteria["criterion_7_tests_and_reproducibility"]["status"] == "PASS"

    # Check final decision
    decision = manifest["final_decision"]["decision"]
    assert decision == "EXPLORATORY_ONLY / BLOCKED FOR SIMULATION"
    assert len(manifest["final_decision"]["evidence_required_for_unblocking"]) == 4
