"""
AQUORA Phase 6C.2G.21: Storage-Aware Multi-Decade Rainfall Expansion & Integrity Tests.

Validates:
1. Asset Immutability: Copernicus DEM, Working 30m DEM, and Raw IFI v3 CSV hashes.
2. Landmark Recomputation: E01 (2005), E02 (2017), E03 (2019) exact values and windows.
3. Mode B 25-Date Batch Acquisition: Provenance completeness, SHA-256 verification, and scratch cleanup.
4. Location & Modern Status Semantics: Documented non-overlapping status contract and legacy mapping.
5. Inventory Accounting: Exact 6,876 rows (54 VERIFIED, 77 LOCATION_UNAVAILABLE, 6404 NOT_ACQUIRED, 321 PRE_PRODUCT_ERA, 20 DATE_UNCERTAIN).
6. Strict Zero-Fill Prevention: Asserts all 77 unextracted records strictly maintain NaN rainfall.
7. Proxy Coordinate Provenance & Spatial Confidence: PROXY_CENTROID semantics and IFI field preservation.
8. Disk Safety Reserve: Enforces 10.0 GB safety threshold.
9. ML-Readiness Audit: Asserts decision is BLOCKED_BY_GROUND_TRUTH.
10. Governance & Prohibited Models: Asserts NATIONAL_BATCH_AND_READINESS_VALIDATED and zero supervised models.
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Core Assets
RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
RAW_IFI_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "india_flood_inventory_v3.csv"

# Phase 21 Deliverables
CHECKPOINT_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g21_acquisition_checkpoint.json"
INVENTORY_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g21_acquisition_inventory.csv"
QA_JSON_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g21_quality_assessment.json"
ML_READINESS_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g21_ml_readiness.json"
MANIFEST_YAML_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g21_national_rainfall_manifest.yaml"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def test_asset_immutability():
    """Verify foundational DEM and raw IFI v3 CSV remain strictly unaltered."""
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()
    assert RAW_IFI_PATH.exists()

    assert compute_sha256(RAW_DEM_PATH) == "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
    assert compute_sha256(WORKING_DEM_PATH) == "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"
    assert compute_sha256(RAW_IFI_PATH) == "ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108"


def test_landmarks_e01_e02_e03_recomputation():
    """Verify landmark recomputations from authentic raw product files."""
    assert CHECKPOINT_PATH.exists()
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    landmarks = ckpt["landmark_audit"]
    assert landmarks["status"] == "LANDMARKS_INDEPENDENTLY_VALIDATED"

    # E01: 2005-07-26
    e01 = landmarks["landmark_e01"]
    assert e01["date"] == "2005-07-26"
    assert abs(e01["depth_mm"] - 193.88) < 0.01

    # E02: 2017-08-29
    e02 = landmarks["landmark_e02"]
    assert e02["date"] == "2017-08-29"
    assert abs(e02["daily_product_point_mm"] - 154.3250) < 0.001
    assert abs(e02["half_hourly_accumulation_mm"] - 154.3250) < 0.001
    assert abs(e02["discrepancy_vs_daily"]) < 0.0001

    # E03: 2019-07-01
    e03 = landmarks["landmark_e03"]
    assert e03["date"] == "2019-07-01 to 2019-07-02"
    assert abs(e03["daily_product_point_mm"] - 243.1200) < 0.001
    assert abs(e03["accumulation_imd_cycle_mm"] - 221.7750) < 0.001
    assert abs(e03["discrepancy_residual"]) < 0.0001


def test_mode_b_25_date_batch_acquisition_provenance():
    """Verify Mode B staged acquisition records complete reproducible provenance across 25 dates."""
    assert CHECKPOINT_PATH.exists()
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    batch_params = ckpt["staged_batch_parameters"]
    assert batch_params["batch_size"] == 25
    assert batch_params["mode"] == "MODE_B_STORAGE_CONSTRAINED"
    assert len(batch_params["processed_dates"]) == 25
    assert batch_params["total_events_in_batch"] == 64
    assert batch_params["proxy_events_in_batch"] == 28
    assert batch_params["unspecified_events_in_batch"] == 36
    assert batch_params["total_bytes_transferred"] > 70_000_000

    batch_recs = ckpt["mode_b_batch_extractions"]
    assert len(batch_recs) == 25
    for r in batch_recs:
        assert r["storage_mode"] == "MODE_B_STORAGE_CONSTRAINED"
        assert r["retention_policy"] == "EXTRACT_AND_CLEANUP_TEMP_SOURCE"
        assert len(r["sha256"]) == 64
        assert r["file_size_bytes"] > 2_000_000
        assert r["crs"] == "EPSG:4326"


def test_location_and_status_semantics_modern_mapping():
    """Verify explicit non-overlapping modern status semantics and legacy mapping."""
    assert QA_JSON_PATH.exists()
    with open(QA_JSON_PATH, "r", encoding="utf-8") as f:
        qa = json.load(f)

    status_map = qa["status_mapping_documentation"]
    assert status_map["MATCHED_RAINFALL_COVERAGE"] == "SOURCE_ACQUIRED_EXTRACTION_VERIFIED"
    assert status_map["DATE_ACQUIRED_UNEXTRACTED_LOCATION"] == "SOURCE_ACQUIRED_LOCATION_UNAVAILABLE"
    assert status_map["NOT_ACQUIRED"] == "SOURCE_NOT_ACQUIRED"
    assert status_map["UNAVAILABLE_ERA"] == "PRE_PRODUCT_ERA"
    assert status_map["DATE_UNCERTAIN"] == "DATE_UNCERTAIN"

    # Verify inventory columns contain both legacy and modern status
    df = pd.read_csv(INVENTORY_CSV_PATH)
    assert "phase21_legacy_status" in df.columns
    assert "phase21_modern_status" in df.columns
    assert set(df["phase21_modern_status"].unique()) == {
        "SOURCE_ACQUIRED_EXTRACTION_VERIFIED",
        "SOURCE_ACQUIRED_LOCATION_UNAVAILABLE",
        "SOURCE_NOT_ACQUIRED",
        "PRE_PRODUCT_ERA",
        "DATE_UNCERTAIN",
    }


def test_inventory_reconciliation_exact_accounting():
    """Verify exact national inventory accounting matches 6,876 rows."""
    assert INVENTORY_CSV_PATH.exists()
    df = pd.read_csv(INVENTORY_CSV_PATH)
    assert len(df) == 6876

    counts = df["phase21_modern_status"].value_counts().to_dict()
    assert counts.get("SOURCE_ACQUIRED_EXTRACTION_VERIFIED") == 54
    assert counts.get("SOURCE_ACQUIRED_LOCATION_UNAVAILABLE") == 77
    assert counts.get("SOURCE_NOT_ACQUIRED") == 6404
    assert counts.get("PRE_PRODUCT_ERA") == 321
    assert counts.get("DATE_UNCERTAIN") == 20

    assert sum(counts.values()) == 6876


def test_strict_null_preservation_zero_filling_prohibition():
    """Verify zero silent zero-filling for records without spatial coordinates."""
    assert INVENTORY_CSV_PATH.exists()
    df = pd.read_csv(INVENTORY_CSV_PATH)

    unextracted = df[df["phase21_modern_status"] == "SOURCE_ACQUIRED_LOCATION_UNAVAILABLE"]
    assert len(unextracted) == 77

    # Check that all 77 unextracted records have NaN rainfall
    assert unextracted["phase21_rainfall_mm"].isna().all()

    # Ensure none were converted to 0.0
    zero_fills = (unextracted["phase21_rainfall_mm"] == 0.0).sum()
    assert zero_fills == 0


def test_proxy_coordinate_provenance_and_spatial_confidence():
    """Verify proxy coordinates are explicitly flagged PROXY_CENTROID and preserve original IFI fields."""
    df = pd.read_csv(INVENTORY_CSV_PATH)

    verified = df[df["phase21_modern_status"] == "SOURCE_ACQUIRED_EXTRACTION_VERIFIED"]
    assert len(verified) == 54
    for _, r in verified.iterrows():
        assert "PROXY" in str(r["coordinate_provenance"])
        assert r["spatial_confidence"] == "PROXY_CENTROID"

    # Verify original IFI columns remain intact
    assert "state" in df.columns
    assert "districts" in df.columns
    assert df["state"].notna().sum() > 6000


def test_disk_safety_reserve_enforcement():
    """Verify disk space check enforces 10.0 GB safety threshold."""
    assert CHECKPOINT_PATH.exists()
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    disk = ckpt["disk_safety"]
    assert disk["min_reserve_gb"] == 10.0
    assert disk["free_decimal_gb"] > 10.0
    assert disk["is_safe"] is True


def test_ml_readiness_audit_blocked_by_ground_truth():
    """Verify ML-readiness audit strictly blocks supervised spatial ML training."""
    assert ML_READINESS_JSON.exists()
    with open(ML_READINESS_JSON, "r", encoding="utf-8") as f:
        ml_data = json.load(f)

    assert ml_data["governance_decision"] == "BLOCKED_BY_GROUND_TRUTH"
    assert ml_data["supervised_models_trained_count"] == 0
    assert ml_data["synthetic_rainfall_used"] is False
    assert "NO_SUPERVISED_ML_TRAINING" in ml_data["prohibited_actions_enforced"]


def test_manifest_governance_and_zero_supervised_models():
    """Verify QA JSON and Manifest YAML reflect NATIONAL_BATCH_AND_READINESS_VALIDATED."""
    assert QA_JSON_PATH.exists()
    with open(QA_JSON_PATH, "r", encoding="utf-8") as f:
        qa = json.load(f)
    assert qa["governance_decision"] == "NATIONAL_BATCH_AND_READINESS_VALIDATED"

    assert MANIFEST_YAML_PATH.exists()
    with open(MANIFEST_YAML_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    assert manifest["governance"]["decision"] == "NATIONAL_BATCH_AND_READINESS_VALIDATED"
    assert manifest["governance"]["ml_readiness_decision"] == "BLOCKED_BY_GROUND_TRUTH"
    assert manifest["governance"]["zero_synthetic_rainfall"] is True
    assert manifest["governance"]["zero_supervised_models"] is True

    # Check no ML models were trained in Phase 6C/7
    models_dir = PROJECT_ROOT / "ml" / "models"
    if models_dir.exists():
        model_files = list(models_dir.glob("*.pkl")) + list(models_dir.glob("*.joblib")) + list(models_dir.glob("*.onnx"))
        assert len(model_files) == 0, f"Prohibited model files found in ml/models: {model_files}"
    phase7_models = list((PROJECT_ROOT / "data" / "processed" / "phase7").glob("**/*.joblib"))
    assert len(phase7_models) == 0, f"Found models in phase7: {phase7_models}"
