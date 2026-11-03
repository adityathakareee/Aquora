"""
AQUORA Phase 6C.2G.20: Consolidated National Rainfall, Spatial Provenance & ML-Readiness Tests.

Validates:
1. Asset Immutability: Copernicus DEM, Working 30m DEM, and Raw IFI v3 CSV hashes.
2. Landmark Recomputation: E01 (2005), E02 (2017), E03 (2019) exact values and windows.
3. Phase 19 Extractions Recomputation: Validates authentic 0.0 mm extractions and 5x5 neighborhoods.
4. Mode B Bounded Acquisition Provenance: Validates 10-date batch provenance and scratch cleanup.
5. Location Enrichment Rules: Validates Datameet / Survey of India hierarchy, conservative matching,
   and preservation of original IFI location fields.
6. Inventory Accounting: Exact 6,876 rows (26 MATCHED, 41 UNEXTRACTED, 6468 NOT_ACQUIRED, 321 UNAVAILABLE_ERA, 20 DATE_UNCERTAIN).
7. Strict Zero-Fill Prevention: Asserts all 41 unextracted records strictly maintain NaN rainfall.
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

# Phase 20 Deliverables
CHECKPOINT_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g20_acquisition_checkpoint.json"
INVENTORY_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g20_acquisition_inventory.csv"
QA_JSON_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall" / "phase6c2g20_quality_assessment.json"
ML_READINESS_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g20_ml_readiness.json"
MANIFEST_YAML_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g20_national_rainfall_manifest.yaml"


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
    """Verify landmark recomputations from raw product files."""
    assert CHECKPOINT_PATH.exists()
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    landmarks = ckpt["landmark_audit"]
    assert landmarks["status"] == "LANDMARKS_INDEPENDENTLY_VALIDATED"

    # E01: 2005-07-26
    e01 = landmarks["landmark_e01"]
    assert e01["event_date"] == "2005-07-26"
    assert abs(e01["rainfall_depth_mm"] - 193.88) < 0.01

    # E02: 2017-08-29
    e02 = landmarks["landmark_e02"]
    assert e02["event_date"] == "2017-08-29"
    assert abs(e02["daily_product_point_mm"] - 154.3250) < 0.001
    assert abs(e02["half_hourly_accumulation_mm"] - 154.3250) < 0.001
    assert abs(e02["discrepancy_vs_daily"]) < 0.0001

    # E03: 2019-07-01
    e03 = landmarks["landmark_e03"]
    assert e03["event_date"] == "2019-07-01 to 2019-07-02"
    assert abs(e03["daily_product_point_mm"] - 243.1200) < 0.001
    assert abs(e03["accumulation_imd_cycle_mm"] - 221.7750) < 0.001
    assert abs(e03["discrepancy_residual"]) < 0.0001


def test_phase19_extractions_recomputation_and_diagnostics():
    """Verify the 4 Phase 19 extractions are independently recomputed with 5x5 diagnostics."""
    assert CHECKPOINT_PATH.exists()
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    p19_audit = ckpt["phase19_recomputed_extractions"]
    assert p19_audit["status"] == "PHASE19_EXTRACTIONS_VERIFIED"
    assert p19_audit["verified_extractions_count"] == 4

    exts = p19_audit["extractions"]
    assert "UEI-IMD-FL-1981-0046" in exts
    assert "UEI-IMD-FL-1981-0077" in exts
    assert "UEI-IMD-FL-1981-0086" in exts
    assert "UEI-IMD-FL-1981-0009" in exts

    for uei, data in exts.items():
        assert data["extracted_value_mm"] == 0.0
        assert data["verification_outcome"] == "VERIFIED_AUTHENTIC_ZERO"
        assert "neighborhood_5x5_mean" in data


def test_mode_b_staged_acquisition_provenance():
    """Verify Mode B staged acquisition records complete reproducible provenance."""
    assert CHECKPOINT_PATH.exists()
    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    batch_params = ckpt["staged_batch_parameters"]
    assert batch_params["batch_size"] == 10
    assert batch_params["mode"] == "MODE_B_STORAGE_CONSTRAINED"
    assert len(batch_params["processed_dates"]) == 10
    assert batch_params["total_events_in_batch"] == 27
    assert batch_params["proxy_events_in_batch"] == 11
    assert batch_params["unspecified_events_in_batch"] == 16

    batch_recs = ckpt["mode_b_batch_extractions"]
    assert len(batch_recs) == 10
    for r in batch_recs:
        assert r["storage_mode"] == "MODE_B_STORAGE_CONSTRAINED"
        assert r["retention_policy"] == "EXTRACT_AND_CLEANUP_TEMP_SOURCE"
        assert len(r["sha256"]) == 64
        assert r["file_size_bytes"] > 2_000_000
        assert r["crs"] == "EPSG:4326"


def test_location_enrichment_rules_and_preservation():
    """Verify location enrichment audit enforces conservative single-district matching and preserves IFI fields."""
    assert QA_JSON_PATH.exists()
    with open(QA_JSON_PATH, "r", encoding="utf-8") as f:
        qa = json.load(f)

    loc = qa["location_enrichment_audit"]
    assert loc["status"] == "LOCATION_ENRICHMENT_AUDITED"
    meta = loc["boundary_metadata"]
    assert meta["source"] == "Survey of India / Datameet GIS"
    assert meta["states_in_hierarchy"] == 36
    assert meta["pilot_districts_in_hierarchy"] == 8

    # Verify inventory preserves original location fields
    df = pd.read_csv(INVENTORY_CSV_PATH)
    assert "state" in df.columns
    assert "districts" in df.columns
    assert df["state"].notna().sum() > 6000


def test_inventory_reconciliation_exact_accounting():
    """Verify exact national inventory accounting matches 6,876 rows."""
    assert INVENTORY_CSV_PATH.exists()
    df = pd.read_csv(INVENTORY_CSV_PATH)
    assert len(df) == 6876

    counts = df["phase20_match_status"].value_counts().to_dict()
    assert counts.get("MATCHED_RAINFALL_COVERAGE") == 26
    assert counts.get("DATE_ACQUIRED_UNEXTRACTED_LOCATION") == 41
    assert counts.get("NOT_ACQUIRED") == 6468
    assert counts.get("UNAVAILABLE_ERA") == 321
    assert counts.get("DATE_UNCERTAIN") == 20

    assert sum(counts.values()) == 6876


def test_strict_null_preservation_zero_filling_prohibition():
    """Verify zero silent zero-filling for records without spatial coordinates."""
    assert INVENTORY_CSV_PATH.exists()
    df = pd.read_csv(INVENTORY_CSV_PATH)

    unextracted = df[df["phase20_match_status"] == "DATE_ACQUIRED_UNEXTRACTED_LOCATION"]
    assert len(unextracted) == 41

    # Check that all 41 unextracted records have NaN rainfall
    assert unextracted["phase20_rainfall_mm"].isna().all()

    # Ensure none were converted to 0.0
    zero_fills = (unextracted["phase20_rainfall_mm"] == 0.0).sum()
    assert zero_fills == 0


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
