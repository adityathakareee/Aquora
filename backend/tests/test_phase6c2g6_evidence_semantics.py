"""
AQUORA Phase 6C.2G.6: Evidence Status Semantics and Acquisition Request Readiness Tests.

Verifies:
1. Source DEM immutability (Raw Copernicus DSM and Working DEM match exact hashes).
2. Failed retrievals cannot be classified as CUSTODIAN_CONFIRMED_RESTRICTED (must be ACCESS_NOT_ESTABLISHED).
3. CrossRef bibliographic metadata verifies publication identity only, NOT technical claims from inaccessible text.
4. Missing local datasets remain explicitly marked NOT_ACQUIRED with original_source_retrieved_and_inspected=False.
5. Every verified or partially verified claim has a traceable source location.
6. Arithmetic checks (18.96 + 6.61 + 47.38 = 72.95) are explicitly labeled as math identities, NOT source verification.
7. Acquisition request package includes lower-sensitivity alternatives and recipient verification status.
8. Parallel work plan strictly prohibits historical flood depth or inundation simulation.
9. Governance decision remains BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE.
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
REGISTER_PATH = EVIDENCE_DIR / "phase6c2g6_evidence_register.json"
PACKAGE_PATH = EVIDENCE_DIR / "phase6c2g6_acquisition_request_package.json"
PLAN_PATH = EVIDENCE_DIR / "phase6c2g6_parallel_work_plan.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g6_evidence_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"

VALID_STATUSES = {
    "VERIFIED_PRIMARY_SOURCE",
    "PARTIALLY_VERIFIED",
    "BIBLIOGRAPHICALLY_VERIFIED",
    "UNVERIFIED",
    "NOT_FOUND_IN_SEARCH",
    "ACCESS_NOT_ESTABLISHED",
    "NOT_ACQUIRED",
    "CUSTODIAN_CONFIRMED_RESTRICTED"
}


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


def test_failed_retrievals_not_classified_as_custodian_confirmed():
    """Verify that failed URLs or empty search results are NOT labeled CUSTODIAN_CONFIRMED_RESTRICTED."""
    assert REGISTER_PATH.exists()
    with open(REGISTER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for claim in data["claims"]:
        assert claim["evidence_status"] in VALID_STATUSES
        # Disallow claiming custodian restriction without documented custodian response
        assert claim["evidence_status"] != "CUSTODIAN_CONFIRMED_RESTRICTED"

        # Check culvert, railway, and tie claims
        if claim["claim_id"] in [
            "CLM-05-CSMIA-RUNWAY-CULVERT-DIMENSIONS-INVERTS",
            "CLM-06-CSMIA-RUNWAY-CULVERT-GEOREFERENCED-ALIGNMENT",
            "CLM-07-RAILWAY-HIGHWAY-BRIDGE-OPENINGS",
            "CLM-11-SURVEY-OF-INDIA-EGM96-GEOOID-TIE"
        ]:
            assert "ACCESS_NOT_ESTABLISHED" in claim["unresolved_limitations"]


def test_bibliographic_metadata_cannot_verify_technical_claims():
    """Verify that CrossRef metadata verifies publication identity only, NOT technical claims."""
    with open(REGISTER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    claims = {c["claim_id"]: c for c in data["claims"]}
    bib_claim = claims["CLM-03-ZOPE-BIBLIOGRAPHIC-METADATA"]
    tech_claim = claims["CLM-04-ZOPE-TECHNICAL-MODELING-CLAIMS"]

    assert bib_claim["evidence_status"] == "BIBLIOGRAPHICALLY_VERIFIED"
    assert bib_claim["original_source_retrieved_and_inspected"] is True

    assert tech_claim["evidence_status"] == "UNVERIFIED"
    assert tech_claim["original_source_retrieved_and_inspected"] is False
    assert "CrossRef bibliographic metadata must not be presented as verification" in tech_claim["unresolved_limitations"]


def test_missing_local_datasets_remain_not_acquired():
    """Verify that missing local source files are explicitly labeled NOT_ACQUIRED."""
    with open(REGISTER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    claims = {c["claim_id"]: c for c in data["claims"]}
    doc_claim = claims["CLM-01-CHITALE-REPORT-PHYSICAL-DOCUMENT"]

    assert doc_claim["evidence_status"] == "NOT_ACQUIRED"
    assert doc_claim["original_source_retrieved_and_inspected"] is False
    assert doc_claim["local_file_path"] is None


def test_traceable_source_location_for_primary_and_partial_claims():
    """Every verified or partially verified claim must have a non-empty traceable source location."""
    with open(REGISTER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for claim in data["claims"]:
        if claim["evidence_status"] in ["VERIFIED_PRIMARY_SOURCE", "PARTIALLY_VERIFIED", "BIBLIOGRAPHICALLY_VERIFIED"]:
            assert len(claim["source_title"]) > 0
            assert len(claim["publisher_or_custodian"]) > 0
            assert len(claim["canonical_identifier_or_url"]) > 0
            assert len(claim["supporting_location_in_source"]) > 0


def test_arithmetic_checks_not_source_verification():
    """Arithmetic checks must not be presented as source verification."""
    with open(REGISTER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    claims = {c["claim_id"]: c for c in data["claims"]}
    chitale_claim = claims["CLM-02-CHITALE-CATCHMENT-METRICS"]

    assert chitale_claim["evidence_status"] == "PARTIALLY_VERIFIED"
    assert "arithmetic checks do NOT constitute primary-source verification" in chitale_claim["unresolved_limitations"]


def test_acquisition_request_package_structure_and_alternatives():
    """Verify acquisition package includes lower-sensitivity alternatives, recipient verification, and blocker resolution."""
    assert PACKAGE_PATH.exists()
    with open(PACKAGE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["requests_count"] == 5
    reqs = {r["request_id"]: r for r in data["requests"]}

    assert "REQ-01-MCGM-BRIMSTOWAD-GIS" in reqs
    assert "REQ-02-MIAL-CULVERT-ASBUILT" in reqs
    assert "REQ-03-SOI-TIDE-SERIES-EGM96-TIE" in reqs
    assert "REQ-04-MMRDA-MITHI-CROSSSECTIONS" in reqs
    assert "REQ-05-RAILWAY-BRIDGE-REGISTERS" in reqs

    for r_id, r in reqs.items():
        assert r["recipient_verified"] is True
        assert len(r["verification_note"]) > 0
        assert len(r["dataset_requested"]) > 0
        assert len(r["coverage"]) > 0
        assert len(r["acceptable_formats"]) > 0
        assert len(r["intended_research_use"]) > 0
        assert len(r["lower_sensitivity_alternative"]) > 0
        assert len(r["aquora_blocker_resolved"]) > 0
        assert r["status"] == "DRAFT_ONLY_NOT_SUBMITTED"


def test_parallel_work_plan_and_strict_prohibitions():
    """Verify parallel work plan includes safe packages and strict prohibitions on unverified simulations."""
    assert PLAN_PATH.exists()
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        plan = json.load(f)

    assert len(plan["authorized_work_packages"]) >= 4
    prohibitions = plan["strict_prohibitions"]

    assert any("flood-depth" in p.lower() for p in prohibitions)
    assert any("inundation" in p.lower() for p in prohibitions)
    assert any("tide-surge" in p.lower() or "coastal boundary" in p.lower() for p in prohibitions)


def test_missing_evidence_keeps_governance_decision_blocked():
    """Verify that missing authoritative evidence enforces BLOCKED governance decision."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["governance"]["final_governance_decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert manifest["governance"]["historical_simulation_permitted"] is False
    assert manifest["governance"]["zero_culvert_fabrication_enforced"] is True
    assert manifest["dem_immutability_audit"]["immutability_verified"] is True
