# AQUORA — Phase 7E Partial-Feature Model Validation, Missing-Feature Governance & Artifact Integrity Audit

**Document ID:** `AQUORA-P7E-PFV-2026-11`  
**Classification:** Scientific Governance, Diagnostic Experimentation & Cryptographic Reconciliation Audit  
**Date:** 2026-11-03  
**Status:** COMPLETE & CERTIFIED  
**Governing Standard:** Zero Data Fabrication, Strict Phase Boundaries, Complete Event Holdout Quarantine  
**Holdout Policy:** DFO 2507 holdout dataset (196,505 samples) was **strictly quarantined and unaccessed** during all diagnostic experiments.  
**Deterministic Physics Authority:** Phase 6 hydrodynamic finite-volume 2D shallow water solver remains sole authority for inundation depths.  

---

## Executive Summary & Direct Scientific Decision

### The Core Inquiry
In Phase 7E, the Kaggle Version 2 XGBoost screening model was trained on historical flood events where feature missingness was strictly **0.00%**. At operational runtime, municipal screening points such as Patna and Guwahati evaluated terrain layers successfully but lacked real-time rain gauge telemetries, resulting in scores (e.g. Patna 4.77%, Guwahati 3.30%) evaluated with 3 missing precipitation predictors.

**Question:** *Are partial-feature predictions scientifically defensible, or does XGBoost's mechanical ability to traverse default tree branches on NaNs produce misleading artifacts?*

### The Definitive Scientific Decision: **PARTIAL INFERENCE SUPPRESSED**
1. **Indefensible Under Missing Data:**
   Diagnostic experiments on the official Phase 7E validation dataset (**DFO 3372**, $N=5,000$) demonstrate that evaluating the model without rainfall predictors causes a **catastrophic probability distortion**:
   - The mean predicted susceptibility probability increases nearly **5-fold** (from $0.0582$ to $0.2916$).
   - The maximum predicted score explodes from $0.2831$ to $0.9892$.
   - **False Positives explode**: $80.8\%$ of dry validation points (2,020 out of 2,500) are falsely flagged positive at the frozen $0.01$ threshold.
   - Tree inspection reveals that because the model was trained on monsoon flood disasters where precipitation was high, XGBoost learned default `missing` splits that route directly into the high-gain deluge branches. Passing `NaN` for unobserved rain gauges causes the tree to evaluate the location as if it were experiencing an extreme monsoon deluge!
2. **Strict Operational Policy Codified:**
   - Operational macro screening requires **all 7 trained predictors** (`rainfall_24h_mm`, `rainfall_72h_mm`, `rainfall_anomaly_index`, `elevation_m`, `slope_deg`, `distance_to_river_m`, `landcover_class`).
   - If any predictor is missing, operational inference is **strictly suppressed**, returning `status: INSUFFICIENT_INPUT_DATA`, `predicted_probability: null`, `susceptibility_grade: null`.
   - Patna and Guwahati in operational observation mode return `INSUFFICIENT_INPUT_DATA` due to unobserved real-time gauges.
   - Missing rainfall is **never zero-filled or fabricated**.
3. **Benchmark Scenario Isolation:**
   - Non-operational historical storm deluge fixtures (July 2023 Ganga Patna, June 2022 Brahmaputra Guwahati) remain strictly isolated under `allow_benchmark_rainfall=True`.
   - In benchmark mode, where complete 7-feature vectors are provided by the historical scenario fixture, inference executes and is tagged with an explicit amber warning: `BENCHMARK / HISTORICAL INPUT (Scenario Testing Only; Not Live Operational Gauges)`.
4. **Terminology Correction:**
   - Replaced `LOW RISK`, `MEDIUM RISK`, `HIGH RISK` with **`LOW MODEL SCORE`**, **`MEDIUM MODEL SCORE`**, and **`HIGH MODEL SCORE`**.
   - These bands are documented as uncalibrated presentation categories, not validated flood-risk classifications or public warnings.
5. **Geographic Resolution Realism:**
   - Basin assignments in `hydrobasins_india.json` and `hydrobasins_india.geojson` use rectangular bounding boxes, not true watershed catchment polygons.
   - All spatial assignments are formally classified as **`APPROXIMATE_MACRO_BOUNDS`**; precise hydrological polygon resolution is explicitly disclaimed.

---

## 1. Missing-Feature Diagnostic Validation Experiments

### 1.1 Experimental Protocol & Quarantine Compliance
All diagnostic experiments were executed strictly on the Phase 7E training and validation datasets from `data/packages/phase7e_kaggle_package/phase7c_multievent_binary_dataset.parquet`.
- **Validation Dataset:** Event `DFO_3372` (Upper Brahmaputra Basin, Assam; August 30, 2008). $N = 5,000$ samples (2,500 flooded, 2,500 dry).
- **Training Dataset:** Events `DFO_4499` (Lower Ganga, Bengal, $N=5,000$) and `DFO_2935` (Upper Godavari, Maharashtra, $N=700$). Total $N = 5,700$ samples (2,850 flooded, 2,850 dry).
- **Combined Train + Validation:** $N = 10,700$ samples.
- **Holdout Quarantine:** The protected test event **DFO 2507** ($N=196,505$) was **strictly quarantined and untouched**.
- **Model Invariant:** Evaluated the frozen live artifact `aquora_national_screening_model.joblib` (booster SHA-256 `5940b9bd...`) at the frozen decision threshold $\tau = 0.01$. No retraining or threshold retuning was performed.

### 1.2 Quantitative Diagnostic Results

The model was evaluated across 5 feature availability configurations:
1. **Baseline:** All 7 trained predictors present as observed in the ground-truth dataset.
2. **Missing Rainfall:** The 3 rainfall predictors (`rainfall_24h_mm`, `rainfall_72h_mm`, `rainfall_anomaly_index`) set to `NaN` (simulating operational gauge unavailability).
3. **Missing Geomorphic:** The 3 terrain predictors (`elevation_m`, `slope_deg`, `distance_to_river_m`) set to `NaN`.
4. **Missing Landcover:** The 1 categorical landcover predictor (`landcover_class`) set to `NaN`.
5. **Geomorphic Only:** Rainfall and landcover missing; only elevation, slope, and distance to river available.

#### Table 1: Validation Set Diagnostics (DFO 3372, N=5,000; 2,500 Flood, 2,500 Dry)

| Experiment Configuration | ROC-AUC | PR-AUC | Precision | Recall | F1 Score | Brier Score* | Flagged Ratio | Score Min | Score Median | Score Mean | Score Max | False Positives (out of 2,500 dry) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline (All 7 Features)** | **0.7788** | **0.8241** | **0.7020** | 0.6860 | **0.6939** | 0.4080 | 48.86% | 0.0034 | 0.0099 | 0.0582 | 0.2831 | **728** |
| **Missing Rainfall (3 features NaN)** | 0.8138 | 0.8436 | 0.5439 | 0.9636 | 0.6953 | 0.2330 | **88.58%** | 0.0036 | 0.0488 | **0.2916** | **0.9892** | **2,020** (+177.5%) |
| **Missing Geomorphic (3 features NaN)** | 0.7498 | 0.8181 | 0.5000 | 1.0000 | 0.6667 | 0.4774 | **100.0%** | 0.0153 | 0.0211 | 0.0218 | 0.0262 | **2,500** (100% FP) |
| **Missing Landcover (1 feature NaN)** | 0.7693 | 0.8048 | 0.6292 | 0.7784 | 0.6959 | 0.4429 | 61.86% | 0.0047 | 0.0135 | 0.0375 | 0.1465 | 1,147 |
| **Geomorphic Only (Rainfall & LC NaN)** | 0.8064 | 0.8328 | 0.5200 | 0.9888 | 0.6816 | 0.2663 | **95.08%** | 0.0059 | 0.0529 | 0.2181 | 0.8686 | **2,282** (+213.5%) |

*\*Note: Brier score is reported purely as a diagnostic dispersion indicator; because the model is uncalibrated, Brier scores cannot be interpreted as operational forecast reliability.*

#### Table 2: Training Set Diagnostics (DFO 4499 + DFO 2935, N=5,700; 2,850 Flood, 2,850 Dry)

| Experiment Configuration | ROC-AUC | PR-AUC | Precision | Recall | F1 Score | Brier Score* | Flagged Ratio | Score Min | Score Median | Score Mean | Score Max | False Positives (out of 2,850 dry) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline (All 7 Features)** | 0.9744 | 0.9722 | 0.5721 | 1.0000 | 0.7278 | 0.0627 | 87.40% | 0.0021 | 0.5784 | 0.5006 | 0.9913 | 2,132 |
| **Missing Rainfall (3 features NaN)** | 0.9222 | 0.9130 | 0.5504 | 1.0000 | 0.7100 | 0.1115 | 90.84% | 0.0033 | 0.5303 | 0.5013 | 0.9892 | 2,328 |
| **Missing Geomorphic (3 features NaN)** | **0.5320** | **0.5653** | 0.5065 | 0.9923 | 0.6707 | 0.4735 | 97.95% | 0.0075 | 0.0233 | 0.0259 | 0.0965 | 2,755 |
| **Missing Landcover (1 feature NaN)** | 0.9673 | 0.9632 | 0.5588 | 1.0000 | 0.7170 | 0.1427 | 89.47% | 0.0027 | 0.2355 | 0.3036 | 0.9687 | 2,250 |
| **Geomorphic Only (Rainfall & LC NaN)** | 0.9045 | 0.8876 | 0.5273 | 1.0000 | 0.6905 | 0.1884 | 94.82% | 0.0059 | 0.2425 | 0.2893 | 0.8891 | 2,555 |

#### Table 3: Combined Population Diagnostics (N=10,700)

| Experiment Configuration | ROC-AUC | PR-AUC | Precision | Recall | F1 Score | Flagged Ratio | Score Min | Score Mean | Score Max | False Positives (out of 5,350 dry) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline (All 7 Features)** | 0.8128 | 0.8486 | 0.6148 | 0.8533 | 0.7147 | 69.39% | 0.0021 | 0.2939 | 0.9913 | 2,860 |
| **Missing Rainfall (3 features NaN)** | 0.8591 | 0.8755 | 0.5474 | 0.9830 | 0.7032 | 89.79% | 0.0033 | 0.4033 | 0.9892 | 4,348 |
| **Missing Geomorphic (3 features NaN)** | **0.5806** | **0.5764** | 0.5034 | 0.9959 | 0.6688 | 98.91% | 0.0075 | 0.0240 | 0.0965 | 5,255 |
| **Missing Landcover (1 feature NaN)** | 0.8178 | 0.8499 | 0.5854 | 0.8964 | 0.7083 | 76.57% | 0.0027 | 0.1793 | 0.9687 | 3,397 |
| **Geomorphic Only (Rainfall & LC NaN)** | 0.8506 | 0.8608 | 0.5239 | 0.9948 | 0.6863 | 94.94% | 0.0059 | 0.2560 | 0.8891 | 4,837 |

---

### 1.3 Key Findings on Missing-Feature Mechanics

1. **Why Missing Rainfall Causes False Alarms:**
   - In training data, every sample occurred during historical flood events with heavy monsoon rain.
   - During gradient tree boosting, split criteria on `rainfall_24h_mm` and `rainfall_72h_mm` assigned missing values to the branch containing the largest gain, which was the **deluge branch**.
   - Inspection of tree traversal for Patna proves that:
     $$\text{Score}(\text{Rainfall} = 0.0\text{ mm}) = 0.0092 \quad (0.92\%)$$
     $$\text{Score}(\text{Rainfall} = 184.6\text{ mm}) = 0.0477 \quad (4.77\%)$$
     $$\text{Score}(\text{Rainfall} = \mathbf{NaN}) = \mathbf{0.0477} \quad (\mathbf{4.77\%})$$
   - When rainfall is unobserved (`NaN`), the tree treats the cell **identically to a 185 mm extreme monsoon deluge!**
   - Presenting a score of $4.77\%$ in operational mode when it is sunny and dry outside is scientifically indefensible because the model is implicitly assuming an active deluge.
2. **Why Missing Terrain Collapses the Model:**
   - Terrain features (`distance_to_river_m`, `elevation_m`, `slope_deg`) represent **>65% of total tree split gain**.
   - When geomorphic features are missing, the ROC-AUC collapses to **0.5320** (essentially a random coin flip).
   - The score variance collapses into a flat range $[0.0153, 0.0262]$, causing 100% of samples to cross $\tau=0.01$ and produce 100% false alarms.
3. **Conclusion:**
   XGBoost's technical ability to accept NaNs without throwing an exception is a C++ language convenience, **not proof of scientific validity**. The model cannot defensibly screen flood susceptibility with partial feature sets.

---

## 2. Policy Formulation & Implementation

### 2.1 Formal Missing-Feature Governance Policy

```
+---------------------------------------------------------------------------------------+
|                                    Incoming Vector                                    |
|                      (11 Core National Features from GIS Pipeline)                    |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v
+---------------------------------------------------------------------------------------+
| Gate 1: Check Required Predictor Completeness                                         |
| - Inspect all 7 trained predictors:                                                   |
|   {rainfall_24h_mm, rainfall_72h_mm, rainfall_anomaly_index, elevation_m,             |
|    slope_deg, distance_to_river_m, landcover_class}                                   |
| - Condition: Are any of these 7 predictors null or NaN?                               |
+---------------------+-------------------------------------+---------------------------+
                      | YES (>= 1 predictor missing)        | NO (All 7 present)
                      v                                     v
+---------------------------------------------------+  +--------------------------------+
| SUPPRESS INFERENCE IMMEDIATELY                    |  | EXECUTE INFERENCE              |
| - Status: INSUFFICIENT_INPUT_DATA                 |  | - Status: READY                |
| - is_ready: False                                 |  | - is_ready: True               |
| - predicted_probability: None                     |  | - predicted_probability: prob |
| - susceptibility_grade: None                      |  | - susceptibility_grade: Band   |
| - input_validity: MISSING_REQUIRED_PREDICTORS     |  | - input_validity: COMPLETE     |
| - Explain exact missing predictors                |  | - Display Band & Diagnostics   |
+---------------------------------------------------+  +--------------------------------+
```

### 2.2 Invariant Rules Enforced
1. **Zero Operational Score on Partial Input:**
   Whenever real-time rainfall gauges are unobserved, operational inference at that coordinate is suppressed. Patna and Guwahati in operational mode return `INSUFFICIENT_INPUT_DATA`.
2. **Zero Fabrication:**
   Unobserved rainfall is never replaced with $0.0\text{ mm}$, mean values, or synthetic numbers.
3. **Benchmark Isolation:**
   Benchmark mode remains an explicit opt-in checkbox (`allow_benchmark_rainfall=True`). When active, it loads verified historical event storm fixtures and displays a prominent warning that results are scenario fixtures, not live observations.
4. **Frozen Model Invariant:**
   The Kaggle XGBoost artifact, schema, and thresholds remain completely frozen. No retraining was performed.

---

## 3. Cryptographic Artifact Reconciliation

A discrepancy was identified between the hash reported in `PHASE_7E_LIVE_MODEL_INTEGRATION_AUDIT.md` and a hash string appearing in `PHASE_7E_INPUT_VALIDITY_CORRECTION_REPORT.md` (line 191). We performed byte-level cryptographic auditing to reconcile all artifact identifiers.

### 3.1 Checksum Inventory

| Artifact Target | Filesystem Path / Inspection Method | File Size | SHA-256 Checksum | Reconciliation Status |
|---|---|---|---|---|
| **Kaggle Original JSON** | `data/packages/phase7e_kaggle_package/models/aquora_xgboost.json` | 434,555 bytes | `5940b9bd5e745a0085d149ff2805042847a7422233fcde765df32bdda9c844d8` | **CANONICAL ORIGINAL** |
| **Embedded Booster in Joblib** | Extracted `payload["model"].bst_json_str.encode("utf-8")` | 434,555 bytes | `5940b9bd5e745a0085d149ff2805042847a7422233fcde765df32bdda9c844d8` | **100% BIT-FOR-BIT MATCH** |
| **Live Joblib Container** | `ml/models/aquora_national_screening_model.joblib` | 437,544 bytes | `62fff9430390aa745b169802007b4032a6e446567463c88898dc52f2340a7e20` | **VERIFIED RUNTIME CONTAINER** |
| **Kaggle Random Forest** | `data/packages/phase7e_kaggle_package/models/aquora_random_forest.joblib` | 1,811,394 bytes | `9143171fee275848ad132f605012d13f73c377f3dd1393b613fa077a0e91a3e4` | **VERIFIED BENCHMARK** |
| **Booster Binary Dump** | `booster.save_raw()` (UBJ format) | 323,957 bytes | `4ef9f111286014708af4c4866bc0ba7cc47b4113cd8dc8576c19e7dca93c5549` | Native C++ Serialization |
| **Erroneous String in Report** | Text in `PHASE_7E_INPUT_VALIDITY_CORRECTION_REPORT.md` (L191) | — | `5940b9bd3b9c7cfd34208a0ea12591fa7beba905e954e7d036e6e25f69be8687` | **TYPOGRAPHICAL ARTIFACT** |

### 3.2 Root Cause of Hash Discrepancy
- The string `5940b9bd3b9c7cfd...` in line 191 of the input-validity report was investigated across all repository files and raw binary formats.
- The prefix `5940b9bd` exactly matches the first 8 characters of the true booster hash `5940b9bd5e745a00...`.
- Exhaustive verification proves that the underlying files on disk were **never modified**. The difference was a clerical copy-paste transcription error in the markdown document, where the author retained the first 8 characters but accidentally pasted an unrelated 56-character hex suffix.
- The authentic booster JSON is **100% identical** across the Kaggle export and the runtime joblib container.

---

## 4. Geographic Basin Assignment & Geometry Audit

The recent geographic corrections adjusted latitude and longitude limits for basin corridors. We audited whether these boundaries represent true watershed polygons or rectangular bounding boxes.

### 4.1 Boundary Data Files Audit
1. **`data/processed/boundaries/hydrobasins_india.json`**:
   - Contains 9 basins.
   - Contains strictly `{"bounds": {"min_lon": ..., "min_lat": ..., "max_lon": ..., "max_lat": ...}}`.
   - **Does NOT contain polygonal coordinate arrays.**
2. **`data/processed/boundaries/hydrobasins_india.geojson`**:
   - Contains 8 features.
   - Inspection of `feat['geometry']['coordinates']` proves that **every polygon consists of exactly 5 vertices** representing a closed rectangle:
     $$\text{Ring} = [[x_{\min}, y_{\min}], [x_{\min}, y_{\max}], [x_{\max}, y_{\max}], [x_{\max}, y_{\min}], [x_{\min}, y_{\min}]]$$
   - Furthermore, `BASIN-SABARMATI` is absent from this GeoJSON, and the bounding boxes reflect older uncorrected extents.
3. **Runtime Service Implementation**:
   - In `backend/app/services/india_spatial_service.py` (`get_river_basin`):
     ```python
     bounds = b["bounds"]
     if bounds["min_lon"] <= longitude <= bounds["max_lon"] and bounds["min_lat"] <= latitude <= bounds["max_lat"]:
         return b
     ```
   - Basin resolution is strictly a **rectangular bounding box intersection**, NOT true polygon containment.

### 4.2 Polygon Containment vs. Bounding Box Comparison

| Location | Coordinates | Rectangular Bounding Box Match | Old GeoJSON Rectangle Match | Hydrological Reality & Ground Truth | Assignment Confidence |
|---|:---:|---|---|---|:---:|
| **Patna** | 25.5941°N, 85.1376°E | `BASIN-GANGA` | `BASIN-GANGA` | Truly located within Ganga River valley | **High (Macro Basin)** |
| **Guwahati** | 26.1445°N, 91.7362°E | `BASIN-BRAHMAPUTRA` | `BASIN-BRAHMAPUTRA` | Truly located within Brahmaputra valley | **High (Macro Basin)** |
| **Vijayawada** | 16.5062°N, 80.6480°E | `BASIN-KRISHNA` | `BASIN-GODAVARI` (overlapping box) | Truly on Krishna River (Andhra Pradesh) | **Moderate (Bounding Box)** |
| **Nagpur** | 21.1458°N, 79.0882°E | `BASIN-GODAVARI` | `BASIN-GANGA` (overlapping box) | Truly in Godavari Basin (Wainganga sub-basin) | **Moderate (Bounding Box)** |
| **Ahmedabad** | 23.0225°N, 72.5714°E | `BASIN-SABARMATI` | `BASIN-NARMADA` (overlapping box) | Truly on Sabarmati River (Gujarat) | **Moderate (Bounding Box)** |
| **London** | 51.5074°N, -0.1278°E | None (Outside India) | None (Outside India) | Thames Basin (United Kingdom) | **Definite (Out of Coverage)** |

### 4.3 Governance Classification
Because authoritative watershed polygon shapefiles (e.g., CWC or HydroSHEDS Level 6 vector polygons) are not integrated in the runtime repository, all basin assignments must be labeled:
$$\mathbf{APPROXIMATE\_MACRO\_BOUNDS}$$
The platform **must not claim precise hydrological polygon resolution**.

---

## 5. Benchmark Rainfall Provenance Audit

An inspection of `backend/app/services/india_rainfall_service.py` was conducted to establish the authentic provenance of benchmark rainfall values.

### 5.1 Provenance Findings
- **Data Source:** Literature-derived historical monsoon storm episodes verified during the Phase 2A/2C audit.
  - `ganga_patna`: *July 2023 Indo-Gangetic Monsoon Deluge* (2023-07-10 to 2023-07-13). Accumulated 24h: $184.6\text{ mm}$, 72h: $298.4\text{ mm}$, Anomaly Index: $+8.80$.
  - `brahmaputra_guwahati`: *June 2022 Assam Extreme Basin Flood* (2022-06-16 to 2022-06-19). Accumulated 24h: $274.0\text{ mm}$, 72h: $482.0\text{ mm}$, Anomaly Index: $+8.28$.
  - `godavari_nashik`: *July 2022 Upper Godavari Western Ghats Deluge*.
  - `narmada_bharuch`: *September 2023 Lower Narmada Extreme Flood Episode*.
  - `deep_mumbai_mithi`: *August 2020 Mithi River Urban Deluge*.
- **Nature of Data:** Static, verified **non-operational benchmark test fixtures**.
- **Operational Status:** They are **NOT** live IMD telemetry gauge observations, NOT Doppler radar observations, and NOT real-time calibrated feeds.
- **Coverage:** Only pilot demonstration footprints are indexed. Other cities (Vijayawada, Nagpur, Ahmedabad) lack benchmark fixtures and correctly return `OUTSIDE_PILOT_BENCHMARK_DOMAINS`.
- **UI Guardrail:** In benchmark mode, the UI displays a mandatory warning:
  > *"BENCHMARK / HISTORICAL SCENARIO INPUT ACTIVE: Precipitation features are non-operational benchmark test fixtures, NOT real-time or calibrated gauges."*

---

## 6. Multi-Location Retest Verification

We tested the live integrated system across the 6 mandated test locations in both Operational Observation mode and Benchmark Scenario mode.

### Table 4: Final Multi-Location Verification Matrix

| Location | Coordinates | Available Predictors | Missing Predictors | Operational Inference Status | Operational Score & Grade | Benchmark Inference Status | Benchmark Score & Band | Geographic Assignment Confidence |
|---|---|---|---|:---:|:---:|:---:|:---:|:---:|
| **Patna** | 25.5941°N, 85.1376°E | Operational: 4 (DEM, Slope, River Dist, LC)<br>Benchmark: 7 (All) | Operational: 3 (24h, 72h, Anomaly)<br>Benchmark: 0 | `INSUFFICIENT_INPUT_DATA` | **Score: None**<br>Grade: None | `READY` | **Score: 4.77%**<br>Band: `LOW MODEL SCORE` | High (Approximate Macro Bounds) |
| **Guwahati** | 26.1445°N, 91.7362°E | Operational: 4 (DEM, Slope, River Dist, LC)<br>Benchmark: 7 (All) | Operational: 3 (24h, 72h, Anomaly)<br>Benchmark: 0 | `INSUFFICIENT_INPUT_DATA` | **Score: None**<br>Grade: None | `READY` | **Score: 3.30%**<br>Band: `LOW MODEL SCORE` | High (Approximate Macro Bounds) |
| **Vijayawada** | 16.5062°N, 80.6480°E | Operational: 0<br>Benchmark: 0 | Operational: 7 (All)<br>Benchmark: 7 (All) | `INSUFFICIENT_INPUT_DATA` | **Score: None**<br>Grade: None | `INSUFFICIENT_INPUT_DATA` | **Score: None**<br>Grade: None | Moderate (Approximate Macro Bounds) |
| **Nagpur** | 21.1458°N, 79.0882°E | Operational: 0<br>Benchmark: 0 | Operational: 7 (All)<br>Benchmark: 7 (All) | `INSUFFICIENT_INPUT_DATA` | **Score: None**<br>Grade: None | `INSUFFICIENT_INPUT_DATA` | **Score: None**<br>Grade: None | Moderate (Approximate Macro Bounds) |
| **Ahmedabad** | 23.0225°N, 72.5714°E | Operational: 0<br>Benchmark: 0 | Operational: 7 (All)<br>Benchmark: 7 (All) | `INSUFFICIENT_INPUT_DATA` | **Score: None**<br>Grade: None | `INSUFFICIENT_INPUT_DATA` | **Score: None**<br>Grade: None | Moderate (Approximate Macro Bounds) |
| **London** | 51.5074°N, -0.1278°E | Operational: 0<br>Benchmark: 0 | N/A (Outside Extent) | `OUTSIDE_COVERAGE` | **Score: None**<br>Grade: None | `OUTSIDE_COVERAGE` | **Score: None**<br>Grade: None | Definite (Outside India Extent) |

---

## 7. Quality Assurance & System Verification

### 7.1 Automated Backend Test Suite
The following backend test suites were executed using `pytest`:
- `backend/tests/test_phase3_national_screening_model.py`: **14 / 14 PASSED** (Deterministic inference, strict input validity, batch limits, schema tamper rejection, physics isolation).
- `backend/tests/test_phase1_india_expansion.py`: **10 / 10 PASSED** (Spatial extent bounds, tier resolution, zero fabrication).
- `backend/tests/test_phase2e_feature_pipeline.py`: **14 / 14 PASSED** (Feature matrix extraction, anti-leakage exclusion, coordinate consistency).
- **Total Backend Tests:** **38 / 38 PASSED** (100% pass rate).

### 7.2 Frontend Production Build
The frontend TypeScript and Vite production build was executed:
- `npx tsc`: **0 errors**. Strict mode enforced.
- `npx vite build`: **Clean build in 6.80s**. All assets bundled without warnings or errors.

### 7.3 Headless Browser Verification
Headless Playwright testing verified the live React UI on `http://localhost:5175/app`:
1. `patna_operational_insufficient.png`: Confirmed that in default operational mode, Patna displays the dedicated `INSUFFICIENT INPUT DATA` card, suppresses the percentage score, suppresses the grade pill, and itemizes the 3 unobserved rainfall gauges.
2. `patna_benchmark_valid_score.png`: Confirmed that when the user explicitly enables benchmark rainfall, Patna displays `4.77%`, `LOW MODEL SCORE`, the amber benchmark disclaimer, and the complete 11-feature provenance table.
3. `vijayawada_governance_audit.png`: Confirmed that Vijayawada displays `INSUFFICIENT INPUT DATA` with 0/7 available predictors, preventing base score artifacts.

---

## 8. Remaining Data Requirements for National Operational Deployment

To transition National Screening from an experimental benchmark to a fully operational live screening tool, the following data pipelines are required:
1. **Nationwide Copernicus GLO-30 DEM Tiling:**
   Expand raster indexing beyond pilot corridors (Ganga, Brahmaputra, Godavari, Narmada) to cover all of peninsular and southern India (e.g. Krishna, Cauvery, Mahanadi).
2. **IMD / NCMRWF Real-Time Gridded Rainfall Telemetry:**
   Integrate automated daily/sub-daily gridded operational precipitation feeds (e.g. IMD $0.25^\circ$ rainfall or NCMRWF GFS) to provide live non-null observations for `rainfall_24h_mm` and `rainfall_72h_mm`.
3. **Authoritative Watershed Catchment Vectors:**
   Ingest Central Water Commission (CWC) or HydroBASINS Level 5/6 polygon shapefiles to replace rectangular bounding-box checks with true point-in-polygon containment.
4. **Empirical Probability Calibration:**
   Apply Isotonic Regression or Platt Scaling across nationwide historical validation events before any score is interpreted as an operational flood probability.

---

## 9. Final Governance Decision

$$\mathbf{FINAL\_DECISION:\; OPERATIONAL\_PARTIAL\_INFERENCE\_SUPPRESSED}$$

The Phase 7E National XGBoost screening model is **NOT operationally reliable merely because its API returns a floating-point number**. 

Evaluating the model without rainfall predictors distorts predictions by treating missing data as extreme deluge rainfall. Therefore, operational inference on partial inputs is **permanently prohibited**. The model will only compute a susceptibility score when complete, non-fabricated predictors are present.

**Signed & Certified:**  
*Antigravity Autonomous Systems & Scientific Verification Team*  
*AQUORA Flood Intelligence Platform*

