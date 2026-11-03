# AQUORA — PHASE 7E: KAGGLE PACKAGE PREPARATION REPORT

**Document Version:** `1.0.0-final-package-audit`  
**Phase:** Phase 7E Kaggle Package & Notebook Preparation  
**Date:** 2026-10-30  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**License:** CC-BY-NC-4.0 (GFD v1.4 / Copernicus DEM / CHIRPS / ESA WorldCover)  

---

## 1. Executive Summary & Objective

Following the official closure of Phase 7D under `EXPERIMENTAL_EVALUATION_ONLY`, Phase 7E establishes the complete, reproducible Kaggle package and training harness for experimental machine learning evaluation.

This phase strictly prepares dataset packages, documentation, anti-leakage guards, and executable preflight notebook cells. In accordance with governance constraints:
- **No model training has been executed** during this phase.
- **Authoritative Phase 7D datasets were preserved unmodified**.
- **No Git commits or pushes were executed**.
- **The Phase 6 deterministic hydrodynamic physics engine remains the primary flood authority**.

---

## 2. Package Architecture & Deliverable Register

The complete Kaggle package is assembled at [data/packages/phase7e_kaggle_package/](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/):

```
data/packages/phase7e_kaggle_package/
├── phase7c_multievent_binary_dataset.parquet   # 207,205 rows, 24 cols (Binary supervised set)
├── phase7c_multievent_binary_dataset.csv       # 207,205 rows, 24 cols (CSV export)
├── aquora_ml_feature_schema_v1.json            # Governed 11-feature schema (v1.0.0)
├── AQUORA_Phase_7E_Experimental_ML.ipynb       # Reproducible 15-section Kaggle notebook
├── DATA_DICTIONARY.md                          # Full feature dictionary with units & policies
├── TARGET_LABEL_DOCUMENTATION.md               # GFD ground truth, 0/1 labels & quarantine rules
├── SPLIT_DOCUMENTATION.md                      # Event-level disjoint holdouts & DFO 2507 policy
├── DATA_QUALITY_AND_LIMITATIONS.md             # Sensor quality, domain shift & error limitations
├── phase7e_kaggle_package_manifest.yaml        # Machine-readable SHA-256 package manifest
└── README.md                                   # Package guide & step-by-step upload instructions
```

### Reference Dataset Preservation:
To prevent unnecessary duplication of large files, the master dataset containing permanent water controls (`flood_label = -1`) is preserved separately at:
- `data/processed/phase7/ml/phase7c_multievent_dataset.parquet` (209,116 rows, 2.77 MB, SHA-256: `a3ed9802...`)
- `data/processed/phase7/ml/phase7c_multievent_dataset.csv` (209,116 rows, 42.87 MB, SHA-256: `e2e26d03...`)
- `data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet` (5,500 rows, 136.7 KB, SHA-256: `4d809d47...`)

---

## 3. Cryptographic SHA-256 Checksum Register

All files were verified directly using physical disk reads:

| Packaged File | File Size (Bytes) | SHA-256 Cryptographic Checksum | Governance Role |
| :--- | :---: | :--- | :--- |
| [phase7c_multievent_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.parquet) | 2,742,428 | `f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7` | Primary binary modeling table |
| [phase7c_multievent_binary_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.csv) | 42,479,340 | `754724649d8e856093d21986fcce0e383b21bacf922c333f9b64dcdea2fb27cb` | CSV export of binary dataset |
| [aquora_ml_feature_schema_v1.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/aquora_ml_feature_schema_v1.json) | 1,558 | `47ffdeedc73ee602f6ea1349347323b5ee3d58180fdc3b20261b94b9afee5911` | Governed predictor schema |
| [AQUORA_Phase_7E_Experimental_ML.ipynb](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/AQUORA_Phase_7E_Experimental_ML.ipynb) | 39,922 | `e0e3e77fd1f2db7fe8153242c5a74a0248e7261ec55c2be6b01f7bb1cec2ebe4` | Executable preflight notebook |
| [DATA_DICTIONARY.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/DATA_DICTIONARY.md) | 5,293 | `a3888f9b77a61c8c8003b8d5774488fb2d8079a05365023ac660bd5983e0160c` | Feature dictionary & units |
| [TARGET_LABEL_DOCUMENTATION.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/TARGET_LABEL_DOCUMENTATION.md) | 2,800 | `0c9c8187c077df8ca53b8b2a42103e1a7388374b869131264ba0eb34a04f15f0` | Ground truth & quality gates |
| [SPLIT_DOCUMENTATION.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/SPLIT_DOCUMENTATION.md) | 2,956 | `c1d19303263c95a6af910ca704671a1e7c9bfb3c6c5ec1c906b8309aab86850f` | Split policy & holdout rules |
| [DATA_QUALITY_AND_LIMITATIONS.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/DATA_QUALITY_AND_LIMITATIONS.md) | 4,134 | `fe42a16895843dbb974f08f7a3551c6cb58fd9c1b1b91eaed5fcce84f88e0ba3` | Scientific limitations & errors |
| [phase7e_kaggle_package_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/phase7e_kaggle_package_manifest.yaml) | 4,158 | `82bfebeeb3b23e3e0ec36f2ec5267e716bc26f568600863ebec6bdf4395b4515` | Authoritative package manifest |
| [README.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/README.md) | 4,004 | `ea81a4e777de0db48069acf53e003dc0cd165955b133d301851d34cc73513564` | Package upload instructions |

---

## 4. Governed Feature Schema & Anti-Leakage Policy

### A. The 11 Core National Features (`CORE_11_PREDICTORS`):
1. `rainfall_1h_mm`: `float32` (Sub-daily 1h rainfall; unobserved in daily CHIRPS; preserved strictly as explicit `NaN`)
2. `rainfall_3h_mm`: `float32` (Sub-daily 3h rainfall; unobserved in daily CHIRPS; preserved strictly as explicit `NaN`)
3. `rainfall_6h_mm`: `float32` (Sub-daily 6h rainfall; unobserved in daily CHIRPS; preserved strictly as explicit `NaN`)
4. `rainfall_24h_mm`: `float32` (CHIRPS daily rainfall on observation date, mm)
5. `rainfall_72h_mm`: `float32` (CHIRPS 3-day antecedent rainfall sum preceding observation date, mm)
6. `rainfall_anomaly_index`: `float32` (Normalized rainfall anomaly; collinear with `rainfall_72h_mm`, $r = 1.0000$)
7. `elevation_m`: `float32` (Copernicus DEM GLO-30 elevation, meters above mean sea level)
8. `slope_deg`: `float32` (Copernicus DEM 30m terrain gradient, degrees)
9. `distance_to_river_m`: `float32` (Euclidean distance to nearest JRC permanent open surface water body, meters)
10. `historical_flood_frequency`: `float32` (**STRICTLY EXCLUDED FROM MODEL TRAINING**)
11. `landcover_class`: `int32` (ESA WorldCover 2021 10m discrete land cover code; carries 4-17 year temporal gap)

### B. Strict Feature Exclusion: `historical_flood_frequency`:
- Sourced from the 2000–2018 GFD national disaster catalog.
- Evaluated on DFO 2507 (June 2004), it incorporates future disaster occurrences up to 14 years into the future.
- Possesses **zero intra-basin spatial variance**, effectively functioning as a direct event identifier shortcut.
- **Enforcement**: Excluded from `MODEL_TRAINING_FEATURES` (leaving exactly 10 model training features).

### C. Missing Rainfall Policy:
- Zero-filling missing rainfall (`1h`, `3h`, `6h`) is **strictly prohibited** because 0.0 mm falsely indicates dry weather.
- Preserved as 100% explicit `NaN`.
- XGBoost routes NaNs natively via `missing=np.nan`.
- Random Forest utilizes `SimpleImputer(strategy='median')` fitted **exclusively on the training split**.

---

## 5. Event-Level Holdout Cross-Validation & DFO 2507 Holdout Status

| Partition | Event ID | River Basin & State | Sample Count | Flood (`1`) | Dry (`0`) | Balance Strategy |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **Train** | **DFO 4499** | Lower Ganga Basin (West Bengal) | 5,000 | 2,500 | 2,500 | 50.0% / 50.0% balanced training subset |
| **Train** | **DFO 2935** | Upper Godavari Basin (Maharashtra) | 700 | 350 | 350 | 50.0% / 50.0% balanced training subset |
| **Validation** | **DFO 3372** | Upper Brahmaputra Basin (Assam) | 5,000 | 2,500 | 2,500 | 50.0% / 50.0% balanced validation subset |
| **Test** | **DFO 2507** | North Bihar / Kosi Basin (Bihar) | **196,505** | **11,435** | **185,070** | **NATURAL POPULATION (5.819% prevalence)** |

### Strict Holdout Mandate (`ALREADY_INSPECTED_HOLDOUT`):
Because DFO 2507 was previously inspected and evaluated during the Phase 7D closure audit:
1. DFO 2507 is formally designated as an **`ALREADY_INSPECTED_HOLDOUT`**.
2. It must **NEVER** be used for feature selection, hyperparameter tuning, model architecture selection, or threshold selection.
3. Model selection and threshold selection are restricted strictly to the validation split (`DFO_3372`).
4. DFO 2507 is held frozen for a final, qualified benchmark comparison.
5. All reports must state clearly that DFO 2507 is an already-inspected holdout.

---

## 6. Kaggle Notebook Architecture & Required Sections

The notebook [notebooks/AQUORA_Phase_7E_Experimental_ML.ipynb](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/notebooks/AQUORA_Phase_7E_Experimental_ML.ipynb) (and its packaged copy) implements all 15 required sections:

| Section # | Section Title | Implementation Scope & Anti-Leakage Guard |
| :---: | :--- | :--- |
| **1** | Environment setup and dependency installation | Imports, version printing, `RANDOM_SEED = 42` initialization. |
| **2** | Dataset loading and integrity verification | Dynamic Kaggle/local discovery, SHA-256 hash assertions, row count check (207,205). |
| **3** | Feature and target inspection | Adheres to `aquora_ml_feature_schema_v1.json`, excludes `historical_flood_frequency`. |
| **4** | Train/validation/test split verification | Enforces event disjointness, 0 coordinate overlap, marks DFO 2507 as `ALREADY_INSPECTED_HOLDOUT`. |
| **5** | Missing-value analysis | Confirms sub-daily rainfalls are 100% NaN, establishes training-only median imputation for RF and native routing for XGBoost. |
| **6** | Baseline model preparation | Configures Constant Prior baseline ($P=0.50$) and Inverted Elevation Ranking baseline (Brier = N/A). |
| **7** | Random Forest model definition | Implements `Pipeline([('imputer', SimpleImputer()), ('classifier', RandomForestClassifier())])`. |
| **8** | XGBoost model definition | Configures `xgb.XGBClassifier(missing=np.nan)` with logloss evaluation metric. |
| **9** | Training pipeline | Encapsulates fitting strictly on `X_train, y_train`. Guarded by `EXECUTE_TRAINING = False` for preflight. |
| **10** | Validation-based model comparison | Compares models on DFO 3372, scans thresholds $\tau \in [0.01, 0.99]$ to select $\tau^*$ maximizing validation F1. |
| **11** | Evaluation metrics and confusion matrices | Computes all 9 metrics: ROC-AUC, PR-AUC, Precision, Recall, F1, Brier, FPR, FNR, Confusion Matrix. Asserts sum == 196,505. |
| **12** | Feature importance analysis | Extracts Gini importances (RF) and Gain/Weight importances (XGBoost). |
| **13** | Error analysis | Profiles False Positives and False Negatives across Copernicus DEM elevation and ESA WorldCover classes. |
| **14** | Final experimental evaluation report | Synthesizes benchmark findings, highlights cross-basin shift and elevation baseline superiority. |
| **15** | Model artifact export and metadata | Prepares export to `./kaggle_outputs` with mandatory governance warnings: `PROTOTYPE_ONLY`, `NOT_CALIBRATED`, `NOT_FOR_PUBLIC_ALERTS`. |

---

## 7. Model Artifact Export Requirements

Every exported model artifact is tagged with standardized governance metadata:

```json
{
  "project": "AQUORA",
  "phase": "PHASE_7E_EXPERIMENTAL_ML",
  "model_version": "1.2.0-phase7e-experimental",
  "governance_status": "PROTOTYPE_ONLY",
  "calibration_status": "NOT_CALIBRATED",
  "operational_readiness": "NOT_FOR_PUBLIC_ALERTS",
  "hydrodynamic_authority": "Phase 6 deterministic physics engine remains primary authority",
  "dataset_source": "phase7c_multievent_binary_dataset.parquet",
  "dataset_sha256": "f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7",
  "features_used": [
    "rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm",
    "rainfall_24h_mm", "rainfall_72h_mm", "rainfall_anomaly_index",
    "elevation_m", "slope_deg", "distance_to_river_m", "landcover_class"
  ],
  "features_excluded": ["historical_flood_frequency"],
  "holdout_event_id": "DFO_2507",
  "holdout_designation": "ALREADY_INSPECTED_HOLDOUT"
}
```

---

## 8. Automated Test Suite Execution & Verification

A dedicated test suite was executed using `backend\.venv\Scripts\python.exe`:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_phase7_real_flood_dataset.py backend/tests/test_phase7c_multievent_dataset.py backend/tests/test_phase7d_kaggle_preflight.py backend/tests/test_phase7e_kaggle_package.py backend/tests/test_terrain_engine.py -v
```

| Test Suite | File Path | Tests Executed | Passed | Failed | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Phase 7E Kaggle Package** | `backend/tests/test_phase7e_kaggle_package.py` | 8 | **8** | 0 | **PASS** |
| **Phase 7D Preflight** | `backend/tests/test_phase7d_kaggle_preflight.py` | 6 | **6** | 0 | **PASS** |
| **Phase 7C Multi-Event Dataset** | `backend/tests/test_phase7c_multievent_dataset.py` | 6 | **6** | 0 | **PASS** |
| **Phase 7B Pilot Dataset** | `backend/tests/test_phase7_real_flood_dataset.py` | 11 | **11** | 0 | **PASS** |
| **Phase 6 Terrain Engine** | `backend/tests/test_terrain_engine.py` | 16 | **16** | 0 | **PASS** |
| **Total Consolidated Suite** | — | **47** | **47** | **0** | **100% PASS** |

---

## 9. Step-by-Step Kaggle Upload Instructions

### Step 1: Upload Dataset Package to Kaggle
1. Navigate to [kaggle.com/datasets](https://www.kaggle.com/datasets) and click **New Dataset**.
2. Set the Title to: **`aquora-phase7e-kaggle-package`**.
3. Upload all files located in [data/packages/phase7e_kaggle_package/](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/):
   - `phase7c_multievent_binary_dataset.parquet`
   - `phase7c_multievent_binary_dataset.csv`
   - `aquora_ml_feature_schema_v1.json`
   - `DATA_DICTIONARY.md`
   - `TARGET_LABEL_DOCUMENTATION.md`
   - `SPLIT_DOCUMENTATION.md`
   - `DATA_QUALITY_AND_LIMITATIONS.md`
   - `phase7e_kaggle_package_manifest.yaml`
   - `README.md`
4. Click **Create**.

### Step 2: Create Kaggle Notebook & Attach Input
1. Create a new notebook on Kaggle (Python 3 runtime).
2. Under **Input**, search for and attach the uploaded dataset: `aquora-phase7e-kaggle-package`.
3. The dataset will mount at `/kaggle/input/aquora-phase7e-kaggle-package/`.

### Step 3: Run `AQUORA_Phase_7E_Experimental_ML.ipynb`
1. Import `AQUORA_Phase_7E_Experimental_ML.ipynb` into the notebook editor.
2. In Section 9, toggle `EXECUTE_TRAINING = True` to initiate training of the Random Forest and XGBoost models.
3. The notebook will automatically execute model training, validation threshold tuning, baseline comparisons, and export governance-tagged artifacts to `./kaggle_outputs`.

---

## 10. Architectural Governance & Safety Confirmation

- **Primary Authority**: The Phase 6 deterministic hydrodynamic physics engine remains the sole authority for physical flood depths, velocities, and evacuation routing.
- **Deep Intelligence Zone**: Mumbai / Mithi River remains the only validated Deep Zone. National models use only Core National features.
- **Safety Invariant**: Machine learning models prepared here are screening prototypes only and must not be connected to automated public warning or alerting infrastructure.
- **Zero Commit / Push**: Confirmed zero Git commits and zero Git pushes during Phase 7E.
