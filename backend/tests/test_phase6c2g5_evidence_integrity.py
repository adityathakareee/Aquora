"""
AQUORA Phase 6C.2G.5: Evidence Artifact Integrity and Data Acquisition Readiness Tests.

Verifies:
1. Source DEM immutability (Raw DEM and Working DEM hashes).
2. Phase 6C.2G.4 evidence artifacts existence, readability, file size, and SHA-256 checksums.
3. Strict distinction between JSON metadata/search records and original source documents.
4. Chitale Committee 2006 claims status: PARTIALLY_VERIFIED (PDF not possessed on disk, link 404, no GIS polygon).
5. Zope et al. (2015) CrossRef verification: PARTIALLY_VERIFIED (DOI 10.1007/s11069-014-1356-4, 70.57 km2, open GIS UNAVAILABLE).
6. Municipal culvert/railway claims (UNVERIFIED) and tidal datum claims (PARTIALLY_VERIFIED).
7. Prioritized dataset acquisition plan (ACQ-01 to ACQ-05) and Phase 6C.2G.5 manifest governance invariants.
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
PHASE6C2G4_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase6c2g4_acquisition_manifest.yaml"
PHASE6C2G5_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase6c2g5_integrity_and_readiness_manifest.yaml"

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
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()

    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256


def test_phase6c2g4_artifacts_integrity_and_checksums():
    """Verify that all Phase 6C.2G.4 artifacts exist, match exact file sizes and SHA-256 hashes."""
    assert PHASE6C2G4_MANIFEST.exists()
    with open(PHASE6C2G4_MANIFEST, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    entries = manifest["acquisition_evidence_package"]["entries"]
    assert len(entries) == 5

    for entry in entries:
        fpath = PROJECT_ROOT / entry["local_path"]
        assert fpath.exists(), f"Missing file: {fpath}"
        assert fpath.stat().st_size == entry["file_size_bytes"]
        assert compute_sha256(fpath) == entry["sha256"]

        # Readability check
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)


def test_distinction_original_sources_vs_json_metadata():
    """Verify that evidence artifacts are recognized as JSON metadata records, not raw original documents."""
    assert PHASE6C2G5_MANIFEST.exists()
    with open(PHASE6C2G5_MANIFEST, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    audit_table = manifest["phase6c2g4_artifacts_integrity_audit"]
    assert len(audit_table) == 5

    for item in audit_table:
        assert item["original_source_document_possessed"] is False
        assert "JSON" in item["artifact_type"]


def test_chitale_committee_claims_downgrade():
    """Verify Chitale claims: breakdown verified, original PDF not possessed, status PARTIALLY_VERIFIED."""
    reg_file = EVIDENCE_DIR / "phase6c2g5_corrected_evidence_register.json"
    assert reg_file.exists()

    with open(reg_file, "r", encoding="utf-8") as f:
        reg = json.load(f)

    claims = {c["claim_id"]: c for c in reg["claims"]}
    assert "CLM-01-CHITALE-CATCHMENT-AREA" in claims
    chitale_claim = claims["CLM-01-CHITALE-CATCHMENT-AREA"]

    assert chitale_claim["corrected_status"] == "PARTIALLY_VERIFIED"
    assert chitale_claim["original_document_possessed_on_disk"] is False
    assert "72.95 sq km" in chitale_claim["claimed_metric"]
    assert "18.96" in chitale_claim["claimed_metric"]
    assert "6.61" in chitale_claim["claimed_metric"]
    assert "47.38" in chitale_claim["claimed_metric"]
    assert "HTTP 404" in chitale_claim["source_inspection_finding"]


def test_zope_et_al_crossref_verification():
    """Verify Zope et al. claims: CrossRef API verified, 70.57 km2, open GIS UNAVAILABLE, PARTIALLY_VERIFIED."""
    reg_file = EVIDENCE_DIR / "phase6c2g5_corrected_evidence_register.json"
    with open(reg_file, "r", encoding="utf-8") as f:
        reg = json.load(f)

    claims = {c["claim_id"]: c for c in reg["claims"]}
    assert "CLM-02-ZOPE-HYDRODYNAMIC-LITERATURE" in claims
    zope_claim = claims["CLM-02-ZOPE-HYDRODYNAMIC-LITERATURE"]

    assert zope_claim["corrected_status"] == "PARTIALLY_VERIFIED"
    assert "10.1007/s11069-014-1356-4" in zope_claim["source_cited"]
    assert "70.57 sq km" in zope_claim["claimed_metric"]
    assert "privately held at IIT Bombay" in zope_claim["justification"]


def test_culvert_railway_tide_claims_status():
    """Verify culvert/railway claims downgraded to UNVERIFIED and tide to PARTIALLY_VERIFIED."""
    reg_file = EVIDENCE_DIR / "phase6c2g5_corrected_evidence_register.json"
    with open(reg_file, "r", encoding="utf-8") as f:
        reg = json.load(f)

    claims = {c["claim_id"]: c for c in reg["claims"]}
    assert claims["CLM-03-CSMIA-RUNWAY-CULVERT-GEOMETRY"]["corrected_status"] == "UNVERIFIED"
    assert claims["CLM-04-RAILWAY-HIGHWAY-CROSSINGS"]["corrected_status"] == "UNVERIFIED"
    assert claims["CLM-05-MUMBAI-PORT-TIDAL-DATUM"]["corrected_status"] == "PARTIALLY_VERIFIED"


def test_prioritized_acquisition_plan_and_manifest():
    """Verify prioritized dataset acquisition plan (ACQ-01 to ACQ-05) and BLOCKED manifest decision."""
    plan_file = EVIDENCE_DIR / "prioritized_dataset_acquisition_plan.json"
    assert plan_file.exists()

    with open(plan_file, "r", encoding="utf-8") as f:
        plan = json.load(f)

    datasets = {d["dataset_id"]: d for d in plan["prioritized_datasets"]}
    assert len(datasets) == 5
    assert "ACQ-01-MCGM-BRIMSTOWAD-GIS" in datasets
    assert "ACQ-02-MIAL-RUNWAY-CULVERT-ASBUILT" in datasets
    assert "ACQ-03-SOI-TIDE-SERIES-EGM96-TIE" in datasets
    assert "ACQ-04-MMRDA-MITHI-CROSSSECTIONS" in datasets
    assert "ACQ-05-RAILWAY-BRIDGE-REGISTERS" in datasets

    # Verify rank order
    for d in plan["prioritized_datasets"]:
        assert d["priority_rank"] in [1, 2, 3, 4, 5]
        assert len(d["responsible_custodian"]) > 0
        assert len(d["intended_use_in_aquora"]) > 0
        assert len(d["minimum_acceptable_format"]) > 0

    # Manifest verification
    with open(PHASE6C2G5_MANIFEST, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["phase"] == "PHASE_6C_2G_5_EVIDENCE_ARTIFACT_INTEGRITY_AND_DATA_ACQUISITION_READINESS"
    assert manifest["governance"]["final_governance_decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert manifest["governance"]["historical_simulation_permitted"] is False
    assert manifest["dem_immutability_audit"]["immutability_verified"] is True
