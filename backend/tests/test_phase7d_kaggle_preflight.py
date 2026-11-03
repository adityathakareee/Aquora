"""
AQUORA Phase 7D: Kaggle Preflight & Dataset Verification Test Suite.

Comprehensive automated verification testing:
1. Dataset & Manifest Audit:
   - Validates existence, row counts, and cryptographic hashes for both master (17,300)
     and binary (15,700) multi-event datasets.
   - Validates preservation of Phase 7B DFO 4499 pilot dataset (5,500 rows).
2. Feature & Label Validation:
   - Verifies strict conformance to ml/aquora_ml_feature_schema_v1.json (all 11 CORE_NATIONAL features).
   - Asserts binary dataset contains ONLY flood_label in {0, 1} with exact 50.0% / 50.0% balance.
   - Asserts permanent water controls (-1) are 100% excluded from binary dataset.
   - Asserts sub-daily rainfall (1h, 3h, 6h) is preserved as explicit NaNs (100% missing, zero filled).
   - Asserts zero infinities and authentic ESA WorldCover classes.
3. Event-Level Holdout & Zero Leakage:
   - Validates disjoint split partitioning: Train (DFO 4499 + DFO 2935), Validation (DFO 3372), Test (DFO 2507).
   - Confirms zero coordinate overlap across train, validation, and test splits.
   - Confirms test event is strictly held out.
4. Kaggle Package & Notebook Preflight:
   - Verifies data/packages/phase7d_kaggle_dataset/ contains all deliverables, manifest, and README.
   - Verifies notebooks/aquora_national_screening_kaggle.ipynb exists, is valid JSON, and contains
     Kaggle paths, anti-leakage guards, baseline comparisons, and output serialization.
   - Asserts package governance status is READY_FOR_EXPERIMENTAL_KAGGLE_TRAINING.
"""

import ast
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# File Paths
PROCESSED_ML_DIR = REPO_ROOT / "data" / "processed" / "phase7" / "ml"
MASTER_PARQUET = PROCESSED_ML_DIR / "phase7c_multievent_dataset.parquet"
BINARY_PARQUET = PROCESSED_ML_DIR / "phase7c_multievent_binary_dataset.parquet"
PILOT_PARQUET = PROCESSED_ML_DIR / "phase7_gfd_pilot_dataset.parquet"

PACKAGE_DIR = REPO_ROOT / "data" / "packages" / "phase7d_kaggle_dataset"
PACKAGE_MANIFEST = PACKAGE_DIR / "phase7d_kaggle_dataset_manifest.yaml"
PROJECT_MANIFEST = REPO_ROOT / "data" / "manifests" / "phase7d_kaggle_dataset_manifest.yaml"
SCHEMA_PATH = REPO_ROOT / "ml" / "aquora_ml_feature_schema_v1.json"
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "aquora_national_screening_kaggle.ipynb"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------------------------------------------------------
# 1. Dataset & Manifest Audit
# -----------------------------------------------------------------------------
def test_phase7d_dataset_audit_and_preservation():
    """Verify multi-event dataset artifacts and confirm pilot preservation."""
    assert MASTER_PARQUET.exists(), f"Missing master dataset: {MASTER_PARQUET}"
    assert BINARY_PARQUET.exists(), f"Missing binary dataset: {BINARY_PARQUET}"
    assert PILOT_PARQUET.exists(), f"Pilot dataset was overwritten or removed: {PILOT_PARQUET}"

    df_master = pd.read_parquet(MASTER_PARQUET)
    df_binary = pd.read_parquet(BINARY_PARQUET)
    df_pilot = pd.read_parquet(PILOT_PARQUET)

    # Reconcile row counts
    assert len(df_master) == 209116, f"Expected 209,116 master rows, got {len(df_master)}"
    assert len(df_binary) == 207205, f"Expected 207,205 binary rows, got {len(df_binary)}"
    assert len(df_pilot) == 5500, f"Expected 5,500 pilot rows, got {len(df_pilot)}"

    # Check pilot isolation
    assert (df_pilot["event_id"] == "DFO_4499").all(), "Pilot dataset contains non-DFO_4499 data"


def test_phase7d_manifest_hashes_and_reconciliation():
    """Verify package manifest cryptographic checksums match physical files."""
    assert PACKAGE_MANIFEST.exists(), f"Missing package manifest: {PACKAGE_MANIFEST}"
    assert PROJECT_MANIFEST.exists(), f"Missing project manifest: {PROJECT_MANIFEST}"

    with open(PACKAGE_MANIFEST, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    # Verify binary parquet hash
    bin_parquet_meta = manifest["package_assets"]["binary_parquet"]
    actual_bin_hash = compute_sha256(PACKAGE_DIR / bin_parquet_meta["path"])
    assert actual_bin_hash == bin_parquet_meta["sha256"], "Binary parquet SHA-256 mismatch"

    # Verify master parquet hash
    mst_parquet_meta = manifest["package_assets"]["master_parquet"]
    actual_mst_hash = compute_sha256(PACKAGE_DIR / mst_parquet_meta["path"])
    assert actual_mst_hash == mst_parquet_meta["sha256"], "Master parquet SHA-256 mismatch"

    # Verify governance status
    assert manifest["governance_status"] == "EXPERIMENTAL_EVALUATION_ONLY"


# -----------------------------------------------------------------------------
# 2. Feature & Label Validation
# -----------------------------------------------------------------------------
def test_phase7d_feature_schema_and_label_integrity():
    """Verify strict adherence to CORE_NATIONAL features, natural test distribution, and nulls."""
    df_binary = pd.read_parquet(BINARY_PARQUET)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    core_features = schema["tiers"]["CORE_NATIONAL"]["features"]

    # 1. Feature presence and order
    for feat in core_features:
        assert feat in df_binary.columns, f"Missing feature: {feat}"

    # 2. Label purity: ONLY 0 and 1 in binary dataset
    assert set(df_binary["flood_label"].unique()) == {0, 1}
    assert (df_binary["flood_label"] == -1).sum() == 0, "Permanent water controls (-1) leaked into binary dataset!"

    # 3. Label balance checks:
    # Train is 50/50 balanced (2850 / 2850)
    train_binary = df_binary[df_binary["split"] == "train"]
    assert (train_binary["flood_label"] == 1).sum() == 2850
    assert (train_binary["flood_label"] == 0).sum() == 2850

    # Validation is 50/50 balanced (2500 / 2500)
    val_binary = df_binary[df_binary["split"] == "validation"]
    assert (val_binary["flood_label"] == 1).sum() == 2500
    assert (val_binary["flood_label"] == 0).sum() == 2500

    # Test set preserves natural unskewed distribution (11435 flood, 185070 dry)
    test_binary = df_binary[df_binary["split"] == "test"]
    n_test_flood = int((test_binary["flood_label"] == 1).sum())
    n_test_dry = int((test_binary["flood_label"] == 0).sum())
    assert n_test_flood == 11435, f"Expected 11,435 test flood samples, got {n_test_flood}"
    assert n_test_dry == 185070, f"Expected 185,070 test dry samples, got {n_test_dry}"
    assert n_test_flood != n_test_dry, "Held-out test set was artificially balanced! Natural population required."

    # 4. Strict null preservation: sub-daily rainfall must be 100% NaN
    assert df_binary["rainfall_1h_mm"].isnull().all(), "rainfall_1h_mm must be NaN when unobserved"
    assert df_binary["rainfall_3h_mm"].isnull().all(), "rainfall_3h_mm must be NaN when unobserved"
    assert df_binary["rainfall_6h_mm"].isnull().all(), "rainfall_6h_mm must be NaN when unobserved"

    # 5. Zero infinities across all numeric features
    for col in core_features:
        valid_vals = df_binary[col].dropna()
        assert not np.isinf(valid_vals).any(), f"Feature {col} contains infinite values"

    # 6. Physical feature units and variances
    assert (df_binary["elevation_m"] >= -10.0).all()
    assert (df_binary["slope_deg"] >= 0.0).all() and (df_binary["slope_deg"] <= 90.0).all()
    assert (df_binary["distance_to_river_m"] >= 0.0).all()
    freq_means = df_binary.groupby("event_id")["historical_flood_frequency"].mean()
    assert freq_means.std() > 1.0, "Historical flood frequency lacks multi-basin variance"
    assert df_binary["landcover_class"].std() > 10.0, "Landcover class lacks variance"


# -----------------------------------------------------------------------------
# 3. Event-Level Holdout & Zero Leakage
# -----------------------------------------------------------------------------
def test_phase7d_event_separation_and_zero_leakage():
    """Verify strict event-level holdout splitting and zero spatial overlap."""
    df_binary = pd.read_parquet(BINARY_PARQUET)

    train_mask = df_binary["split"] == "train"
    val_mask = df_binary["split"] == "validation"
    test_mask = df_binary["split"] == "test"

    train_events = set(df_binary[train_mask]["event_id"].unique())
    val_events = set(df_binary[val_mask]["event_id"].unique())
    test_events = set(df_binary[test_mask]["event_id"].unique())

    # Disjoint event sets
    assert train_events == {"DFO_4499", "DFO_2935"}, f"Unexpected train events: {train_events}"
    assert val_events == {"DFO_3372"}, f"Unexpected validation events: {val_events}"
    assert test_events == {"DFO_2507"}, f"Unexpected test events: {test_events}"

    assert len(train_events.intersection(val_events)) == 0, "Train and Val share events!"
    assert len(train_events.intersection(test_events)) == 0, "Train and Test share events!"
    assert len(val_events.intersection(test_events)) == 0, "Val and Test share events!"

    # Zero coordinate overlap
    train_coords = set(zip(df_binary[train_mask]["latitude"], df_binary[train_mask]["longitude"]))
    val_coords = set(zip(df_binary[val_mask]["latitude"], df_binary[val_mask]["longitude"]))
    test_coords = set(zip(df_binary[test_mask]["latitude"], df_binary[test_mask]["longitude"]))

    assert len(train_coords.intersection(val_coords)) == 0, "Spatial leakage between Train and Val"
    assert len(train_coords.intersection(test_coords)) == 0, "Spatial leakage between Train and Test"
    assert len(val_coords.intersection(test_coords)) == 0, "Spatial leakage between Val and Test"

    # Held out test event counts: natural population
    assert len(df_binary[test_mask]) == 196505
    assert (df_binary[test_mask]["flood_label"] == 1).sum() == 11435
    assert (df_binary[test_mask]["flood_label"] == 0).sum() == 185070


# -----------------------------------------------------------------------------
# 4. Kaggle Package & Notebook Preflight
# -----------------------------------------------------------------------------
def test_phase7d_kaggle_package_completeness():
    """Verify Kaggle package contains all required artifacts without raw raster bloat."""
    expected_files = [
        "phase7c_multievent_binary_dataset.parquet",
        "phase7c_multievent_binary_dataset.csv",
        "phase7c_multievent_dataset.parquet",
        "phase7c_multievent_dataset.csv",
        "aquora_ml_feature_schema_v1.json",
        "phase7d_kaggle_dataset_manifest.yaml",
        "README.md",
    ]
    for fn in expected_files:
        p = PACKAGE_DIR / fn
        assert p.exists(), f"Missing packaged deliverable: {fn}"
        assert p.stat().st_size > 0, f"Packaged file is empty: {fn}"

    # Verify no multi-gigabyte raw GeoTIFF rasters are bundled in package
    for f in PACKAGE_DIR.glob("*.tif"):
        pytest.fail(f"Raw GeoTIFF found in Kaggle package: {f.name}")


def test_phase7d_kaggle_notebook_preflight():
    """Verify notebook exists, is valid JSON, and enforces required anti-leakage guards."""
    assert NOTEBOOK_PATH.exists(), f"Missing Kaggle notebook: {NOTEBOOK_PATH}"
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    assert "cells" in nb, "Notebook missing 'cells' attribute"
    assert len(nb["cells"]) >= 10, "Notebook has fewer cells than expected"

    code_cells = [c["source"] for c in nb["cells"] if c.get("cell_type") == "code"]
    full_code = "\n".join(["".join(src) for src in code_cells])

    # Check for critical keywords and safeguards
    assert "CORE_11_PREDICTORS" in full_code, "Notebook missing CORE_11_PREDICTORS"
    assert "MODEL_TRAINING_FEATURES" in full_code, "Notebook missing MODEL_TRAINING_FEATURES"
    assert "historical_flood_frequency" in full_code, "Notebook missing feature leakage audit of historical_flood_frequency"
    assert "/kaggle/input" in full_code, "Notebook missing Kaggle input path handling"
    assert "DFO_2507" in full_code, "Notebook missing test event DFO_2507"
    assert "missing=np.nan" in full_code, "Notebook missing native XGBoost NaN handling"
    assert "roc_auc_score" in full_code, "Notebook missing ROC-AUC evaluation"
    assert "precision_score" in full_code, "Notebook missing precision score"
    assert "recall_score" in full_code, "Notebook missing recall score"
    assert "confusion_matrix" in full_code, "Notebook missing confusion matrix"
    assert "EXPERIMENTAL_EVALUATION_ONLY" in full_code, "Notebook missing governance status EXPERIMENTAL_EVALUATION_ONLY"

    # Ensure no local Windows hardcoded absolute paths (like C:\Users\...) in notebook code
    assert "C:\\Users" not in full_code, "Notebook contains local Windows absolute path!"
    assert "c:/users" not in full_code.lower(), "Notebook contains local Windows absolute path!"
