# AQUORA Phase 3 — National Screening Model & ML Training Pipeline

## 1. Executive Summary & Objective

Phase 3 implements the complete machine learning architecture for the **National Flood Risk Screening Model (Level 1 Intelligence)** for AQUORA, continuing directly from Phase 2E (commit `76967a5`).

### Physical Authority & Screening Complementarity
- **National ML Screening** is a complementary macro-scale susceptibility estimator across India.
- The **Phase 6 deterministic physics engine** (`MithiPhysicsEngine`, `WeshFluidEngine`, `HydrodynamicEngine`) remains the physical-model authority for hydraulic simulations, flow velocities, and urban water depths.
- National screening strictly **never invokes** or mimics the physical hydraulic solver as a shortcut or side-effect.

---

## 2. Invariants & Zero-Fabrication Rules

1. **Exact 11 Core National Features**:
   - The estimator evaluates strictly the 11 `CORE_NATIONAL` features governed by `ml/aquora_ml_feature_schema_v1.json` (v1.0.0) in governed order:
     `rainfall_1h_mm`, `rainfall_3h_mm`, `rainfall_6h_mm`, `rainfall_24h_mm`, `rainfall_72h_mm`, `rainfall_anomaly_index`, `elevation_m`, `slope_deg`, `distance_to_river_m`, `historical_flood_frequency`, `landcover_class`.
   - Regional and Deep-Zone exclusive features are strictly excluded from the predictor matrix.
2. **Zero-Leakage Target Boundary**:
   - Target labels (`flood_label ∈ {-1, 0, 1}`) and SAR backscatter change ($\Delta \gamma^0_{vv}$) are kept in separate columns and metadata structures, never leaked into predictor features.
3. **Unknown Label Exclusion (`-1`)**:
   - Locations without coincident confirmed flood or defensible non-flood observations (`flood_label == -1`) are strictly excluded from supervised training splits.
   - Stable SAR backscatter is **never silently converted to non-flood (`0`)**.
4. **Data Sufficiency Gate & Zero Fabrication**:
   - If authentic supervised ground-truth is missing, imbalanced to a single class, or spans $< 2$ spatial groups, operational model training is **halted honestly**.
   - The model reports explicit `NOT_TRAINED` / `PLANNED` status; it **never fabricates synthetic predictions or fake operational metrics**.
5. **Native Missing Values vs Zero Rainfall**:
   - XGBoost histogram split routing handles missing values (`np.nan`) natively without synthetic zero-imputation.
   - Genuine observed zero rainfall is preserved as `0.0`.

---

## 3. Architecture & Implemented Components

### 3.1. Training Dataset Generator (`ml/dataset_generator.py`)
- **Class `NationalDatasetGenerator`** (governed alias `NationalScreeningDatasetGenerator`):
  - Ingests multi-point coordinates or sample definitions.
  - Samples the 11 Core National features via Phase 2E `IndiaFeaturePipelineService`.
  - Resolves spatial basin groups via `IndiaSpatialService.get_river_basin()`.
  - Emits:
    - `{name}_master.parquet`: Complete audit log with all requested samples and missingness.
    - `{name}_supervised.parquet`: Strictly filtered to `flood_label ∈ {0, 1}`.
    - `{name}_manifest.json`: Traceable audit manifest with exclusion accounting.
- **Harness CLI**: `scripts/build_national_training_dataset.py`.

### 3.2. Training & Validation Pipeline (`ml/training_pipeline.py`)
- **Class `NationalScreeningTrainingPipeline`**:
  - Implements **Spatial GroupKFold** cross-validation grouped by `basin_id` (HydroBASINS).
  - Asserts zero basin overlap between train and validation folds.
  - Evaluates out-of-fold metrics: PR-AUC, ROC-AUC, Brier score, F1-score.
  - Enforces `DataSufficiencyError` on:
    - 0 supervised samples (100% unknown labels).
    - Single-class datasets (missing positives or negatives).
    - Fewer than 2 distinct spatial basins.
  - Handles single-class training folds safely without crashing.
  - Serializes verified model artifacts with metadata, schema version `1.0.0`, feature list, and training provenance.
- **Harness CLI**: `scripts/train_national_screening_model.py`.

### 3.3. Model Registry Integration (`backend/app/services/ml_model_registry.py`)
- Replaces `NationalScreeningModelPlaceholder` with `NationalScreeningModel`.
- Preserves full backward compatibility with Phase 1 registry contracts.
- **Untrained / Missing Artifact Behavior**:
  - `is_ready = False`, `status = "PLANNED"`.
  - `predict_risk(features)` safely returns `is_ready: False`, `predicted_probability: None`, `susceptibility_grade: None`, and a clear zero-fabrication message.
  - Refuses synthetic inference; never falls back to Mumbai prototype.
- **Trained Artifact Behavior**:
  - Validates schema version (`1.0.0`) and exact 11 feature names on artifact reload.
  - Executes deterministic probability prediction in $[0, 1]$.
  - Maps to susceptibility grades: `LOW` (<0.33), `MEDIUM` (0.33-0.66), `HIGH` ($\ge 0.66$).

### 3.4. National Screening API Endpoints (`backend/app/api/v1/intelligence.py`)
- **`POST /api/v1/intelligence/screening/national`**:
  - Coordinate-based single-point national screening request.
  - Validates bounding box against India National extent $[6.5^\circ - 37.5^\circ\text{N}, 68.0^\circ - 97.5^\circ\text{E}]$.
  - Points outside extent return `status: "OUTSIDE_COVERAGE"` without fallback.
  - Points inside extent extract features via Phase 2E pipeline and dispatch to registered model.
  - Returns `NationalScreeningResponse` (status `MODEL_NOT_TRAINED` when untrained).
- **`POST /api/v1/intelligence/screening/national/batch`**:
  - Bounded batch screening for up to 250 points per request.
  - Rejects oversized batches with HTTP 422/400.

---

## 4. Operational Training Data Readiness & Gap Audit

An audit of the local repository was performed using 10 multi-basin pilot points across Ganga, Brahmaputra, Godavari, and Narmada basins:
- **Total Points Sampled**: 10
- **Total Supervised Samples**: 0
- **Unknown/Unobserved Samples (`flood_label == -1`)**: 10 (100%)
- **Data Gap Identified**:
  - Local repository lacks coincident event-window Sentinel-1 SLC/GRD SAR acquisitions for verified flood events.
  - No authoritative flood polygon catalog (e.g., CWC / Dartmouth Flood Observatory / NRSC Bhuvan) is locally ingested.
- **Resolution Under Governance Rules**:
  - Zero-fabrication rule strictly forbade inventing synthetic training labels or substituting proxies.
  - The training pipeline software is fully built and tested using isolated test fixtures.
  - The operational model registry correctly remains in `PLANNED` / `NOT_TRAINED` status with inference gracefully reporting unavailability.

---

## 5. Verification & Test Evidence

### 5.1. Dedicated Phase 3 Test Suite (`backend/tests/test_phase3_national_screening_model.py`)
- **14/14 tests passing (100%)**:
  1. `test_governed_11_features_exact_match`
  2. `test_rejection_of_leakage_and_prohibited_columns`
  3. `test_unknown_label_exclusion_in_dataset_generator`
  4. `test_missing_values_vs_authentic_zero_in_dataset`
  5. `test_training_pipeline_data_sufficiency_gate`
  6. `test_synthetic_fixture_training_and_deterministic_inference`
  7. `test_artifact_tamper_and_schema_mismatch_rejection`
  8. `test_default_registry_model_is_not_trained`
  9. `test_model_registry_catalog`
  10. `test_api_screening_single_point_untrained`
  11. `test_api_screening_outside_coverage`
  12. `test_api_screening_batch`
  13. `test_api_screening_batch_limit_enforcement`
  14. `test_physics_engine_isolation`

### 5.2. Regression Test Results
- `backend/tests/test_phase2e_feature_pipeline.py`: **14/14 passing (100%)**
- `backend/tests/test_phase1_india_expansion.py`: **10/10 passing (100%)**
- `backend/tests/test_phase2b_india_foundation.py`: **26/26 passing (100%)**
- `backend/tests/test_phase2d_sar.py`: **22/22 passing (100%)**
- **Total Passing Regression Tests**: **86/86 passing (100%)**

---

## 6. Reproducible Execution Instructions

### Generate Dataset from Coordinates
```bash
python scripts/build_national_training_dataset.py \
  --name national_screening_pilot \
  --output data/processed/ml/national_screening
```

### Train & Evaluate Model (When Authentic Data is Ingested)
```bash
python scripts/train_national_screening_model.py \
  --dataset data/processed/ml/national_screening/national_screening_pilot_supervised.parquet \
  --splits 5 \
  --seed 42
```

### Run Phase 3 Test Battery
```bash
pytest backend/tests/test_phase3_national_screening_model.py -v
```
