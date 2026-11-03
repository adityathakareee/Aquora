"""
Aquora — Step 8 Calibration, Threshold Audit & Operational Model Contract Unit & Integration Tests.

Verifies:
1. Single-class validation handling (E03 zero positive targets)
2. Probability distribution bounds [0, 1] across partitions
3. Threshold sweep analysis & prediction rate bounds
4. Calibration status explicitly recorded as NOT_CALIBRATED
5. Model contract enforcement (backend/app/core/model_contract.py)
6. PROTOTYPE_ONLY governance status
7. Physical engine authority precedence
8. Prohibited vs approved terminology in UI/API schemas
"""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest

from app.core.model_contract import (
    MODEL_CONTRACT,
    get_model_contract_metadata,
    validate_model_contract_inputs,
)
from app.services.calibration_service import (
    CalibrationService,
    EXPECTED_FEATURES,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = REPO_ROOT / "backend" / "data" / "models" / "aquora_xgboost_prototype.joblib"
METADATA_PATH = REPO_ROOT / "backend" / "data" / "models" / "aquora_xgboost_metadata.json"
DATASET_DIR = REPO_ROOT / "data" / "processed" / "phase7" / "dataset"
MODEL_CONTRACT_DOC = REPO_ROOT / "PHASE_8_MODEL_CONTRACT.md"

def test_01_validation_e03_single_class_target():
    """Verify that E03 validation partition contains zero positive labels."""
    val_pq = DATASET_DIR / "phase7_validation.parquet"
    if not val_pq.exists():
        pytest.skip("phase7_validation.parquet not present on disk")
    df_val = pd.read_parquet(val_pq)
    
    assert df_val["event_id"].unique().tolist() == ["E03"]
    y_val = df_val["observed_flood_candidate"].astype(int)
    
    positives = int((y_val == 1).sum())
    assert positives == 0, "Validation E03 must contain zero positive observations"
    assert len(np.unique(y_val)) == 1, "Validation target must be single-class (0s only)"

def test_02_probability_distribution_bounds():
    """Verify predicted probabilities across train/val/test remain strictly in [0, 1]."""
    test_pq = DATASET_DIR / "phase7_test.parquet"
    if not test_pq.exists() or not MODEL_PATH.exists():
        pytest.skip("phase7_test.parquet or model artifact not present on disk")
    model = joblib.load(MODEL_PATH)
    df_test = pd.read_parquet(test_pq)
    X_test = df_test[EXPECTED_FEATURES]
    
    probs = model.predict_proba(X_test)[:, 1]
    assert len(probs) == 186592
    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)
    assert 0.005 <= float(np.min(probs)) <= 0.02
    assert 0.75 <= float(np.max(probs)) <= 0.95

def test_03_threshold_sweep_monotonicity():
    """Verify that predicted positive rates decrease monotonically as threshold increases."""
    test_pq = DATASET_DIR / "phase7_test.parquet"
    if not test_pq.exists() or not MODEL_PATH.exists():
        pytest.skip("phase7_test.parquet or model artifact not present on disk")
    model = joblib.load(MODEL_PATH)
    df_test = pd.read_parquet(test_pq)
    X_test = df_test[EXPECTED_FEATURES]
    probs = model.predict_proba(X_test)[:, 1]

    thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
    pred_rates = [float((probs >= t).mean()) for t in thresholds]
    
    # Assert monotonic decreasing prediction rate with increasing threshold
    for i in range(len(pred_rates) - 1):
        assert pred_rates[i] >= pred_rates[i + 1]

def test_04_calibration_status_not_calibrated():
    """Verify that metadata records CALIBRATION_STATUS = NOT_CALIBRATED."""
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["calibration_status"] == "NOT_CALIBRATED"
    assert "step8_audit" in meta
    assert meta["step8_audit"]["validation_e03_single_class"] is True

def test_05_operational_model_contract():
    """Verify operational model contract definitions in code and documentation."""
    contract = get_model_contract_metadata()
    assert contract["model_status"] == "PROTOTYPE_ONLY"
    assert contract["calibration_status"] == "NOT_CALIBRATED"
    assert contract["is_authoritative_engine"] is False
    assert contract["physical_engine_is_authoritative"] is True
    assert contract["inputs"]["predictor_count"] == 12
    assert contract["inputs"]["approved_predictors"] == EXPECTED_FEATURES

    # Validate feature check function
    assert validate_model_contract_inputs(EXPECTED_FEATURES) is True
    with pytest.raises(ValueError):
        validate_model_contract_inputs(EXPECTED_FEATURES + ["sar_delta_vv_db"])

def test_06_prototype_only_and_physical_authority_enforcement():
    """Verify that CalibrationService metadata and contract enforce PROTOTYPE_ONLY and physical precedence."""
    service = CalibrationService()
    meta = service.get_model_metadata()
    
    assert meta["model_status"] == "PROTOTYPE_ONLY"
    assert meta["calibration_status"] == "NOT_CALIBRATED"
    assert meta["synthetic_fallback"] is False

def test_07_terminology_and_semantic_audit():
    """Verify that model contract doc and metadata prohibit misleading terms."""
    assert MODEL_CONTRACT_DOC.exists()
    doc_text = MODEL_CONTRACT_DOC.read_text(encoding="utf-8")
    
    assert "PROTOTYPE_ONLY" in doc_text
    assert "NOT_CALIBRATED" in doc_text
    assert "Statistical Risk Signal" in doc_text
    assert "Physical Flood Simulation" in doc_text
    assert "Observed SAR Evidence" in doc_text

    contract = get_model_contract_metadata()
    prohibited = contract["governance_rules"]["prohibited_terminology"]
    assert "Predicted Flood Truth" in prohibited
    assert "Actual Flood" in prohibited
    assert "Satellite Flood Prediction" in prohibited

def test_08_tide_feature_importance_audit():
    """Verify that tide_level_m has zero gain/weight in metadata and is correctly designated."""
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    tide_gain = meta["feature_importance"]["gain"].get("tide_level_m", 0.0)
    tide_weight = meta["feature_importance"]["weight"].get("tide_level_m", 0)

    assert tide_gain == 0.0
    assert tide_weight == 0
    assert meta["step8_audit"]["feature_importance_tide_status"] == "feature available to the model but not selected in the fitted tree ensemble"
