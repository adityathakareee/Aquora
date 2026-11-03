# AQUORA — Final Stabilization, Model Governance & Architectural Safety Report

**Document ID:** `DOC-AQUORA-FINAL-STABILIZATION-2026-V1`  
**Classification:** Scientific Governance, Model Safety & Architectural Verification Report  
**Date:** November 3, 2026  
**Status:** Approved & Validated Project Closure Baseline  
**Authority:** Antigravity Engineering & Hydrological Systems Group  

---

## 1. Executive Overview & Governance Mandate

This report documents the comprehensive stabilization, semantic reconciliation, and architectural safety enforcement executed to achieve formal project closure for **AQUORA 2.0**.

AQUORA is a dual-tier hydrological intelligence system integrating:
1. **Deterministic Hydrodynamics (Phase 6):** 2D shallow-water physical solver operating with strict mass balance conservation ($\Delta M < 10^{-4}\,\text{m}^3$) as the primary, authoritative simulation engine.
2. **National Macro Screening (Phase 7E):** Uncalibrated machine learning susceptibility ranking based on a frozen 7-feature XGBoost classifier.

To prevent misapplication, catastrophic extrapolation, or misleading scientific claims, all system components have been stabilized under strict governance protocols:
- **ML Authority Restriction:** The Phase 7E ML model remains classified as `PROTOTYPE_ONLY`, `NOT_CALIBRATED`, and `NOT_FOR_PUBLIC_ALERTS`. Its outputs are strictly interpreted as uncalibrated macro susceptibility ranking scores (`LOW`, `MEDIUM`, `HIGH`), never as calibrated probabilities, flood warnings, or inundation depths.
- **Physical Solver Primacy:** In any geographic overlap (e.g., Mumbai / Mithi River catchment), the deterministic shallow-water solver possesses unconditional operational primacy. Machine learning models are strictly secondary and exploratory.
- **Operational vs. Benchmark Strict Decoupling:** Non-operational disaster benchmark fixtures (e.g., NASA IMERG historical deluges, CHIRPS storm reconstructions) are strictly isolated behind explicit test flags (`allow_benchmark_rainfall=True`). Operational live inference suppresses scoring (`INSUFFICIENT_INPUT_DATA`) whenever complete, real-time observations are unavailable.
- **Holdout DFO 2507 Quarantine:** Dartmouth Flood Observatory event DFO 2507 remains completely untouched in blind quarantine for independent post-closure evaluation.

---

## 2. Frozen Model Feature Compatibility & Semantic Reconciliation

### 2.1 Investigation of `distance_to_river_m` Training Semantics

An exhaustive code-level audit of the Phase 7 training pipeline was conducted to establish the exact physical and mathematical definition of the `distance_to_river_m` feature consumed by the frozen Phase 7E XGBoost model:
- **Training Source Code Audit:** In `scripts/prepare_phase7c_multievent_dataset.py` (lines 324–336), `scripts/generate_kaggle_notebook.py` (line 82), and `scripts/package_phase7e_kaggle_package.py` (lines 95, 257), the predictor `distance_to_river_m` was derived via Euclidean distance transformation over the **Global Flood Database (GFD) Band 5 / JRC Global Surface Water permanent water mask (`gfd_jrc_perm_water == 1.0`)**.
- **Physical Meaning:** The training feature represents metric distance to the perimeter of permanent surface open water bodies (river channels, lake shores, estuarine deltas) as observed optically by multi-decadal satellite sensors (JRC GSW, Pekel et al., 2016).
- **Comparison with HydroRIVERS Asia:** HydroRIVERS v1.0 represents a vector topological streamline network based on synthetic digital elevation drainage algorithms (Lehner & Grill, 2013). While topologically rich, HydroRIVERS reach centerlines do not represent 2D open-water surface boundaries.

### 2.2 Quantitative Semantic Divergence

Comparative analysis over the Vijayawada (`krishna_vijayawada`) domain demonstrates significant semantic divergence:

| Metric | JRC Permanent Open Water Distance | HydroRIVERS Reach Centerline Distance | Divergence ($\Delta$) |
| :--- | :--- | :--- | :--- |
| **Physical Feature** | 2D Open Water Boundary | 1D Streamline Topological Centerline | Different physical entity |
| **Minimum Distance** | $0.0\,\text{m}$ | $0.0\,\text{m}$ | $0.0\,\text{m}$ |
| **Mean Distance** | $4,493.9\,\text{m}$ | $2,918.8\,\text{m}$ | $+1,575.1\,\text{m}$ ($+54.0\%$) |
| **Maximum Distance**| $11,901.4\,\text{m}$ | $15,056.2\,\text{m}$ | $-3,154.8\,\text{m}$ |
| **Standard Deviation**| $2,784.2\,\text{m}$ | $3,421.0\,\text{m}$ | $-636.8\,\text{m}$ |

### 2.3 Strict Separation Policy & Architectural Implementation

Feeding HydroRIVERS reach distances into the frozen Phase 7E model would cause substantial out-of-distribution feature drift and violate scientific integrity. The architecture has therefore been updated with clean separation:
1. **`distance_to_river_m`:** Preserved strictly as Euclidean distance to authentic JRC permanent surface water pixels. Fed into the frozen Phase 7E model only when derived from authentic JRC GSW occurrence rasters (e.g., Patna, Vijayawada).
2. **`hydrorivers_reach_distance_m`:** Preserved as an independent, authentic hydrographic metric in `NationalDataContract`, `NationalScreeningResponse`, `IndiaSpatialService`, and API contracts.
3. **Unobserved JRC Protection:** In domains where authentic JRC occurrence tiles were not acquired (Guwahati, Nagpur, Ahmedabad), `distance_to_river_m` is strictly recorded as `None`. Under Policy Gate 3, the national screening service suppresses inference with `INSUFFICIENT_INPUT_DATA`, preventing uncalibrated, distorted inference.
4. **Model Freeze Preservation:** The frozen model artifact `ml/models/aquora_national_screening_model.joblib` (SHA-256: `62fff9430390aa745b169802007b4032a6e446567463c88898dc52f2340a7e20`) has NOT been retrained, modified, or altered in any way.

---

## 3. Model Governance & Terminology Audit

All backend schemas, service responses, API documentation, and frontend views have been harmonized under approved terminology:

| Category | Approved Terminology | Prohibited Terminology | Enforcement Action |
| :--- | :--- | :--- | :--- |
| **Physics Solver** | "Physical Flood Simulation", "Deterministic 2D Shallow-Water Solver" | "ML Flood Forecast", "Statistical Model Depth" | Enforced in `app/core/model_contract.py` |
| **Screening ML** | "Statistical Risk Signal", "Macro Flood Susceptibility Score", "Uncalibrated Ranking" | "Calibrated Probability", "Validated Flood Forecast", "Predicted Depth" | Enforced in `screening.py` & UI labels |
| **Radar Evidence** | "Observed SAR Evidence", "Sentinel-1 Backscatter Delta" | "Observed Depth", "Flood Extent Truth" | Enforced in `india_sar_service.py` |
| **Meteorology** | "Historical Benchmark Fixture", "Operational Gauge Observation" | "Live Observation" (when benchmark) | Enforced in `india_rainfall_service.py` |

### API Contract Invariants
The `NationalScreeningResponse` contract explicitly delivers mandatory governance fields on every request:
```json
{
  "status": "READY",
  "is_ready": true,
  "calibration_status": "UNCALIBRATED_MACRO_SCREENING",
  "governance_status": "PROTOTYPE_ONLY",
  "operational_readiness": "NOT_FOR_PUBLIC_ALERTS",
  "physics_engine_primacy": "Phase 6 deterministic physics engine remains primary authority",
  "hydrorivers_reach_distance_m": 2918.8
}
```

---

## 4. Operational vs. Benchmark Rainfall Isolation

To prevent benchmark-to-operational leakage:
1. **Default Operational Mode:** When `allow_benchmark_rainfall=False` (the default), `IndiaRainfallService` queries real-time providers. Because real-time telemetry is currently unintegrated, rainfall features evaluate to `None`.
2. **Policy Gate 3 Enforcement:** Any missing predictor among the 7 trained features triggers immediate inference suppression:
   - `status`: `"INSUFFICIENT_INPUT_DATA"`
   - `is_ready`: `false`
   - `susceptibility_probability`: `null`
   - `susceptibility_grade`: `null`
3. **Explicit Benchmark Tagging:** When `allow_benchmark_rainfall=True` is provided (dev/testing), the response provenance records:
   - `rainfall_status`: `"UNAVAILABLE"`
   - `rainfall_is_benchmark`: `true`
   - `rainfall_note`: `"NON_OPERATIONAL_TEST_FIXTURE"`

---

## 5. Geographic Hierarchy Stabilization across 6 Priority Cities

The seven-tier geographic hierarchy:
$$\text{Country} \longrightarrow \text{State} \longrightarrow \text{District} \longrightarrow \text{Regional Basin} \longrightarrow \text{City} \longrightarrow \text{Local Catchment} \longrightarrow \text{Deep Intelligence Zone}$$
has been verified across all six operational anchor locations:

| City | State | Resolved Regional Watershed (HydroBASINS Lev04) | HydroBASINS Pkg ID | Local Catchment Identity | Deep Intelligence Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Patna** | Bihar (`IN-BR`) | Ganga River Basin | `4040960480` | Patna Urban Storm Corridor | Supported National / Regional |
| **Guwahati** | Assam (`IN-AS`) | Brahmaputra River Basin | `4040960200` | Guwahati Hills & Floodplain | Supported National / Regional |
| **Mumbai** | Maharashtra (`IN-MH`) | Coastal Maharashtra / Western Ghats | `4040029530` | Mithi River Catchment | **EXCLUSIVE DEEP ZONE** |
| **Vijayawada** | Andhra Pradesh (`IN-AP`) | Krishna River Basin | `4040027940` | Krishna Delta / Prakasam | Supported National / Regional |
| **Nagpur** | Maharashtra (`IN-MH`) | Godavari River Basin | `4040027780` | Nag River / Kanhan Valley | Supported National / Regional |
| **Ahmedabad**| Gujarat (`IN-GJ`) | Sabarmati River Basin | `4040031820` | Sabarmati Riverfront | Supported National / Regional |

**Critical Architectural Invariant:** Mumbai / Mithi River catchment remains the **sole and exclusive Deep Intelligence Zone** in the entire AQUORA platform. All other locations reject Deep requests with explicit HTTP 400 / 422 error envelopes.

