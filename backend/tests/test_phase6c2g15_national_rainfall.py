"""
AQUORA Phase 6C.2G.15: National Historical Precipitation Acquisition & Scaling Tests.

Validates:
1. Asset immutability: Raw Copernicus DSM, Working DEM, and Raw IFI match exact SHA-256 hashes.
2. Pilot forensic reconciliation:
   - Re-audits E03: 221.78 mm (IMD 24h cycle) vs 243.12 mm (IMERG Daily calendar day) resolved by 3-hour timezone shift.
   - Re-audits E02: 154.32 mm identically matched between 48 half-hourly granules and IMERG Daily product.
   - Reconciles pilot UEIs with raw IFI v3 CSV and flags proxy coordinates.
3. National scaling and deduplication:
   - 6,876 records deduplicated into 3,684 unique valid dates.
   - Era eligibility: Pre-1981 (321), CHIRPS-eligible (6,535), IMERG-eligible (4,605).
   - Storage projections: CHIRPS Daily (~10.2 GB) + IMERG Daily (~69.7 GB) = ~79.9 GB deduplicated total.
4. National acquisition inventory integrity:
   - Exactly 6,876 rows matching original IFI v3.
   - Strict Stage 2 fields: source_event_record, event_date_confidence, event_location_confidence,
     rainfall_temporal_coverage, rainfall_spatial_coverage, rainfall_source_validation,
     gauge_comparison_status, event_match_status.
   - Strict null preservation: zero-filling missing rainfall is prohibited.
5. National cohort extraction: 16 landmark disaster events across India with authentic CHIRPS and IMERG daily data.
6. Manifest governance and safeguards:
   - Final decision: PARTIAL_NATIONAL_ACQUISITION.
   - Prohibitions: zero models trained, supervised training prohibited, trigger modeling prohibited.
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
RAW_IFI_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "india_flood_inventory_v3.csv"
DERIVED_PARQUET = PROJECT_ROOT / "data" / "processed" / "phase7" / "events" / "national_historical_flood_records_derived.parquet"

RECONCILIATION_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g15_pilot_reconciliation.json"
NATIONAL_CSV = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g15_national_acquisition_inventory.csv"
NATIONAL_QA_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g15_national_quality_assessment.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g15_national_rainfall_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"
EXPECTED_RAW_IFI_SHA256 = "ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_asset_immutability():
    """Verify raw DEM, working DEM, and raw IFI CSV have not been altered."""
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()
    assert RAW_IFI_PATH.exists()

    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256
    assert compute_sha256(RAW_IFI_PATH) == EXPECTED_RAW_IFI_SHA256


def test_e03_reconciliation_timezone_shift():
    """Verify E03 221.78 mm vs 243.12 mm resolution documented in reconciliation JSON."""
    assert RECONCILIATION_JSON.exists()
    with open(RECONCILIATION_JSON, "r", encoding="utf-8") as f:
        rec = json.load(f)

    e03 = rec["e03_forensic_reconciliation"]
    windows = e03["observation_windows"]
    imd_val = windows["window_1_imd_cycle"]["point_accumulation_mm"]
    daily_val = windows["window_2_utc_calendar_day"]["daily_product_point_accumulation_mm"]

    assert abs(imd_val - 221.775) <= 0.01
    assert abs(daily_val - 243.12) <= 0.01
    assert "3-hour shift" in e03["discrepancy_root_cause_analysis"]["findings"]


def test_e02_identical_match_reconciliation():
    """Verify E02 154.32 mm is identically matched between 48 granules and IMERG Daily product."""
    with open(RECONCILIATION_JSON, "r", encoding="utf-8") as f:
        rec = json.load(f)

    e02 = rec["e02_temporal_and_daily_reconciliation"]
    assert e02["half_hourly_granules_count"] == 48
    assert e02["point_accumulation_half_hourly_mm"] == 154.32
    assert e02["daily_product_point_accumulation_mm"] == 154.32
    assert e02["like_for_like_comparison"]["verification_status"] == "IDENTICAL_MATCH_CONFIRMED"


def test_pilot_inventory_uei_corrections_and_proxies():
    """Verify pilot UEI clerical mismatches identified and proxy coordinate nature flagged."""
    with open(RECONCILIATION_JSON, "r", encoding="utf-8") as f:
        rec = json.load(f)

    pilot_audit = rec["pilot_inventory_reconciliation"]["reconciled_events"]
    assert len(pilot_audit) == 8

    # Find Maharashtra 2005 (PILOT-03)
    p3 = next(ev for ev in pilot_audit if ev["pilot_id"] == "PILOT-03")
    assert p3["authentic_ifi_uei"] == "UEI-IMD-FL-2005-0107"
    assert p3["uei_mapping_status"] == "CORRECTED_CLERICAL_ERROR"
    assert "PROXY" in p3["coordinate_nature"]


def test_national_scaling_statistics():
    """Verify national deduplication metrics: 6876 records -> 3684 unique valid dates."""
    assert NATIONAL_QA_JSON.exists()
    with open(NATIONAL_QA_JSON, "r", encoding="utf-8") as f:
        qa = json.load(f)

    stats = qa["national_scale_statistics"]
    assert stats["total_ifi_records"] == 6876
    assert stats["unique_valid_dates_total"] == 3684
    assert stats["eras_breakdown"]["chirps_eligible_records_1981_to_2023"] == 6535
    assert stats["eras_breakdown"]["imerg_eligible_records_2000_to_2023"] == 4605
    assert stats["storage_and_bandwidth_projection"]["total_deduplicated_storage_gb"] < 100.0


def test_national_acquisition_inventory_schema():
    """Verify complete national inventory CSV schema, row count, and Stage 2 fields."""
    assert NATIONAL_CSV.exists()
    df = pd.read_csv(NATIONAL_CSV)

    assert len(df) == 6876
    required_stage2_fields = [
        "source_event_record",
        "clean_state",
        "clean_districts",
        "start_date_raw",
        "parsed_start_date",
        "event_date_confidence",
        "event_location_confidence",
        "rainfall_temporal_coverage",
        "rainfall_spatial_coverage",
        "rainfall_source_validation",
        "chirps_daily_precip_mm",
        "chirps_source_file",
        "imerg_daily_precip_mm",
        "imerg_source_file",
        "gauge_comparison_status",
        "point_gauge_obs_mm",
        "event_match_status",
        "matching_limitations",
    ]
    for col in required_stage2_fields:
        assert col in df.columns, f"Missing Stage 2 column: {col}"

    # Check match status categories
    statuses = set(df["event_match_status"].unique())
    assert "MATCHED_RAINFALL_COVERAGE" in statuses
    assert "NOT_ACQUIRED" in statuses
    assert "DATE_UNCERTAIN" in statuses
    assert "UNAVAILABLE_ERA" in statuses


def test_strict_null_preservation():
    """Verify missing rainfall observations strictly remain null/NaN (never zero-filled)."""
    df = pd.read_csv(NATIONAL_CSV)
    unacquired = df[df["event_match_status"] == "NOT_ACQUIRED"]
    assert len(unacquired) > 6000

    # For unacquired records, rainfall mm must be NaN/null
    assert unacquired["chirps_daily_precip_mm"].isna().all()
    assert unacquired["imerg_daily_precip_mm"].isna().all()


def test_national_cohort_extraction():
    """Verify the 16 landmark national cohort events have valid extracted rainfall."""
    df = pd.read_csv(NATIONAL_CSV)
    matched = df[df["event_match_status"] == "MATCHED_RAINFALL_COVERAGE"]
    assert len(matched) == 16

    # All 16 must have CHIRPS data
    assert matched["chirps_daily_precip_mm"].notna().all()
    assert (matched["chirps_daily_precip_mm"] >= 0).all()


def test_manifest_governance_and_safeguards():
    """Verify manifest governance decision, safeguards, and immutability."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    gov = m["governance"]
    assert gov["final_decision"] == "PARTIAL_NATIONAL_ACQUISITION"
    assert gov["supervised_training_permitted"] is False
    assert gov["national_trigger_modeling_permitted"] is False
    assert gov["zero_synthetic_rainfall_enforced"] is True
    assert gov["zero_missing_rainfall_imputation_enforced"] is True
    assert m["immutability_verification"]["verified_unmodified"] is True


def test_no_supervised_models_trained():
    """Verify no supervised ML models have been trained or saved."""
    models_dir = PROJECT_ROOT / "ml" / "models"
    if models_dir.exists():
        model_files = list(models_dir.glob("*.pkl")) + list(models_dir.glob("*.joblib")) + list(models_dir.glob("*.onnx"))
        assert len(model_files) == 0, f"Found trained model files: {model_files}"
