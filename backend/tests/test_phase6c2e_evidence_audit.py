"""
AQUORA Phase 6C.2E Automated Test Suite: Mithi Catchment & Drainage Evidence Audit.

Validates:
1. Complete, unclipped coverage of the densified geographic study window in the working DEM.
2. Raw and working DEM byte-level immutability.
3. Classification of candidate catchment boundary sources (including detection of synthetic rectangle flaw).
4. Evidence status of critical hydraulic connections (runway culvert, railway embankments, lake spillways).
5. Tidal evidence inventory (absence of local continuous series, datum reduction requirements).
6. Manifest schema, governance status, and non-execution of historical simulations.
"""

from pathlib import Path
import pytest
import yaml

from scripts.audit_phase6c2e_evidence import (
    EXPECTED_RAW_DEM_SHA256,
    EXPECTED_WORKING_DEM_SHA256,
    HYDROBASINS_PATH,
    MANIFEST_PATH,
    PROJECT_ROOT,
    RAW_DEM_PATH,
    RAW_TIDE_DIR,
    WORKING_DEM_PATH,
    audit_candidate_catchment_sources,
    audit_dem_geographic_extent,
    audit_hydraulic_connectivity_evidence,
    audit_tide_and_datum_inventory,
    compute_sha256,
)


def test_working_dem_and_source_immutability():
    """Verify raw Copernicus DEM and working derived DEM are 100% byte-for-byte unchanged."""
    assert RAW_DEM_PATH.exists()
    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256

    assert WORKING_DEM_PATH.exists()
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256


def test_densified_study_extent_coverage():
    """Verify all 400 densified boundary points fall strictly inside working DEM without clipping."""
    report = audit_dem_geographic_extent(WORKING_DEM_PATH)
    assert report["dem_exists"] is True
    assert report["valid_data_percentage"] == 100.0

    b_test = report["densified_boundary_test"]
    assert b_test["zero_clipping_confirmed"] is True
    assert b_test["points_inside_bounds"] == 400
    assert b_test["total_points_evaluated"] == 400

    # Margins must be strictly positive
    assert b_test["grid_left_margin_m"] > 0.0
    assert b_test["grid_right_margin_m"] > 0.0
    assert b_test["grid_bottom_margin_m"] > 0.0
    assert b_test["grid_top_margin_m"] > 0.0


def test_catchment_boundary_evidence_classification():
    """Verify candidate catchment sources and detect the synthetic rectangle flaw in hydrobasins_india.geojson."""
    sources = audit_candidate_catchment_sources()

    # Chitale Committee tabular benchmark
    assert sources["CHITALE_COMMITTEE_REPORT_2006"]["readiness_status"] == "AUTHORITATIVE_TABULAR_BENCHMARK"
    assert sources["CHITALE_COMMITTEE_REPORT_2006"]["stated_area_km2"] == 72.95

    # Flawed local repository geometry
    local_box = sources["EXISTING_REPOSITORY_HYDROBASINS_MITHI"]
    assert local_box["readiness_status"] == "RETIRED_SYNTHETIC_RECTANGLE"
    assert local_box["actual_measured_polygon_area_km2"] > 160.0
    assert local_box["stated_area_in_properties"] == 72.95
    # Confirms contradiction between stated property area and measured polygon geometry
    assert abs(local_box["actual_measured_polygon_area_km2"] - local_box["stated_area_in_properties"]) > 90.0


def test_hydraulic_connectivity_audit():
    """Verify evidence status for runway culvert, railway crossings, and lake spillways."""
    evidence = audit_hydraulic_connectivity_evidence()

    # CSMIA culvert
    culvert = evidence["csmia_runway_culvert"]
    assert "DOCUMENTED" in culvert["classification"]
    assert culvert["digital_cad_vector_available"] is False

    # Channel centerline
    channel = evidence["channel_centerline"]
    assert channel["classification"] == "PARTIALLY_VERIFIED"
    assert channel["surveyed_cross_sections_available"] is False

    # Outfall
    outfall = evidence["downstream_river_outlet"]
    assert "VERIFIED" in outfall["classification"]
    assert outfall["dynamic_marine_boundary_available"] is False


def test_tide_inventory_and_datum_reduction_risk():
    """Verify that local tide directory lacks continuous series and documents geodetic reduction risk."""
    tide_audit = audit_tide_and_datum_inventory()
    assert tide_audit["local_tide_files_present"] is False
    assert tide_audit["raw_tide_files_count"] == 0
    assert tide_audit["readiness_status"].startswith("BLOCKED")
    assert "2.51" in tide_audit["vertical_datum_reduction"]["datum_offset_formula"]


def test_manifest_phase6c2e_integrity():
    """Verify Phase 6C.2E manifest exists, is valid YAML, and enforces governance safeguards."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    assert m["phase"] == "PHASE_6C_2E_EVIDENCE_AUDIT"
    assert m["governance"]["status"] == "GEOGRAPHIC_EVIDENCE_AUDIT_COMPLETED"
    assert m["governance"]["zero_fabrication_enforced"] is True
    assert m["governance"]["historical_simulation_permitted"] is False
    assert m["readiness_summary"]["catchment_polygon_ready"] is False
    assert m["readiness_summary"]["culvert_enforcement_ready"] is False
    assert m["readiness_summary"]["working_dem_ready"] is True
