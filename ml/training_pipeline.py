"""
AQUORA Phase 3 — National Flood Screening Model Training & Validation Pipeline.

Implements leakage-resistant spatial GroupKFold validation, native missing value routing,
deterministic XGBoost training, and versioned artifact packaging.

GOVERNANCE & SAFETY INVARIANTS:
1. Exactly the 11 CORE_NATIONAL features in governed order.
2. Leakage Prevention: flood_label, SAR delta, coordinates, and Phase 6 physics outputs are strictly excluded from predictors.
3. Grouped Cross-Validation: Grouped strictly by basin_id (HydroBASINS); samples from the same river basin never leak across folds.
4. Native Missing Values: XGBoost default split routing handles NaNs directly without synthetic imputation.
5. Data Sufficiency Gate: Rejects training if authentic supervised samples are missing, imbalanced to a single class, or span < 2 spatial groups.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import structlog
from sklearn.model_selection import GroupKFold
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
import xgboost as xgb

logger = structlog.get_logger("aquora.ml.training_pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_DIR = PROJECT_ROOT / "ml" / "models"


class DataSufficiencyError(ValueError):
    """Raised when labeled training data fails quality or sufficiency gates."""
    pass


class NationalScreeningTrainingPipeline:
    """
    Supervised training harness for the 11-feature National Flood Screening Model.
    """

    CORE_11_PREDICTORS: List[str] = [
        "rainfall_1h_mm",
        "rainfall_3h_mm",
        "rainfall_6h_mm",
        "rainfall_24h_mm",
        "rainfall_72h_mm",
        "rainfall_anomaly_index",
        "elevation_m",
        "slope_deg",
        "distance_to_river_m",
        "historical_flood_frequency",
        "landcover_class",
    ]

    FORBIDDEN_COLUMNS: List[str] = [
        "flood_label",
        "sar_delta_vv_db",
        "sar_scene_id",
        "water_depth_m",
        "flow_velocity_ms",
        "modeled_depth_m",
        "latitude",
        "longitude",
    ]

    def __init__(
        self,
        model_dir: Optional[Path] = None,
        n_splits: int = 5,
        random_state: int = 42,
    ):
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.n_splits = n_splits
        self.random_state = random_state

    def validate_dataset(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validate training dataset against schema, predictors, label distribution, and spatial groups.
        """
        # Ensure target column exists
        if "flood_label" not in df.columns:
            raise ValueError("Dataset missing target column: 'flood_label'")

        if "basin_id" not in df.columns:
            raise ValueError("Dataset missing spatial group column: 'basin_id'")

        # Ensure all 11 core predictors exist
        missing_preds = [c for c in self.CORE_11_PREDICTORS if c not in df.columns]
        if missing_preds:
            raise ValueError(f"Dataset missing required core predictors: {missing_preds}")

        # Check for forbidden columns in predictor subset
        for forbidden in self.FORBIDDEN_COLUMNS:
            if forbidden in self.CORE_11_PREDICTORS:
                raise ValueError(f"Forbidden column detected in predictor list: {forbidden}")

        # Filter out unknown (-1) labels
        df_supervised = df[df["flood_label"].isin([0, 1])].copy()
        total_rows = len(df)
        supervised_rows = len(df_supervised)
        unknown_rows = int((df["flood_label"] == -1).sum())

        audit = {
            "total_rows": total_rows,
            "supervised_rows": supervised_rows,
            "unknown_excluded": unknown_rows,
            "positive_count": int((df_supervised["flood_label"] == 1).sum()) if supervised_rows > 0 else 0,
            "negative_count": int((df_supervised["flood_label"] == 0).sum()) if supervised_rows > 0 else 0,
            "unique_basins": list(df_supervised["basin_id"].unique()) if supervised_rows > 0 else [],
        }

        # Data sufficiency gate
        if supervised_rows == 0:
            raise DataSufficiencyError(
                f"No supervised training samples available (all {total_rows} rows have unobserved label -1). "
                "Zero-fabrication rule forbids training without authentic flood ground-truth."
            )

        if audit["positive_count"] == 0 or audit["negative_count"] == 0:
            raise DataSufficiencyError(
                f"Class imbalance error: Dataset contains only one class "
                f"(positives={audit['positive_count']}, negatives={audit['negative_count']}). Both classes required."
            )

        if len(audit["unique_basins"]) < 2:
            raise DataSufficiencyError(
                f"Insufficient spatial groups: Found {len(audit['unique_basins'])} distinct river basins. "
                "At least 2 independent basins required for spatial cross-validation."
            )

        return df_supervised, audit

    def validate_training_data_sufficiency(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Alias for validate_dataset adhering to Phase 3 naming."""
        return self.validate_dataset(df)

    def train_and_evaluate(
        self,
        df: pd.DataFrame,
        n_splits: Optional[int] = None,
        random_state: Optional[int] = None,
        model_version: str = "1.0.0-national-screening",
    ) -> Dict[str, Any]:
        """
        Execute leakage-resistant spatial GroupKFold evaluation and train final model.
        """
        df_supervised, audit = self.validate_dataset(df)

        actual_splits = n_splits or self.n_splits
        actual_seed = random_state if random_state is not None else self.random_state

        X = df_supervised[self.CORE_11_PREDICTORS].copy()
        y = df_supervised["flood_label"].astype(int).values
        groups = df_supervised["basin_id"].values

        # Adjust n_splits if groups < n_splits
        unique_groups = len(np.unique(groups))
        effective_splits = min(actual_splits, unique_groups)

        gkf = GroupKFold(n_splits=effective_splits)
        fold_metrics: List[Dict[str, Any]] = []

        oof_preds = np.zeros(len(y), dtype=np.float32)

        for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=groups)):
            X_train, y_train = X.iloc[train_idx], y[train_idx]
            X_val, y_val = X.iloc[val_idx], y[val_idx]

            # Verify zero group leakage between train and val
            train_groups = set(groups[train_idx])
            val_groups = set(groups[val_idx])
            overlap = train_groups.intersection(val_groups)
            assert len(overlap) == 0, f"Spatial group leakage detected in fold {fold}: {overlap}"

            # Detect folds without both classes in training set
            if len(np.unique(y_train)) < 2:
                logger.warning(
                    "Fold training partition lacks both classes; fold marked invalid",
                    fold=fold + 1,
                    train_classes=list(np.unique(y_train)),
                )
                fold_metrics.append({
                    "fold": fold + 1,
                    "train_samples": len(train_idx),
                    "val_samples": len(val_idx),
                    "val_basins": list(val_groups),
                    "status": "INVALID_SINGLE_CLASS_FOLD",
                    "roc_auc": None,
                    "pr_auc": None,
                    "f1_at_0.5": None,
                })
                continue

            # Calculate class imbalance scale
            n_neg = (y_train == 0).sum()
            n_pos = (y_train == 1).sum()
            scale_pos = (n_neg / max(1, n_pos)) if n_pos > 0 else 1.0

            fold_clf = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                scale_pos_weight=scale_pos,
                random_state=actual_seed + fold,
                eval_metric="logloss",
                tree_method="hist",
            )

            fold_clf.fit(X_train, y_train)
            probs = fold_clf.predict_proba(X_val)[:, 1]
            oof_preds[val_idx] = probs

            # Compute fold metrics if both classes present in fold validation
            if len(np.unique(y_val)) > 1:
                roc_auc = float(roc_auc_score(y_val, probs))
                pr_auc = float(average_precision_score(y_val, probs))
            else:
                roc_auc = None
                pr_auc = None

            preds_bin = (probs >= 0.5).astype(int)
            f1 = float(f1_score(y_val, preds_bin, zero_division=0))

            fold_metrics.append({
                "fold": fold + 1,
                "train_samples": len(train_idx),
                "val_samples": len(val_idx),
                "val_basins": list(val_groups),
                "roc_auc": roc_auc,
                "pr_auc": pr_auc,
                "f1_at_0.5": f1,
            })

        # Aggregate Out-of-Fold (OOF) Metrics
        overall_pr_auc = float(average_precision_score(y, oof_preds)) if len(np.unique(y)) > 1 else None
        overall_roc_auc = float(roc_auc_score(y, oof_preds)) if len(np.unique(y)) > 1 else None
        overall_brier = float(brier_score_loss(y, oof_preds))

        # Train final estimator on all supervised data
        full_scale_pos = ((y == 0).sum() / max(1, (y == 1).sum()))
        final_model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=full_scale_pos,
            random_state=actual_seed,
            eval_metric="logloss",
            tree_method="hist",
        )
        final_model.fit(X, y)

        # Artifact Packaging
        metadata = {
            "model_id": "aquora_national_screening_xgboost_v1",
            "model_version": model_version,
            "schema_version": "1.0.0",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "algorithm": "XGBoost (Histogram Gradient Boosting)",
            "predictors": self.CORE_11_PREDICTORS,
            "validation_scheme": f"GroupKFold (n_splits={effective_splits}, grouped by HydroBASINS basin_id)",
            "audit": audit,
            "fold_metrics": fold_metrics,
            "aggregate_oof_metrics": {
                "pr_auc": overall_pr_auc,
                "roc_auc": overall_roc_auc,
                "brier_score": overall_brier,
            },
            "environment": {
                "xgboost_version": getattr(xgb, "__version__", "unknown"),
            },
        }

        artifact_payload = {
            "model": final_model,
            "feature_names": self.CORE_11_PREDICTORS,
            "schema_version": "1.0.0",
            "model_version": model_version,
            "status": "OPERATIONAL",
            "metadata": metadata,
        }

        artifact_file = self.model_dir / "aquora_national_screening_model.joblib"
        metadata_file = self.model_dir / "aquora_national_screening_metadata.json"

        joblib.dump(artifact_payload, artifact_file)
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Saved National Screening Model artifact", artifact=str(artifact_file))

        return {
            "status": "SUCCESS",
            "artifact_file": str(artifact_file),
            "metadata_file": str(metadata_file),
            "metadata": metadata,
        }
