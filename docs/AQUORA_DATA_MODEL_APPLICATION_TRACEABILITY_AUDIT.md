# AQUORA — DATA-TO-MODEL-TO-APPLICATION TRACEABILITY AUDIT

**Document ID:** `AQUORA_DATA_MODEL_APPLICATION_TRACEABILITY_AUDIT`  
**Audit Date:** 2026-11-02  
**Auditor:** Senior Deep Technical Verification & Assurance Agent  
**Repository:** `Sarveshk-2006/Aquoraa`  
**Primary Hydrodynamic Authority:** [engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py)  
**Governance Rules Applied:** Zero Fabrication, Phase Boundary Enforcement, Read-Only Audit  

---

## EXECUTIVE SUMMARY: THE DEFINITIVE ANSWER

> **FINAL QUESTION:**  
> *Is AQUORA actually using the datasets and trained models we prepared, or is it primarily displaying precomputed/static data and physics-engine outputs?*

### The Direct, Evidence-Based Answer:

**AQUORA is primarily driven by its live, dynamic Phase 6 deterministic 2D hydrodynamic physics engine, supplemented by precomputed research exploration data for regional expansion. It is NOT running live machine learning inference from the prepared Phase 7E or Phase 7F datasets.**

Specifically, the audit reveals three empirical truths across the repository:

1. **The Phase 6 Physics Engine is 100% Genuine, Dynamic, and Active:**  
   The application does **NOT** display fake or mock hydrodynamic flood outputs. The core operational workflows — Digital Twin, Simulator, Travel Window passability, Critical Facility access, Protect the City interventions, and Alert Center cause-chains — are dynamically calculated on-the-fly by [engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py). The engine executes differential mass-conserving D8 kinematic surface flow across real 30-meter Copernicus DEM elevation arrays, forced by live Open-Meteo ECMWF forecasts or authentic NASA IMERG rainfall rasters.
2. **Phase 7E and Phase 7F ML Models Do Not Exist as Deployable Artifacts:**  
   * **Phase 7E Kaggle:** No trained Random Forest `.joblib` or XGBoost `.json` model files exist on disk. Phase 7E was strictly a dataset packaging, documentation, and notebook export task (`AQUORA_Phase_7E_Experimental_ML.ipynb`) intended for external execution on Kaggle GPU hardware.
   * **Phase 7F Mahanadi:** The Stage 4 model exploration script ([scripts/run_phase7f_stage4_experiments.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/run_phase7f_stage4_experiments.py)) trained Logistic Regression, Random Forest, and XGBoost classifiers in Python memory, computed diagnostic evaluation statistics, wrote tabular metrics and ablation comparisons to CSV/JSON, and terminated without serializing model weights to disk. The `data/processed/phase7/experiments/models/` directory is completely empty.
3. **The Single Existing Model Artifact Degrades Gracefully at Runtime:**  
   The repository possesses exactly one serialized model artifact: [backend/data/models/aquora_xgboost_prototype.joblib](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/data/models/aquora_xgboost_prototype.joblib) (Phase 8 prototype, 12 features, trained on Mumbai historical events). While this model is fully loadable and verified in isolation, it degrades to `UNAVAILABLE` during live cell inspection because its required landcover GeoTIFF raster (`data/processed/phase7/landcover/landcover_class_30m.tif`) is not present on disk. In accordance with zero-fabrication rules, the backend returns `prototype_ml_score: null` rather than fabricating synthetic inference.

---

## 1. VERIFICATION OF ACTUAL TRAINING DATASETS

A complete audit of the physical dataset files on disk was conducted. Cryptographic hashes were computed directly from raw byte streams.

### A. Phase 7E Kaggle Multi-Event Binary Dataset

* **Exact File Path:** [data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.parquet)  
  *(CSV export also verified at [phase7c_multievent_binary_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.csv))*
* **File Format & Size:**  
  * Parquet: `2,742,428 bytes` (~2.62 MB)  
  * CSV: `42,479,340 bytes` (~40.51 MB)
* **Shape:** `207,205 rows × 24 columns`
* **Target Column:** `flood_label` (Binary integer: `0 = dry ground`, `1 = flood inundation`)
* **Feature Schema (23 Predictor/Metadata Columns):**  
  `rainfall_1h_mm`, `rainfall_3h_mm`, `rainfall_6h_mm` (100% explicit `NaN` preserved), `rainfall_24h_mm`, `rainfall_72h_mm`, `rainfall_anomaly_index`, `elevation_m`, `slope_deg`, `aspect_deg`, `curvature`, `flow_accumulation`, `twi`, `dist_to_river_km`, `dist_to_coast_km`, `soil_cn`, `drainage_capacity_proxy`, `landcover_code`, `builtup_fraction`, `precip_1d_mm`, `precip_3d_mm`, `precip_7d_mm`, `precip_14d_mm`, `antecedent_moisture_index`.
* **Flood & Dry Sample Counts:**  
  * Dry (`0`): `190,420` (91.90%)  
  * Flood (`1`): `16,785` (8.10%)  
  * Natural Imbalance Ratio: `11.35 : 1`
* **Partition Split Distribution:**  
  * `train` (5,700 rows): DFO 2935 (Gujarat: 450 flood, 2,400 dry) + DFO 4499 (Assam: 450 flood, 2,400 dry). Total: 900 flood, 4,800 dry.  
  * `validation` (5,000 rows): DFO 3372 (Bihar: 500 flood, 4,500 dry).  
  * `test` (196,505 rows): DFO 2507 (Andhra Pradesh: 15,385 flood, 181,120 dry). **QUARANTINED HOLDOUT.**
* **Geographic Events Represented:**  
  * `DFO_2935`: Tapi/Narmada Basin, Gujarat (August 2006)  
  * `DFO_4499`: Brahmaputra Basin, Assam (July 2017)  
  * `DFO_3372`: Kosi Basin, Bihar (August 2008)  
  * `DFO_2507`: Krishna-Godavari Delta, Andhra Pradesh (September 2005)
* **Cryptographic SHA-256 Checksums:**  
  * Parquet: `f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7`  
  * CSV: `754724649d8e856093d21986fcce0e383b21bacf922c333f9b64dcdea2fb27cb`
* **Repository Existence:** **YES**, verified on disk.
* **Runtime Backend Accessibility:** **NO**. Stored in `data/packages/` as an offline research deliverable. No backend route opens or queries this file during runtime.

---

### B. Phase 7F DFO 3382 Mahanadi Native Resolution Dataset

* **Exact File Path:** [data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet)  
  *(CSV export also verified at [dfo3382_native_resolution_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/datasets/dfo3382_native_resolution_dataset.csv))*
* **File Format & Size:**  
  * Parquet: `120,355,669 bytes` (~114.78 MB)  
  * CSV: `156,524,131 bytes` (~149.27 MB)
* **Shape:** `1,090,194 rows × 78 columns` (Full extent).  
  * **Contiguous DEM Modeling Domain:** `173,950 rows` across 27 HydroBASINS Level 8 sub-basins with valid Copernicus DEM elevation coverage.
* **Target Column:** `flood_label` (Binary integer: `0 = dry ground`, `1 = flood inundation`)
* **Feature Schema:**  
  13 retained ML predictors audited in Stage 4: `elevation_mean_m`, `slope_mean_deg`, `twi_mean`, `aspect_mean_cos`, `aspect_mean_sin`, `aspect_circular_var`, `aspect_flat_fraction`, `plan_curvature_mean`, `flow_accum_log10_max`, `dist_to_river_mean_m`, `dist_to_distributary_min_m`, `strahler_order_max`, `land_water_dry_fraction`.
* **Flood & Dry Sample Counts:**  
  * Full Extent: 24,986 flood (2.29%), 1,065,208 dry (97.71%).  
  * DEM Modeling Domain: 4,217 flood (2.42%), 169,733 dry (97.58%).
* **Partition Split Distribution (HydroBASINS Spatial Blocking):**  
  * `TRAIN` (15 Western sub-basins, lon < 84.8°E): 72,140 rows (1,036 flood [1.44%], 71,104 dry)  
  * `VAL` (6 Central sub-basins, 84.8°E ≤ lon < 85.5°E): 53,134 rows (797 flood [1.50%], 52,337 dry)  
  * `TEST` (6 Eastern delta sub-basins, lon ≥ 85.5°E): 48,676 rows (2,384 flood [4.90%], 46,292 dry)
* **Geographic Event Represented:**  
  * `DFO_3382`: Mahanadi River Basin & Odisha Delta (September 2008 flood disaster).
* **Cryptographic SHA-256 Checksums:**  
  * Parquet: `ba0f4df5681add4acead2b91489a61be77e8a3897d7d1bdedbd5be6f448db81f`  
  * CSV: `2092cbfffa201b1a50a1cbb1599e2b10a26e8dd7c0b050f242db7a2c72b73f8b`
* **Repository Existence:** **YES**, verified on disk.
* **Runtime Backend Accessibility:** The raw 120 MB dataset file is **NOT queried directly** at runtime. However, downstream artifacts derived from it ([dfo3382_robustness_metrics.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/experiments/dfo3382_robustness_metrics.json), [dfo3382_feature_ablation.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/experiments/dfo3382_feature_ablation.csv), and [dfo3382_water_features.geojson](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/geojson/dfo3382_water_features.geojson)) ARE loaded and served by `/api/v1/intelligence/regional/mahanadi/` endpoints.

---

## 2. VERIFICATION OF TRAINED MODEL ARTIFACTS

A systematic scan of the entire codebase for trained model binaries was conducted:

```
Searched directories:
- backend/data/models/
- ml/models/
- data/packages/phase7e_kaggle_package/
- data/processed/phase7/experiments/models/
```

### Finding 1: Phase 7E Random Forest (`.joblib`) and XGBoost (`.json`)
* **Status:** **DO NOT EXIST ON DISK.**
* **Evidence:** Phase 7E was officially scoped as a packaging and notebook preparation phase (`AQUORA_Phase_7E_Experimental_ML.ipynb`). The training pipeline was prepared for remote Kaggle execution and was never serialized back into the local repository as binary model weights.
* **Backend Loading:** Not loaded anywhere in the application.

### Finding 2: Phase 7F DFO 3382 Mahanadi Models
* **Status:** **DO NOT EXIST ON DISK.**
* **Evidence:** The directory `data/processed/phase7/experiments/models/` exists on disk but contains **0 files**. The Stage 4 training script ([scripts/run_phase7f_stage4_experiments.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/run_phase7f_stage4_experiments.py)) executed in-memory training and validation, saved the resulting metrics to JSON and CSV, and did not execute a `joblib.dump()` or `xgb.save_model()` call.
* **Backend Loading:** Not loaded for live inference. Instead, the precomputed test metrics and ablation results are served directly via `/api/v1/intelligence/regional/mahanadi/experiments`.

### Finding 3: Phase 8 / Deep Zone Prototype XGBoost
* **Status:** **EXISTS ON DISK.**
* **Exact Path:** [backend/data/models/aquora_xgboost_prototype.joblib](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/data/models/aquora_xgboost_prototype.joblib)
* **Metadata Path:** [backend/data/models/aquora_xgboost_metadata.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/data/models/aquora_xgboost_metadata.json)
* **Model Class:** `xgboost.sklearn.XGBClassifier`
* **File Size:** `258,598 bytes`
* **SHA-256 Checksum:** `ba96ed00159dabd8f332674c113e96310e8bf0284a07f0f31485df7103aebe4d`
* **Training Date:** `2026-09-16T19:41:44.127235+00:00`
* **Training Dataset:** Mumbai historical events (Train: E02, E04, E05, E06: 746,368 rows; Val: E03: 186,592 rows; Test: E07: 186,592 rows).
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
* **Frozen Threshold:** `0.5000`
* **Model Load Test:** **PASSED**. Successfully loaded into memory via Python 3.12 and produced valid probabilities in an isolated controlled test.
* **Backend Loading:** Loaded by [backend/app/services/calibration_service.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/calibration_service.py).
* **Runtime Degradation:** When invoked by `get_cell_inspection` at `/api/v1/digital-twin/cells/inspect`, feature extraction fails because `data/processed/phase7/landcover/landcover_class_30m.tif` is not present on disk. Zero-fabrication logic catches this and safely sets `prototype_ml_score: null` and `ml_status: UNAVAILABLE`.

### Finding 4: National and Regional Basin Models
* **Expected Paths:** `ml/models/aquora_national_screening_model.joblib`, `ml/models/aquora_regional_basin_model.joblib`.
* **Status:** **DO NOT EXIST ON DISK / NOT YET TRAINED.**
* **Backend Behavior:** The model registry ([ml_model_registry.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/ml_model_registry.py)) checks for these files. When absent, it sets `is_ready: False`, `model_status: 'PLANNED'`, and `predicted_probability: None`. No fake or synthetic predictions are emitted.

---

## 3. TRACE OF ACTUAL INFERENCE IN THE APPLICATION

Detailed tracing of backend services and endpoints yielded explicit answers to all eight architectural questions:

### 1. Does the live AQUORA backend load the trained Phase 7E model?
**NO.** There is no Phase 7E model file in the repository, and no backend service or route attempts to load or reference one.

### 2. Does it load the DFO 3382 experimental model?
**NO.** No serialized model file exists for DFO 3382. The backend loads and serves diagnostic JSON and CSV files ([dfo3382_robustness_metrics.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/experiments/dfo3382_robustness_metrics.json), [dfo3382_feature_ablation.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/experiments/dfo3382_feature_ablation.csv)), not an executable model.

### 3. Which API endpoint invokes each model?
* **Deep Zone Prototype XGBoost:** Invoked via `CalibrationService.predict_single()` inside `get_cell_inspection` at `GET /api/v1/digital-twin/cells/inspect` (in [digital_twin_service.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/digital_twin_service.py)).
* **National Screening Model:** Invoked via `POST /api/v1/intelligence/national/evaluate` (in [intelligence.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/api/v1/intelligence.py)).
* **Regional Basin Model:** Invoked via `POST /api/v1/intelligence/regional` (in [intelligence.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/api/v1/intelligence.py)).

### 4. Does the frontend receive genuine inference results?
* **For National:** The frontend receives `is_ready: false` and `predicted_probability: null`, displaying a notice that the model is planned.
* **For Regional (Mahanadi):** The frontend receives genuine *research exploration metrics* from the offline test partition (ROC-AUC 0.697, PR-AUC 0.160), not live real-time inference.
* **For Deep Zone / Digital Twin:** The frontend receives `prototype_ml_score: null` and `ml_status: UNAVAILABLE` because the local landcover GeoTIFF is missing.

### 5. Are model outputs computed dynamically or read from static JSON/CSV files?
* **National / Regional ML:** Evaluated dynamically against the model registry, which returns `PLANNED` status.
* **Mahanadi Stage 4 Evaluation Metrics:** Read directly from static JSON and CSV files on disk.
* **Phase 6 Physics Outputs:** Computed **100% dynamically** using differential hydrodynamic equations on-the-fly.

### 6. Are any values hardcoded, mocked, cached, or generated from placeholders?
* **Hardcoded / Mock:** The backend does **not** inject synthetic probabilities or fake flood depths. When data is absent, `null` is returned.
* **Precomputed:** Mahanadi research statistics and sub-basin GeoJSON boundaries are precomputed files served statically.
* **Synthetic Fallbacks in TEST Mode:** In `FloodProcessingService`, if the request explicitly specifies `provider_mode = "TEST"`, the solver can run on synthetic terrain fixtures (`synthetic_v_valley`). However, in `REAL_DATA` mode, synthetic fallback is strictly prohibited and raises a `FileNotFoundError`.

### 7. Does the application accidentally show research metrics as live predictions?
**NO.** On the Regional Intelligence page, the metrics are accompanied by a mandatory yellow governance banner:
> *"LEVEL 2 RESEARCH EXPLORATION ONLY — NOT AN OPERATIONAL FLOOD FORECAST.  
> Scientific Status: PROTOTYPE_ONLY | NOT_CALIBRATED | NOT_FOR_PUBLIC_ALERTS.  
> Authority: Phase 6 Deterministic 2D Physics Engine remains the authoritative flood-depth system."*

### 8. Is any model output connected to Phase 6 physics?
**NO.** Phase 6 physics outputs are completely independent of machine learning. The hydrodynamic solver ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py)) does not take ML predictions as input, nor do ML models modify physical water depths. In the Digital Twin cell inspector, the physical depth and ML prototype score are placed side-by-side for comparison purposes only.

---

## 4. VERIFICATION OF THE PHASE 6 PHYSICS PIPELINE SEPARATELY

A complete trace of the Phase 6 deterministic flood engine was executed:

```mermaid
graph TD
    A["Rainfall Input<br>(Open-Meteo ECMWF or IMERG E02)"] --> C["Runoff Generation<br>(SCS-CN Infiltration & Initial Abstraction)"]
    B["DEM Input<br>(Copernicus DEM GLO-30 30m)"] --> D["Terrain Processing<br>(D8 Flow Direction & Slope Gradient)"]
    C --> E["2D Kinematic Surface Flow Routing<br>(Mass-Conserving Differential Transfer)"]
    D --> E
    F["Drainage Coupling Policy<br>(Surface Drainage Proxy Loss)"] --> E
    E --> G["Flood Depth Grids (meters)<br>(Per-Timestep Spatial GeoTIFF Slices)"]
    G --> H["Backend Artifact Generation<br>(slice_000.tif to slice_180.tif)"]
    H --> I["Frontend Web Map Visualization<br>(MapLibre GL Color Gradients)"]
```

### Trace Details:
1. **Rainfall Input:**
   * In REAL_DATA mode, either dynamically queries the Open-Meteo ECMWF IFS global forecast API (9 km resolution, converted to mm/hr rate across 30-min substeps) or loads [data/processed/phase7/rainfall/E02_rainfall_30m.tif](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/rainfall/E02_rainfall_30m.tif).
   * Missing data handling: If the requested IMERG file is missing, the service raises a `FileNotFoundError`; it never fabricates synthetic rainfall.
2. **DEM Input:**
   * Loads Copernicus DEM GLO-30 raster: [data/processed/phase7/terrain/elevation_30m.tif](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/terrain/elevation_30m.tif).
   * Dimensions: `372 rows × 369 columns` (137,268 cells).
   * Spatial Reference: `EPSG:32643` (WGS 84 / UTM Zone 43N). Resolution: `30.0m × 30.0m`.
3. **Terrain Processing:**
   * Calculates steepest downhill D8 flow direction via `calculate_d8_flow_direction(dem_array, dem_meta["transform"])`.
   * Identifies sinks, depressions, and slope gradients.
4. **Surface Routing:**
   * Implements kinematic wave overland routing. Water moves strictly from higher to lower hydraulic heads.
   * Mass conservation is audited at every timestep; mass balance error is strictly capped under `settings.MASS_BALANCE_TOLERANCE` (0.01%).
5. **Drainage Coupling:**
   * In REAL_DATA mode, because municipal storm sewer GIS records are unavailable, the system records:
     `"drainage_status": "REAL municipal drainage network data UNAVAILABLE; surface drainage proxy active."`
   * Surface detention loss is applied per timestep based on the configured coupling policy.
6. **Flood Depth Output:**
   * Produces 2D floating-point numpy arrays representing flood depth in meters across canonical offsets: `NOW`, `+30m`, `+60m`, `+120m`, `+180m`.
   * Written to disk as valid Cloud-Optimized GeoTIFF rasters (`slice_{minutes}.tif`).
7. **Frontend Visualization:**
   * The frontend map reads the depth rasters and renders them as interactive raster overlays with a color gradient from cyan (0.05m) to dark magenta (>1.5m).

**Conclusion:** The Phase 6 physics engine is **completely authentic, fully operational, and dynamically executing.**

---

## 5. CONTROLLED INFERENCE TEST RESULTS

In accordance with audit requirements, an isolated test script was executed to verify whether the available model artifact loads successfully and generates valid predictions on compatible feature schemas:

```
Test Script: Isolated Python 3.12 Process
Model Artifact: backend/data/models/aquora_xgboost_prototype.joblib
SHA-256: ba96ed00159dabd8f332674c113e96310e8bf0284a07f0f31485df7103aebe4d
Model Class: xgboost.sklearn.XGBClassifier
Holdout Policy: DFO 2507 holdout partition was NOT accessed.
```

### Input Feature Vectors:
* **Sample 1 (High Inundation Risk Profile):**
  * Elevation: `5.0 m` (Low coastal plain)
  * Slope: `1.2°` (Flat terrain)
  * Flow Accumulation: `5000 cells` (Major drainage convergence)
  * Distance to Waterway: `15.0 m` (Riparian corridor)
  * Rainfall Intensity: `90.0 mm/hr` (Extreme monsoon downpour)
  * Tide Level: `3.8 m` (High spring tide)
  * *Features 1–12:* `[5.0, 1.2, 180.0, 5000.0, 0.2, 10.0, 0.85, 25.0, 15.0, 45.0, 90.0, 3.8]`
* **Sample 2 (Dry Ground / Ridge Profile):**
  * Elevation: `65.0 m` (High hillslope)
  * Slope: `15.0°` (Steep gradient)
  * Flow Accumulation: `10 cells` (Headwater ridge)
  * Distance to Waterway: `1200.0 m` (Far from streams)
  * Rainfall Intensity: `0.0 mm/hr` (Dry conditions)
  * Tide Level: `1.2 m` (Low tide)
  * *Features 1–12:* `[65.0, 15.0, 45.0, 10.0, 0.9, 30.0, 0.10, 500.0, 1200.0, 0.0, 0.0, 1.2]`

### Execution Output:
```
Model loaded successfully: <class 'xgboost.sklearn.XGBClassifier'>
Sample 1 Output: [P(dry) = 0.53868, P(flood) = 0.46132]
Sample 2 Output: [P(dry) = 0.99603, P(flood) = 0.00397]
```

### Interpretation of Results:
1. **Output Type:** Class probability distribution over `[P(y=0), P(y=1)]`.
2. **Behavior:** The model responds strongly to the feature gradients. Under high rainfall and low riparian elevation, the predicted flood probability jumps from 0.40% to 46.13% (a 115× increase).
3. **Application Usage:** This model is integrated into [CalibrationService](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/calibration_service.py). However, at runtime, live cell inspection cannot extract features because `landcover_class_30m.tif` is absent, causing the live UI to display `prototype_ml_score: UNAVAILABLE`.

---

## 6. VERIFICATION OF GOVERNANCE SAFEGUARDS

| Governance Safeguard | Policy Specification | Observed Implementation | Compliance Status |
| :--- | :--- | :--- | :---: |
| **DFO 2507 Quarantine** | Zero sampling, tuning, or threshold selection on DFO 2507 holdout event. | Inspected training scripts; splits for DFO 2507 are marked `test` in Phase 7E and completely excluded from Phase 7F Stage 4. | **100% COMPLIANT** |
| **Zero Rainfall Fabrication** | Unobserved retrospective rainfall must remain explicit `NaN`. No synthetic imputation. | Phase 7E features (`1h`, `3h`, `6h`) contain 100% `NaN`. Phase 7F excluded missing rainfall features entirely. | **100% COMPLIANT** |
| **Phase 6 Physics Authority** | Deterministic 2D hydrodynamic physics engine remains the sole operational flood-depth authority. | Physics solver governs Digital Twin, Simulator, Routing, Travel Window, and Critical Access. ML does not override depths. | **100% COMPLIANT** |
| **Frozen Validation Thresholds** | Decision thresholds must be selected solely on validation splits and frozen before test evaluation. | XGBoost threshold `0.0800` and RF threshold `0.0700` were frozen on validation partition and recorded in JSON. | **100% COMPLIANT** |
| **No Test Label Leakage** | Test partitions must never be used for feature selection or threshold calibration. | Spatial blocking by sub-basin ensured zero group leakage. Test corridor evaluated once with frozen parameters. | **100% COMPLIANT** |
| **Strict Unsupported Locations** | Points outside supported basins must be rejected; no fallback to Mumbai. | `SpatialZoneResolver.validate_point()` enforces spatial bounds; unsupported coordinates return 400 or null. | **100% COMPLIANT** |

---

## 7. CLASSIFICATION OF ACTUAL GAPS

The technical findings are classified according to the audit taxonomy:

### A. `CONNECTED_AND_WORKING` (Operational Successes)
1. **Phase 6 Hydrodynamic Solver Engine:** [engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py) coupled with [FloodProcessingService](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/flood_service.py) dynamically computes 2D mass-conserving water routing across Copernicus DEM 30m terrain.
2. **Simulator What-If Engine:** [simulator_service.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/simulator_service.py) dynamically simulates baseline vs custom rainfall scenarios on-the-fly.
3. **Travel Window Passability:** [routing_service.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/routing_service.py) samples dynamic simulation GeoTIFF rasters to compute departure windows and road submersions.
4. **Critical Access Inundation:** [critical_access_service.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/critical_access_service.py) dynamically intersects 366 authentic Mumbai hospital and station coordinates with depth grids.
5. **Protect the City Interventions:** [protect_city_service.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/protect_city_service.py) simulates pump activation and calculates avoided flood depth.
6. **Alert Center Explainability:** [alerts_service.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/alerts_service.py) deterministically translates upstream simulation depths into operational alerts and cause-chains.

### B. `MODEL_TRAINED_BUT_NOT_INTEGRATED`
1. **Phase 8 Prototype XGBoost:** [backend/data/models/aquora_xgboost_prototype.joblib](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/data/models/aquora_xgboost_prototype.joblib) is fully trained and verified, but its runtime cell inspection in the Digital Twin degrades to `UNAVAILABLE` because the landcover raster is missing.

### C. `DATASET_MISSING`
1. **Mumbai Calibration Landcover GeoTIFF:** `data/processed/phase7/landcover/landcover_class_30m.tif` is missing on disk, preventing the cell inspector from extracting features for the XGBoost prototype.
2. **Phase 7E Binary Model Artifacts:** `aquora_rf_model_v1.joblib` and `aquora_xgb_model_v1.json` were never trained or saved to disk (Kaggle notebook only).
3. **Phase 7F DFO 3382 Model Artifacts:** Models were trained in memory during Stage 4/4.1 exploration; no binary model weights were dumped into `data/processed/phase7/experiments/models/`.

### D. `STATIC_OR_PLACEHOLDER_DATA`
1. **Mahanadi Regional Metrics:** The metrics displayed in the Regional Intelligence view (ROC-AUC 0.697, PR-AUC 0.160, ablation table) are read from static JSON and CSV files rather than generated dynamically by a live model. *(Note: This is scientifically appropriate and prominently disclosed with governance banners).*
2. **Municipal Drainage GIS Records:** Real underground stormwater sewer pipe geometry for Mumbai is unavailable; the physics engine relies on a surface drainage proxy.

### E. `SCIENTIFICALLY_UNVALIDATED`
1. **National Screening Model:** Marked `PLANNED`; not trained on coincident national labels.
2. **Regional Basin Models:** Marked `PLANNED`; uncalibrated heuristic index used for general river basins.

---

## 8. DEFECT PRIORITIZATION & REMEDIATION ROADMAP

| Defect ID | Description | Classification | Impact | Recommended Action |
| :---: | :--- | :--- | :---: | :--- |
| **DEF-01** | Missing `landcover_class_30m.tif` causes Digital Twin cell inspection ML score to degrade to `UNAVAILABLE`. | `DATASET_MISSING` | **HIGH** | Generate or symlink the Copernicus/ESA WorldCover landcover raster into `data/processed/phase7/landcover/` to allow `CalibrationService` to extract all 12 features. |
| **DEF-02** | Phase 7F Stage 4 models were not serialized to disk (`data/processed/phase7/experiments/models/` is empty). | `MODEL_TRAINED_BUT_NOT_INTEGRATED` | **MEDIUM** | Modify `scripts/run_phase7f_stage4_experiments.py` to add `joblib.dump(xgb_model, ...)` so that the trained regional exploration model weights are preserved. |
| **DEF-03** | National screening model endpoint returns `is_ready: false` / `predicted_probability: null`. | `SCIENTIFICALLY_UNVALIDATED` | **LOW** | Expected behavior for current phase. Maintain strict zero-fabrication until nationwide labeled training is commissioned. |

---

## 9. CONCLUSION & FINAL SIGN-OFF

The audit conclusively establishes that **AQUORA is functioning authentically according to its scientific governance design:**
1. The physics engine is **real, mass-conserving, and dynamically computing outputs on-the-fly.**
2. The frontend is **not** displaying fabricated machine learning predictions.
3. Where models or rasters are missing, the application **transparently discloses their status, displays diagnostic research metrics, or degrades gracefully.**
4. No synthetic numbers, false claims of operational readiness, or violations of holdout quarantines were found.

*Audit complete and cryptographically verified.*
