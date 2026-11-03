"""
AQUORA Phase 6C.2G.12: Event Grouping Validation & Rainfall Analysis Readiness Audit Tests.

Validates:
1. Asset immutability: Raw Copernicus DSM, Working DEM, and Raw IFI match exact SHA-256 hashes.
2. Record preservation and one-to-one mapping: every raw UEI is preserved and maps to exactly one provisional group.
3. Mathematical reconciliation: 6,484 groups + 392 merged records == 6,876 source records.
4. Grouping sensitivity bounds: Stricter (6,803) >= Baseline (6,484) >= Looser (6,109).
5. Date anomalies audit: exactly 20 missing start dates and 17 source date format inversions flagged.
6. Rainfall comparison readiness: E02 and E03 reproducible from local files; 6,874 unacquired events flagged.
7. Governance invariants: final decision strictly GROUPING_VALIDATED_FOR_DESCRIPTIVE_USE; supervised training prohibited;
   national rainfall analysis status is BLOCKED_PENDING_NATIONAL_RAINFALL_ACQUISITION.
8. Safety: zero models trained in ml/models/.
"""

import hashlib
import json
from pathlib import Path
import pandas as pd
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
RAW_IFI_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "india_flood_inventory_v3.csv"

DERIVED_PARQUET = PROJECT_ROOT / "data" / "processed" / "phase7" / "events" / "national_historical_flood_records_derived.parquet"
STORM_PARQUET = PROJECT_ROOT / "data" / "processed" / "phase7" / "events" / "national_storm_events_grouped.parquet"

GROUPING_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "events" / "phase6c2g12_grouping_audit.json"
DATE_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "events" / "phase6c2g12_date_quality_audit.json"
RAINFALL_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "events" / "phase6c2g12_rainfall_readiness.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g12_validation_manifest.yaml"
SCHEMA_PATH = PROJECT_ROOT / "ml" / "aquora_ml_feature_schema_v1.json"

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
    """Verify Raw DEM, Working DEM, and Raw IFI have not been modified."""
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()
    assert RAW_IFI_PATH.exists()
    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256
    assert compute_sha256(RAW_IFI_PATH) == EXPECTED_RAW_IFI_SHA256


def test_record_preservation_and_mapping():
    """Verify 1-to-1 preservation of source UEIs and deterministic storm_id mapping."""
    df_der = pd.read_parquet(DERIVED_PARQUET)
    df_stm = pd.read_parquet(STORM_PARQUET)

    assert len(df_der) == 6876
    assert df_der["UEI"].nunique() == 6876
    assert df_der["storm_id"].isna().sum() == 0
    assert df_der["storm_id"].nunique() == 6484

    # Check sum of constituent records in storm table
    assert df_stm["constituent_record_count"].sum() == 6876


def test_mathematical_reconciliation():
    """Verify mathematical reconciliation: 6484 groups + 392 merged == 6876 source records."""
    assert GROUPING_JSON.exists()
    with open(GROUPING_JSON, "r", encoding="utf-8") as f:
        audit = json.load(f)

    rec = audit["mathematical_reconciliation"]
    assert rec["total_source_records"] == 6876
    assert rec["unique_source_ueis"] == 6876
    assert rec["provisional_storm_groups"] == 6484
    assert rec["merged_records_count"] == 392
    assert rec["is_reconciled"] is True


def test_grouping_sensitivity_bounds():
    """Verify sensitivity bounds: Stricter (6,803) >= Baseline (6,484) >= Looser (6,109)."""
    with open(GROUPING_JSON, "r", encoding="utf-8") as f:
        audit = json.load(f)

    sens = audit["grouping_sensitivity_analysis"]
    strict = sens["stricter_same_day_duplicates_only"]
    baseline = sens["baseline_phase6c2g11_provisional_groups"]
    looser = sens["looser_state_and_district_overlap"]

    assert strict == 6803
    assert baseline == 6484
    assert looser == 6109
    assert strict > baseline > looser


def test_date_anomalies_audited_and_flagged():
    """Verify 20 missing start dates and 17 source inversions are recorded with exact counts."""
    assert DATE_JSON.exists()
    with open(DATE_JSON, "r", encoding="utf-8") as f:
        d_audit = json.load(f)

    summ = d_audit["date_audit_summary"]
    assert summ["total_records"] == 6876
    assert summ["missing_date_records_count"] == 20
    assert summ["inverted_source_date_records_count"] == 17
    assert summ["total_date_compromised_records"] == 37
    assert summ["fully_validated_chronological_records"] == 6839

    # Check that raw date strings are preserved in derived parquet
    df_der = pd.read_parquet(DERIVED_PARQUET)
    assert df_der["is_missing_date"].sum() == 20
    assert df_der["is_date_inverted_in_source"].sum() == 17


def test_rainfall_readiness_and_missing_data_constraints():
    """Verify E02 and E03 reproducibility and strict missing rainfall boundaries."""
    assert RAINFALL_JSON.exists()
    with open(RAINFALL_JSON, "r", encoding="utf-8") as f:
        rain = json.load(f)

    e03 = rain["benchmark_event_e03"]
    assert e03["reproducibility_status"] == "FULLY_REPRODUCIBLE_FROM_LOCAL_FILES"
    assert e03["granules_present_count"] == 48
    assert e03["reported_imerg_total_mm"] == 221.78
    assert e03["imd_gauge_benchmark"]["reported_gauge_rainfall_mm"] == 375.2

    e02 = rain["benchmark_event_e02"]
    assert e02["reproducibility_status"] == "FULLY_REPRODUCIBLE_FROM_LOCAL_FILES"

    scope = rain["national_rainfall_readiness_scope"]
    assert scope["events_with_locally_reproducible_rainfall"] == 2
    assert scope["events_with_missing_local_rainfall"] == 6874
    assert scope["unacquired_status"] == "NOT_LOCALLY_ACQUIRED"


def test_manifest_governance_decision():
    """Verify manifest governance decision is strictly GROUPING_VALIDATED_FOR_DESCRIPTIVE_USE."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    gov = m["governance"]
    assert gov["final_decision"] == "GROUPING_VALIDATED_FOR_DESCRIPTIVE_USE"
    assert gov["provisional_grouping_validated"] is True
    assert gov["supervised_training_permitted"] is False
    assert gov["national_rainfall_analysis_status"] == "BLOCKED_PENDING_NATIONAL_RAINFALL_ACQUISITION"
    assert gov["zero_synthetic_labels_enforced"] is True
    assert gov["zero_missing_rainfall_imputation_enforced"] is True


def test_safety_and_zero_models_trained():
    """Verify safety constraint: no model training occurred."""
    models_dir = PROJECT_ROOT / "ml" / "models"
    if models_dir.exists():
        model_files = list(models_dir.glob("*.joblib")) + list(models_dir.glob("*.onnx")) + list(models_dir.glob("*.pt"))
        assert len(model_files) == 0

    assert SCHEMA_PATH.exists()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["schema_version"] == "1.0.0"
