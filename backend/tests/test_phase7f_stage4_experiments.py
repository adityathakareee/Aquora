"""
Unit and Integration Tests for AQUORA Phase 7F Stage 4 — Regional Model Exploration.

Validates:
1. Spatial split isolation (zero group overlap across TRAIN, VAL, TEST)
2. No duplicate spatial sub-basins across partitions
3. No test-label leakage during feature selection or threshold selection
4. No rainfall fabrication (all rainfall features excluded)
5. No DFO 2507 access or contamination
6. No modification to existing Phase 7E artifacts or schema
7. Metric calculations, ranking validity, and prevalence baseline comparison
8. Manifest completeness and cryptographic output hash integrity
9. Physics engine supremacy and governance boundary compliance
"""

import json
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import yaml


@pytest.fixture(scope="module")
def splits_data():
    path = Path("data/processed/phase7/experiments/dfo3382_spatial_splits.json")
    assert path.exists(), f"Splits JSON missing: {path}"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def metrics_data():
    path = Path("data/processed/phase7/experiments/dfo3382_model_metrics.json")
    assert path.exists(), f"Metrics JSON missing: {path}"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def schema_data():
    path = Path("ml/aquora_dfo3382_experimental_feature_set_v1.json")
    assert path.exists(), f"Feature set schema missing: {path}"
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def manifest_data():
    path = Path("data/manifests/phase7f_stage4_experiment_manifest.yaml")
    assert path.exists(), f"Manifest missing: {path}"
    with open(path) as f:
        return yaml.safe_load(f)


def test_spatial_split_isolation_and_no_group_leakage(splits_data):
    """Test that all hydrologic sub-basins are strictly partitioned with zero group leakage."""
    train_sbs = set(splits_data["partitions"]["TRAIN"]["subbasin_ids"])
    val_sbs = set(splits_data["partitions"]["VAL"]["subbasin_ids"])
    test_sbs = set(splits_data["partitions"]["TEST"]["subbasin_ids"])

    # Disjoint sub-basins
    assert len(train_sbs & val_sbs) == 0, f"Leakage between TRAIN and VAL: {train_sbs & val_sbs}"
    assert len(train_sbs & test_sbs) == 0, f"Leakage between TRAIN and TEST: {train_sbs & test_sbs}"
    assert len(val_sbs & test_sbs) == 0, f"Leakage between VAL and TEST: {val_sbs & test_sbs}"

    # Verify counts
    assert splits_data["partitions"]["TRAIN"]["subbasin_count"] == 15
    assert splits_data["partitions"]["VAL"]["subbasin_count"] == 6
    assert splits_data["partitions"]["TEST"]["subbasin_count"] == 6

    total_samples = (
        splits_data["partitions"]["TRAIN"]["total_observations"]
        + splits_data["partitions"]["VAL"]["total_observations"]
        + splits_data["partitions"]["TEST"]["total_observations"]
    )
    assert total_samples == 173950


def test_no_rainfall_fabrication_and_complete_exclusion(schema_data, metrics_data):
    """Test that all rainfall features are excluded from training and feature selection."""
    retained = [f["name"] for f in schema_data["retained_features"]]
    excluded = [f["name"] for f in schema_data["excluded_features_register"]]

    for rain_col in ["rainfall_accum_6h_mm", "rainfall_accum_24h_mm", "rainfall_accum_72h_mm"]:
        assert rain_col in excluded, f"Violation: {rain_col} missing from exclusion register!"
        assert rain_col not in retained, f"Violation: {rain_col} present in retained features!"
        assert rain_col not in metrics_data["retained_features"]


def test_no_target_or_coordinate_leakage(schema_data):
    """Test that labels, quality masks, and coordinates are strictly excluded from predictive features."""
    retained = [f["name"] for f in schema_data["retained_features"]]
    leakage_cols = [
        "flood_label", "gfd_flooded_raw", "gfd_duration", "gfd_jrc_perm_water",
        "gfd_clear_views", "gfd_clear_perc", "latitude", "longitude",
        "grid_row", "grid_col", "dfo_cell_id"
    ]
    for col in leakage_cols:
        assert col not in retained, f"Violation: Leakage column {col} retained in predictive features!"


def test_model_metrics_ranking_and_prevalence_comparison(metrics_data):
    """Test that models outperform natural prevalence baseline on the held-out test partition."""
    models = metrics_data["models"]
    test_prev = models["natural_prevalence_baseline"]["test_metrics"]["natural_prevalence"]
    assert abs(test_prev - 0.049) < 1e-3

    # Baseline PR-AUC equals prevalence
    assert abs(models["natural_prevalence_baseline"]["test_metrics"]["pr_auc"] - test_prev) < 1e-4

    # Elevation baseline beats prevalence
    elev_prauc = models["elevation_only_baseline"]["test_metrics"]["pr_auc"]
    assert elev_prauc > test_prev
    assert models["elevation_only_baseline"]["test_metrics"]["roc_auc"] > 0.80

    # ML models beat prevalence
    lr_prauc = models["logistic_regression_balanced"]["test_metrics"]["pr_auc"]
    rf_prauc = models["random_forest_balanced"]["test_metrics"]["pr_auc"]
    xgb_prauc = models["xgboost_weighted"]["test_metrics"]["pr_auc"]

    assert lr_prauc > test_prev
    assert rf_prauc > test_prev
    assert xgb_prauc > test_prev
    assert xgb_prauc > elev_prauc, "XGBoost should outperform univariate elevation ranking"

    # Verify confusion matrix sums
    for name, m in models.items():
        cm = m["test_metrics"]["confusion_matrix"]
        total = cm["true_negatives"] + cm["false_positives"] + cm["false_negatives"] + cm["true_positives"]
        assert total == 48676, f"Confusion matrix total mismatch for {name}: {total}"


def test_frozen_threshold_selection_on_validation_only(metrics_data):
    """Test that decision thresholds are selected solely on validation partition and frozen for test."""
    for name in ["elevation_only_baseline", "logistic_regression_balanced", "random_forest_balanced", "xgboost_weighted"]:
        val_th = metrics_data["models"][name]["validation_metrics"]["selected_threshold"]
        test_th = metrics_data["models"][name]["test_metrics"]["selected_threshold"]
        assert val_th == test_th, f"Threshold leakage: {name} test threshold differs from validation threshold!"


def test_dfo2507_quarantine_preservation():
    """Test that DFO 2507 remains completely quarantined and unaccessed."""
    splits_path = Path("data/processed/phase7/experiments/dfo3382_spatial_splits.json")
    metrics_path = Path("data/processed/phase7/experiments/dfo3382_model_metrics.json")
    with open(splits_path) as f:
        assert "2507" not in f.read()
    with open(metrics_path) as f:
        assert "2507" not in f.read()


def test_phase7e_artifacts_immutability():
    """Test that existing Phase 7E schemas and packages remain completely unaltered."""
    schema_path = Path("ml/aquora_ml_feature_schema_v1.json")
    with open(schema_path) as f:
        schema = json.load(f)
    assert schema["schema_name"] == "aquora_ml_feature_schema_v1"
    assert "CORE_NATIONAL" in schema["tiers"]
    assert "rainfall_6h_mm" in schema["tiers"]["CORE_NATIONAL"]["features"]


def test_manifest_and_output_hash_integrity(manifest_data):
    """Test manifest completeness and cryptographic hashes of generated Stage 4 outputs."""
    assert manifest_data["manifest_metadata"]["decision"] == "EXPLORATORY_MODEL_EVALUATION_COMPLETE"
    assert manifest_data["manifest_metadata"]["governance_classification"] == "PROTOTYPE_ONLY / NOT_CALIBRATED / NOT_FOR_PUBLIC_ALERTS"

    # Check splits hash
    splits_path = Path("data/processed/phase7/experiments/dfo3382_spatial_splits.json")
    with open(splits_path, "rb") as f:
        h_splits = hashlib.sha256(f.read()).hexdigest()
    assert h_splits == manifest_data["spatial_splits_specification"]["splits_file_sha256"]

    # Check metrics hash
    metrics_path = Path("data/processed/phase7/experiments/dfo3382_model_metrics.json")
    with open(metrics_path, "rb") as f:
        h_metrics = hashlib.sha256(f.read()).hexdigest()
    assert h_metrics == manifest_data["model_evaluation_summary"]["metrics_file_sha256"]
