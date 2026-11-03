"""
AQUORA Phase 7F Stage 4 — Regional Model Exploration Pipeline
Authoritative, reproducible experimental model evaluation for DFO 3382 Mahanadi Dataset.

Governance & Safeguards:
- Single-event diagnostic study; NOT operational deployment or public alert forecasting.
- Spatial block evaluation grouped by HydroBASINS Level 8 sub-basins (zero group leakage).
- All thresholds selected solely on validation partition and frozen before test evaluation.
- Zero rainfall fabrication; unobserved precipitation preserved as missing/excluded.
- Phase 7E artifacts, schemas, and models preserved completely unchanged.
- DFO 2507 holdout quarantine strictly preserved (zero access).
- Phase 6 deterministic 2D shallow water physics engine remains the primary flood authority.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    brier_score_loss,
)
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_phase7f_stage4_experiments")

# -----------------------------------------------------------------------------
# 1. SPATIAL SPLIT DEFINITION
# -----------------------------------------------------------------------------

def create_spatial_splits(df_m: pd.DataFrame) -> dict:
    """Partitions the 27 Mahanadi sub-basins with valid DEM into 3 disjoint geographic partitions:
    - TRAIN: Western Upper Approach Corridor (15 sub-basins, centroid lon < 84.8°E)
    - VAL: Central Mid-Reach Valley (6 sub-basins, 84.8°E <= centroid lon < 85.5°E)
    - TEST: Eastern Delta Inundation Corridor (6 sub-basins, centroid lon >= 85.5°E)
    """
    sb_cents = df_m.groupby("subbasin_id_lev08")["longitude"].mean().to_dict()
    
    def assign_partition(sb_id):
        c = sb_cents[sb_id]
        if c < 84.8:
            return "TRAIN"
        elif c < 85.5:
            return "VAL"
        else:
            return "TEST"
            
    df_m["spatial_partition"] = df_m["subbasin_id_lev08"].map(assign_partition)
    
    split_info = {
        "strategy": "HYDROLOGIC_SUBBASIN_SPATIAL_BLOCKING",
        "description": "Disjoint hydrologic sub-basins partitioned by longitudinal drainage corridor",
        "zero_group_leakage": True,
        "partitions": {}
    }
    
    for part in ["TRAIN", "VAL", "TEST"]:
        sub = df_m[df_m["spatial_partition"] == part]
        sb_list = sorted([int(x) for x in sub["subbasin_id_lev08"].unique()])
        n_flood = int(sub["flood_label"].sum())
        n_dry = int((sub["flood_label"] == 0).sum())
        tot = len(sub)
        prev = (n_flood / tot) * 100.0 if tot > 0 else 0.0
        
        split_info["partitions"][part] = {
            "subbasin_count": len(sb_list),
            "subbasin_ids": sb_list,
            "total_observations": tot,
            "verified_flood_count": n_flood,
            "verified_dry_count": n_dry,
            "natural_prevalence_percent": round(prev, 4),
            "min_longitude": round(float(sub["longitude"].min()), 4),
            "max_longitude": round(float(sub["longitude"].max()), 4),
            "min_latitude": round(float(sub["latitude"].min()), 4),
            "max_latitude": round(float(sub["latitude"].max()), 4),
        }
    
    return split_info

# -----------------------------------------------------------------------------
# 2. FEATURE SELECTION SPECIFICATION
# -----------------------------------------------------------------------------

RETAINED_FEATURES = [
    "elevation_mean_m",
    "slope_mean_deg",
    "twi_mean",
    "aspect_mean_cos",
    "aspect_mean_sin",
    "aspect_circular_var",
    "aspect_flat_fraction",
    "plan_curvature_mean",
    "flow_accum_log10_max",
    "dist_to_river_mean_m",
    "dist_to_distributary_min_m",
    "strahler_order_max",
    "land_water_dry_fraction",
]

FEATURE_RATIONALE = {
    "elevation_mean_m": "Primary gravitational potential; floodwaters accumulate in topographic minima.",
    "slope_mean_deg": "Hydraulic gradient driving runoff velocity; flat delta terrain (< 1.5°) impedes rapid drainage.",
    "twi_mean": "Steady-state Topographic Wetness Index ln(a/tan(beta)) indicating natural zones of water convergence.",
    "aspect_mean_cos": "North-South directional orientation of hillslopes relative to monsoonal atmospheric inflow.",
    "aspect_mean_sin": "East-West directional orientation of terrain facets.",
    "aspect_circular_var": "Directional dispersion of topography [0=collinear, 1=isotropic flat/chaotic plain].",
    "aspect_flat_fraction": "Proportion of completely flat sub-pixel cells (aspect = -1) characteristic of fluvial floodplains.",
    "plan_curvature_mean": "Transverse flow convergence (+) into natural depressions versus divergent convex ridges (-).",
    "flow_accum_log10_max": "Order-of-magnitude upstream contributing cells capturing regional drainage concentration.",
    "dist_to_river_mean_m": "Euclidean proximity to natural HydroRIVERS stream network.",
    "dist_to_distributary_min_m": "Euclidean distance to active delta distributary branches downstream of Naraj bifurcation.",
    "strahler_order_max": "Stream hierarchy distinguishing headwater tributaries from trunk carrying discharge.",
    "land_water_dry_fraction": "Proportion of dry terrestrial land within DFO cell; accounts for sub-pixel riparian boundaries."
}

EXCLUSION_REGISTER = {
    "rainfall_accum_6h_mm": "UNAVAILABLE: No retrospective 6-hour rainfall observed locally for DFO 3382.",
    "rainfall_accum_24h_mm": "UNAVAILABLE: No retrospective daily precipitation observed locally for DFO 3382.",
    "rainfall_accum_72h_mm": "UNAVAILABLE: No retrospective antecedent rainfall observed locally for DFO 3382.",
    "elevation_std_m": "HIGH_MULTICOLLINEARITY: r = 0.958 with slope_mean_deg; redundant sub-pixel slope proxy.",
    "elevation_min_m": "EXTREME_COLLINEARITY: r = 0.999 with elevation_mean_m.",
    "elevation_max_m": "EXTREME_COLLINEARITY: r = 0.999 with elevation_mean_m.",
    "elevation_median_m": "EXTREME_COLLINEARITY: r = 0.999 with elevation_mean_m.",
    "profile_curvature_mean": "HIGH_MULTICOLLINEARITY: r = -0.969 with elevation_mean_m in regional mosaic.",
    "flow_accum_log10_mean": "REDUNDANCY: Collinear with flow_accum_log10_max; peak flow accumulation is more physically diagnostic.",
    "dist_to_river_min_m": "REDUNDANCY: Collinear with dist_to_river_mean_m.",
    "strahler_order_rep": "REDUNDANCY: Collinear with strahler_order_max.",
    "historical_flood_frequency": "LEAKAGE_RISK: Encodes historical labels across multiple years; violates single-event independence.",
    "dfo_cell_id": "IDENTIFIER: Non-predictive spatial hash.",
    "grid_row": "COORDINATE_LEAKAGE: Artificial spatial grid coordinate.",
    "grid_col": "COORDINATE_LEAKAGE: Artificial spatial grid coordinate.",
    "latitude": "COORDINATE_MEMORIZATION: Would induce spatial memorization rather than physical feature learning.",
    "longitude": "COORDINATE_MEMORIZATION: Would induce spatial memorization rather than physical feature learning.",
    "gfd_flooded_raw": "TARGET_LEAKAGE: Direct raw sensor observation used to construct label.",
    "gfd_duration": "TARGET_LEAKAGE: Encodes flood duration.",
    "gfd_clear_views": "QUALITY_METRIC: Used strictly for observation filtering, not hazard prediction.",
    "gfd_clear_perc": "QUALITY_METRIC: Optical view fraction used for quality filtering.",
    "gfd_jrc_perm_water": "TARGET_LEAKAGE: Permanent water mask used for ground truth exclusion."
}

# -----------------------------------------------------------------------------
# 3. THRESHOLD OPTIMIZATION (VALIDATION ONLY)
# -----------------------------------------------------------------------------

def select_best_threshold(y_true, y_probs) -> float:
    """Finds decision threshold maximizing F1 on validation set."""
    best_th = 0.5
    best_f1 = -1.0
    for th in np.linspace(0.05, 0.95, 91):
        preds = (y_probs >= th).astype(int)
        f1 = f1_score(y_true, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_th = float(th)
    return best_th

# -----------------------------------------------------------------------------
# 4. METRIC COMPUTATION ENGINE
# -----------------------------------------------------------------------------

def compute_model_metrics(y_true, y_probs, threshold: float) -> dict:
    """Computes comprehensive binary classification and ranking metrics."""
    preds = (y_probs >= threshold).astype(int)
    
    roc_auc = float(roc_auc_score(y_true, y_probs)) if len(np.unique(y_true)) > 1 else 0.5
    pr_auc = float(average_precision_score(y_true, y_probs)) if len(np.unique(y_true)) > 1 else 0.0
    prec = float(precision_score(y_true, preds, zero_division=0))
    rec = float(recall_score(y_true, preds, zero_division=0))
    f1 = float(f1_score(y_true, preds, zero_division=0))
    brier = float(brier_score_loss(y_true, y_probs))
    
    cm = confusion_matrix(y_true, preds)
    tn, fp, fn, tp = [int(x) for x in cm.ravel()]
    
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    prev = float(y_true.mean())
    
    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "natural_prevalence": round(prev, 4),
        "pr_auc_over_prevalence_ratio": round(pr_auc / prev, 2) if prev > 0 else 1.0,
        "selected_threshold": round(threshold, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": {
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp,
            "total_samples": len(y_true)
        }
    }

# -----------------------------------------------------------------------------
# 5. MAIN EXPERIMENT PIPELINE
# -----------------------------------------------------------------------------

def run_stage4_experiments():
    t_start = time.time()
    logger.info("Initializing AQUORA Phase 7F Stage 4 Regional Model Exploration Pipeline...")

    # Paths
    dataset_path = Path("data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet")
    exp_dir = Path("data/processed/phase7/experiments")
    model_dir = exp_dir / "models"
    exp_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    out_splits = exp_dir / "dfo3382_spatial_splits.json"
    out_metrics = exp_dir / "dfo3382_model_metrics.json"
    out_feature_imp = exp_dir / "dfo3382_feature_importance.csv"
    out_errors = exp_dir / "dfo3382_error_analysis.csv"
    out_schema = Path("ml/aquora_dfo3382_experimental_feature_set_v1.json")

    # 1. Load Dataset & Filter to Valid Mahanadi Basin
    logger.info(f"Loading master dataset from {dataset_path}...")
    df = pd.read_parquet(dataset_path)
    logger.info(f"Master dataset loaded: {df.shape[0]:,} rows x {df.shape[1]} columns")

    valid_mask = df["in_mahanadi_basin"] & (~df["elevation_mean_m"].isna())
    df_m = df[valid_mask].copy().reset_index(drop=True)
    logger.info(f"Filtered to Mahanadi Basin with valid DEM coverage: {len(df_m):,} samples ({df_m['flood_label'].sum():,} flood cells, {df_m['flood_label'].mean()*100:.3f}% prevalence)")

    # 2. Establish Spatial Splits
    logger.info("Establishing hydrologic sub-basin spatial partitions...")
    split_info = create_spatial_splits(df_m)
    with open(out_splits, "w") as f:
        json.dump(split_info, f, indent=2)
    logger.info(f"Spatial splits saved to {out_splits}")

    train_df = df_m[df_m["spatial_partition"] == "TRAIN"].copy().reset_index(drop=True)
    val_df = df_m[df_m["spatial_partition"] == "VAL"].copy().reset_index(drop=True)
    test_df = df_m[df_m["spatial_partition"] == "TEST"].copy().reset_index(drop=True)

    logger.info(f"TRAIN partition: {len(train_df):,} samples, {train_df['flood_label'].sum():,} flood cells ({train_df['flood_label'].mean()*100:.3f}%)")
    logger.info(f"VAL partition:   {len(val_df):,} samples, {val_df['flood_label'].sum():,} flood cells ({val_df['flood_label'].mean()*100:.3f}%)")
    logger.info(f"TEST partition:  {len(test_df):,} samples, {test_df['flood_label'].sum():,} flood cells ({test_df['flood_label'].mean()*100:.3f}%)")

    # 3. Export Feature Schema & Register
    logger.info(f"Writing experimental feature contract to {out_schema}...")
    schema_spec = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_name": "aquora_dfo3382_experimental_feature_set_v1",
        "version": "1.0.0",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "governance": {
            "status": "EXPERIMENTAL_FEATURE_SET",
            "study_event": "DFO_3382_MAHANADI_2008",
            "target_resolution": "Native DFO ~250m",
            "primary_operational_authority": "engines/flood/solver.py",
            "phase7e_model_status": "PRESERVED_UNCHANGED"
        },
        "retained_features_count": len(RETAINED_FEATURES),
        "retained_features": [
            {"name": k, "rationale": v} for k, v in FEATURE_RATIONALE.items()
        ],
        "excluded_features_count": len(EXCLUSION_REGISTER),
        "excluded_features_register": [
            {"name": k, "exclusion_reason": v} for k, v in EXCLUSION_REGISTER.items()
        ]
    }
    with open(out_schema, "w") as f:
        json.dump(schema_spec, f, indent=2)

    # 4. Prepare Feature Matrices
    X_train = train_df[RETAINED_FEATURES].values
    y_train = train_df["flood_label"].values
    
    X_val = val_df[RETAINED_FEATURES].values
    y_val = val_df["flood_label"].values
    
    X_test = test_df[RETAINED_FEATURES].values
    y_test = test_df["flood_label"].values

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    all_metrics = {
        "event_id": "DFO_3382",
        "evaluation_strategy": "SPATIALLY_BLOCKED_SUBBASINS",
        "retained_feature_count": len(RETAINED_FEATURES),
        "retained_features": RETAINED_FEATURES,
        "models": {}
    }

    # -------------------------------------------------------------------------
    # MODEL 1: NATURAL PREVALENCE BASELINE
    # -------------------------------------------------------------------------
    logger.info("Evaluating Model 1: Natural Prevalence Baseline...")
    train_prev = float(y_train.mean())
    val_probs_prev = np.full(len(y_val), train_prev)
    test_probs_prev = np.full(len(y_test), train_prev)
    
    all_metrics["models"]["natural_prevalence_baseline"] = {
        "description": "Uninformed baseline assigning constant training prevalence probability",
        "validation_metrics": compute_model_metrics(y_val, val_probs_prev, threshold=train_prev),
        "test_metrics": compute_model_metrics(y_test, test_probs_prev, threshold=train_prev)
    }

    # -------------------------------------------------------------------------
    # MODEL 2: ELEVATION-ONLY RANKING BASELINE
    # -------------------------------------------------------------------------
    logger.info("Evaluating Model 2: Elevation-Only Ranking Baseline...")
    # Normalize negative elevation to [0, 1] ranking score: lower elevation -> higher flood score
    elev_idx = RETAINED_FEATURES.index("elevation_mean_m")
    val_elev = val_df["elevation_mean_m"].values
    test_elev = test_df["elevation_mean_m"].values
    
    val_elev_norm = (val_elev.max() - val_elev) / (val_elev.max() - val_elev.min() + 1e-6)
    test_elev_norm = (test_elev.max() - test_elev) / (test_elev.max() - test_elev.min() + 1e-6)
    
    elev_best_th = select_best_threshold(y_val, val_elev_norm)
    all_metrics["models"]["elevation_only_baseline"] = {
        "description": "Physical univariate baseline ranking cells inversely by mean elevation",
        "validation_metrics": compute_model_metrics(y_val, val_elev_norm, threshold=elev_best_th),
        "test_metrics": compute_model_metrics(y_test, test_elev_norm, threshold=elev_best_th)
    }

    # -------------------------------------------------------------------------
    # MODEL 3: LOGISTIC REGRESSION (BALANCED)
    # -------------------------------------------------------------------------
    logger.info("Training Model 3: Logistic Regression (Balanced)...")
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr.fit(X_train_scaled, y_train)
    
    val_probs_lr = lr.predict_proba(X_val_scaled)[:, 1]
    lr_best_th = select_best_threshold(y_val, val_probs_lr)
    test_probs_lr = lr.predict_proba(X_test_scaled)[:, 1]
    
    all_metrics["models"]["logistic_regression_balanced"] = {
        "description": "Standardized linear model with inverse class weighting",
        "validation_metrics": compute_model_metrics(y_val, val_probs_lr, threshold=lr_best_th),
        "test_metrics": compute_model_metrics(y_test, test_probs_lr, threshold=lr_best_th)
    }

    # -------------------------------------------------------------------------
    # MODEL 4: RANDOM FOREST CLASSIFIER
    # -------------------------------------------------------------------------
    logger.info("Training Model 4: Random Forest Classifier...")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_leaf=20,
        class_weight="balanced",
        random_state=42,
        n_jobs=4
    )
    rf.fit(X_train, y_train)
    
    val_probs_rf = rf.predict_proba(X_val)[:, 1]
    rf_best_th = select_best_threshold(y_val, val_probs_rf)
    test_probs_rf = rf.predict_proba(X_test)[:, 1]
    
    all_metrics["models"]["random_forest_balanced"] = {
        "description": "Nonlinear decision tree ensemble with balanced bootstrapping and depth=10",
        "validation_metrics": compute_model_metrics(y_val, val_probs_rf, threshold=rf_best_th),
        "test_metrics": compute_model_metrics(y_test, test_probs_rf, threshold=rf_best_th)
    }

    # -------------------------------------------------------------------------
    # MODEL 5: XGBOOST CLASSIFIER
    # -------------------------------------------------------------------------
    pos_cnt = int(np.sum(y_train))
    neg_cnt = len(y_train) - pos_cnt
    scale_pos = float(neg_cnt / pos_cnt)
    model_xgb = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=scale_pos,
        random_state=42,
        n_jobs=4,
        eval_metric="logloss"
    )
    model_xgb.fit(X_train, y_train)
    
    val_probs_xgb = model_xgb.predict_proba(X_val)[:, 1]
    xgb_best_th = select_best_threshold(y_val, val_probs_xgb)
    test_probs_xgb = model_xgb.predict_proba(X_test)[:, 1]
    
    all_metrics["models"]["xgboost_weighted"] = {
        "description": "Gradient boosted decision trees with scale_pos_weight and depth=5",
        "validation_metrics": compute_model_metrics(y_val, val_probs_xgb, threshold=xgb_best_th),
        "test_metrics": compute_model_metrics(y_test, test_probs_xgb, threshold=xgb_best_th)
    }

    # Save metrics
    with open(out_metrics, "w") as f:
        json.dump(all_metrics, f, indent=2)
    logger.info(f"Model metrics saved to {out_metrics}")

    # -------------------------------------------------------------------------
    # 6. FEATURE IMPORTANCE EXTRACTION
    # -------------------------------------------------------------------------
    logger.info("Extracting feature importances...")
    rf_imp = rf.feature_importances_
    xgb_imp = model_xgb.feature_importances_
    lr_coef = np.abs(lr.coef_[0])

    df_imp = pd.DataFrame({
        "feature_name": RETAINED_FEATURES,
        "rf_importance": rf_imp,
        "xgb_importance": xgb_imp,
        "lr_abs_coefficient": lr_coef,
        "scientific_rationale": [FEATURE_RATIONALE[f] for f in RETAINED_FEATURES]
    }).sort_values("xgb_importance", ascending=False)
    
    df_imp.to_csv(out_feature_imp, index=False)
    logger.info(f"Feature importance table saved to {out_feature_imp}")

    # -------------------------------------------------------------------------
    # 7. ERROR ANALYSIS & SUB-BASIN BREAKDOWN
    # -------------------------------------------------------------------------
    logger.info("Computing spatial error analysis across test sub-basins...")
    test_preds_xgb = (test_probs_xgb >= xgb_best_th).astype(int)
    test_df["xgb_pred"] = test_preds_xgb
    test_df["xgb_prob"] = test_probs_xgb
    test_df["error_type"] = np.where(
        (test_df["flood_label"] == 1) & (test_df["xgb_pred"] == 1), "TRUE_POSITIVE",
        np.where(
            (test_df["flood_label"] == 0) & (test_df["xgb_pred"] == 0), "TRUE_NEGATIVE",
            np.where((test_df["flood_label"] == 0) & (test_df["xgb_pred"] == 1), "FALSE_POSITIVE", "FALSE_NEGATIVE")
        )
    )

    err_rows = []
    for s_id, group in test_df.groupby("subbasin_id_lev08"):
        tot = len(group)
        obs_flood = int(group["flood_label"].sum())
        pred_flood = int(group["xgb_pred"].sum())
        tp = int(((group["flood_label"] == 1) & (group["xgb_pred"] == 1)).sum())
        fp = int(((group["flood_label"] == 0) & (group["xgb_pred"] == 1)).sum())
        fn = int(((group["flood_label"] == 1) & (group["xgb_pred"] == 0)).sum())
        tn = int(((group["flood_label"] == 0) & (group["xgb_pred"] == 0)).sum())
        
        pr_score = float(average_precision_score(group["flood_label"], group["xgb_prob"])) if obs_flood > 0 else 0.0
        roc_score = float(roc_auc_score(group["flood_label"], group["xgb_prob"])) if obs_flood > 0 and obs_flood < tot else 0.5
        
        err_rows.append({
            "subbasin_id_lev08": int(s_id),
            "total_cells": tot,
            "observed_flood_cells": obs_flood,
            "predicted_flood_cells": pred_flood,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "subbasin_precision": round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0,
            "subbasin_recall": round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0,
            "subbasin_pr_auc": round(pr_score, 4),
            "subbasin_roc_auc": round(roc_score, 4),
            "natural_prevalence_pct": round(obs_flood / tot * 100.0, 3),
            "mean_elevation_m": round(float(group["elevation_mean_m"].mean()), 2),
            "mean_slope_deg": round(float(group["slope_mean_deg"].mean()), 2),
            "mean_dist_to_distributary_m": round(float(group["dist_to_distributary_min_m"].mean()), 2)
        })

    df_err = pd.DataFrame(err_rows).sort_values("total_cells", ascending=False)
    df_err.to_csv(out_errors, index=False)
    logger.info(f"Sub-basin error analysis saved to {out_errors}")

    elapsed = time.time() - t_start
    logger.info(f"Phase 7F Stage 4 model exploration complete in {elapsed:.2f}s!")
    return all_metrics

if __name__ == "__main__":
    run_stage4_experiments()
