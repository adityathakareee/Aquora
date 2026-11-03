"""
AQUORA Phase 6C.2G: Evidence Acquisition and Outlet Validation Tests.

Verifies:
1. Source DEM immutability and provenance.
2. Completeness and provenance of the 5 authoritative evidence categories.
3. Candidate outlet evaluation and rejection of the road-deck cell (666, 107).
4. Full mathematical reproducibility of Phase 6C.2F scratch rasters and drainage areas.
5. Evidence-gap register structure, uncertainty bounds, and blocking classifications.
6. Governance invariants, non-forcing of benchmarks, and BLOCKED final decision.
"""

import hashlib
from pathlib import Path
import numpy as np
import pytest
import rasterio
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
SCRATCH_DIR = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "scratch"
SCRATCH_FILLED_PATH = SCRATCH_DIR / "elevation_30m_exploratory_filled.tif"
SCRATCH_FDIR_PATH = SCRATCH_DIR / "elevation_30m_exploratory_fdir.tif"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g_evidence_gap_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"

D8_NEIGHBORS = [
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1)
]


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_source_dem_immutability_and_provenance():
    """Verify raw DEM and working DEM hashes, dimensions, CRS, and transform remain unchanged."""
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()

    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256

    with rasterio.open(WORKING_DEM_PATH) as ds:
        assert ds.crs.to_string() == "EPSG:32643"
        assert ds.width == 536
        assert ds.height == 746
        assert ds.res == (30.0, 30.0)
        assert ds.nodata == -9999.0
        assert ds.bounds.left == 269460.0
        assert ds.bounds.bottom == 2104260.0


def test_authoritative_evidence_catalog_and_provenance():
    """Verify all 5 evidence categories are documented with traceable provenance and limitations."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    catalog = manifest["authoritative_evidence_catalog"]
    expected_categories = [
        "category_1_channel_and_outlet_geometry",
        "category_2_csmia_airport_culvert",
        "category_3_railway_and_highway_crossings",
        "category_4_chitale_catchment_benchmark",
        "category_5_vertical_datum_reduction",
    ]
    for cat in expected_categories:
        assert cat in catalog, f"Missing category: {cat}"
        item = catalog[cat]
        assert "title" in item and len(item["title"]) > 0
        assert "publisher" in item and len(item["publisher"]) > 0
        assert "date" in item and len(item["date"]) > 0
        assert "identifier_or_url" in item and len(item["identifier_or_url"]) > 0
        assert "extracted_statement" in item and len(item["extracted_statement"]) > 0
        assert "geographic_coverage" in item and len(item["geographic_coverage"]) > 0
        assert "vertical_datum" in item and len(item["vertical_datum"]) > 0
        assert "verification_status" in item and len(item["verification_status"]) > 0
        assert "spatial_limitations" in item and len(item["spatial_limitations"]) > 0

    # Specific checks
    # Category 2: CSMIA culvert
    assert "Chitale" in catalog["category_2_csmia_airport_culvert"]["title"]
    assert "NOT AVAILABLE" in catalog["category_2_csmia_airport_culvert"]["verification_status"]

    # Category 4: Chitale benchmark
    assert "72.95" in catalog["category_4_chitale_catchment_benchmark"]["extracted_statement"]
    assert "NOT AVAILABLE" in catalog["category_4_chitale_catchment_benchmark"]["verification_status"]

    # Category 5: Datum formula
    assert "2.51" in catalog["category_5_vertical_datum_reduction"]["extracted_statement"]
    assert "VERIFIED PRIMARY SOURCE" in catalog["category_5_vertical_datum_reduction"]["verification_status"]


def test_candidate_outlets_audit_and_rejection_of_road_deck():
    """Verify candidate outlet evaluations and rejection of road deck cell (666, 107)."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    outlets = manifest["candidate_outlets_audit"]["candidates"]
    assert len(outlets) == 6

    by_id = {c["id"]: c for c in outlets}

    # Proposed road deck cell
    road_deck = by_id["A_ORIGINAL_PROPOSED"]
    assert road_deck["mapped_pixel"] == [666, 107]
    assert road_deck["elevation_msl_m"] > 8.0
    assert road_deck["is_elevated_infrastructure"] is True
    assert "REJECTED_INFRASTRUCTURE" in road_deck["hydrological_verdict"]

    # Creek channel cell
    creek = by_id["B_CREEK_CHANNEL_BRIDGE"]
    assert creek["mapped_pixel"] == [655, 100]
    assert creek["elevation_msl_m"] < 1.0
    assert creek["is_active_water_cell"] is True
    assert "CANDIDATE_CHANNEL" in creek["hydrological_verdict"]

    # Mahim Bay cell
    bay = by_id["C_MAHIM_BAY_MOUTH"]
    assert bay["mapped_pixel"] == [635, 84]
    assert bay["elevation_msl_m"] == 0.0
    assert bay["is_active_water_cell"] is True
    assert "CANDIDATE_BAY_MOUTH" in bay["hydrological_verdict"]


def test_conditioning_reproducibility_from_scratch_rasters():
    """Directly recompute drainage areas from scratch flow direction raster and verify match."""
    assert SCRATCH_FDIR_PATH.exists()
    assert SCRATCH_FILLED_PATH.exists()

    with rasterio.open(SCRATCH_FDIR_PATH) as ds:
        fdir = ds.read(1)

    def trace_upstream(pour_r: int, pour_c: int) -> int:
        rows, cols = fdir.shape
        visited = np.zeros((rows, cols), dtype=bool)
        stack = [(pour_r, pour_c)]
        visited[pour_r, pour_c] = True
        while stack:
            cr, cc = stack.pop()
            for idx, (dr, dc) in enumerate(D8_NEIGHBORS):
                nr, nc = cr - dr, cc - dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if not visited[nr, nc] and fdir[nr, nc] == idx:
                        visited[nr, nc] = True
                        stack.append((nr, nc))
        return int(np.sum(visited))

    # Exact reproduction of Phase 6C.2F numbers
    cells_bay = trace_upstream(635, 84)
    cells_causeway = trace_upstream(666, 107)

    assert cells_bay == 83739, f"Expected 83739 cells, got {cells_bay}"
    assert cells_causeway == 372, f"Expected 372 cells, got {cells_causeway}"

    area_bay = cells_bay * 0.0009
    assert abs(area_bay - 75.3651) < 1e-4

    # Check manifest record of reproducibility
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    repro = manifest["conditioning_reproducibility_review"]
    assert repro["reproduced_metrics"]["exact_match_with_phase6c2f_manifest"] is True
    assert repro["monotonicity_evaluation"]["flow_path_monotonic"] is True
    # Powai lake artifact: +3.76m
    assert abs(repro["lake_preservation_audit"]["powai_unphysical_delta_m"] - 3.76) < 0.1


def test_evidence_gap_register_structure_and_blocking_counts():
    """Verify evidence-gap register entries, uncertainty fields, and blocking statuses."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    register = manifest["evidence_gap_register"]
    assert register["total_gaps_identified"] == 5
    assert register["blocking_delineation_gaps"] == 3
    assert register["blocking_outlet_gaps"] == 1

    gap_ids = [g["gap_id"] for g in register["gaps"]]
    assert "GAP-01-OUTLET-GEOMETRY" in gap_ids
    assert "GAP-02-CSMIA-CULVERT" in gap_ids
    assert "GAP-03-RAILWAY-BRIDGES" in gap_ids
    assert "GAP-04-WATERSHED-BOUNDARY-GIS" in gap_ids
    assert "GAP-05-VERTICAL-DATUM-TIE" in gap_ids

    for g in register["gaps"]:
        assert "uncertainty_horizontal_m" in g
        assert "uncertainty_vertical_m" in g
        assert "concrete_next_action" in g
        assert len(g["concrete_next_action"]) > 10


def test_manifest_governance_and_final_decision():
    """Verify governance invariants and authoritative BLOCKED final decision."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["status"] == "EVIDENCE_GAP_AUDIT_COMPLETED"
    assert gov["final_decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert gov["historical_simulation_permitted"] is False
    assert gov["zero_culvert_fabrication_enforced"] is True
    assert gov["synthetic_box_retired"] is True
    assert gov["working_dem_immutable"] is True

    decision = manifest["decision_rationale"]["chosen_decision"]
    assert decision == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert len(manifest["decision_rationale"]["unblocking_requirements"]) >= 3
