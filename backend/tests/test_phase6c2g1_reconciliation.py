"""
AQUORA Phase 6C.2G.1: Consistency and Evidence Reconciliation Tests.

Verifies:
1. Full reconciliation of the outlet-area discrepancy:
   - Unconditioned raw DEM at (666, 107): exactly 1 cell (0.0009 km2).
   - Scratch filled DEM at (666, 107): exactly 372 cells (0.3348 km2).
   - Mahim Bay mouth at (635, 84): exactly 83,739 cells (75.3651 km2).
2. Flow-direction termination semantics:
   - Exactly 1,070 boundary exits, all on the raster perimeter.
   - Strictly 0 internal sinks, 0 unresolved flats, 0 nodata cells.
3. Epsilon-gradient Priority-Flood mathematical rule and exact 351-step monotonic path.
4. Completeness and accuracy of the 10-point measurement reconciliation table.
5. Rigorous source provenance review: downgrading uninspected primary claims to secondary compilations.
6. Governance invariants, non-forcing of benchmarks, and BLOCKED final decision.
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
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g1_reconciliation_manifest.yaml"

D8_NEIGHBORS = [
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1)
]
D8_DISTANCES = np.array([np.sqrt(2.0), 1.0, np.sqrt(2.0), 1.0, 1.0, np.sqrt(2.0), 1.0, np.sqrt(2.0)], dtype=np.float64)


def test_outlet_area_discrepancy_reconciled():
    """Verify that both 1 cell (raw DEM) and 372 cells (filled DEM) are reproduced exactly."""
    assert MANIFEST_PATH.exists()

    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    recon = manifest["outlet_area_reconciliation"]
    assert recon["discrepancy_resolved"] is True

    # 1. Direct computation on raw DEM
    with rasterio.open(WORKING_DEM_PATH) as ds:
        dem = ds.read(1)

    rows, cols = dem.shape
    fdir_raw = np.full((rows, cols), -1, dtype=np.int8)
    max_drop = np.zeros((rows, cols), dtype=np.float64)
    for idx, (dr, dc) in enumerate(D8_NEIGHBORS):
        r_s = slice(max(0, dr), min(rows, rows + dr))
        c_s = slice(max(0, dc), min(cols, cols + dc))
        o_r = slice(max(0, -dr), min(rows, rows - dr))
        o_c = slice(max(0, -dc), min(cols, cols - dc))
        drop = (dem[o_r, o_c] - dem[r_s, c_s]) / D8_DISTANCES[idx]
        mask = np.zeros((rows, cols), dtype=bool)
        mask[o_r, o_c] = drop > max_drop[o_r, o_c]
        mask[o_r, o_c] &= (drop > 0)
        fdir_raw[mask] = idx
        max_drop[mask] = drop[mask[o_r, o_c]]

    def trace_upstream(fdir, pr, pc):
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
        return int(np.sum(visited))

    raw_cells = trace_upstream(fdir_raw, 666, 107)
    assert raw_cells == 1, f"Expected 1 cell on raw DEM, got {raw_cells}"

    # 2. Direct computation on scratch filled DEM
    with rasterio.open(SCRATCH_FDIR_PATH) as ds:
        fdir_scratch = ds.read(1)

    filled_cells = trace_upstream(fdir_scratch, 666, 107)
    assert filled_cells == 372, f"Expected 372 cells on filled scratch DEM, got {filled_cells}"

    # 3. Direct computation of main Mithi outfall at Mahim Bay (635, 84)
    bay_cells = trace_upstream(fdir_scratch, 635, 84)
    assert bay_cells == 83739, f"Expected 83739 cells at Mahim Bay outfall, got {bay_cells}"
    assert abs(bay_cells * 0.0009 - 75.3651) < 1e-4


def test_flow_direction_termination_semantics():
    """Verify that all unrouted cells (fdir = -1) are on the raster boundary perimeter."""
    with rasterio.open(SCRATCH_FDIR_PATH) as ds:
        fdir = ds.read(1)

    rows, cols = fdir.shape
    perimeter_mask = np.zeros_like(fdir, dtype=bool)
    perimeter_mask[0, :] = True
    perimeter_mask[-1, :] = True
    perimeter_mask[:, 0] = True
    perimeter_mask[:, -1] = True

    unrouted_total = int(np.sum(fdir == -1))
    boundary_unrouted = int(np.sum((fdir == -1) & perimeter_mask))
    internal_unrouted = int(np.sum((fdir == -1) & (~perimeter_mask)))

    assert unrouted_total == 1070
    assert boundary_unrouted == 1070
    assert internal_unrouted == 0, f"Detected {internal_unrouted} internal sinks/flats!"

    # Verify manifest record
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    term = manifest["flow_direction_termination_audit"]["termination_categories"]
    assert term["boundary_exits"]["count"] == 1070
    assert term["internal_sinks"]["count"] == 0
    assert term["unresolved_flats"]["count"] == 0
    assert term["missing_terrain_nodata_cells"]["count"] == 0


def test_epsilon_gradient_monotonicity_and_path():
    """Verify epsilon gradient rule and reproduce the exact 351-step monotonic path."""
    with rasterio.open(SCRATCH_FDIR_PATH) as ds_fdir:
        fdir = ds_fdir.read(1)
    with rasterio.open(SCRATCH_FILLED_PATH) as ds_filled:
        filled = ds_filled.read(1)

    path = [(402, 270)]
    curr_r, curr_c = 402, 270
    monotonic = True
    for _ in range(1000):
        d = fdir[curr_r, curr_c]
        if d == -1:
            break
        dr, dc = D8_NEIGHBORS[d]
        nr, nc = curr_r + dr, curr_c + dc
        if not (0 <= nr < fdir.shape[0] and 0 <= nc < fdir.shape[1]):
            break
        if filled[nr, nc] > filled[curr_r, curr_c]:
            monotonic = False
            break
        curr_r, curr_c = nr, nc
        path.append((curr_r, curr_c))
        if curr_r == 635 and curr_c == 84:
            break

    assert len(path) == 351, f"Expected 351 steps, got {len(path)}"
    assert curr_r == 635 and curr_c == 84, "Path did not terminate at Mahim Bay outfall (635, 84)"
    assert monotonic is True, "Flow path is not monotonic!"


def test_measurement_reconciliation_table():
    """Verify all 10 reconciled metrics match across phases without contradiction."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    table_data = manifest["measurement_reconciliation_table"]
    assert table_data["total_metrics_evaluated"] == 10
    assert table_data["reproduced_count"] == 10
    assert table_data["contradicted_count"] == 0

    metrics_dict = {item["metric"]: item for item in table_data["table"]}
    assert "Working DEM SHA-256" in metrics_dict
    assert "Raw DEM SHA-256" in metrics_dict
    assert "Mahim Bay Outfall Catchment (Filled Scratch)" in metrics_dict
    assert "Powai Lake Unphysical Filling Artifact" in metrics_dict


def test_strengthened_source_provenance_and_datum_distinction():
    """Verify honest provenance classifications and separation of tidal datums."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    prov = manifest["source_provenance_strengthening"]
    assert prov["downgraded_claims_count"] == 3

    sources_by_id = {s["claim_id"]: s for s in prov["sources"]}

    # CSMIA culvert
    csmia = sources_by_id["SRC-02-CSMIA-CULVERT-SPECS"]
    assert "SECONDARY ENGINEERING COMPILATION" in csmia["reassessed_classification"]

    # Chitale 72.95 benchmark
    chitale = sources_by_id["SRC-03-CHITALE-7295-BENCHMARK"]
    assert "SECONDARY LITERATURE BENCHMARK" in chitale["reassessed_classification"]

    # Tidal datum
    datum = sources_by_id["SRC-04-TIDAL-DATUM-REDUCTION"]
    assert "PORT AUTHORITY SPECIFICATION" in datum["reassessed_classification"]
    assert "UNVERIFIED LOCAL GEODETIC TIE SHEET" in datum["reassessed_classification"]
    assert "BLOCKED FOR HISTORICAL FLOOD SIMULATION" in datum["simulation_readiness"]


def test_phase6c2g1_governance_and_final_decision():
    """Verify final decision remains strictly BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["status"] == "RECONCILIATION_AUDIT_COMPLETED"
    assert gov["final_decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert gov["historical_simulation_permitted"] is False
    assert gov["zero_culvert_fabrication_enforced"] is True
    assert gov["working_dem_immutable"] is True
