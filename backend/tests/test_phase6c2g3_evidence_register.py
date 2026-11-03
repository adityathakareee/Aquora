"""
AQUORA Phase 6C.2G.3: Authoritative Watershed and Outlet Evidence Acquisition Tests.

Verifies:
1. Working DEM and Raw DEM source immutability.
2. Evidence register completeness across all 6 required domains with traceable citations.
3. Rigorous 6-tier geospatial geometry taxonomy separating scalar statistics from official GIS vectors.
4. Coastal outlet evaluation and identification of tidal marine boundary gaps.
5. Governance invariants, non-forcing of benchmarks, and BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE decision.
"""

from pathlib import Path
import pytest
import rasterio
import yaml
import hashlib

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g3_evidence_register_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_source_dem_immutability():
    """Verify raw DEM and working DEM are unchanged and match established hashes."""
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()

    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256


def test_evidence_register_domains_and_provenance():
    """Verify evidence register covers all 6 required domains with traceable metadata."""
    assert MANIFEST_PATH.exists()

    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    reg = manifest["evidence_register"]
    assert reg["register_entries_count"] >= 6
    entries = {e["evidence_id"]: e for e in reg["register"]}

    # Required domains
    assert "REG-01-CHITALE-REPORT-2006" in entries
    assert "REG-02-MCGM-BRIMSTOWAD-MASTERPLAN" in entries
    assert "REG-03-MMRDA-MITHI-MASTERPLAN" in entries
    assert "REG-04-IIT-BOMBAY-ZOPE-ET-AL" in entries
    assert "REG-05-CSMIA-RUNWAY-CULVERT" in entries
    assert "REG-06-RAILWAY-HIGHWAY-CROSSINGS" in entries
    assert "REG-07-MUMBAI-PORT-TIDAL-DATUM" in entries

    for e_id, e in entries.items():
        assert len(e["exact_title"]) > 0
        assert len(e["issuing_organization"]) > 0
        assert len(e["publication_date"]) > 0
        assert len(e["retrievable_url_or_path"]) > 0
        assert len(e["relevant_citation_location"]) > 0
        assert len(e["what_it_actually_supports"]) > 0
        assert len(e["what_remains_unverified"]) > 0
        assert len(e["verification_status"]) > 0
        assert len(e["permitted_use"]) > 0
        assert len(e["outstanding_evidence_needed"]) > 0


def test_geospatial_geometry_taxonomy():
    """Verify taxonomy separates scalar statistics and OSM data from surveyed and official GIS geometry."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    taxonomy = manifest["geospatial_geometry_assessment"]["tiers"]
    assert len(taxonomy) == 6

    tiers_by_name = {t["tier"]: t for t in taxonomy}
    assert "PUBLISHED_AREA_STATISTICS" in tiers_by_name
    assert "SCHEMATIC_MAPS_AND_PDF_FIGURES" in tiers_by_name
    assert "DIGITIZED_APPROXIMATIONS" in tiers_by_name
    assert "VOLUNTEERED_GEOGRAPHIC_DATA" in tiers_by_name
    assert "SURVEYED_ASBUILT_ENGINEERING_GEOMETRY" in tiers_by_name
    assert "OFFICIAL_GIS_VECTOR_DATA" in tiers_by_name

    # Check status
    assert "UNAVAILABLE" in tiers_by_name["SURVEYED_ASBUILT_ENGINEERING_GEOMETRY"]["current_status"]
    assert "UNAVAILABLE" in tiers_by_name["OFFICIAL_GIS_VECTOR_DATA"]["current_status"]


def test_outlet_and_tidal_evidence():
    """Verify causeway outlet rejection, bay mouth exploratory status, and tidal gaps."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    outlets = manifest["outlet_and_tidal_evidence"]
    assert "REJECTED" in outlets["proposed_causeway_outlet"]["verdict"]
    assert "EXPLORATORY" in outlets["mahim_bay_mouth_outlet"]["verdict"]

    tide = outlets["marine_tidal_boundary_condition"]
    assert tide["reported_peak_tide"]["peak_level_cd"] == 4.59
    assert tide["reported_peak_tide"]["equivalent_local_msl"] == 2.08
    assert len(tide["critical_knowledge_gaps"]) >= 3
    assert "STRICTLY BLOCKED" in tide["governance_rule"]


def test_phase6c2g3_governance_and_go_no_go_decision():
    """Verify decision is BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE."""
    with open(MANIFEST_PATH, "r") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["status"] == "EVIDENCE_REGISTER_AUDIT_COMPLETED"
    assert gov["watershed_status"] == "EXPLORATORY_ONLY"
    assert gov["final_governance_decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert gov["historical_simulation_permitted"] is False
    assert gov["zero_culvert_fabrication_enforced"] is True

    decision = manifest["go_no_go_decision"]
    assert decision["decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert len(decision["precise_datasets_required_to_unblock"]) >= 4
