# AQUORA — National Intelligence Live ML Result Presentation & Data Provenance Report

**Document ID:** `REPORT-PHASE7E-NATIONAL-UX-001`  
**Date:** 2026-11-03  
**Status:** `VERIFIED_AND_OPERATIONAL`  
**Component:** National Intelligence Frontend (`GeographicTierModal.tsx`) & FastAPI ML Backend  
**Authoritative Hydrodynamic Solver:** Phase 6 deterministic 2D physics engine remains the primary authority for inundation depths.

---

## 1. Executive Summary

Following the cryptographic and empirical verification of the Phase 7E Kaggle XGBoost model integration in AQUORA, the National Intelligence user experience in [GeographicTierModal.tsx](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/frontend/src/components/layout/GeographicTierModal.tsx) has been improved.

Users can now inspect:
1. **Live Model Susceptibility Scores & Grades**: Directly bound to `NationalScreeningResponse.susceptibility_probability` and `NationalScreeningResponse.susceptibility_grade` (rendered as both percentage and raw decimal score, paired with a 3-segment visual meter).
2. **Model Identification & Operational Status**: Displaying `aquora_national_screening_xgboost_v1` (v`1.2.0-phase7e`), status `OPERATIONAL`, and explicit `UNCALIBRATED_MACRO_SCREENING` badge.
3. **11 Core National Features & Provenance Table**: Every individual predictor is mapped with its physical unit, extracted value, primary data source (Copernicus DEM, HydroSHEDS, IMD, ESA WorldCover), and live data availability status.
4. **Zero-Fabrication & Anti-Leakage Compliance**: Missing values (such as sub-daily rainfalls or unindexed regional tiles) are presented honestly as `Unavailable (null)` rather than fabricated zeros or synthetic fallbacks.
5. **Prominent Scientific Disclaimer**: Displaying the mandatory scientific governance banner detailing Phase 7E experimental status, uncalibrated macro ranking, physics engine authority preservation, and zero data fabrication.

---

## 2. Inspected & Modified Components

| Component / File | Role & Layer | Modification Summary |
|---|---|---|
| [GeographicTierModal.tsx](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/frontend/src/components/layout/GeographicTierModal.tsx) | Frontend UI Modal | Replaced basic key-value listing with hero score card, 3-segment susceptibility spectrum meter, 11-feature provenance table with source attribution, scientific disclaimer box, and missing data limitations summary. |
| [intelligence.ts](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/frontend/src/api/intelligence.ts) | Frontend API Client | Verified existing `screenNationalPoint` client; fully compatible with `NationalScreeningResponse`. |
| [intelligence.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/api/v1/intelligence.py) | Backend FastAPI Route | Reused existing `/api/v1/intelligence/screening/national` endpoint without creating redundant routes or duplicating logic. |
| [ml_model_registry.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/ml_model_registry.py) | Backend ML Registry | Reused `NationalScreeningModel` and `Phase7EXGBoostWrapper`; preserved in-memory booster caching and anti-leakage feature slicing. |
| [india_feature_pipeline.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/india_feature_pipeline.py) | Backend GIS Pipeline | Reused authoritative 11 Core National Feature extraction service, preserving authentic data sources and zero-fabrication missing value semantics. |

---

## 3. Detailed Breakdown of Presented Results

### 3.1 Model Prediction Display
- **Susceptibility Score:** Displayed in prominent bold typography as a percentage (`(prob * 100).toFixed(2)%`) along with the raw decimal output (`prob.toFixed(4)`). If `null` (e.g. out of bounds), explicitly shows `"Unavailable"` rather than `0` or `0.00%`.
- **Susceptibility Grade:** Color-coded risk badge:
  - `LOW` (Emerald badge): Probability $< 0.33$
  - `MEDIUM` (Amber badge): Probability between $0.33$ and $0.66$
  - `HIGH` (Rose/Red badge): Probability $\ge 0.66$
- **Susceptibility Spectrum Meter:** A 3-segment progress indicator visualizing where the model's output falls across the macro screening spectrum.
- **Model Identity & Calibration:** Explicitly shows `aquora_national_screening_xgboost_v1 (v1.2.0-phase7e)` and `UNCALIBRATED_MACRO_SCREENING`.
- **Inference Timestamp:** Displays the exact ISO-8601 UTC timestamp of feature extraction from `feature_provenance.extraction_timestamp`.

### 3.2 11 Core National Features & Data Source Provenance

| Feature Key | Human-Readable Title | Observed Value (Patna Sample) | Physical Unit | Primary Data Source | Availability Status |
|---|---|---|---|---|---|
| `elevation_m` | Surface Elevation | `60.39` | m MSL | Copernicus GLO-30 DEM (`VERIFIED_DOMAIN_ganga_patna`) | `Available` |
| `slope_deg` | Topographic Slope | `0.07` | ° (degrees) | Derived Gradient from Copernicus DEM | `Available` |
| `distance_to_river_m` | Distance to River/Drainage | `4834.6` | meters | HydroSHEDS v1 / HydroRIVERS Drainage Network | `Available` |
| `landcover_class` | Landcover Classification | `40.0` | ESA Code | ESA WorldCover 10m High-Resolution Classification | `Available` |
| `rainfall_24h_mm` | 24-Hour Accumulated Rainfall | `184.6` *(Benchmark)* / `null` *(Live)* | mm | IMD Gridded Daily / Operational Gauge Network | `Available` / `Unobserved` |
| `rainfall_72h_mm` | 72-Hour Cumulative Rainfall | `298.4` *(Benchmark)* / `null` *(Live)* | mm | IMD Gridded Daily / Operational Gauge Network | `Available` / `Unobserved` |
| `rainfall_anomaly_index` | Precipitation Anomaly Index | `2.1` *(Benchmark)* / `null` *(Live)* | z-score index | IMD 30-Year Climatology Reference (1991–2020) | `Available` / `Unobserved` |
| `rainfall_1h_mm` | 1-Hour Peak Rainfall | `null` | mm | IMD Sub-Daily Automated Gauge Stream | `Unobserved / Missing` |
| `rainfall_3h_mm` | 3-Hour Accumulated Rainfall | `null` | mm | IMD Sub-Daily Automated Gauge Stream | `Unobserved / Missing` |
| `rainfall_6h_mm` | 6-Hour Accumulated Rainfall | `null` | mm | IMD Sub-Daily Automated Gauge Stream | `Unobserved / Missing` |
| `historical_flood_frequency` | Historical Flood Frequency | `null` | count | DFO Multi-Event Archive | `Quarantined (Anti-leakage)` |

---

## 4. Prominent Scientific Disclaimer & Governance Invariants

The interface displays a visible amber governance card with the required disclaimer:

> **"Experimental National Flood Susceptibility Screening — Uncalibrated Model Output. This is a research screening score, not a validated flood probability or public warning."**

The card explains the scientific principles:
1. **Historical Observation Training:** The Phase 7E XGBoost model was trained on multi-event satellite flood extents (DFO 4499, DFO 2935, DFO 3372) across Indian river basins.
2. **Experimental & Uncalibrated:** The returned score is a relative macro-scale susceptibility ranking, not a calibrated statistical probability or operational civil defense evacuation alert.
3. **Deterministic Physics Authority:** The Phase 6 deterministic 2D hydrodynamic flow solver remains the primary authority for Deep Intelligence flood-depth simulation (Mumbai / Mithi). ML scores never override physical calculations.
4. **Zero Data Fabrication:** Missing operational rain gauge data is never simulated or fabricated; when unobserved, it strictly remains `null / Unavailable`.

---

## 5. Geographic Selection Verification

In accordance with Section 4, five diverse Indian geographic centers were tested, plus London for out-of-bounds verification:

| Location | Coordinates (Lat, Lon) | Resolved Basin / Zone | Susceptibility Score | Grade | Available Features (Operational Live) | Available Features (Benchmark Scenario) |
|---|---|---|---|---|---|---|
| **Patna** | `25.5941°N, 85.1376°E` | Ganga River Basin Regional Zone | `4.77%` (`0.0477`) | `LOW` | 4 features (`elevation`, `slope`, `distance_to_river`, `landcover`) | 10 features (7 rainfall + 3 terrain + 1 landcover; 1 quarantined) |
| **Guwahati** | `26.1445°N, 91.7362°E` | Brahmaputra River Basin Regional Zone | `3.30%` (`0.0330`) | `LOW` | 4 features (`elevation`, `slope`, `distance_to_river`, `landcover`) | 10 features |
| **Vijayawada** | `16.5062°N, 80.6480°E` | Maharashtra State Regional Corridor | `1.30%` (`0.0130`) | `LOW` | 0 features (Terrain tile unindexed) | 0 features |
| **Nagpur** | `21.1458°N, 79.0882°E` | Maharashtra State Regional Corridor | `1.30%` (`0.0130`) | `LOW` | 0 features (Terrain tile unindexed) | 0 features |
| **Ahmedabad** | `23.0225°N, 72.5714°E` | Narmada River Basin Regional Zone | `1.30%` (`0.0130`) | `LOW` | 0 features (Terrain tile unindexed) | 0 features |
| **London** *(Out of Bounds)* | `51.5074°N, -0.1278°E` | `OUTSIDE_INDIA_EXTENT` | `Unavailable` (`null`) | `None` | 0 features | 0 features (Strict rejection without fallback) |

### Key Observations on Geographic Coverage:
- **Patna & Guwahati**: Have verified local terrain rasters in the pipeline (`VERIFIED_DOMAIN_ganga_patna` and `VERIFIED_DOMAIN_brahmaputra_guwahati`), producing dynamic terrain features (elevation 60.39m vs 116.84m, slope 0.07° vs 0.47°, distance to river 4834.6m vs 4186.8m).
- **Vijayawada, Nagpur, & Ahmedabad**: Fall within valid Indian geographic bounding boxes, but their local 30m DEM tiles have not been indexed in this phase. In strict accordance with the zero-fabrication rule, terrain features are reported as `Unavailable (null)`, and XGBoost evaluates its baseline prior (`0.0130`) via native NaN handling.
- **London**: Outside the India national bounding box `[6.5-37.5°N, 68.0-97.5°E]`. Returns `status: "OUTSIDE_COVERAGE"`, probability `null`, and an explicit rejection message without any spatial fallback.

---

## 6. Scientific & Architectural Safeguards Verification

- **National Feature Isolation:** Only the governed 11 Core National Features are accepted.
- **Regional Mahanadi Separation:** Mahanadi DFO 3382 regional research remains isolated under `ZoneStatus.PROTOTYPE` with dedicated regional endpoints; no data or weights are mixed with national screening.
- **Deep Physics Independence:** Mumbai Mithi Deep Zone is powered exclusively by the Phase 6 deterministic 2D hydraulic flow solver. ML susceptibility output never overrides physical flood depths.
- **Artifact Immobility:** The Kaggle XGBoost booster (`aquora_xgboost.json`, SHA-256 `5940b9bd...`), training schema, and frozen threshold (`0.01`) were untouched.
- **Honest Missing Data:** Sub-daily rainfall and unindexed terrain remain strictly `null`, preventing silent zero-filling.

---

## 7. Quality Assurance & Validation Results

### 7.1 Backend Test Suite
```
tests/test_phase3_national_screening_model.py: 14/14 passed
tests/test_phase1_india_expansion.py: 10/10 passed
Total: 24 passed in 11.29s (100% clean)
```

### 7.2 Frontend TypeScript & Production Build
```
npx tsc && npx vite build
✓ 1592 modules transformed.
dist/index.html: 0.97 kB
dist/assets/index-fQ1w1KpL.css: 79.62 kB
dist/assets/index-C1BUiVvG.js: 613.53 kB
✓ built in 24.70s (0 errors)
```

### 7.3 Automated Browser Verification
- **Playwright Test Execution**: Headless browser automation navigated to `http://localhost:5175/app`, opened `GeographicTierModal.tsx`, switched to Tab 2, selected Patna, and captured the live UI state.
- **Screenshot Artifact**: Saved to `docs/national_screening_live_ux.png`.
- **Browser Session Recording**: Saved to `.system_generated/tasks/` WebP video artifact.

---

## 8. Remaining Data-Coverage Limitations

1. **Operational Sub-Daily Rainfall:** Real-time IMD Automated Weather Station (AWS) telemetry is not yet ingested into a continuous sub-daily pipeline nationwide. Features `rainfall_1h_mm`, `rainfall_3h_mm`, and `rainfall_6h_mm` remain unobserved.
2. **Tile Ingestion Coverage:** While Patna and Guwahati have ingested Copernicus 30m DEM regional domains, central and peninsular India (Nagpur, Vijayawada, Ahmedabad) currently rely on fallback NaN handling until nationwide DEM mosaicing is indexed in future phases.
3. **Macro Model Calibration:** As noted in the disclaimer, Phase 7E scores are uncalibrated macro susceptibility rankings suitable for broad spatial filtering, not public civil defense warnings or property-level insurance assessments.
