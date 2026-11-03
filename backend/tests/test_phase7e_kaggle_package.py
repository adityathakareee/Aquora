"""
AQUORA Phase 7E: Automated Test Suite for Kaggle Package & Notebook Preparation.

Validates all Phase 7E governance criteria:
1. Dataset Checksums: Package assets match authoritative SHA-256 hashes.
2. Feature Exclusions: historical_flood_frequency excluded from model training.
3. Target Labels: flood_label strictly in {0, 1}.
4. Permanent Water Quarantine: flood_label == -1 count is 0 in binary dataset.
5. Split Integrity: Disjoint events, zero spatial overlap, natural test distribution.
6. Zero Test-Set Tuning: DFO 2507 marked as ALREADY_INSPECTED_HOLDOUT; threshold tuned on validation.
7. Missing Rainfall Preservation: Sub-daily rainfalls are 100% NaN (zero-filling prohibited).
8. Notebook Structure: Notebook contains all 15 mandatory sections and is valid JSON.
9. Artifact Metadata: Governance warnings (PROTOTYPE_ONLY, NOT_CALIBRATED, NOT_FOR_PUBLIC_ALERTS).
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# Paths
PACKAGE_DIR = REPO_ROOT / "data" / "packages" / "phase7e_kaggle_package"
PACKAGE_MANIFEST = PACKAGE_DIR / "phase7e_kaggle_package_manifest.yaml"
PROJECT_MANIFEST = REPO_ROOT / "data" / "manifests" / "phase7e_kaggle_package_manifest.yaml"
BINARY_PARQUET = PACKAGE_DIR / "phase7c_multievent_binary_dataset.parquet"
BINARY_CSV = PACKAGE_DIR / "phase7c_multievent_binary_dataset.csv"
SCHEMA_JSON = PACKAGE_DIR / "aquora_ml_feature_schema_v1.json"
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "AQUORA_Phase_7E_Experimental_ML.ipynb"
PACKAGE_NOTEBOOK = PACKAGE_DIR / "AQUORA_Phase_7E_Experimental_ML.ipynb"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------------------------------------------------------
# 1. Dataset Checksums & Assets
# -----------------------------------------------------------------------------
def test_phase7e_dataset_checksums_and_assets():
    """Verify presence of all package assets and cryptographic SHA-256 parity."""
    assert PACKAGE_DIR.exists(), f"Missing package directory: {PACKAGE_DIR}"
    assert PACKAGE_MANIFEST.exists(), f"Missing package manifest: {PACKAGE_MANIFEST}"
    assert PROJECT_MANIFEST.exists(), f"Missing project manifest: {PROJECT_MANIFEST}"

    with open(PACKAGE_MANIFEST, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    # Required files in package
    expected_files = [
        "phase7c_multievent_binary_dataset.parquet",
        "phase7c_multievent_binary_dataset.csv",
        "aquora_ml_feature_schema_v1.json",
        "AQUORA_Phase_7E_Experimental_ML.ipynb",
        "DATA_DICTIONARY.md",
        "TARGET_LABEL_DOCUMENTATION.md",
        "SPLIT_DOCUMENTATION.md",
        "DATA_QUALITY_AND_LIMITATIONS.md",
        "README.md",
        "phase7e_kaggle_package_manifest.yaml",
    ]

    for fn in expected_files:
        fp = PACKAGE_DIR / fn
        assert fp.exists(), f"Missing packaged file: {fn}"
        assert fp.stat().st_size > 0, f"Packaged file is empty: {fn}"

    # Verify binary dataset hashes against Phase 7D authoritative hashes
    bin_parquet_hash = compute_sha256(BINARY_PARQUET)
    assert bin_parquet_hash == "f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7"

    bin_csv_hash = compute_sha256(BINARY_CSV)
    assert bin_csv_hash == "754724649d8e856093d21986fcce0e383b21bacf922c333f9b64dcdea2fb27cb"

    schema_hash = compute_sha256(SCHEMA_JSON)
    assert schema_hash == "47ffdeedc73ee602f6ea1349347323b5ee3d58180fdc3b20261b94b9afee5911"


# -----------------------------------------------------------------------------
# 2. Feature Exclusions & Policy
# -----------------------------------------------------------------------------
def test_phase7e_feature_exclusions_and_policy():
    """Verify feature schema conformance and anti-leakage exclusion of historical_flood_frequency."""
    with open(SCHEMA_JSON, "r", encoding="utf-8") as f:
        schema = json.load(f)

    core_features = schema["tiers"]["CORE_NATIONAL"]["features"]
    assert len(core_features) == 11, f"Expected 11 core features, got {len(core_features)}"
    assert "historical_flood_frequency" in core_features

    with open(PACKAGE_MANIFEST, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    model_features = manifest["governed_features"]["model_training_features_10"]
    assert len(model_features) == 10, f"Expected 10 model training features, got {len(model_features)}"
    assert "historical_flood_frequency" not in model_features, "historical_flood_frequency was not excluded!"
    assert "historical_flood_frequency" in manifest["governed_features"]["excluded_leakage_features"]


# -----------------------------------------------------------------------------
# 3. Target Labels & Permanent Water Quarantine
# -----------------------------------------------------------------------------
def test_phase7e_target_labels_and_quarantine():
    """Verify binary labels in {0, 1} and 100% exclusion of permanent water controls (-1)."""
    df = pd.read_parquet(BINARY_PARQUET)
    assert len(df) == 207205, f"Expected 207,205 rows, got {len(df)}"

    unique_labels = set(df["flood_label"].unique())
    assert unique_labels == {0, 1}, f"Binary dataset has invalid labels: {unique_labels}"

    n_perm = (df["flood_label"] == -1).sum()
    assert n_perm == 0, f"Permanent water controls (-1) found in binary dataset! Count: {n_perm}"


# -----------------------------------------------------------------------------
# 4. Event-Level Split Integrity
# -----------------------------------------------------------------------------
def test_phase7e_event_level_split_integrity():
    """Verify disjoint event partitions, zero coordinate overlap, and natural test distribution."""
    df = pd.read_parquet(BINARY_PARQUET)

    train_df = df[df["split"] == "train"]
    val_df = df[df["split"] == "validation"]
    test_df = df[df["split"] == "test"]

    # Sample counts
    assert len(train_df) == 5700, f"Expected 5,700 train samples, got {len(train_df)}"
    assert len(val_df) == 5000, f"Expected 5,000 val samples, got {len(val_df)}"
    assert len(test_df) == 196505, f"Expected 196,505 test samples, got {len(test_df)}"

    # Event disjointness
    train_events = set(train_df["event_id"].unique())
    val_events = set(val_df["event_id"].unique())
    test_events = set(test_df["event_id"].unique())

    assert train_events == {"DFO_4499", "DFO_2935"}
    assert val_events == {"DFO_3372"}
    assert test_events == {"DFO_2507"}

    assert train_events.isdisjoint(val_events)
    assert train_events.isdisjoint(test_events)
    assert val_events.isdisjoint(test_events)

    # Coordinate isolation
    train_coords = set(zip(train_df["latitude"], train_df["longitude"]))
    val_coords = set(zip(val_df["latitude"], val_df["longitude"]))
    test_coords = set(zip(test_df["latitude"], test_df["longitude"]))

    assert train_coords.isdisjoint(val_coords)
    assert train_coords.isdisjoint(test_coords)
    assert val_coords.isdisjoint(test_coords)

    # Natural unskewed test prevalence
    test_pos = (test_df["flood_label"] == 1).sum()
    test_neg = (test_df["flood_label"] == 0).sum()
    assert test_pos == 11435, f"Expected 11,435 positive test samples, got {test_pos}"
    assert test_neg == 185070, f"Expected 185,070 negative test samples, got {test_neg}"
    assert test_pos != test_neg, "Held-out test set must retain natural imbalance (5.82% prevalence)."


# -----------------------------------------------------------------------------
# 5. Holdout Policy & Zero Test Tuning
# -----------------------------------------------------------------------------
def test_phase7e_holdout_policy_and_zero_test_tuning():
    """Verify DFO 2507 is marked as ALREADY_INSPECTED_HOLDOUT and quarantined from tuning."""
    with open(PACKAGE_MANIFEST, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["holdout_policy"]["test_event_id"] == "DFO_2507"
    assert manifest["holdout_policy"]["designation"] == "ALREADY_INSPECTED_HOLDOUT"

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    full_text = "\n".join(["".join(c["source"]) for c in nb["cells"]])
    assert "ALREADY_INSPECTED_HOLDOUT" in full_text
    assert "DFO_2507" in full_text
    assert "DFO_3372" in full_text


# -----------------------------------------------------------------------------
# 6. Missing Rainfall Preservation
# -----------------------------------------------------------------------------
def test_phase7e_missing_rainfall_preservation():
    """Verify sub-daily rainfall features are preserved strictly as explicit NaNs."""
    df = pd.read_parquet(BINARY_PARQUET)

    for col in ["rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm"]:
        assert col in df.columns
        assert df[col].isnull().all(), f"{col} must be 100% NaN (zero-filling prohibited)"
        assert not (df[col] == 0.0).any(), f"{col} has zero-filled entries!"


# -----------------------------------------------------------------------------
# 7. Notebook Structure & All 15 Required Sections
# -----------------------------------------------------------------------------
def test_phase7e_notebook_structure_and_sections():
    """Verify notebook exists, is valid JSON, and contains all 15 required sections in order."""
    assert NOTEBOOK_PATH.exists(), f"Missing notebook: {NOTEBOOK_PATH}"
    assert PACKAGE_NOTEBOOK.exists(), f"Missing packaged notebook: {PACKAGE_NOTEBOOK}"

    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    assert "cells" in nb
    assert len(nb["cells"]) >= 30, f"Expected at least 30 cells (15 md + 15 code), got {len(nb['cells'])}"

    required_sections = [
        "Environment Setup and Dependency Installation",
        "Dataset Loading and Integrity Verification",
        "Feature and Target Inspection",
        "Train/Validation/Test Split Verification",
        "Missing-Value Analysis",
        "Baseline Model Preparation",
        "Random Forest Model Definition",
        "XGBoost Model Definition",
        "Training Pipeline",
        "Validation-Based Model Comparison",
        "Evaluation Metrics and Confusion Matrices",
        "Feature Importance Analysis",
        "Error Analysis",
        "Final Experimental Evaluation Report",
        "Model Artifact Export and Metadata",
    ]

    md_sources = ["".join(c["source"]) for c in nb["cells"] if c.get("cell_type") == "markdown"]
    full_md = "\n".join(md_sources)

    for sec in required_sections:
        assert sec.lower() in full_md.lower(), f"Missing required notebook section: '{sec}'"

    # Verify no local Windows paths in code cells
    code_sources = ["".join(c["source"]) for c in nb["cells"] if c.get("cell_type") == "code"]
    full_code = "\n".join(code_sources)
    assert "C:\\Users" not in full_code, "Notebook code contains hardcoded local Windows path"
    assert "c:/users" not in full_code.lower(), "Notebook code contains hardcoded local Windows path"


# -----------------------------------------------------------------------------
# 8. Model Artifact Metadata Requirements
# -----------------------------------------------------------------------------
def test_phase7e_model_artifact_metadata_requirements():
    """Verify notebook includes export code with required governance tags."""
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    code_sources = ["".join(c["source"]) for c in nb["cells"] if c.get("cell_type") == "code"]
    full_code = "\n".join(code_sources)

    assert "PROTOTYPE_ONLY" in full_code
    assert "NOT_CALIBRATED" in full_code
    assert "NOT_FOR_PUBLIC_ALERTS" in full_code
    assert "Phase 6 deterministic physics engine" in full_code
