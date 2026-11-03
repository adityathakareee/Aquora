"""
AQUORA Phase 7D: Kaggle-Ready Real Flood Dataset Packaging Pipeline.

Packages the authoritative multi-event satellite flood dataset for Kaggle training:
1. Binary modeling dataset (15,700 samples, 50/50 balanced, flood_label in {0, 1}).
2. Master multi-event dataset (17,300 samples, including -1 permanent water controls).
3. Machine learning predictor schema (aquora_ml_feature_schema_v1.json).
4. Authoritative manifest with SHA-256 hashes, split distributions, and governance metadata.
5. README guide detailing data dictionary, Kaggle upload protocol, and scientific limitations.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

# Source Paths
PROCESSED_ML_DIR = REPO_ROOT / "data" / "processed" / "phase7" / "ml"
SRC_BINARY_PARQUET = PROCESSED_ML_DIR / "phase7c_multievent_binary_dataset.parquet"
SRC_BINARY_CSV = PROCESSED_ML_DIR / "phase7c_multievent_binary_dataset.csv"
SRC_MASTER_PARQUET = PROCESSED_ML_DIR / "phase7c_multievent_dataset.parquet"
SRC_MASTER_CSV = PROCESSED_ML_DIR / "phase7c_multievent_dataset.csv"
SRC_SCHEMA = REPO_ROOT / "ml" / "aquora_ml_feature_schema_v1.json"
SRC_MANIFEST = REPO_ROOT / "data" / "manifests" / "phase7c_multievent_dataset_manifest.yaml"

# Target Package Directory
PACKAGE_DIR = REPO_ROOT / "data" / "packages" / "phase7d_kaggle_dataset"
PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

DEST_BINARY_PARQUET = PACKAGE_DIR / "phase7c_multievent_binary_dataset.parquet"
DEST_BINARY_CSV = PACKAGE_DIR / "phase7c_multievent_binary_dataset.csv"
DEST_MASTER_PARQUET = PACKAGE_DIR / "phase7c_multievent_dataset.parquet"
DEST_MASTER_CSV = PACKAGE_DIR / "phase7c_multievent_dataset.csv"
DEST_SCHEMA = PACKAGE_DIR / "aquora_ml_feature_schema_v1.json"
DEST_MANIFEST = PACKAGE_DIR / "phase7d_kaggle_dataset_manifest.yaml"
DEST_README = PACKAGE_DIR / "README.md"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def assemble_kaggle_package():
    print("=" * 80)
    print("AQUORA PHASE 7D: PACKAGING REPRODUCIBLE KAGGLE DATASET")
    print("=" * 80)

    # 1. Verify sources exist
    for src in [SRC_BINARY_PARQUET, SRC_BINARY_CSV, SRC_MASTER_PARQUET, SRC_MASTER_CSV, SRC_SCHEMA, SRC_MANIFEST]:
        if not src.exists():
            raise FileNotFoundError(f"Missing source file: {src}")

    # 2. Copy files to package directory
    print(f"[1/4] Copying core dataset deliverables to {PACKAGE_DIR.relative_to(REPO_ROOT)}...")
    shutil.copy2(SRC_BINARY_PARQUET, DEST_BINARY_PARQUET)
    shutil.copy2(SRC_BINARY_CSV, DEST_BINARY_CSV)
    shutil.copy2(SRC_MASTER_PARQUET, DEST_MASTER_PARQUET)
    shutil.copy2(SRC_MASTER_CSV, DEST_MASTER_CSV)
    shutil.copy2(SRC_SCHEMA, DEST_SCHEMA)

    # 3. Verify hashes of copied files
    print("[2/4] Verifying cryptographic SHA-256 hashes of packaged assets...")
    hashes = {
        "binary_parquet": {
            "path": DEST_BINARY_PARQUET.name,
            "bytes": DEST_BINARY_PARQUET.stat().st_size,
            "sha256": compute_sha256(DEST_BINARY_PARQUET),
        },
        "binary_csv": {
            "path": DEST_BINARY_CSV.name,
            "bytes": DEST_BINARY_CSV.stat().st_size,
            "sha256": compute_sha256(DEST_BINARY_CSV),
        },
        "master_parquet": {
            "path": DEST_MASTER_PARQUET.name,
            "bytes": DEST_MASTER_PARQUET.stat().st_size,
            "sha256": compute_sha256(DEST_MASTER_PARQUET),
        },
        "master_csv": {
            "path": DEST_MASTER_CSV.name,
            "bytes": DEST_MASTER_CSV.stat().st_size,
            "sha256": compute_sha256(DEST_MASTER_CSV),
        },
        "feature_schema": {
            "path": DEST_SCHEMA.name,
            "bytes": DEST_SCHEMA.stat().st_size,
            "sha256": compute_sha256(DEST_SCHEMA),
        },
    }

    # Verify binary dataset matches source
    assert hashes["binary_parquet"]["sha256"] == compute_sha256(SRC_BINARY_PARQUET)
    assert hashes["master_parquet"]["sha256"] == compute_sha256(SRC_MASTER_PARQUET)

    # 4. Generate Authoritative Package Manifest
    print("[3/4] Generating authoritative package manifest...")
    package_manifest = {
        "manifest_version": "1.1.0",
        "phase": "PHASE_7D_CORRECTION_PACKAGE",
        "package_name": "aquora-phase7-real-flood-dataset",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "governance_status": "EXPERIMENTAL_EVALUATION_ONLY",
        "package_assets": hashes,
        "dataset_structure": {
            "binary_dataset_rows": 207205,
            "master_dataset_rows": 209116,
            "columns_count": 24,
            "label_column": "flood_label",
            "event_id_column": "event_id",
            "split_column": "split",
            "supervised_labels": [0, 1],
            "excluded_controls": [-1],
        },
        "split_summary": {
            "train": {
                "events": ["DFO_4499", "DFO_2935"],
                "regions": ["Lower Ganga Basin (West Bengal)", "Upper Godavari Basin (Maharashtra)"],
                "binary_samples": 5700,
                "flood_samples": 2850,
                "dry_samples": 2850,
                "permanent_water_controls": 600,
                "class_balance": "50.0% / 50.0% balanced training subset",
            },
            "validation": {
                "events": ["DFO_3372"],
                "regions": ["Upper Brahmaputra Basin (Assam)"],
                "binary_samples": 5000,
                "flood_samples": 2500,
                "dry_samples": 2500,
                "permanent_water_controls": 500,
                "class_balance": "50.0% / 50.0% balanced validation subset",
            },
            "test": {
                "events": ["DFO_2507"],
                "regions": ["North Bihar / Kosi Basin (Bihar)"],
                "binary_samples": 196505,
                "flood_samples": 11435,
                "dry_samples": 185070,
                "permanent_water_controls": 811,
                "class_balance": "NATURAL_POPULATION (5.819% flood prevalence; zero artificial rebalancing)",
            },
        },
        "governed_features": {
            "schema_name": "aquora_ml_feature_schema_v1",
            "core_11_features": [
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
            ],
            "model_training_features_10": [
                "rainfall_1h_mm",
                "rainfall_3h_mm",
                "rainfall_6h_mm",
                "rainfall_24h_mm",
                "rainfall_72h_mm",
                "rainfall_anomaly_index",
                "elevation_m",
                "slope_deg",
                "distance_to_river_m",
                "landcover_class",
            ],
            "feature_leakage_and_semantics_audit": {
                "historical_flood_frequency": {
                    "source": "GFD 2000-2018 national catalog",
                    "audit_finding": "EXCLUDED_FROM_MODEL_TRAINING",
                    "rationale": "Future data leakage (computed from 2000-2018 catalog, encompassing events up to 14 years after DFO 2507) and zero intra-basin spatial variance (basin event proxy).",
                },
                "rainfall_anomaly_index": {
                    "source": "Derived from rainfall_72h_mm and fixed baseline parameters",
                    "audit_finding": "COLLINEAR_WITH_RAINFALL_72H",
                    "rationale": "Exact linear affine transformation within each event footprint (r = 1.0000). Provides zero independent variance but introduces no future leakage.",
                },
                "distance_to_river_m": {
                    "source": "GFD Band 5 (JRC Global Surface Water permanent water mask)",
                    "audit_finding": "SEMANTIC_CLARIFICATION_REQUIRED",
                    "rationale": "Represents Euclidean metric distance to perennial open water bodies (lakes, reservoirs, major river channels), not an explicit vector river network. Retained for schema compliance.",
                },
                "landcover_class": {
                    "source": "ESA WorldCover 2021 (10m)",
                    "audit_finding": "TEMPORAL_MISMATCH_DOCUMENTED",
                    "rationale": "2021 baseline introduces a 4-to-17 year temporal gap relative to historical disaster events (2004, 2006, 2008, 2017).",
                },
                "unobserved_subdaily_rainfall": {
                    "features": ["rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm"],
                    "treatment": "PRESERVED_AS_EXPLICIT_NAN",
                    "policy": "Zero synthetic filling or imputation; native tree routing required",
                },
            },
        },
        "scientific_limitations": [
            "Natural Test Class Imbalance: Held-out test set preserves the unskewed natural population (5.82% flood prevalence, 185,070 dry vs 11,435 flood). Precision and PR-AUC reflect real-world false alarm vulnerability.",
            "Cross-Basin Generalization Gap: Absolute elevation does not generalize across distinct river basins without relative hydrologic normalization (e.g. HAND); the model underperforms simple inverted elevation ranking within the test basin.",
            "Temporal Mismatch: Land cover is derived from ESA WorldCover 2021 (10m), carrying temporal offsets for historical events.",
            "Sub-daily Rainfall Absence: Daily CHIRPS product cannot resolve 1h, 3h, or 6h flash storm peaks; features are strictly missing (NaN).",
            "Governance Status: EXPERIMENTAL_EVALUATION_ONLY. Not calibrated or approved for civil defense, flood forecasting, or evacuation planning.",
        ],
    }

    with open(DEST_MANIFEST, "w") as f:
        yaml.dump(package_manifest, f, sort_keys=False, indent=2)

    # Copy to project manifests directory as well
    project_manifest_path = REPO_ROOT / "data" / "manifests" / "phase7d_kaggle_dataset_manifest.yaml"
    shutil.copy2(DEST_MANIFEST, project_manifest_path)

    # 5. Write Kaggle Package README
    print("[4/4] Writing package README and Kaggle ingestion instructions...")
    readme_content = f"""# AQUORA Phase 7D: Multi-Event Real Flood Dataset for Kaggle Training

**Dataset Name:** `aquora-phase7-real-flood-dataset`  
**Governance Decision:** `EXPERIMENTAL_EVALUATION_ONLY`  
**License:** CC-BY-NC-4.0 (GFD v1.4 / Copernicus DEM / CHIRPS / ESA WorldCover)  
**Created:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  

---

## 1. Dataset Overview

This dataset provides authentic, multi-event satellite flood inundation observations across 4 major Indian river basins. It is specifically prepared for benchmarking machine learning flood risk models under **strict event-level holdout cross-validation**:

- **Binary Training & Evaluation Dataset** (`phase7c_multievent_binary_dataset.parquet` / `.csv`):
  * **207,205 rows**, 24 columns.
  * **Train Split**: 5,700 samples (50.0% flood / 50.0% dry balanced for training stability).
  * **Validation Split**: 5,000 samples (50.0% flood / 50.0% dry).
  * **Test Split (Held-Out)**: **196,505 samples** representing the **complete natural valid-data population** of DFO 2507 (11,435 flood, 185,070 dry; **5.819% natural prevalence**). Zero artificial balancing or downsampling.
  * Quarantines permanent water controls (`flood_label = -1`) from binary evaluation.
- **Master Dataset** (`phase7c_multievent_dataset.parquet` / `.csv`):
  * **209,116 rows**, 24 columns.
  * Includes 1,911 JRC Global Surface Water permanent water controls (`flood_label = -1`).

---

## 2. Event-Level Disjoint Splits

| Split Role | Event ID | River Basin & Region | Observation Date | Binary Samples | Flood (`1`) | Dry (`0`) | Permanent Water (`-1`) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **Train** | **DFO 4499** | Lower Ganga Basin (West Bengal) | `2017-07-27` | 5,000 | 2,500 | 2,500 | 500 |
| **Train** | **DFO 2935** | Upper Godavari Basin (Maharashtra) | `2006-07-28` | 700 | 350 | 350 | 100 |
| **Validation** | **DFO 3372** | Upper Brahmaputra Basin (Assam) | `2008-08-30` | 5,000 | 2,500 | 2,500 | 500 |
| **Test (Holdout)** | **DFO 2507** | North Bihar / Kosi Basin (Bihar) | `2004-06-20` | **196,505** | **11,435** | **185,070** | **811** |

> **Anti-Leakage Mandate**: The test event (`DFO_2507`) and validation event (`DFO_3372`) must NEVER be used for training, preprocessing, or hyperparameter selection.

---

## 3. Governed Predictor Schema & Leakage Audit

Conforms strictly to `ml/aquora_ml_feature_schema_v1.json`:
1. `rainfall_1h_mm`: `float32` (Unobserved; preserved as explicit `NaN`)
2. `rainfall_3h_mm`: `float32` (Unobserved; preserved as explicit `NaN`)
3. `rainfall_6h_mm`: `float32` (Unobserved; preserved as explicit `NaN`)
4. `rainfall_24h_mm`: `float32` (CHIRPS daily rainfall on observation date, mm)
5. `rainfall_72h_mm`: `float32` (CHIRPS 3-day antecedent rainfall sum, mm)
6. `rainfall_anomaly_index`: `float32` (Collinear with `rainfall_72h_mm`, r = 1.0)
7. `elevation_m`: `float32` (Copernicus DEM GLO-30 elevation, meters)
8. `slope_deg`: `float32` (Copernicus DEM 30m terrain gradient, degrees)
9. `distance_to_river_m`: `float32` (Euclidean distance to JRC perennial water bodies, meters)
10. `historical_flood_frequency`: `float32` (**EXCLUDED FROM MODEL FITTING**: Leaks future 2000-2018 catalog and lacks intra-basin variance)
11. `landcover_class`: `int32` (ESA WorldCover 2021 10m discrete class code; carries 4-17 year temporal gap)

---

## 4. How to Use on Kaggle

### Step 1: Upload Dataset to Kaggle
1. Go to [kaggle.com/datasets](https://www.kaggle.com/datasets) and click **New Dataset**.
2. Set the Title to: `aquora-phase7-real-flood-dataset`.
3. Drag and drop all files from this directory (`data/packages/phase7d_kaggle_dataset/`).
4. Click **Create**.

### Step 2: Attach to Notebook
1. In your Kaggle Notebook, click **Add Input** (top right).
2. Search for your dataset `aquora-phase7-real-flood-dataset` and click **Add**.
3. Files will be mounted automatically at:
   `/kaggle/input/aquora-phase7-real-flood-dataset/phase7c_multievent_binary_dataset.parquet`

### Step 3: Run the Official Notebook
1. Upload or paste the code from `notebooks/aquora_national_screening_kaggle.ipynb`.
2. The notebook will automatically detect the input dataset, train strictly on `split == 'train'`, validate on `split == 'validation'`, and evaluate on the unskewed natural test event `split == 'test'`.
"""

    with open(DEST_README, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("\n" + "=" * 80)
    print("PHASE 7D KAGGLE DATASET PACKAGE CREATED SUCCESSFULLY!")
    print(f"Package Directory: {PACKAGE_DIR.relative_to(REPO_ROOT)}")
    print(f"Total Package Size: {sum(f.stat().st_size for f in PACKAGE_DIR.glob('*')):,} bytes")
    print("=" * 80)


if __name__ == "__main__":
    assemble_kaggle_package()
