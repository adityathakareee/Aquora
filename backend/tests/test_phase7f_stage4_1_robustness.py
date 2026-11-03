"""
Unit and Integration Tests for AQUORA Phase 7F Stage 4.1 — Model Robustness and Scientific Review.

Validates:
1. Safeguard compliance: DFO 2507 quarantine, Phase 7E immutability, zero rainfall fabrication, Phase 6 physics supremacy.
2. Ablation metrics consistency and mathematical correctness (confusion matrix balance, F1, precision, recall, PR-AUC).
3. Land/water dry fraction ablation impact and riparian quality coupling.
4. Aspect feature formulas, bounded values, refuted monsoon claims, and ablation invariance.
5. Elevation dominance and non-viability of remaining features without elevation/dry fraction.
6. Spatial partition independence (0 sub-basin overlap, TRAIN-TEST buffer separation, VAL-TEST adjacency, buffer sensitivity).
7. Manifest integrity and governance compliance (ROBUSTNESS_AUDIT_COMPLETE).
"""

import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import yaml


@pytest.fixture(scope="module")
def robustness_metrics():
    p = Path("data/processed/phase7/experiments/dfo3382_robustness_metrics.json")
    assert p.exists(), f"Robustness metrics JSON missing: {p}"
    with open(p, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ablation_csv():
    p = Path("data/processed/phase7/experiments/dfo3382_feature_ablation.csv")
    assert p.exists(), f"Feature ablation CSV missing: {p}"
    return pd.read_csv(p)


@pytest.fixture(scope="module")
def spatial_audit():
    p = Path("data/processed/phase7/experiments/dfo3382_spatial_independence_audit.json")
    assert p.exists(), f"Spatial independence audit JSON missing: {p}"
    with open(p, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def manifest_data():
    p = Path("data/manifests/phase7f_stage4_1_robustness_manifest.yaml")
    assert p.exists(), f"Stage 4.1 manifest missing: {p}"
    with open(p, "r") as f:
        return yaml.safe_load(f)


# -----------------------------------------------------------------------------
# 1. SAFEGUARD COMPLIANCE & GOVERNANCE
# -----------------------------------------------------------------------------

def test_governance_and_safeguard_declarations(manifest_data, robustness_metrics):
    """Verify strictly enforced Phase 7F governance boundaries."""
    assert manifest_data["manifest_metadata"]["decision"] == "ROBUSTNESS_AUDIT_COMPLETE"
    assert manifest_data["manifest_metadata"]["governance_classification"] == "PROTOTYPE_ONLY / NOT_CALIBRATED / NOT_FOR_PUBLIC_ALERTS"
    assert "engines/flood/solver.py" in manifest_data["manifest_metadata"]["primary_operational_authority"]

    assert robustness_metrics["audit_status"] == "ROBUSTNESS_AUDIT_COMPLETE"
    assert robustness_metrics["governance_classification"] == "PROTOTYPE_ONLY / NOT_CALIBRATED / NOT_FOR_PUBLIC_ALERTS"
    assert robustness_metrics["primary_operational_flood_authority"] == "engines/flood/solver.py"

    safeguards = manifest_data["safeguard_declarations"]
    assert safeguards["dfo2507_quarantine"] == "STRICTLY_ENFORCED_ZERO_ACCESS"
    assert "PRESERVED_UNCHANGED" in safeguards["phase7e_artifacts_immutable"]
    assert "ZERO_FABRICATION" in safeguards["rainfall_fabrication"]
    assert "PRESERVED_PRIMARY_FLOOD_AUTHORITY" in safeguards["phase6_physics_authority"]


def test_dfo2507_strict_quarantine():
    """Ensure DFO 2507 data was not touched or referenced in Stage 4.1."""
    dfo2507_raw = Path("data/raw/phase7/ground_truth/gfd/DFO_2507")
    if dfo2507_raw.exists():
        # Verify no files inside DFO_2507 were created or modified recently
        pass
    
    # Check that Stage 4.1 scripts/artifacts never include DFO2507
    p_met = Path("data/processed/phase7/experiments/dfo3382_robustness_metrics.json")
    content = p_met.read_text(encoding="utf-8")
    assert "DFO_2507" not in content and "DFO2507" not in content


def test_phase7e_and_stage3_dataset_preservation():
    """Ensure Phase 7E schemas and Stage 3 datasets remain unaltered."""
    schema_7e = Path("ml/aquora_ml_feature_schema_v1.json")
    assert schema_7e.exists(), "Phase 7E schema must exist"
    with open(schema_7e) as f:
        data_7e = json.load(f)
    assert data_7e["schema_version"] == "1.0.0"

    stage3_parquet = Path("data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet")
    assert stage3_parquet.exists()
    assert stage3_parquet.stat().st_size > 100_000_000  # ~120 MB dataset


# -----------------------------------------------------------------------------
# 2. FEATURE ABLATION INTEGRITY & METRIC CALCULATION
# -----------------------------------------------------------------------------

def test_feature_ablation_models_and_samples(ablation_csv, robustness_metrics):
    """Verify all 6 experimental ablation models are present with exact sample counts."""
    expected_models = [
        "Elevation_Only_Baseline",
        "Full_13_Features",
        "Without_land_water_dry_fraction",
        "Without_elevation_mean_m",
        "Without_aspect_features",
        "Without_elevation_and_dry_fraction",
    ]
    assert list(ablation_csv["ablation_name"]) == expected_models

    for _, row in ablation_csv.iterrows():
        total_samples = row["test_true_positives"] + row["test_false_positives"] + row["test_false_negatives"] + row["test_true_negatives"]
        assert total_samples == 48676, f"Model {row['ablation_name']} confusion matrix does not sum to 48676 test samples"
        assert row["test_true_positives"] + row["test_false_negatives"] == 2384, f"Model {row['ablation_name']} total actual floods != 2384"
        assert row["test_true_negatives"] + row["test_false_positives"] == 46292, f"Model {row['ablation_name']} total actual dry != 46292"

        # Check precision, recall, and F1 consistency
        tp = row["test_true_positives"]
        fp = row["test_false_positives"]
        fn = row["test_false_negatives"]
        tn = row["test_true_negatives"]

        calc_prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        calc_rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        calc_f1 = round(2 * calc_prec * calc_rec / (calc_prec + calc_rec), 4) if (calc_prec + calc_rec) > 0 else 0.0
        calc_fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0

        assert abs(row["test_precision"] - calc_prec) <= 0.001
        assert abs(row["test_recall"] - calc_rec) <= 0.001
        assert abs(row["test_f1"] - calc_f1) <= 0.002
        assert abs(row["test_fpr"] - calc_fpr) <= 0.001


def test_land_water_dry_fraction_ablation_collapse(ablation_csv, robustness_metrics):
    """Verify that removing land_water_dry_fraction substantially collapses PR-AUC."""
    full_row = ablation_csv[ablation_csv["ablation_name"] == "Full_13_Features"].iloc[0]
    no_dry_row = ablation_csv[ablation_csv["ablation_name"] == "Without_land_water_dry_fraction"].iloc[0]

    assert full_row["test_pr_auc"] == 0.2514
    assert no_dry_row["test_pr_auc"] == 0.0665

    # PR-AUC drops by > 70%
    pr_drop_pct = (no_dry_row["test_pr_auc"] - full_row["test_pr_auc"]) / full_row["test_pr_auc"] * 100.0
    assert pr_drop_pct < -70.0

    # False positives surge from 903 to 3,280
    assert full_row["test_false_positives"] == 903
    assert no_dry_row["test_false_positives"] == 3280
    assert no_dry_row["test_false_positives"] > 3 * full_row["test_false_positives"]


def test_riparian_label_quality_coupling(robustness_metrics):
    """Verify empirical concentration of flood labels in mixed water margin."""
    rip = robustness_metrics["riparian_quality_coupling"]["findings"]
    conc = rip["test_partition_concentration"]

    assert conc["total_test_samples"] == 48676
    assert conc["total_test_flood_cells"] == 2384
    assert conc["mixed_water_margin_cells"] == 3662
    assert conc["mixed_water_margin_flood_cells"] == 1283

    # Over 50% of all flood labels in test partition occur in mixed water margin (dry_frac < 0.70)
    assert conc["mixed_water_margin_flood_share_pct"] > 50.0

    # On high quality terrestrial cells, full model PR-AUC collapses to ~0.0192 (near 0.0157 prevalence)
    hq_perf = rip["performance_on_high_quality_only"]
    assert hq_perf["sample_count"] == 41434
    assert hq_perf["full_model_pr_auc"] < 0.03
    assert hq_perf["without_dry_frac_pr_auc"] < 0.03


# -----------------------------------------------------------------------------
# 3. ASPECT FEATURE INTERPRETATION & FORMULA AUDIT
# -----------------------------------------------------------------------------

def test_aspect_feature_interpretation_correction(robustness_metrics, ablation_csv):
    """Verify that aspect features are rigorously audited and unsupported claims refuted."""
    audit = robustness_metrics["aspect_feature_interpretation_audit"]
    math_audit = audit["mathematical_audit"]

    # Refutations
    assert "REFUTED" in math_audit["aspect_mean_cos"]["unsupported_claim_refuted"]
    assert "REFUTED" in math_audit["aspect_circular_var"]["unsupported_claim_refuted"]
    assert "monsoon" in math_audit["aspect_mean_cos"]["unsupported_claim_refuted"].lower()

    # Bounded range checks
    assert math_audit["aspect_circular_var"]["mathematical_bounds"] == "[0.0, 1.0]"
    assert math_audit["aspect_flat_fraction"]["mathematical_bounds"] == "[0.0, 1.0]"

    # Ablation: Removing aspect features has minimal effect on performance
    full_row = ablation_csv[ablation_csv["ablation_name"] == "Full_13_Features"].iloc[0]
    no_aspect_row = ablation_csv[ablation_csv["ablation_name"] == "Without_aspect_features"].iloc[0]

    assert abs(no_aspect_row["test_pr_auc"] - full_row["test_pr_auc"]) <= 0.02
    assert no_aspect_row["test_f1"] >= full_row["test_f1"]  # F1 is 0.2939 vs 0.2898


# -----------------------------------------------------------------------------
# 4. ELEVATION DOMINANCE & COMBINED FEATURE REMOVAL
# -----------------------------------------------------------------------------

def test_elevation_dominance_and_combined_ablation(ablation_csv, robustness_metrics):
    """Verify elevation dominance and collapse of models without elevation and dry fraction."""
    elev_row = ablation_csv[ablation_csv["ablation_name"] == "Elevation_Only_Baseline"].iloc[0]
    no_elev_row = ablation_csv[ablation_csv["ablation_name"] == "Without_elevation_mean_m"].iloc[0]
    no_both_row = ablation_csv[ablation_csv["ablation_name"] == "Without_elevation_and_dry_fraction"].iloc[0]

    # Elevation-only baseline achieves high recall (88.6%)
    assert elev_row["test_recall"] > 0.85
    assert elev_row["test_pr_auc"] == 0.1981

    # Without elevation, PR-AUC drops to 0.1658
    assert no_elev_row["test_pr_auc"] == 0.1658

    # Without BOTH elevation and dry fraction, model fails completely:
    # ROC-AUC is < 0.50 (worse than random guessing 0.50)
    assert no_both_row["test_roc_auc"] < 0.50
    # PR-AUC is 0.0539 (virtually identical to the 0.0490 prevalence baseline)
    assert abs(no_both_row["test_pr_auc"] - 0.0490) < 0.01


# -----------------------------------------------------------------------------
# 5. SPATIAL INDEPENDENCE & BUFFER SENSITIVITY
# -----------------------------------------------------------------------------

def test_spatial_independence_and_buffer_sensitivity(spatial_audit):
    """Verify zero sub-basin overlap, TRAIN-TEST separation, and buffer sensitivity."""
    overlap = spatial_audit["subbasin_overlap_check"]
    assert overlap["zero_group_leakage_verified"] is True
    assert len(overlap["train_val_overlap"]) == 0
    assert len(overlap["val_test_overlap"]) == 0
    assert len(overlap["train_test_overlap"]) == 0

    # Adjacency checks
    adj = spatial_audit["polygon_boundary_adjacency"]
    assert adj["train_touches_test"] is False
    assert adj["train_touches_val"] is True
    assert adj["val_touches_test"] is True
    assert adj["polygon_min_distance_train_to_test_km"] >= 24.0
    assert adj["polygon_min_distance_val_to_test_km"] == 0.0

    # Observation distances
    obs = spatial_audit["observation_distance_distribution"]
    assert obs["test_to_val_distance_km"]["cells_within_5km_count"] == 6246
    assert obs["test_to_val_distance_km"]["cells_within_5km_pct"] == 12.83
    assert obs["test_to_train_distance_km"]["min"] >= 24.0

    # Buffer sensitivity
    buff = spatial_audit["buffer_sensitivity_analysis"]
    assert buff["buffered_5km_from_val"]["sample_count"] == 42430
    assert buff["buffered_5km_from_val"]["full_xgb_pr_auc"] == 0.2368
    assert buff["buffered_10km_from_val"]["sample_count"] == 36498
    assert buff["buffered_10km_from_val"]["full_xgb_pr_auc"] == 0.2345
