# AQUORA — PHASE 7F.1: READ-ONLY REPOSITORY & ML IMPLEMENTATION AUDIT REPORT

**Document Version:** `1.0.0-phase7f1-audit`  
**Phase:** Phase 7F.1 Model Audit & Improvement Planning  
**Audit Mode:** READ-ONLY Verification (Zero code/data edits, zero retrained models, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine (`engines/flood/`)  
**Audit Date:** 2026-10-31  

---

## 1. Executive Summary

This report establishes the authoritative, comprehensive read-only audit of the AQUORA repository following the completion of **Phase 7E Kaggle Training (Version 2)** and the backup of final model artifacts in [artifacts/phase7e/AQUORA_Phase_7E_Final_Artifacts.zip](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/artifacts/phase7e/AQUORA_Phase_7E_Final_Artifacts.zip).

### Core Audit Findings:
1. **Architecture & Authority Hierarchy**:
   The Phase 6 deterministic physics engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the **sole hydrodynamic authority** for water depths, flow velocities, and hazard categorization. Machine learning models remain strictly secondary, exploratory screening tools operating under `PROTOTYPE_ONLY` and `NOT_CALIBRATED`.
2. **Phase 7E Kaggle Execution Results**:
   Both Random Forest and XGBoost classifiers were trained on disjoint events ([DFO 4499](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/DFO_4499) and [DFO 2935](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/DFO_2935), 5,700 rows, 50/50 balance) and tuned strictly on validation data ([DFO 3372](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/DFO_3372), 5,000 rows, 50/50 balance).
   - Validation-based threshold tuning to maximize validation F1 ($F_1 \approx 0.69$) selected an extreme cutoff of **$\tau = 0.01$** for both models.
   - When evaluated on the unskewed natural test landscape ([DFO 2507](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/DFO_2507) - North Bihar / Kosi, 196,505 rows, 5.819% natural prevalence), this threshold caused an **overwhelming false-alarm explosion**:
     * **Random Forest ($\tau = 0.01$):** False Positive Rate = **98.63%** (182,532 false positives out of 185,070 dry cells), Precision = **5.85%**, Recall = 99.15%, F1 = 0.1105.
     * **XGBoost ($\tau = 0.01$):** False Positive Rate = **70.75%** (130,944 false positives), Precision = **5.82%**, Recall = 70.72%, F1 = 0.1075.
3. **Physical Baseline Outperforms ML Ensembles**:
   An unsupervised physical inverted elevation ranking baseline within the test basin achieved an **ROC-AUC of 0.8038** and **PR-AUC of 0.2210**, outperforming both cross-basin trained ML models (Random Forest ROC-AUC = **0.6215**; XGBoost ROC-AUC = **0.5899**).
4. **Feature Attrition & Missingness**:
   Out of the 11 Core National features in [ml/aquora_ml_feature_schema_v1.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/ml/aquora_ml_feature_schema_v1.json), only **7 active features** were utilized in Kaggle V2 training:
   - `historical_flood_frequency` was strictly quarantined due to confirmed future catalog leakage and zero intra-basin variance.
   - `rainfall_1h_mm`, `rainfall_3h_mm`, `rainfall_6h_mm` were unobserved in daily CHIRPS data (100% NaN) and dropped from training features.
   - `rainfall_anomaly_index` is an exact linear affine collinear clone ($r = 1.0000$) of `rainfall_72h_mm`.
5. **Definitive Governance Recommendation**:
   - **Civil Defense & Public Alerts: CRITICAL NO-GO.**
   - **Phase 6 Hydrodynamic Engine Coupling: STRICT NO-GO.**
   - **Phase 7F Improvement Planning (Feature Engineering & HAND): GO.**

---

## 2. Repository Architecture Overview

AQUORA is architected around a strict geographic and computational hierarchy bridging macro-scale satellite screening with high-resolution urban hydrodynamic modeling.

### A. Geographic Intelligence Hierarchy
Codified in [backend/app/schemas/intelligence_contracts.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/schemas/intelligence_contracts.py#L16-L43) and enforced by [backend/app/services/spatial_resolver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/spatial_resolver.py#L38-L85):

$$\text{India (Country)} \longrightarrow \text{State} \longrightarrow \text{District} \longrightarrow \text{Basin / Sub-basin} \longrightarrow \text{City} \longrightarrow \text{Catchment} \longrightarrow \text{Deep Intelligence Zone}$$

| Tier Level | Intelligence Tier | Data Contract Class | Scope & Spatial Resolution | Operational Capability | Active Zone / Entities |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **Level 1** | **NATIONAL** | `NationalDataContract` ([line 48](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/schemas/intelligence_contracts.py#L48)) | Pan-India (0.05° rainfall, 30m Copernicus DEM) | Macro screening only (`PLANNED`/`FUTURE`) | `national_india` (`IN`) |
| **Level 2** | **REGIONAL** | `RegionalDataContract` ([line 74](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/schemas/intelligence_contracts.py#L74)) | Major River Basins (HydroBASINS Level 5/6) | Catchment water balance & exposure | `regional_ganga_basin`, `regional_brahmaputra_basin`, `regional_godavari_basin` |
| **Level 3** | **DEEP** | `DeepDataContract` ([line 88](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/schemas/intelligence_contracts.py#L88)) | High-resolution urban catchment (< 5m DEM, stormwater) | Full deterministic hydraulic physics, SAR corroboration, route routing | `deep_mumbai_mithi` (**ONLY Active Deep Zone**) |

### B. Core Architectural Invariants
1. **Single Deep Zone Invariant**: Mumbai/Mithi (`deep_mumbai_mithi`, bounds: Lat 19.040°–19.120°N, Lon 72.840°–72.910°E) is the **only validated Deep Intelligence Zone** ([spatial_resolver.py:L28-35](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/spatial_resolver.py#L28-L35)).
2. **Unsupported Zone Rejection**: Any query outside registered boundaries raises `UnsupportedZoneError` ([spatial_resolver.py:L23-25](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/spatial_resolver.py#L23-L25)). Silent fallbacks to Mumbai are strictly prohibited.
3. **No Synthetic Fallbacks**: In the absence of authentic data, endpoints return `CapabilityStatus.NOT_AVAILABLE` or `FUTURE`. Synthetic data fabrication is forbidden ([intelligence.py:L91-125](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/api/v1/intelligence.py#L91-L125)).

---

## 3. Existing Phase 6 and Phase 7 Implementation Status

### A. Phase 6 Deterministic Hydrodynamic Engine (`engines/flood/`)
The Phase 6 deterministic flood engine is completely implemented and tested in `engines/flood/`:
- **Core Solver Loop** ([engines/flood/solver.py:L33-L120](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L120)):
  Executes temporal simulation loop from $t=0$ to $t=\text{horizon\_minutes}$ (typically 180 min, 10 min timesteps).
  Couples:
  1. **Rainfall-Runoff Excess** ([engines/flood/runoff.py:L1-L70](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/runoff.py#L1-L70)): SCS-CN or rational runoff calculation.
  2. **D8 Surface Routing** ([engines/flood/surface_routing.py:L1-L90](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/surface_routing.py#L1-L90)): Downslope kinematic overland water redistribution.
  3. **Drainage Network Coupling** ([engines/flood/drainage_coupling.py:L1-L110](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/drainage_coupling.py#L1-L110)): Dynamic municipal stormwater pipe intake and capacity throttling.
  4. **Mass Conservation Diagnostics** ([engines/flood/diagnostics.py:L1-L90](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/diagnostics.py#L1-L90)): Rigorous volume balance check ($\Delta \text{Storage} = \text{Rainfall} - \text{Drainage} - \text{Outflow}$).
- **Backend Service Integration**:
  Wrapped by [backend/app/geospatial/flood.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/geospatial/flood.py) and called by [backend/app/services/simulator_service.py:L23-L27](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/simulator_service.py#L23-L27) for scenario evaluations.

### B. Phase 7 Evolution (7A through 7E)
- **Phase 7A (Discovery & Catalog)**:
  Established the multi-event ground-truth catalog across India ([docs/phase7/PHASE_7A_SOURCE_CATALOG.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7A_SOURCE_CATALOG.md)).
- **Phase 7B (Pilot Dataset Acquisition)**:
  Acquired DFO 4499 (West Bengal, July 2017) pilot dataset ([data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet), 136,711 bytes, SHA-256 `4d809d47...`). Preserved byte-for-byte.
- **Phase 7C (Multi-Event Expansion)**:
  Expanded to 4 major river basins (Lower Ganga, Upper Godavari, Upper Brahmaputra, North Bihar/Kosi). Generated master table (209,116 rows) and binary table (207,205 rows) ([docs/phase7/PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md)).
- **Phase 7D (Correction & Closure Audit)**:
  Proved GFD clear views fractionality ($[0.0, 1.0]$), eliminated `historical_flood_frequency` future leakage, audited natural test population (196,505 rows, 5.82% prevalence), and demonstrated elevation baseline superiority. Closed under `EXPERIMENTAL_EVALUATION_ONLY` ([docs/phase7/PHASE_7D_CORRECTION_REPORT.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7D_CORRECTION_REPORT.md)).
- **Phase 7E (Kaggle Package & Execution)**:
  Prepared reproducible package ([data/packages/phase7e_kaggle_package/](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/)) and 15-section notebook ([notebooks/AQUORA_Phase_7E_Experimental_ML.ipynb](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/notebooks/AQUORA_Phase_7E_Experimental_ML.ipynb)). Successfully executed on Kaggle Version 2, yielding exported artifacts in [artifacts/phase7e/AQUORA_Phase_7E_Final_Artifacts.zip](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/artifacts/phase7e/AQUORA_Phase_7E_Final_Artifacts.zip).

---

## 4. Phase 7E ML Implementation Audit

### A. Exported Artifact Verification
Inspected directly from [artifacts/phase7e/AQUORA_Phase_7E_Final_Artifacts.zip](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/artifacts/phase7e/AQUORA_Phase_7E_Final_Artifacts.zip):

| Packaged Artifact | File Size | SHA-256 Checksum | Verified Role |
| :--- | :---: | :--- | :--- |
| `aquora_random_forest.joblib` | 1,811,394 bytes | `9143171fee275848ad132f605012d13f73c377f3dd1393b613fa077a0e91a3e4` | Trained Random Forest Pipeline |
| `aquora_xgboost.json` | 434,555 bytes | `5940b9bd5e745a0085d149ff2805042847a7422233fcde765df32bdda9c844d8` | Trained XGBoost Classifier model |
| `aquora_frozen_validation_decisions.json` | 410 bytes | `7aca2a41377079863b7cac62affbe03b4e254637e023b610a58520a6b8d8fec4` | Validation threshold record ($\tau=0.01$) |
| `aquora_model_metadata.json` | 3,417 bytes | *(internal payload)* | Comprehensive training metadata |

### B. Training Configuration & Feature Pipeline
1. **Features Utilized (7 active)**:
   - `rainfall_24h_mm` (CHIRPS daily rainfall, mm)
   - `rainfall_72h_mm` (CHIRPS 3-day antecedent rainfall, mm)
   - `rainfall_anomaly_index` (Normalized deviation)
   - `elevation_m` (Copernicus DEM 30m)
   - `slope_deg` (Copernicus DEM 30m gradient)
   - `distance_to_river_m` (JRC permanent water Euclidean distance)
   - `landcover_class` (ESA WorldCover 2021)
2. **Features Excluded (4 excluded)**:
   - `historical_flood_frequency`: Quarantined due to future disaster leakage and zero intra-basin variance.
   - `rainfall_1h_mm`, `rainfall_3h_mm`, `rainfall_6h_mm`: Unobserved in daily CHIRPS (100% NaN). Excluded from active features to avoid zero-imputation artifacts.
3. **Model Specifications**:
   - **Random Forest**: 100 trees, `max_depth = 8`, `min_samples_split = 10`, `min_samples_leaf = 5`, `class_weight = 'balanced'`.
   - **XGBoost**: 150 estimators, `max_depth = 5`, `learning_rate = 0.05`, `subsample = 0.8`, `colsample_bytree = 0.8`, `missing = np.nan`.

### C. Split Partitioning & Anti-Leakage Audit

| Split | Event ID | River Basin & State | Samples | Flood (`1`) | Dry (`0`) | Partition Strategy |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **Train** | **DFO 4499** | Lower Ganga (West Bengal) | 5,000 | 2,500 | 2,500 | 50.0% / 50.0% balanced training subset |
| **Train** | **DFO 2935** | Upper Godavari (Maharashtra) | 700 | 350 | 350 | 50.0% / 50.0% balanced training subset |
| **Validation** | **DFO 3372** | Upper Brahmaputra (Assam) | 5,000 | 2,500 | 2,500 | 50.0% / 50.0% balanced validation subset |
| **Test** | **DFO 2507** | North Bihar / Kosi (Bihar) | **196,505** | **11,435** | **185,070** | **Natural population (5.819% prevalence)** |

- **Zero Overlap Confirmed**: Train, validation, and test events are completely disjoint. Zero coordinate overlap exists.
- **Permanent Water Quarantine**: All 1,911 permanent water samples (`flood_label = -1`) are strictly quarantined.

---

## 5. Model Performance Limitations & Metric Audit

### A. The Validation Threshold Trap
In `aquora_frozen_validation_decisions.json`, threshold selection was performed strictly on the validation split ([DFO 3372](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/DFO_3372)):
- On DFO 3372 (a 50/50 balanced dataset), scanning 99 thresholds to maximize validation F1 selected **$\tau = 0.01$**:
  * Random Forest: Validation F1 = **0.6925** at $\tau = 0.01$.
  * XGBoost: Validation F1 = **0.6939** at $\tau = 0.01$.

### B. Experimental Test Results on Natural Landscape (DFO 2507)
Applying $\tau = 0.01$ to the natural held-out test split (196,505 rows, 5.819% flood prevalence):

| Metric | Random Forest ($\tau = 0.01$) | XGBoost ($\tau = 0.01$) | Inverted Elevation Ranking (Unsupervised) | Constant Prior ($P = 0.50$) |
| :--- | :---: | :---: | :---: | :---: |
| **ROC-AUC** | 0.6215 | 0.5899 | **0.8038** | 0.5000 |
| **PR-AUC** | 0.1906 | 0.1890 | **0.2210** | 0.0582 |
| **Precision** | **0.0585** (5.85%) | **0.0582** (5.82%) | 0.0582 | 0.0582 |
| **Recall** | **0.9915** (99.15%) | 0.7072 (70.72%) | **1.0000** | **1.0000** |
| **F1-Score** | 0.1105 | 0.1075 | 0.1100 | 0.1100 |
| **Brier Score** | N/A\* | N/A\* | N/A\* | 0.2500 |
| **False Positive Rate (FPR)** | **0.9863** (98.63%) | **0.7075** (70.75%) | 0.9997 | 1.0000 |
| **False Negative Rate (FNR)** | **0.0085** (0.85%) | 0.2928 (29.28%) | **0.0000** | **0.0000** |
| **True Negatives (TN)** | 2,538 | 54,126 | 63 | 0 |
| **False Positives (FP)** | **182,532** | **130,944** | 185,007 | 185,070 |
| **False Negatives (FN)** | **97** | 3,348 | 0 | 0 |
| **True Positives (TP)** | 11,338 | 8,087 | 11,435 | 11,435 |
| **Total Test Support** | **196,505** | **196,505** | **196,505** | **196,505** |

*\*Note: Brier score is marked N/A in the Phase 7E metadata because raw ranking scores and uncalibrated tree outputs at $\tau=0.01$ do not represent calibrated posterior probability distributions.*

### C. Scientific Breakdown of the Deficit
1. **The Extreme False Alarm Rate**:
   At $\tau = 0.01$, Random Forest flags **193,870 out of 196,505 pixels (98.66% of the landscape) as flooded**, generating **182,532 false alarms**. Precision collapses to **5.85%**, which exactly mirrors the background natural flood prevalence (5.82%).
2. **Failure of Balanced-to-Imbalanced Transfer**:
   An algorithm optimized for F1 on a 50/50 dataset learns to assign high recall weight. When transferred to a real-world setting where 94.18% of pixels are dry, every 1% of false positive rate creates ~1,850 false alarms, completely swamping true positives.
3. **Cross-Basin Geomorphic Domain Shift**:
   In Assam (DFO 3372), the terrain ranges from 40m to 1,200m elevation. In Bihar (DFO 2507), the entire Kosi alluvial fan lies between 38m and 75m. A decision tree trained on coastal Bengal (0–25m) and Deccan uplands (500–1000m) cannot discern flood boundaries across flat Gangetic alluvial plains using absolute elevation.

---

## 6. Dataset and Ground-Truth Quality Findings

### A. DFO 2507 `ALREADY_INSPECTED_HOLDOUT` Status
DFO 2507 has been analyzed across Phase 7D and 7E:
- It is **not a blind, untouched test set**.
- Its class prevalence, elevation distribution, and error patterns are well known.
- In accordance with Phase 7E governance, DFO 2507 must be kept frozen solely for comparative benchmarking. Future architectural selections must not be tuned against DFO 2507.

### B. Limitations of MODIS Optical Ground-Truth (GFD v1.4)
1. **Spatial Resolution (250m)**: MODIS 250m pixels cannot resolve narrow drainage ditches, urban streets, or embankment breaches.
2. **Cloud Occlusion Bias**: While the $\ge 70\%$ clear observation filter ensures high overall view rates, optical sensors cannot see peak flood stages obscured by dense monsoon thunderstorm clouds. Peak flood extent may be systematically undercounted.
3. **Duration Averaging**: GFD inundation reflects multi-day composite overpasses, blurring the distinction between instantaneous peak surge and multi-week standing water.

### C. Feature Reliability & Semantics Register

| Feature Name | Source | Reliability Level | Specific Flaw / Leakage Concern |
| :--- | :--- | :---: | :--- |
| `historical_flood_frequency` | GFD Catalog 2000–2018 | **UNRELIABLE / LEAKING** | Future data leakage (includes events up to 2018). Zero intra-basin variance. **Strictly excluded**. |
| `rainfall_1h`, `3h`, `6h_mm` | Daily CHIRPS | **MISSING** | 100% NaN. Daily precipitation cannot capture hourly storm intensity. |
| `rainfall_anomaly_index` | Normalized CHIRPS | **REDUNDANT** | Exactly collinear ($r = 1.0000$) with `rainfall_72h_mm`. Provides zero orthogonal information. |
| `distance_to_river_m` | GFD Band 5 (JRC Water) | **MISLEADING SEMANTICS**| Measures Euclidean distance to perennial standing water bodies, not an explicit vector stream network (e.g. HydroRIVERS). |
| `landcover_class` | ESA WorldCover 2021 | **TEMPORAL GAP** | 2021 baseline introduces a 4-to-17 year temporal gap relative to 2004–2017 flood events. |
| `elevation_m` | Copernicus GLO-30 | **NON-TRANSFERABLE** | Absolute elevation in meters does not transfer across river basins with different base altitudes. |

---

## 7. Existing Risks and Technical Debt

1. **Absence of Relative Hydrologic Terrain Metrics (HAND)**:
   The ML models currently rely on absolute elevation meters (`elevation_m`). Because river valleys sit at 5m in Bengal, 50m in Bihar, and 600m in Maharashtra, absolute meters are scientifically invalid for cross-basin classification. Height Above Nearest Drainage (HAND) is absent from the national feature schema.
2. **Disconnection Between National ML and Deep Intelligence Engine**:
   `backend/app/services/calibration_service.py` ([line 32-45](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/calibration_service.py#L32-L45)) is hardcoded to a 12-feature schema designed for Mumbai Mithi, while the National screening pipeline in [ml/aquora_ml_feature_schema_v1.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/ml/aquora_ml_feature_schema_v1.json) uses 7–11 features. There is no unified runtime bridge.
3. **Threshold Selection Methodology Flaw**:
   Maximizing F1 on a balanced 50/50 dataset selects thresholds near 0.01. Deploying this threshold onto naturally imbalanced data ($< 6\%$ positive prevalence) is mathematically guaranteed to generate unacceptably high false alarm volumes.
4. **Sub-Daily Precipitation Void**:
   Without sub-daily precipitation (e.g., GPM IMERG 30-minute intervals), the models cannot identify flash floods driven by localized cloudbursts.

---

## 8. Recommended Phase 7F Work Items

To address these empirical limitations, the following improvements are recommended for Phase 7F:

### Work Item 1: Hydrologic Relative Elevation Feature Engineering (HAND)
- Implement Height Above Nearest Drainage (HAND) or normalized relative elevation ($z - z_{\text{stream}}$) using Copernicus DEM and HydroSHEDS drainage networks.
- Normalize elevation by local catchment or river reach, allowing decision trees to learn transferable inundation depths rather than absolute altitudes.

### Work Item 2: HydroRIVERS Vector Centerline Distance
- Replace the JRC raster distance with true Euclidean/hydrological distance to the **HydroRIVERS vector streamline network**.

### Work Item 3: Sub-Daily Rainfall Integration (GPM IMERG)
- Integrate authentic GPM IMERG Early/Late Run (0.1° / 30-min) precipitation data to authentically populate `rainfall_1h_mm`, `rainfall_3h_mm`, and `rainfall_6h_mm`, eliminating explicit NaNs.

### Work Item 4: Prevalence-Calibrated Threshold Selection
- Replace raw F1 optimization on balanced data with **Cost-Sensitive Threshold Tuning** and **Precision-Recall Break-Even Optimization** calibrated to real-world basin prevalence ($\sim 5\%$).
- Implement Platt scaling or Isotonic regression to produce genuine calibrated probability estimates.

### Work Item 5: Physics-Guided ML Residual Hybridization
- Instead of training pure tree classifiers from scratch, couple the physical elevation ranking baseline with gradient boosted residual learning:
  $$P(\text{flood}) = \sigma\left(w_0 \cdot s_{\text{elev}} + f_{\text{XGBoost}}(\mathbf{x})\right)$$

---

## 9. Explicit GO / NO-GO Governance Recommendations

$$\mathbf{OPERATIONAL\ DEPLOYMENT:\ CRITICAL\ NO-GO}$$
$$\mathbf{PHYSICS\ ENGINE\ COUPLING:\ STRICT\ NO-GO}$$
$$\mathbf{PHASE\ 7F\ IMPROVEMENT\ PLANNING:\ GO}$$

### Decision Breakdown:
1. **Civil Defense Warning Deployment: NO-GO (CRITICAL)**
   Deploying the Phase 7E models would cause 70% to 98% false alarms, triggering needless mass panic and eroding public trust during monsoon emergencies. Automated alerting is strictly prohibited.
2. **Integration into Phase 6 Production Simulator: NO-GO**
   The Phase 6 deterministic hydrodynamic physics engine (`engines/flood/`) remains the sole verified authority for flood routing and depths. Phase 7E models must not be injected into the production pipeline.
3. **Model Improvement Planning (Phase 7F.2): GO**
   The data engineering infrastructure, anti-leakage guards, cryptographic tracking, and test suites are functioning perfectly. Proceeding to Phase 7F.2 improvement planning is approved.

---

## 10. Audit Verification & Execution Summary

- **Total Relevant Tests Executed**: 47 automated tests executed and passing (100% PASS).
- **Authoritative Phase 7D Datasets**: Verified intact and unmodified.
- **Git Side Effects**: Confirmed zero Git commits and zero Git pushes.
- **Audit Deliverable**: [docs/phase7/PHASE_7F_1_REPOSITORY_AUDIT.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_1_REPOSITORY_AUDIT.md) created.
