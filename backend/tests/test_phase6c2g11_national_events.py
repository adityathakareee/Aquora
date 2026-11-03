"""
AQUORA Phase 6C.2G.11: National Historical Event Analysis Tests.

Validates:
1. Source DEM immutability (Raw Copernicus DSM and Working DEM match exact hashes).
2. Raw IFI dataset integrity (strictly read-only, matching exact SHA-256 hash).
3. Derived records dataset integrity: 100% preservation (6,876 rows), storm_id assignment,
   missing date flags (20 rows), date inversion flags (17 rows).
4. Grouped storm events consistency: 6,484 unique storm events, sum of constituent UEIs == 6,876.
5. Descriptive summary tables:
   - annual_flood_frequency.csv (1967-2023, sums to 6,876).
   - state_flood_summary.csv (Maharashtra top with 1,012 records; Assam second with 908).
   - mumbai_flood_history.csv (182 records).
6. Rainfall comparison assessment: E02 and E03 valid; unacquired national events flagged; zero-filling prohibited.
7. Data quality report integrity: coordinates 100% missing, reporting bias documented.
8. Manifest governance decision: strictly EVENT_ANALYSIS_READY; supervised ML training strictly prohibited.
"""

from datetime import datetime
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

EVENTS_DIR = PROJECT_ROOT / "data" / "processed" / "phase7" / "events"
DERIVED_PARQUET = EVENTS_DIR / "national_historical_flood_records_derived.parquet"
STORM_PARQUET = EVENTS_DIR / "national_storm_events_grouped.parquet"
ANNUAL_CSV = EVENTS_DIR / "annual_flood_frequency.csv"
STATE_CSV = EVENTS_DIR / "state_flood_summary.csv"
DISTRICT_CSV = EVENTS_DIR / "top_districts_flood_frequency.csv"
MUMBAI_CSV = EVENTS_DIR / "mumbai_flood_history.csv"
DQR_JSON = EVENTS_DIR / "phase6c2g11_data_quality_report.json"
RAINFALL_JSON = EVENTS_DIR / "phase6c2g11_rainfall_comparison_assessment.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g11_national_event_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"
EXPECTED_RAW_IFI_SHA256 = "ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108"


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


def test_raw_ifi_read_only_and_hash():
    """Verify raw IFI file is preserved unmodified with exact checksum."""
    assert RAW_IFI_PATH.exists()
    assert compute_sha256(RAW_IFI_PATH) == EXPECTED_RAW_IFI_SHA256
    assert RAW_IFI_PATH.stat().st_size == 1801579


def test_derived_dataset_integrity_and_record_preservation():
    """Verify derived records table preserves all 6,876 rows, original columns, and flags."""
    assert DERIVED_PARQUET.exists()
    df_derived = pd.read_parquet(DERIVED_PARQUET)

    # Must preserve exactly 6,876 rows
    assert len(df_derived) == 6876

    # Must contain original columns plus derived columns
    assert "UEI" in df_derived.columns
    assert "Start Date" in df_derived.columns
    assert "storm_id" in df_derived.columns
    assert "is_missing_date" in df_derived.columns
    assert "is_date_inverted_in_source" in df_derived.columns

    # Every row must have a non-null storm_id
    assert df_derived["storm_id"].isna().sum() == 0

    # Exactly 20 records flagged with missing dates
    assert df_derived["is_missing_date"].sum() == 20

    # Exactly 17 records flagged with source date inversions
    assert df_derived["is_date_inverted_in_source"].sum() == 17


def test_grouped_storms_consistency():
    """Verify grouped storms table aggregates into 6,484 unique storms without record loss."""
    assert STORM_PARQUET.exists()
    df_storm = pd.read_parquet(STORM_PARQUET)

    assert len(df_storm) == 6484
    assert df_storm["storm_id"].nunique() == 6484

    # Check constituent UEIs sum up to exactly 6,876
    total_constituents = df_storm["constituent_record_count"].sum()
    assert total_constituents == 6876

    # Check that constituent UEIs string unpacks to 6,876 unique UEIs
    all_ueis = []
    for uei_str in df_storm["constituent_ueis"]:
        all_ueis.extend(uei_str.split(";"))
    assert len(all_ueis) == 6876
    assert len(set(all_ueis)) == 6876


def test_descriptive_summaries_accuracy():
    """Verify annual, state, and district summary tables."""
    assert ANNUAL_CSV.exists()
    assert STATE_CSV.exists()
    assert DISTRICT_CSV.exists()
    assert MUMBAI_CSV.exists()

    df_annual = pd.read_csv(ANNUAL_CSV)
    assert df_annual["raw_record_count"].sum() == 6876
    assert df_annual["unique_storm_count"].sum() == 6484
    assert df_annual["year"].min() == 1967
    assert df_annual["year"].max() == 2023

    df_state = pd.read_csv(STATE_CSV)
    assert df_state.iloc[0]["clean_state"] == "Maharashtra"
    assert df_state.iloc[0]["raw_record_count"] == 1012
    assert df_state.iloc[1]["clean_state"] == "Assam"
    assert df_state.iloc[1]["raw_record_count"] == 908

    df_mumbai = pd.read_csv(MUMBAI_CSV)
    assert len(df_mumbai) == 182


def test_rainfall_comparison_assessment():
    """Verify rainfall comparison boundaries: E02/E03 valid; unacquired national events flagged."""
    assert RAINFALL_JSON.exists()
    with open(RAINFALL_JSON, "r", encoding="utf-8") as f:
        rain = json.load(f)

    # E03 check
    e03 = rain["local_imerg_assets"]["event_e03"]
    assert e03["comparison_feasibility"] == "VALID_BENCHMARK_COMPARISON"
    assert e03["half_hour_granules_present"] == 48
    assert e03["imerg_24h_accumulation_mm"] == 221.78
    assert "UEI-IMD-FL-2019-0090" in e03["matched_ifi_ueis"]

    # E02 check
    e02 = rain["local_imerg_assets"]["event_e02"]
    assert e02["comparison_feasibility"] == "VALID_BENCHMARK_COMPARISON"
    assert e02["metadata_present"] is True

    # National unacquired check
    nat = rain["national_rainfall_comparison_scope"]
    assert nat["events_without_locally_acquired_rainfall"] == 6874
    assert nat["feasibility_for_unacquired_events"] == "NOT_LOCALLY_ACQUIRED"
    assert any("Do NOT treat missing historical rainfall observations as zero" in p for p in nat["strict_prohibitions"])


def test_data_quality_report():
    """Verify data quality report records coordinate gaps and reporting bias."""
    assert DQR_JSON.exists()
    with open(DQR_JSON, "r", encoding="utf-8") as f:
        dqr = json.load(f)

    missing = dqr["missing_data_audit"]
    assert missing["latitude_longitude_missing_count"] == 6876
    assert missing["latitude_longitude_missing_pct"] == 100.0
    assert missing["missing_start_dates_count"] == 20

    anomalies = dqr["data_anomalies_and_corrections"]
    assert anomalies["source_date_format_inversions"]["count"] == 17

    bias = dqr["reporting_coverage_bias"]
    assert "increased administrative digitization" in bias["interpretation_warning"]


def test_manifest_and_governance():
    """Verify manifest governance decision is EVENT_ANALYSIS_READY and training is prohibited."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    gov = m["governance"]
    assert gov["final_decision"] == "EVENT_ANALYSIS_READY"
    assert gov["descriptive_analysis_ready"] is True
    assert gov["supervised_training_permitted"] is False
    assert gov["zero_synthetic_labels_enforced"] is True
    assert gov["zero_missing_rainfall_imputation_enforced"] is True

    # Check key findings consistency
    findings = m["key_findings"]
    assert findings["raw_records"] == 6876
    assert findings["grouped_storms"] == 6484
    assert findings["consecutive_slices_merged"] == 392
    assert findings["mumbai_records"] == 182


def test_zero_models_trained():
    """Verify safety constraint: no model training occurred."""
    models_dir = PROJECT_ROOT / "ml" / "models"
    if models_dir.exists():
        model_files = list(models_dir.glob("*.joblib")) + list(models_dir.glob("*.onnx")) + list(models_dir.glob("*.pt"))
        assert len(model_files) == 0
