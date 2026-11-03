# AQUORA — DATASET AND MODEL INVENTORY

**Document ID:** `AQUORA_DATASET_AND_MODEL_INVENTORY`  
**Audit Date:** 2026-11-02  
**Repository:** `Sarveshk-2006/Aquoraa`  
**Classification:** Technical Verification & Traceability Audit  
**Authoritative Hydrodynamic Authority:** [engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py)  

---

## 1. Executive Summary

This inventory documents all verified training datasets, reference tables, feature schemas, and trained machine learning artifacts within the AQUORA repository. Each asset has been verified via direct disk read, cryptographic SHA-256 hash calculation, row/column inspection, and runtime code reference tracing.

---

## 2. Training and Reference Datasets

### A. Phase 7E Kaggle Multi-Event Binary Training Dataset

* **Canonical Path:** [data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.parquet)
* **Secondary Export Path:** [data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.csv)
* **Format:** Apache Parquet (snappy compressed) / Comma-Separated Values (CSV)
* **File Size:**
  * Parquet: `2,742,428 bytes` (~2.62 MB)
  * CSV: `42,479,340 bytes` (~40.51 MB)
* **Dimensions:** `207,205 rows × 24 columns`
* **Target Column:** `flood_label` (Binary integer: `0 = dry ground`, `1 = flood inundation`)
* **Class Distribution:**
  * `0 (Dry)`: 190,420 samples (91.90%)
  * `1 (Flood)`: 16,785 samples (8.10%)
  * Total: 207,205 samples (Imbalance ratio: 11.35 : 1)
* **Partition Split Distribution (Event-Disjoint):**
  * `train` (5,700 rows, 2.75%):
    * DFO 2935 (Gujarat 2006): 2,850 rows (450 flood, 2,400 dry)
    * DFO 4499 (Assam 2017): 2,850 rows (450 flood, 2,400 dry)
    * Total Train: 900 flood (15.79%), 4,800 dry (84.21%)
  * `validation` (5,000 rows, 2.41%):
    * DFO 3372 (Bihar 2008): 5,000 rows (500 flood, 4,500 dry)
    * Total Validation: 500 flood (10.00%), 4,500 dry (90.00%)
  * `test` (196,505 rows, 94.84%):
    * DFO 2507 (Andhra Pradesh / Krishna-Godavari 2005): 196,505 rows (15,385 flood, 181,120 dry)
    * **Governance Status:** STRICTLY QUARANTINED HOLDOUT. No validation or hyperparameter tuning permitted.
* **Geographic Events Represented:**
  1. `DFO_2935`: Tapi / Narmada Basin, Gujarat (August 2006)
  2. `DFO_4499`: Brahmaputra Basin, Assam (July 2017)
  3. `DFO_3372`: Kosi River Basin, Bihar (August 2008)
  4. `DFO_2507`: Krishna-Godavari Delta, Andhra Pradesh (September 2005)
* **Governed Features (23 Columns + 1 Target):**
  1. `rainfall_1h_mm` (Explicit `NaN` preserved; sub-daily unobserved in CHIRPS)
  2. `rainfall_3h_mm` (Explicit `NaN` preserved)
  3. `rainfall_6h_mm` (Explicit `NaN` preserved)
  4. `rainfall_24h_mm` (CHIRPS daily accumulation, mm)
  5. `rainfall_72h_mm` (CHIRPS 3-day antecedent sum, mm)
  6. `rainfall_anomaly_index` (Normalized deviation from baseline)
  7. `elevation_m` (Copernicus DEM GLO-30, meters)
  8. `slope_deg` (Copernicus DEM 30m gradient, degrees)
  9. `aspect_deg` (Terrain azimuthal orientation, degrees)
  10. `curvature` (Surface profile curvature)
  11. `flow_accumulation` (D8 upstream contributing cells)
  12. `twi` (Topographic Wetness Index: $\ln(a / \tan\beta)$)
  13. `dist_to_river_km` (Euclidean distance to JRC permanent water, km)
  14. `dist_to_coast_km` (Euclidean distance to shoreline, km)
  15. `soil_cn` (SCS-CN runoff curve number)
  16. `drainage_capacity_proxy` (Hydraulic drainage impedance index)
  17. `landcover_code` (ESA WorldCover 2021 discrete class)
  18. `builtup_fraction` (Sub-pixel impermeable built environment ratio)
  19. `precip_1d_mm`, `precip_3d_mm`, `precip_7d_mm`, `precip_14d_mm`
  20. `antecedent_moisture_index`
  21. `event_id`, `sar_observed_date`, `split_assignment`, `latitude`, `longitude`
* **Cryptographic SHA-256 Checksums:**
  * Parquet: `f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7`
  * CSV: `754724649d8e856093d21986fcce0e383b21bacf922c333f9b64dcdea2fb27cb`
* **Current Existence in Repository:** YES (Fully accessible on disk).
* **Runtime Accessibility to Backend:** NO. Stored as an offline package in `data/packages/phase7e_kaggle_package/`. Not loaded by any runtime API route or background worker.

---

### B. Phase 7F DFO 3382 Mahanadi Native Resolution Dataset

* **Canonical Path:** [data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet)
* **Secondary Export Path:** [data/processed/phase7/datasets/dfo3382_native_resolution_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/datasets/dfo3382_native_resolution_dataset.csv)
* **Format:** Apache Parquet (snappy compressed) / Comma-Separated Values (CSV)
* **File Size:**
  * Parquet: `120,355,669 bytes` (~114.78 MB)
  * CSV: `156,524,131 bytes` (~149.27 MB)
* **Dimensions:** `1,090,194 rows × 78 columns`
* **Valid DEM Modeling Domain:** `173,950 rows` across 27 HydroBASINS Level 8 sub-basins with contiguous Copernicus DEM mosaic coverage.
* **Target Column:** `flood_label` (Binary integer: `0 = dry ground`, `1 = flood inundation`)
* **Class Distribution:**
  * *Full Dataset (1,090,194 rows):*
    * `0 (Dry)`: 1,065,208 (97.71%)
    * `1 (Flood)`: 24,986 (2.29%)
  * *Valid DEM Modeling Domain (173,950 rows):*
    * `0 (Dry)`: 169,733 (97.58%)
    * `1 (Flood)`: 4,217 (2.42%)
* **Spatial Split Distribution (HydroBASINS Spatial Blocking):**
  * `TRAIN` (15 Western sub-basins, lon < 84.8°E): 72,140 rows (1,036 flood [1.44%], 71,104 dry)
  * `VAL` (6 Central sub-basins, 84.8°E ≤ lon < 85.5°E): 53,134 rows (797 flood [1.50%], 52,337 dry)
  * `TEST` (6 Eastern delta sub-basins, lon ≥ 85.5°E): 48,676 rows (2,384 flood [4.90%], 46,292 dry)
* **Geographic Event Represented:**
  * `DFO_3382`: Mahanadi River Basin & Odisha Delta (September 2008 flood disaster, IMD `UEI-IMD-FL-2008-0095`).
* **13 Retained Predictor Features (Evaluated in Stage 4/4.1):**
  1. `elevation_mean_m` (Aggregated 250m mean Copernicus elevation)
  2. `slope_mean_deg` (Mean topographic slope)
  3. `twi_mean` (Mean Topographic Wetness Index)
  4. `aspect_mean_cos` (North-South hillslope orientation)
  5. `aspect_mean_sin` (East-West hillslope orientation)
  6. `aspect_circular_var` (Terrain directional dispersion)
  7. `aspect_flat_fraction` (Fraction of zero-slope alluvial cells)
  8. `plan_curvature_mean` (Transverse flow convergence/divergence)
  9. `flow_accum_log10_max` (Peak upstream contributing area)
  10. `dist_to_river_mean_m` (Euclidean distance to HydroRIVERS streams)
  11. `dist_to_distributary_min_m` (Distance to delta distributary channels)
  12. `strahler_order_max` (Maximum Strahler stream order)
  13. `land_water_dry_fraction` (Terrestrial land fraction from optical mask)
* **Explicitly Excluded Features (22 columns):**
  * `rainfall_accum_6h_mm`, `rainfall_accum_24h_mm`, `rainfall_accum_72h_mm` (100% missing retrospective observations; zero fabrication enforced)
  * `historical_flood_frequency` (future disaster leakage excluded)
  * `elevation_std_m`, `profile_curvature_mean`, `elevation_min_m`, `elevation_max_m`, `elevation_median_m` (severe multicollinearity $r > 0.95$)
* **Cryptographic SHA-256 Checksums:**
  * Parquet: `ba0f4df5681add4acead2b91489a61be77e8a3897d7d1bdedbd5be6f448db81f`
  * CSV: `2092cbfffa201b1a50a1cbb1599e2b10a26e8dd7c0b050f242db7a2c72b73f8b`
* **Current Existence in Repository:** YES (Fully accessible on disk).
* **Runtime Accessibility to Backend:** NO direct query of the 120 MB dataset file. However, its downstream evaluation artifacts (`dfo3382_robustness_metrics.json`, `dfo3382_feature_ablation.csv`, and `dfo3382_water_features.geojson`) ARE accessed and served by `/api/v1/intelligence/regional/mahanadi/` endpoints.

---

### C. Reference Pilot Datasets and Master Tables

| Dataset Identifier | File Path | Format | Size | Rows × Cols | Target / Content | SHA-256 Checksum |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **Phase 7C Master Multi-Event Table** | [data/processed/phase7/ml/phase7c_multievent_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_dataset.parquet) | Parquet | 2,766,983 B | 209,116 × 24 | Preserves permanent water control cells (`flood_label = -1`) | `a3ed9802c38865c3...` |
| **Phase 7 GFD Pilot Dataset** | [data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet) | Parquet | 136,711 B | 5,500 × 24 | Pilot multi-sensor alignment test set | `4d809d475ce99818...` |
| **Phase 7 GFD Pilot Binary Dataset** | [data/processed/phase7/ml/phase7_gfd_pilot_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_binary_dataset.parquet) | Parquet | 128,470 B | 5,000 × 24 | Pilot binary calibration set | `55d3f8f117bc0961...` |
| **Mahanadi HydroBASINS Sub-basins** | [data/processed/phase7/boundaries/mahanadi_hydrobasins/mahanadi_hydrobasins_lev08.geojson](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/boundaries/mahanadi_hydrobasins/mahanadi_hydrobasins_lev08.geojson) | GeoJSON | 2,410,512 B | 27 Features | 27 Level 8 watershed boundary polygons | `6f38ba230e7912...` |
| **Mahanadi Water Features GeoJSON** | [data/processed/phase7/geojson/dfo3382_water_features.geojson](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/geojson/dfo3382_water_features.geojson) | GeoJSON | 1,845,910 B | Vector GIS | MODIS & JRC permanent water polygons | `31bcde418088fa...` |

---

## 3. Trained Model Artifacts

### A. Deep Intelligence Zone XGBoost Prototype (`aquora_xgboost_prototype.joblib`)

* **Exact Path:** [backend/data/models/aquora_xgboost_prototype.joblib](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/data/models/aquora_xgboost_prototype.joblib)
* **Associated Metadata:** [backend/data/models/aquora_xgboost_metadata.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/data/models/aquora_xgboost_metadata.json)
* **Model Class:** `xgboost.sklearn.XGBClassifier` (Version: XGBoost 2.0+, Python 3.12 compatible)
* **File Size:** `258,598 bytes` (~252.5 KB)
* **Cryptographic SHA-256 Checksum:** `ba96ed00159dabd8f332674c113e96310e8bf0284a07f0f31485df7103aebe4d`
* **Training Date:** `2026-09-16T19:41:44.127235+00:00`
* **Training Dataset & Split:**
  * Derived from Mumbai historical events: Train (E02, E04, E05, E06: 746,368 rows), Val (E03: 186,592 rows), Test (E07: 186,592 rows).
  * Target: `observed_flood_candidate` (derived from Sentinel-1 SAR bitemporal backscatter drop).
* **Feature Schema (12 Features in Exact Order):**
  1. `elevation_m`
  2. `slope_deg`
  3. `aspect_deg`
  4. `flow_accumulation_cells`
  5. `drainage_proxy_score`
  6. `landcover_class`
  7. `built_up_fraction`
  8. `distance_to_road_m`
  9. `distance_to_waterway_m`
  10. `rainfall_30min_mm`
  11. `rainfall_intensity_mm_hr`
  12. `tide_level_m`
* **Hyperparameters:** `n_estimators=100`, `max_depth=6`, `learning_rate=0.05`, `subsample=0.8`, `colsample_bytree=0.8`, `scale_pos_weight=48.9009` (train partition only), `random_state=42`.
* **Frozen Threshold:** `0.5000`
* **Model Test Performance:** Accuracy: 0.1983, Precision: 0.0775, Recall: 0.9533, F1: 0.1434, ROC-AUC: 0.5914, PR-AUC: 0.0890.
* **Model Load Test:** PASSED. Successfully instantiated and produced probability predictions in isolated test.
* **Runtime Application Integration:** LOADED by [backend/app/services/calibration_service.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/calibration_service.py) and registered as `MumbaiMithiDeepModel` in [backend/app/services/ml_model_registry.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/ml_model_registry.py).
* **Runtime Execution Status:** **DEGRADED AT RUNTIME**. In cell inspection (`/api/v1/digital-twin/cells/inspect`), feature extraction fails because raster `data/processed/phase7/landcover/landcover_class_30m.tif` is not present on disk. Zero-fabrication logic catches this and safely sets `prototype_ml_score: null` and `ml_status: UNAVAILABLE`.

---

### B. Phase 7E Kaggle Random Forest (`aquora_rf_model_v1.joblib`)

* **Intended Path:** `data/packages/phase7e_kaggle_package/models/aquora_rf_model_v1.joblib`
* **Status:** **NOT FOUND ON DISK / NEVER SERIALIZED**.
* **Rationale:** Phase 7E governance strictly limited work to dataset packaging, schema definition, and Kaggle notebook creation (`AQUORA_Phase_7E_Experimental_ML.ipynb`). The training cells were prepared for external Kaggle GPU runtime and were not committed back as binary model weights.
* **Runtime Application Status:** NOT INTEGRATED (Cannot be loaded; no backend code references this filename).

---

### C. Phase 7E Kaggle XGBoost (`aquora_xgb_model_v1.json`)

* **Intended Path:** `data/packages/phase7e_kaggle_package/models/aquora_xgb_model_v1.json`
* **Status:** **NOT FOUND ON DISK / NEVER SERIALIZED**.
* **Rationale:** Same as Phase 7E Random Forest above.
* **Runtime Application Status:** NOT INTEGRATED.

---

### D. Phase 7F DFO 3382 Mahanadi Experimental Models

* **Intended Directory:** `data/processed/phase7/experiments/models/`
* **Inspected Status:** **DIRECTORY EXISTS BUT IS COMPLETELY EMPTY (0 files)**.
* **Diagnostic Execution:** The exploration scripts ([scripts/run_phase7f_stage4_experiments.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/run_phase7f_stage4_experiments.py) and [scripts/run_phase7f_stage4_1_robustness_audit.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/run_phase7f_stage4_1_robustness_audit.py)) trained Logistic Regression, Random Forest, and XGBoost models in Python memory, computed test statistics, wrote tabular metrics/ablation results to CSV/JSON, and terminated without saving model weights to disk.
* **Frozen Validation Thresholds (Recorded in JSON):**
  * XGBoost Best Validation Threshold: `0.0800` (Validation F1: 0.1770, Test F1: 0.1416)
  * Random Forest Best Validation Threshold: `0.0700` (Validation F1: 0.1724, Test F1: 0.1348)
  * Logistic Regression Best Validation Threshold: `0.0300` (Validation F1: 0.0863, Test F1: 0.1068)
* **Runtime Application Status:** Backend API `/api/v1/intelligence/regional/mahanadi/experiments` reads the precomputed evaluation metrics and feature importance tables directly. It does NOT execute dynamic model inference.

---

### E. National Screening Model (`aquora_national_screening_model.joblib`)

* **Expected Path:** `ml/models/aquora_national_screening_model.joblib`
* **Status:** **NOT FOUND ON DISK / NOT YET TRAINED**.
* **Implementation in Code:** [NationalScreeningModel](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/ml_model_registry.py#L81) in `ml_model_registry.py`.
* **Runtime Behavior:** Returns `is_ready: False`, `model_status: 'PLANNED'`, `predicted_probability: None`, with message: *"National Screening Model is not trained. Authentic nationwide labeled datasets remain uningested. Zero-fabrication rule strictly prohibits synthetic inference."*
* **Compliance:** 100% compliant with zero-fabrication rules.

---

### F. Regional Basin Model (`aquora_regional_basin_model.joblib`)

* **Expected Path:** `ml/models/aquora_regional_basin_model.joblib`
* **Status:** **NOT FOUND ON DISK / NOT YET TRAINED**.
* **Implementation in Code:** [RegionalBasinModel](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/ml_model_registry.py#L219) in `ml_model_registry.py`.
* **Runtime Behavior:** Returns `is_ready: False`, `model_status: 'PLANNED'`, `predicted_probability: None`. When basic rainfall, slope, and river proximity inputs are provided, it emits an uncalibrated heuristic watershed exposure index (0.0 to 1.0) while clearly stating that the ML model is not trained.
* **Compliance:** 100% compliant with zero-fabrication rules.

---

## 4. Summary Matrix of Model Artifacts

| Model Name / Identifier | File Path | Format | Status on Disk | Loaded at Runtime? | Target Domain | Inference Mode |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **XGBoost Prototype v1** | `backend/data/models/aquora_xgboost_prototype.joblib` | Joblib | **EXISTS** (258 KB) | Yes (`CalibrationService`) | Mumbai / Mithi | Degrades to `UNAVAILABLE` at runtime due to missing landcover raster |
| **Phase 7E Random Forest** | `data/packages/.../aquora_rf_model_v1.joblib` | Joblib | **MISSING** | No | Multi-Event India | Offline Kaggle notebook only |
| **Phase 7E XGBoost** | `data/packages/.../aquora_xgb_model_v1.json` | JSON | **MISSING** | No | Multi-Event India | Offline Kaggle notebook only |
| **Phase 7F DFO 3382 Models** | `data/processed/.../experiments/models/*` | N/A | **MISSING** | No | Mahanadi Basin | Offline evaluation; metrics served via static JSON |
| **National Screening Model** | `ml/models/aquora_national_screening_model.joblib` | Joblib | **MISSING** | Yes (Registry stub) | India National | Reports `PLANNED` / `is_ready=False` (Zero fabrication) |
| **Regional Basin Model** | `ml/models/aquora_regional_basin_model.joblib` | Joblib | **MISSING** | Yes (Registry stub) | India Basins | Reports `PLANNED` / Heuristic index (Zero fabrication) |
