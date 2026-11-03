"""
AQUORA Phase 6C.2G.7: Independent Evidence Register Audit and Rainfall/SAR Validation Tests.

Validates:
1. Source DEM immutability (Raw Copernicus DSM and Working DEM match exact hashes).
2. Source claims without original-source evidence cannot be marked verified (CLM-02, CLM-08, CLM-09).
3. Crossref metadata alone cannot verify article-specific technical findings (CLM-03 vs CLM-04).
4. Missing or corrupt files are reported accurately.
5. Time-zone and acquisition-interval comparisons are handled correctly (UTC vs IST, 30m interval vs instantaneous).
6. Missing observations remain missing, not zero (fill values preserved).
7. Temporal coincidence alone cannot establish flood truth (SAR anomaly != confirmed flood inundation).
8. Five-tier epistemological categorization is strictly structured.
9. Final governance decision remains BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
EVIDENCE_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "evidence"
VALIDATION_DIR = PROJECT_ROOT / "data" / "processed" / "phase7" / "validation"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

AUDIT_PATH = EVIDENCE_DIR / "phase6c2g7_evidence_audit.json"
ALIGNMENT_PATH = VALIDATION_DIR / "phase6c2g7_rainfall_sar_alignment.json"
VALIDATION_MANIFEST_PATH = MANIFEST_DIR / "phase6c2g7_validation_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_source_dem_immutability():
    """Verify raw Copernicus DSM and working study-extent DEM remain strictly unmodified."""
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()
    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256


def test_claims_without_original_source_evidence_cannot_be_verified():
    """Verify that claims without original retrievable sources are downgraded to UNVERIFIED."""
    assert AUDIT_PATH.exists()
    with open(AUDIT_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)

    claims = {c["claim_id"]: c for c in audit["claims"]}

    # CLM-02 (Chitale catchment benchmark)
    clm02 = claims["CLM-02-CHITALE-CATCHMENT-METRICS"]
    assert clm02["audited_status"] == "UNVERIFIED"
    assert clm02["original_source_file_present_on_disk"] is False
    assert clm02["downgrade_applied"] is True
    assert "arithmetic summation" in clm02["audit_finding"].lower() or "mathematical identity" in clm02["audit_finding"].lower()

    # CLM-08 (MbPA tidal datum constant)
    clm08 = claims["CLM-08-MBPA-TIDAL-DATUM-CONSTANT"]
    assert clm08["audited_status"] == "UNVERIFIED"
    assert clm08["original_source_file_present_on_disk"] is False
    assert clm08["downgrade_applied"] is True
    assert "404" in clm08["audit_finding"] or "egm96" in clm08["audit_finding"].lower()

    # CLM-09 (Event E03 peak tide stage)
    clm09 = claims["CLM-09-EVENT-E03-HIGH-TIDE-PEAK"]
    assert clm09["audited_status"] == "UNVERIFIED"
    assert clm09["original_source_file_present_on_disk"] is False
    assert clm09["downgrade_applied"] is True

    # Check rule: No claim with original_source_file_present_on_disk=False is VERIFIED
    for cid, c in claims.items():
        if not c.get("original_source_file_present_on_disk", False):
            assert c["audited_status"] not in ["VERIFIED_PRIMARY_SOURCE", "PARTIALLY_VERIFIED"]


def test_crossref_metadata_cannot_verify_article_technical_findings():
    """Verify strict separation between verified bibliographic metadata and unverified technical claims."""
    with open(AUDIT_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)

    claims = {c["claim_id"]: c for c in audit["claims"]}
    bib = claims["CLM-03-ZOPE-BIBLIOGRAPHIC-METADATA"]
    tech = claims["CLM-04-ZOPE-TECHNICAL-MODELING-CLAIMS"]

    assert bib["audited_status"] == "BIBLIOGRAPHICALLY_VERIFIED"
    assert bib["original_source_retrieved_and_inspected"] is True

    assert tech["audited_status"] == "UNVERIFIED"
    assert tech["original_source_retrieved_and_inspected"] is False
    assert "cannot verify article-internal technical findings" in tech["audit_finding"].lower()


def test_missing_or_corrupt_files_reported_accurately():
    """Verify that unretrieved or missing files are reported accurately without fabrication."""
    with open(AUDIT_PATH, "r", encoding="utf-8") as f:
        audit = json.load(f)

    claims = {c["claim_id"]: c for c in audit["claims"]}
    doc_claim = claims["CLM-01-CHITALE-REPORT-PHYSICAL-DOCUMENT"]
    assert doc_claim["audited_status"] == "NOT_ACQUIRED"
    assert doc_claim["local_file_path"] is None

    # Check SAR zip integrity in alignment artifact
    with open(ALIGNMENT_PATH, "r", encoding="utf-8") as f:
        val = json.load(f)

    assert val["sar_validation_summary"]["scenes_inspected"] == 2
    assert val["temporal_alignment_and_intervals"]["justification_of_temporal_labels"]["post_event_recession"] == "NOT_ACQUIRED: The 2019-07-14 scene is catalog-referenced but not downloaded to disk."


def test_timezone_and_acquisition_interval_comparisons():
    """Verify temporal conversions, intervals, and tide lag are handled correctly."""
    with open(ALIGNMENT_PATH, "r", encoding="utf-8") as f:
        val = json.load(f)

    temp = val["temporal_alignment_and_intervals"]

    # SAR Overpass timestamp
    sar_utc = temp["sentinel1_overpass"]["timestamp_utc"]
    sar_ist = temp["sentinel1_overpass"]["timestamp_ist"]
    assert sar_utc == "2019-07-02T01:02:58Z"
    assert sar_ist == "2019-07-02T06:32:58+05:30"

    # Coincident IMERG step 44 spans the overpass
    coincident = temp["imerg_coincident_step"]
    assert coincident["step_index"] == 44
    assert coincident["filename"] == "3B-HHR.MS.MRG.3IMERG.20190702-S010000-E012959.0060.V07B.HDF5"
    assert coincident["active_precipitation_during_overpass"] is True

    # Preceding rainfall > 90%
    partition = temp["rainfall_partition_relative_to_sar"]
    assert partition["preceding_percentage_of_24h"] >= 90.0
    assert partition["preceding_cloudburst_accumulation_mm"] > 200.0

    # High tide peak lag > 5 hours after SAR overpass
    tide = temp["marine_tidal_phase_alignment"]
    assert tide["sar_overpass_delta_hours_before_peak_tide"] > 5.0
    assert tide["reported_peak_water_level_cd_m"] == 4.59


def test_missing_observations_remain_missing_not_zero():
    """Verify that fill values are not converted to zero rainfall or dry ground."""
    with open(ALIGNMENT_PATH, "r", encoding="utf-8") as f:
        val = json.load(f)

    rain_summary = val["rainfall_validation_summary"]
    assert "never treated as zero rainfall or dry ground" in rain_summary["nodata_semantics"].lower()
    assert rain_summary["missing_observation_intervals"] == 0
    assert rain_summary["granules_inspected"] == 48


def test_temporal_coincidence_cannot_establish_flood_truth():
    """Verify that SAR microwave backscatter anomalies are strictly categorized as candidate evidence, not ground truth."""
    with open(ALIGNMENT_PATH, "r", encoding="utf-8") as f:
        val = json.load(f)

    sar_summary = val["sar_validation_summary"]
    assert "candidate observational evidence only" in sar_summary["scientific_constraint"].lower()
    assert "not verified ground truth" in sar_summary["scientific_constraint"].lower()

    # Check Tier 5 in categorization
    tier5 = val["epistemological_five_tier_categorization"]["tier_5_contextual_or_insufficient_for_validation"]
    sar_tier5 = [item for item in tier5 if "Candidate SAR Flood Anomaly" in item["asset"]][0]
    assert "INSUFFICIENT FOR GROUND TRUTH VALIDATION" in sar_tier5["limitation_reason"]


def test_five_tier_categorization_structure():
    """Verify that all five required epistemological tiers are present and populated."""
    with open(ALIGNMENT_PATH, "r", encoding="utf-8") as f:
        val = json.load(f)

    cat = val["epistemological_five_tier_categorization"]
    assert "tier_1_acquired_and_technically_readable" in cat
    assert "tier_2_temporally_relevant_to_event" in cat
    assert "tier_3_spatially_relevant_to_study_area" in cat
    assert "tier_4_suitable_for_quantitative_corroboration" in cat
    assert "tier_5_contextual_or_insufficient_for_validation" in cat

    for tier_key, items in cat.items():
        assert len(items) >= 2


def test_governance_decision_remains_blocked():
    """Verify that final governance decision is BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE."""
    with open(VALIDATION_MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["final_governance_decision"] == "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE"
    assert gov["historical_simulation_permitted"] is False
    assert gov["zero_culvert_fabrication_enforced"] is True
    assert gov["zero_label_fabrication_enforced"] is True
    assert gov["zero_synthetic_interpolation_enforced"] is True
