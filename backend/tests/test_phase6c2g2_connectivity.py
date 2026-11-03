"""
AQUORA Phase 6C.2G.2: Boundary and Catchment Connectivity Verification Tests.

Verifies:
1. Reclassification of fdir = -1 perimeter cells as unresolved boundary local minima
   (due to absence of modeled off-grid descent in the implementation).
2. Deterministic downstream trace from Causeway cell (666, 107) terminating at the southern
   boundary (Row 745, Col 53), failing to reach Mahim Bay mouth (635, 84).
3. Independent upstream trace from Mahim Bay mouth (635, 84) confirming that (666, 107)
   is NOT in its contributing set (intersection is strictly 0 cells).
4. Manifest discrepancy table classifications (REPRODUCED, CONTRADICTED).
5. Governance invariants: watershed status remains EXPLORATORY ONLY, and final decision
   remains BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE.
"""

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
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g2_connectivity_manifest.yaml"

D8_NEIGHBORS = [
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1)
]


def test_fdir_minus_one_termination_semantics_reclassified():
    """Verify fdir = -1 distribution and confirm reclassification to unresolved boundary local minima."""
    assert SCRATCH_FDIR_PATH.exists()
    assert MANIFEST_PATH.exists()

    with rasterio.open(SCRATCH_FDIR_PATH) as ds:
        fdir = ds.read(1)

    rows, cols = fdir.shape
    perimeter_mask = np.zeros_like(fdir, dtype=bool)
    perimeter_mask[0, :] = True
    perimeter_mask[-1, :] = True
    perimeter_mask[:, 0] = True
    perimeter_mask[:, -1] = True

    unrouted_total = int(np.sum(fdir == -1))
    perimeter_unrouted = int(np.sum((fdir == -1) & perimeter_mask))
    internal_unrouted = int(np.sum((fdir == -1) & (~perimeter_mask)))

    assert unrouted_total == 1070
    assert perimeter_unrouted == 1070
    assert internal_unrouted == 0

    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    reclass = manifest["termination_semantics_audit"]["semantic_reclassification"]
    assert "UNRESOLVED BOUNDARY LOCAL MINIMA" in reclass["corrected_phase6c2g2_verdict"]
    assert "No downhill in-bounds neighbor exists" in reclass["corrected_phase6c2g2_verdict"]


def test_causeway_downstream_trace_to_southern_boundary():
    """Trace downstream from Causeway (666, 107) and prove it terminates at (745, 53) without reaching (635, 84)."""
    with rasterio.open(SCRATCH_FDIR_PATH) as ds:
        fdir = ds.read(1)

    curr_r, curr_c = 666, 107
    path = [(curr_r, curr_c)]
    for step in range(500):
        d = fdir[curr_r, curr_c]
        if d == -1:
            break
        dr, dc = D8_NEIGHBORS[d]
        nr, nc = curr_r + dr, curr_c + dc
        if not (0 <= nr < fdir.shape[0] and 0 <= nc < fdir.shape[1]):
            break
        curr_r, curr_c = nr, nc
        path.append((curr_r, curr_c))
        if curr_r == 635 and curr_c == 84:
            break

    # Must NOT reach Mahim Bay mouth (635, 84)
    assert not (curr_r == 635 and curr_c == 84), "Unexpectedly reached Mahim Bay mouth!"
    # Must terminate at southern boundary (Row 745, Col 53)
    assert curr_r == 745, f"Expected terminal row 745, got {curr_r}"
    assert curr_c == 53, f"Expected terminal col 53, got {curr_c}"
    assert fdir[curr_r, curr_c] == -1


def test_causeway_not_in_bay_upstream_set():
    """Verify that Causeway cell (666, 107) is NOT in the upstream set of (635, 84) and intersection is 0."""
    with rasterio.open(SCRATCH_FDIR_PATH) as ds:
        fdir = ds.read(1)

    def trace_upstream(pr, pc):
        visited = np.zeros(fdir.shape, dtype=bool)
        stack = [(pr, pc)]
        visited[pr, pc] = True
        while stack:
            cr, cc = stack.pop()
            for idx, (dr, dc) in enumerate(D8_NEIGHBORS):
                nr, nc = cr - dr, cc - dc
                if 0 <= nr < fdir.shape[0] and 0 <= nc < fdir.shape[1]:
                    if not visited[nr, nc] and fdir[nr, nc] == idx:
                        visited[nr, nc] = True
                        stack.append((nr, nc))
        return visited

    up_bay = trace_upstream(635, 84)
    up_causeway = trace_upstream(666, 107)

    # (666, 107) is not in up_bay
    assert up_bay[666, 107] is False or up_bay[666, 107] == 0
    # Bay catchment is 83,739 cells
    assert np.sum(up_bay) == 83739
    # Causeway catchment is 372 cells
    assert np.sum(up_causeway) == 372
    # The two catchments are strictly disjoint
    overlap = np.sum(up_bay & up_causeway)
    assert overlap == 0, f"Expected 0 overlapping cells, got {overlap}"


def test_discrepancy_table_classifications():
    """Verify discrepancy table has exactly REPRODUCED and CONTRADICTED findings."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    disc = manifest["discrepancy_table"]
    assert disc["total_findings"] == 5
    assert disc["reproduced_count"] == 3
    assert disc["contradicted_count"] == 2
    assert disc["unresolved_count"] == 0

    findings_by_id = {f["finding_id"]: f for f in disc["table"]}
    assert findings_by_id["FINDING-01-OUTLET-DRAINAGE-AREA"]["classification"] == "REPRODUCED"
    assert findings_by_id["FINDING-02-FDIR-TERMINATION-SEMANTICS"]["classification"] == "CONTRADICTED"
    assert findings_by_id["FINDING-03-CAUSEWAY-BAY-CONNECTIVITY"]["classification"] == "CONTRADICTED"
    assert findings_by_id["FINDING-04-EPSILON-GRADIENT-PATH"]["classification"] == "REPRODUCED"
    assert findings_by_id["FINDING-05-CUMULATIVE-REGRESSION-TESTS"]["classification"] == "REPRODUCED"


def test_governance_invariants_and_final_decision():
    """Verify watershed status is EXPLORATORY ONLY and decision is BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["status"] == "CONNECTIVITY_AUDIT_COMPLETED"
    assert gov["watershed_status"] == "EXPLORATORY_ONLY"
    assert gov["final_governance_decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert gov["historical_simulation_permitted"] is False
    assert gov["zero_culvert_fabrication_enforced"] is True
    assert gov["working_dem_immutable"] is True
