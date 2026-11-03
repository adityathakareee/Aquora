"""
AQUORA Phase 6C.2G.13: National Rainfall Data Acquisition & Event Matching Tests.

Validates:
1. Asset immutability: Raw Copernicus DSM, Working DEM, and Raw IFI match exact SHA-256 hashes.
2. E03 rainfall revalidation: 48 local granules, exact 221.78 mm reproduction, Santacruz gauge separation.
3. E02 rainfall audit: downgrade to PARTIAL_TEMPORAL_COVERAGE due to single 30-min post-event granule (0.215 mm).
4. Candidate source evaluation: 4 sources evaluated (NASA GPM, IMD, CHIRPS, ERA5-Land).
5. Event-match inventory reconciliation: 6,876 total rows = 2 MATCHED + 2 PARTIAL + 37 DATE_UNCERTAIN + 6,835 NOT_ACQUIRED.
6. Pilot acquisition plan: 8 landmark events across diverse Indian states and regions.
7. Manifest governance decision: strictly PARTIAL_ACQUISITION_READY; supervised training and trigger modeling prohibited.
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

SOURCE_ASSESSMENT_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g13_source_assessment.json"
EVENT_MATCH_CSV = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g13_event_match_inventory.csv"
E02_E03_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g13_e02_e03_revalidation.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g13_rainfall_acquisition_manifest.yaml"
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


def test_e03_revalidation_reproducibility():
    """Verify Event E03 24h accumulation (221.78 mm) reproduced from 48 local HDF5 granules."""
    assert E02_E03_JSON.exists()
    with open(E02_E03_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    e03 = data["event_e03_revalidation"]
    assert e03["status"] == "VALIDATED_BENCHMARK_DELUGE"
    assert e03["granules_present_count"] == 48
    assert abs(e03["recalculated_point_accumulation_mm"] - 221.78) <= 0.01
    assert e03["recalculated_peak_half_hour_rate_mm_hr"] == 32.35
    assert e03["imd_santacruz_gauge_reading_mm"] == 375.2
    assert "reproducible" in e03["reproducibility"].lower()
    assert "point gauge" in e03["point_vs_satellite_explanation"].lower()


def test_e02_downgrade_justification():
    """Verify Event E02 is downgraded to PARTIAL_TEMPORAL_COVERAGE due to single 30-min granule."""
    with open(E02_E03_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    e02 = data["event_e02_revalidation"]
    assert e02["status"] == "DOWNGRADED_TO_PARTIAL_TEMPORAL_COVERAGE"
    assert "trailing dissipation" in e02["downgrade_reason"]
    assert e02["local_granule_accumulation_mm"] == 0.215
    assert e02["raw_granule_sha256"] is not None


def test_candidate_source_evaluation():
    """Verify candidate sources assessment evaluates NASA GPM, IMD, CHIRPS, and ERA5-Land."""
    assert SOURCE_ASSESSMENT_JSON.exists()
    with open(SOURCE_ASSESSMENT_JSON, "r", encoding="utf-8") as f:
        assessment = json.load(f)

    sources = assessment["candidate_sources_evaluated"]
    assert "NASA_GPM_IMERG_FINAL_V07B" in sources
    assert "IMD_GRIDDED_DAILY_RAINFALL" in sources
    assert "CHIRPS_V2_DAILY" in sources
    assert "ERA5_LAND_HOURLY" in sources

    # Check GPM details
    gpm = sources["NASA_GPM_IMERG_FINAL_V07B"]
    assert gpm["spatial_resolution"] == "0.1 degree x 0.1 degree (~10 km x 10 km)"
    assert gpm["coverage_temporal"] == "2000-06-01 to Present"

    # Check IMD details
    imd = sources["IMD_GRIDDED_DAILY_RAINFALL"]
    assert "Pune" in imd["provider"]
    assert "1901" in imd["coverage_temporal"]


def test_event_match_inventory_reconciliation():
    """Verify inventory contains exactly 6,876 rows and strictly reconciles status counts."""
    assert EVENT_MATCH_CSV.exists()
    df_inv = pd.read_csv(EVENT_MATCH_CSV)

    assert len(df_inv) == 6876
    assert df_inv["UEI"].nunique() == 6876

    counts = df_inv["rainfall_match_status"].value_counts().to_dict()
    assert counts.get("MATCHED", 0) == 2
    assert counts.get("PARTIAL_TEMPORAL_COVERAGE", 0) == 2
    assert counts.get("DATE_UNCERTAIN", 0) == 37
    assert counts.get("NOT_ACQUIRED", 0) == 6835

    assert sum(counts.values()) == 6876


def test_pilot_acquisition_plan_landmarks():
    """Verify pilot acquisition plan contains 8 landmark events across diverse Indian regions."""
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    assert m["pilot_events_count"] == 8
    assert len(m["candidate_sources_evaluated"]) == 4


def test_manifest_governance_decision():
    """Verify manifest governance decision is PARTIAL_ACQUISITION_READY and training is prohibited."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    gov = m["governance"]
    assert gov["final_decision"] == "PARTIAL_ACQUISITION_READY"
    assert gov["pilot_plan_established"] is True
    assert gov["supervised_training_permitted"] is False
    assert gov["national_trigger_modeling_permitted"] is False
    assert gov["zero_synthetic_rainfall_enforced"] is True
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
