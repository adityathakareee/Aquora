"""
AQUORA Phase 7F.3.6: Automated Test Suite for DFO3382 DEM Spatial Coverage Preflight.

Validates all Phase 7F.3.6 preflight criteria:
1. Manifest integrity: phase7f36_dfo3382_dem_preflight_manifest.yaml exists and is valid YAML.
2. Decision verification: Preflight outcome is strictly READY_FOR_CONTROLLED_DEM_ACQUISITION.
3. Delta extent & bounding box: Core Mahanadi delta bounds and cell counts are verified.
4. Tile staging packages: Package 1 (4 core delta tiles), Package 2 (6 extended delta tiles), Package 3 (9 fluvial basin tiles).
5. Local DEM inventory: Confirms 0% local coverage for Mahanadi Basin and 5 existing non-Mahanadi tiles.
6. Documentation parity: PHASE_7F_3_6_DEM_COVERAGE_PREFLIGHT.md exists and documents all required sections.
7. Governance constraints: DFO 2507 holdout quarantine preserved; Phase 6 solver remains operational authority.
"""

from pathlib import Path
import json
import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Artifact paths
MANIFEST_PATH = REPO_ROOT / "data" / "manifests" / "phase7f36_dfo3382_dem_preflight_manifest.yaml"
REPORT_PATH = REPO_ROOT / "docs" / "phase7" / "PHASE_7F_3_6_DEM_COVERAGE_PREFLIGHT.md"
PREFLIGHT_JSON = REPO_ROOT / "docs" / "phase7" / "DFO_3382_dem_preflight_analysis.json"
BREAKDOWN_JSON = REPO_ROOT / "docs" / "phase7" / "DFO_3382_mahanadi_dem_spatial_breakdown.json"
RAW_DEM_DIR = REPO_ROOT / "data" / "raw" / "phase7" / "dem"


def test_manifest_existence_and_schema():
    """Verify phase7f36 manifest exists, is valid YAML, and contains core metadata."""
    assert MANIFEST_PATH.exists(), f"Preflight manifest missing at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["phase"] == "7F.3.6"
    assert manifest["subphase_title"] == "DFO3382 DEM Spatial Coverage Preflight"
    assert manifest["preflight_decision"] == "READY_FOR_CONTROLLED_DEM_ACQUISITION"
    assert "spatial_domains" in manifest
    assert "local_dem_inventory" in manifest
    assert "candidate_dem_staging_packages" in manifest


def test_spatial_domains_and_cell_counts():
    """Verify core delta and basin flood footprints and verified cell counts."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    domains = manifest["spatial_domains"]
    assert "core_delta" in domains
    assert "mahanadi_basin_corridor" in domains

    core = domains["core_delta"]
    assert core["verified_flood_cells"] == 18682
    assert core["percentage_of_odisha_footprint"] == pytest.approx(59.84, rel=1e-2)
    assert core["tiles_required"] == ["N19E085", "N19E086", "N20E085", "N20E086"]

    corridor = domains["mahanadi_basin_corridor"]
    assert corridor["verified_flood_cells"] == 31219
    assert corridor["tile_count"] == 12


def test_dem_staging_packages():
    """Verify candidate staging packages definition and sizing."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    packages = manifest["candidate_dem_staging_packages"]
    p1 = packages["package_1_core_delta"]
    assert p1["tile_count"] == 4
    assert p1["tiles"] == ["N19E085", "N19E086", "N20E085", "N20E086"]
    assert p1["verified_flood_cells_covered"] == 18682

    p2 = packages["package_2_extended_delta"]
    assert p2["tile_count"] == 6
    assert p2["verified_flood_cells_covered"] == 20532

    p3 = packages["package_3_full_fluvial_corridor"]
    assert p3["tile_count"] == 9
    assert p3["verified_flood_cells_covered"] == 30310


def test_local_dem_inventory_deficit():
    """Verify that local disk currently has 0 tiles covering Mahanadi Basin."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    inv = manifest["local_dem_inventory"]
    assert inv["total_local_dem_tiles"] == 5
    assert inv["mahanadi_tiles_available"] == 0
    assert inv["core_delta_coverage_percentage"] == 0.0

    existing_tiles = inv["existing_tiles"]
    assert "N19E072" in existing_tiles
    assert "N20E073" in existing_tiles
    assert "N22E088" in existing_tiles
    assert "N25E085" in existing_tiles
    assert "N27E094" in existing_tiles

    # Verify actual disk files
    assert RAW_DEM_DIR.exists()
    for tile in existing_tiles:
        expected_tif = RAW_DEM_DIR / f"Copernicus_DSM_COG_10_{tile}_DEM.tif"
        assert expected_tif.exists(), f"Expected legacy DEM tile {expected_tif} to exist on disk"

    # Verify zero Mahanadi tiles exist in data/raw/phase7/dem/
    mahanadi_delta_tiles = ["N19E085", "N19E086", "N20E085", "N20E086"]
    for tile in mahanadi_delta_tiles:
        m_tif = RAW_DEM_DIR / f"Copernicus_DSM_COG_10_{tile}_DEM.tif"
        assert not m_tif.exists(), f"Mahanadi tile {tile} should not exist prior to authorized acquisition"


def test_preflight_json_artifacts():
    """Verify preflight analysis and breakdown JSON artifacts."""
    assert PREFLIGHT_JSON.exists(), f"Missing {PREFLIGHT_JSON}"
    assert BREAKDOWN_JSON.exists(), f"Missing {BREAKDOWN_JSON}"

    with open(PREFLIGHT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_verified_episodic_flood_cells_composite"] == 339963
    assert data["mahanadi_basin"]["verified_flood_cells"] == 31219
    assert data["core_delta"]["verified_flood_cells"] == 18682

    with open(BREAKDOWN_JSON, "r", encoding="utf-8") as f:
        breakdown = json.load(f)
    assert "N19E085" in breakdown
    assert breakdown["N19E085"]["verified_flood_cells"] == 9392
    assert breakdown["N20E086"]["verified_flood_cells"] == 6105
    assert breakdown["N20E085"]["verified_flood_cells"] == 3061
    assert breakdown["N19E086"]["verified_flood_cells"] == 124


def test_report_structure_and_decision():
    """Verify that report markdown is complete and asserts the single approved decision."""
    assert REPORT_PATH.exists(), f"Missing report at {REPORT_PATH}"
    content = REPORT_PATH.read_text(encoding="utf-8")

    assert "# AQUORA — Phase 7F.3.6: DFO3382 DEM Spatial Coverage Preflight Report" in content
    assert "## 10. Audit Conclusions and Final Preflight Decision" in content
    assert "READY_FOR_CONTROLLED_DEM_ACQUISITION" in content
    assert "PARTIAL_COVERAGE" not in content.split("## 10. Audit Conclusions and Final Preflight Decision")[1]
    assert "BLOCKED" not in content.split("## 10. Audit Conclusions and Final Preflight Decision")[1]
    assert "DFO 2507" in content
    assert "ALREADY_INSPECTED_HOLDOUT" in content
