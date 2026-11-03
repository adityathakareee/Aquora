"""
AQUORA Phase 6C.2G.4: Primary-Source Retrieval and Evidence Verification Tests.

Verifies:
1. Working DEM and Raw DEM source immutability against established SHA-256 hashes.
2. Chitale Committee 2006 Report catchment-area benchmark (72.95 km2, Vihar 18.96 km2, Powai 6.61 km2, Direct 47.38 km2).
3. Zope et al. (2015) peer-reviewed hydrodynamic literature verification (DOI: 10.1007/s11069-014-1356-4)
   and correction of prior secondary DOI errors.
4. Municipal and engineering dataset investigation across all 5 prioritized targets.
5. Mumbai Port Authority official tidal datum (+2.51 m MSL rel CD) and continuous series gap.
6. Formal data-request drafts for restricted agency datasets (strictly DRAFT / NOT SENT).
7. Machine-readable acquisition manifest integrity and BLOCKED governance decision.
"""

from pathlib import Path
import hashlib
import json
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
EVIDENCE_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "evidence"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g4_acquisition_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_source_dem_immutability():
    """Verify raw DEM and working DEM remain strictly unmodified."""
    assert RAW_DEM_PATH.exists(), f"Raw DEM missing: {RAW_DEM_PATH}"
    assert WORKING_DEM_PATH.exists(), f"Working DEM missing: {WORKING_DEM_PATH}"

    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256


def test_chitale_committee_2006_benchmark():
    """Verify Chitale Committee 2006 catchment breakdown and lack of georeferenced GIS vector."""
    record_file = EVIDENCE_DIR / "chitale_committee_2006_benchmark_record.json"
    assert record_file.exists()

    with open(record_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["evidence_id"] == "EVID-01-CHITALE-2006-BENCHMARK"
    assert data["issuing_authority"].startswith("Government of Maharashtra")
    assert data["publication_date"] == "March 2006"
    assert data["retrieval_outcome"] == "RETRIEVED_AND_INSPECTED"

    metrics = data["specific_pages_supporting_metrics"]
    assert metrics["printed_page_number"] == 64
    assert metrics["pdf_page_number"] == 64

    tables = {item["metric"]: item for item in metrics["exact_passages_and_tables"]}
    assert "Vihar Lake Catchment Area" in tables
    assert "Powai Lake Catchment Area" in tables
    assert "Direct River Reach Catchment Area (Below Lakes to Mahim Bay)" in tables
    assert "Total Mithi River Catchment Area" in tables

    vihar = tables["Vihar Lake Catchment Area"]["value_sq_km"]
    powai = tables["Powai Lake Catchment Area"]["value_sq_km"]
    direct = tables["Direct River Reach Catchment Area (Below Lakes to Mahim Bay)"]["value_sq_km"]
    total = tables["Total Mithi River Catchment Area"]["value_sq_km"]

    assert vihar == 18.96
    assert powai == 6.61
    assert direct == 47.38
    assert total == 72.95
    assert round(vihar + powai + direct, 2) == total

    # Check GIS geometry assessment
    gis = data["gis_geometry_assessment"]
    assert gis["usable_georeferenced_boundary_present"] is False
    assert gis["vector_shapefile_included"] is False
    assert "MUST NOT digitize schematic report map" in gis["governance_rule"]


def test_zope_et_al_2015_hydrodynamic_literature():
    """Verify Zope et al. bibliographic identity, DOI correction, catchment area, and lack of open GIS."""
    record_file = EVIDENCE_DIR / "zope_et_al_2015_hydrodynamic_literature_record.json"
    assert record_file.exists()

    with open(record_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["evidence_id"] == "EVID-02-ZOPE-ET-AL-2015-LITERATURE"
    bib = data["verified_bibliographic_identity"]
    assert bib["title"] == "Impacts of urbanization on flooding of a coastal urban catchment: a case study of Mumbai City, India"
    assert bib["journal"] == "Natural Hazards"
    assert bib["volume"] == 75
    assert bib["issue"] == 1
    assert bib["pages"] == "887-908"
    assert bib["publication_year"] == 2015
    assert bib["canonical_doi"] == "10.1007/s11069-014-1356-4"

    # Prior erroneous citations resolution
    resolved = {c["erroneous_doi"]: c for c in data["prior_erroneous_citations_resolved"]}
    assert "10.1016/j.jhydrol.2015.03.028" in resolved
    assert "10.1007/s11069-016-2401-y" in resolved
    assert "Thomas" in resolved["10.1016/j.jhydrol.2015.03.028"]["actual_work_resolved"]
    assert "Bao" in resolved["10.1007/s11069-016-2401-y"]["actual_work_resolved"]

    # Hydrological statements
    hydro = data["study_area_and_hydrology"]
    assert hydro["published_catchment_area_sq_km"] == 70.57
    assert "Runway 09/27" in hydro["terrain_conditioning_and_hydraulic_structures_discussion"]

    # Supplementary data audit
    supp = data["supplementary_data_audit"]
    assert supp["electronic_supplementary_material_present"] is False
    assert supp["linked_open_data_repository"] is None
    assert "PRIVATELY_HELD_RESEARCH_ARTIFACTS" in supp["status"]


def test_municipal_and_engineering_investigation():
    """Verify investigation of municipal and engineering datasets across all 5 targets."""
    record_file = EVIDENCE_DIR / "municipal_engineering_datasets_investigation.json"
    assert record_file.exists()

    with open(record_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["evidence_id"] == "EVID-03-MUNICIPAL-ENGINEERING-INVESTIGATION"
    targets = {t["target_id"]: t for t in data["prioritized_targets"]}

    assert len(targets) == 5
    assert "ENG-TGT-01-MITHI-WATERSHED-GIS" in targets
    assert "ENG-TGT-02-MITHI-RIVER-CENTERLINE-CROSSSECTIONS" in targets
    assert "ENG-TGT-03-CSMIA-RUNWAY-CULVERT-ASBUILT" in targets
    assert "ENG-TGT-04-RAILWAY-HIGHWAY-CROSSINGS" in targets
    assert "ENG-TGT-05-COASTAL-OUTLET-BATHYMETRY" in targets

    for t_id, t in targets.items():
        assert len(t["responsible_agencies"]) > 0
        assert len(t["search_url"]) > 0
        assert len(t["evidence_found"]) > 0
        assert t["verification_status"] == "LOCATED_BUT_RESTRICTED"

    # Culvert dimensions
    culvert_info = targets["ENG-TGT-03-CSMIA-RUNWAY-CULVERT-ASBUILT"]["evidence_found"]
    assert "3 x 20m" in culvert_info
    assert "+2.50m MSL" in culvert_info
    assert "+2.10m MSL" in culvert_info
    assert "CAD centerline drawing and inlet/outlet coordinate vectors are strictly proprietary" in culvert_info


def test_mumbai_port_authority_tidal_datum():
    """Verify Mumbai Port Authority datum relationship (+2.51m) and July 2019 continuous series gap."""
    record_file = EVIDENCE_DIR / "mumbai_port_authority_tidal_datum_record.json"
    assert record_file.exists()

    with open(record_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["evidence_id"] == "EVID-04-MUMBAI-PORT-TIDAL-DATUM"
    datum = data["official_datum_relationship_verification"]
    assert datum["source_authority"] == "Mumbai Port Authority (MbPA)"
    assert datum["verified_against_original_source"] is True
    assert "Mean Sea Level (MSL) is +2.51 meters relative to Chart Datum (CD)" in datum["statement"]
    assert datum["datum_reduction_formula"] == "z_local_msl = z_chart_datum - 2.51"

    # Tidal range table
    levels = {row["level_name"]: row for row in datum["official_tidal_range_table_mbpa"]}
    assert levels["Highest High Water recorded"]["height_above_cd_m"] == 5.39
    assert levels["Mean High Water Spring Tides (MHWS)"]["height_above_cd_m"] == 4.42
    assert levels["Mean Sea Level (MSL)"]["height_above_cd_m"] == 2.51
    assert levels["Lowest Low Water recorded"]["height_above_cd_m"] == -0.46

    # Event E03 water level audit
    e03 = data["historical_event_e03_water_level_audit"]
    assert e03["reported_peak_stage"]["peak_water_level_cd_m"] == 4.59
    assert e03["reported_peak_stage"]["equivalent_local_msl_m"] == 2.08
    assert e03["continuous_time_series_retrieval_result"] == "MISSING_FROM_PUBLIC_AUTOMATED_REPOSITORIES"
    assert e03["critical_geodetic_gap"]["egm96_geoid_tie_sheet"] == "MISSING_FROM_OPEN_RECORDS"
    assert "STRICTLY PROHIBITED" in e03["governance_rule"]


def test_formal_data_request_drafts():
    """Verify formal data-request drafts are complete and strictly marked DRAFT_ONLY_NOT_SUBMITTED."""
    record_file = EVIDENCE_DIR / "formal_data_request_letters.json"
    assert record_file.exists()

    with open(record_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["evidence_id"] == "EVID-05-FORMAL-DATA-REQUEST-DRAFTS"
    assert "STRICTLY DRAFT / NOT SENT" in data["governance_notice"]

    drafts = {d["request_id"]: d for d in data["drafts"]}
    assert len(drafts) == 3
    assert "REQ-DRAFT-01-MCGM-BRIMSTOWAD-GIS" in drafts
    assert "REQ-DRAFT-02-MIAL-CULVERT-ASBUILT" in drafts
    assert "REQ-DRAFT-03-SOI-TIDE-AND-EGM96-TIE" in drafts

    for d_id, d in drafts.items():
        assert len(d["recipient_office"]) > 0
        assert len(d["subject"]) > 0
        assert len(d["dataset_requested"]) > 0
        assert len(d["intended_use"]) > 0
        assert d["human_authorization_required"] is True
        assert d["status"] == "DRAFT_ONLY_NOT_SUBMITTED"


def test_acquisition_manifest_integrity_and_governance():
    """Verify acquisition manifest structure, checksums, and BLOCKED governance decision."""
    assert MANIFEST_PATH.exists()

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["phase"] == "PHASE_6C_2G_4_PRIMARY_SOURCE_RETRIEVAL_AND_EVIDENCE_VERIFICATION"
    gov = manifest["governance"]
    assert gov["status"] == "PRIMARY_SOURCE_VERIFICATION_COMPLETED"
    assert gov["watershed_status"] == "EXPLORATORY_ONLY"
    assert gov["final_governance_decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert gov["historical_simulation_permitted"] is False
    assert gov["zero_culvert_fabrication_enforced"] is True
    assert gov["zero_synthetic_interpolation_enforced"] is True
    assert gov["working_dem_immutable"] is True
    assert gov["human_authorization_enforced"] is True

    # Immutability audit
    imm = manifest["dem_immutability_audit"]
    assert imm["immutability_verified"] is True
    assert imm["raw_dem_sha256"] == EXPECTED_RAW_DEM_SHA256
    assert imm["working_dem_sha256"] == EXPECTED_WORKING_DEM_SHA256

    # Package entries
    pkg = manifest["acquisition_evidence_package"]
    assert pkg["entries_count"] == 5
    for entry in pkg["entries"]:
        local_path = PROJECT_ROOT / entry["local_path"]
        assert local_path.exists()
        assert compute_sha256(local_path) == entry["sha256"]
        assert local_path.stat().st_size == entry["file_size_bytes"]

    # Decision justification
    decision = manifest["go_no_go_decision"]
    assert decision["decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert "Chitale Committee" in decision["justification"]
    assert "Zope et al." in decision["justification"]
    assert "Mumbai Port Authority" in decision["justification"]
