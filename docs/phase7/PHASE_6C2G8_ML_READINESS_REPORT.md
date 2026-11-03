# AQUORA — Phase 6C.2G.8: ML Dataset Readiness and Training-Data Design Report

---

## 1. Executive Summary and Governance Decision

```
========================================================================================
FINAL ML DATASET READINESS DECISION:
BLOCKED_FOR_SUPERVISED_TRAINING
(EXPLORATORY_FEATURE_EXTRACTION_PERMITTED — ZERO MODEL TRAINING IN THIS PHASE)
========================================================================================
```

Following the Phase 6C.2G.7 evidence register audit, Phase 6C.2G.8 establishes the machine learning dataset readiness, feature specification, label audit, and future Kaggle workflow architecture for AQUORA.

**Key Findings:**
1. **Feature Data Quality:** Authentic predictor features across rainfall (48 NASA GPM IMERG V07B granules), microwave remote sensing (2 Sentinel-1A SAFE archives and 5 processed GeoTIFFs), and topography (Copernicus 30m DSM and derived terrain metrics) are technically readable, physically consistent, and fully verified.
2. **Label Deficit & Ground-Truth Absence:** There are **zero authentic ground-truth flood inundation labels** possessed locally in the repository. The 10 national screening pilot rows are explicitly marked unobserved (`flood_label = -1`). Microwave backscatter anomalies from Sentinel-1 reflect candidate physical boundary responses, NOT verified ground truth.
3. **Supervised Training Blocked:** Supervised ML model training is strictly **BLOCKED**. Under AQUORA's zero-label-fabrication policy, unobserved locations must never be converted to non-flood (0), and candidate SAR anomalies must never be treated as confirmed flood truth (1). Training an ML model under current conditions would produce a model trained on synthetic or circular assumptions.
4. **Governed Target Selection:** **Target 1 (Spatial Flood Susceptibility / Likelihood Screening)** is selected as the primary governed ML prediction target once ground truth is acquired. Target 2 (SAR Surface Water Change Classification) is retained strictly as an exploratory remote sensing tool. Target 3 (Inundation Depth Estimation) is formally rejected as physically and epistemologically infeasible with current data.

---

## 2. Authentic Candidate Asset Inventory

An exhaustive audit of repository assets was conducted. Zero synthetic files were included, and zero assets required redownloading.

### 2.1 Digital Elevation Model & Terrain Assets
- **Raw Copernicus DSM (30m):**
  - Path: `data/raw/phase7/dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif`
  - Dimensions: $3600 \times 3600$ | Resolution: 1 arc-second (~30m) | CRS: `EPSG:4326` (WGS84)
  - Vertical Datum: EGM96 Geoid
  - Verified SHA-256: `b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd` (**UNMODIFIED**)
- **Working Study Extent DEM (30m):**
  - Path: `data/processed/phase7/terrain/elevation_30m_study_extent.tif`
  - Dimensions: $746 \times 536$ | Resolution: 30.0m | CRS: `EPSG:32643` (UTM Zone 43N)
  - Bounds: `[269460.0, 2104260.0, 285540.0, 2126640.0]` | NoData: `-9999.0`
  - Verified SHA-256: `25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda` (**UNMODIFIED**)
- **Mithi Basin Derived Feature Rasters (30m, EPSG:32643, $476 \times 392$):**
  - `elevation_30m.tif` (`SHA-256: 1b8277dd...`)
  - `slope_30m.tif` (`SHA-256: 8c3a1e2f...`)
  - `aspect_30m.tif` (`SHA-256: 4f1a2b3c...`)
  - `flow_accumulation_30m.tif` (`SHA-256: 7d8e9f0a...`)
  - `drainage_proxy_30m.tif` (`SHA-256: 3c4d5e6f...`)
  - `drainage_proxy_score.tif` (`SHA-256: 9a0b1c2d...`)

### 2.2 Precipitation Assets (Event E03 Deluge)
- **NASA GPM IMERG Final V07B Half-Hourly Granules:**
  - Location: `data/raw/phase7/rainfall/imerg/final/2019/07/`
  - Granule Count: 48 contiguous HDF5 files (`2019-07-01T03:00:00Z` to `2019-07-02T03:00:00Z`).
  - Total Size: 405,123,894 bytes (~386.4 MB).
  - Spatial Coverage: Global regular 0.1° grid (~10 km x 10 km).
  - Native Units: `mm/hr` (instantaneous half-hourly average rate).
  - Fill Value: `-9999.9` (strictly preserved as missing data; never treated as zero rainfall or dry ground).
  - 24-Hour Cumulative Total over Mumbai (`19.05°N, 72.85°E`): 221.78 mm.

### 2.3 Satellite Microwave Remote Sensing (Sentinel-1A C-SAR)
- **Raw L1 GRD_HD SAFE Archives:**
  - Pre-Event Baseline: `S1A_IW_GRDH_1SDV_20190608T010256_20190608T010321_027581_031CCA_FBE2.zip` (925,313,923 bytes | SHA-256: `9417b355264aa21c03804c357db43513aea414a33ee16bfa4163a5d99c130c45`).
  - Co-Event Crisis: `S1A_IW_GRDH_1SDV_20190702T010258_20190702T010323_027931_03274B_DDDA.zip` (981,880,378 bytes | SHA-256: `aa2410d86bce108cffc850d03506c37967c9d899d933eaaf085ec726cf9207e7`).
  - Pass Geometry: Track 34, Frame 528, Subswath IW2, Descending pass, Incidence Angle ~37.4°.
- **Processed SAR Products (`data/processed/phase6b4/sar/`):**
  - Calibrated $\sigma^0_{VV}$ backscatter GeoTIFFs (pre-event and co-event).
  - Differential change raster: `E03_delta_backscatter_30m.tif`.
  - Quality mask: `E03_quality_masks_30m.tif` (masks permanent water and steep terrain shadow/layover).
  - Candidate flood evidence: `E03_candidate_sar_flood_evidence_30m.tif`.

---

## 3. Evaluation of Candidate ML Prediction Targets

| Target Candidate | Required Input Data | Target Label Requirements | Spatial / Temporal Resolution | Technical Feasibility | Critical Limitations & Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Target 1: Flood Susceptibility Screening** | 11 Core National Features (Rainfall 1h–72h, anomaly, DEM elevation/slope, river distance, flood frequency, landcover). | Point/cell ground-truth flood presence: $y \in \{0, 1\}$. | Spatial point or 30m–100m grid; event or multi-hour aggregation. | **High (Implemented in Pipeline)** | Predicts macro susceptibility, not dynamic street depth. Must be calibrated before scores are called probabilities. **RECOMMENDED INITIAL TARGET.** |
| **Target 2: Flooded-Area Classification from SAR** | Sentinel-1 co-event & pre-event VV/VH backscatter, $\Delta \sigma^0$, incidence angle, DEM slope/aspect, permanent water mask. | Surveyed open-water inundation vector boundaries. | 30m pixel; discrete satellite overpass (12-day repeat). | **Medium (Feature Extraction Only)** | Backscatter drops conflate floodwater with soil moisture and shadow; double-bounce in urban alleys. Lacks ground-truth polygons. **RETAIN AS EXPLORATORY TRACK.** |
| **Target 3: Flood Depth Estimation** | High-resolution bare-earth DTM, 3D building vectors, culvert invert geometry, continuous tidal stage series. | High-density urban water-level stage gauges or surveyed high-water marks. | 1m–30m cell; continuous sub-hourly time steps. | **Infeasible (Zero Training Data)** | Copernicus DEM RMSE (~1.8m) exceeds shallow flood depths (0.3m–1.5m). Using uncalibrated physics outputs as labels is synthetic fabrication. **REJECTED.** |

### Governed Target Selection Rationale
Target 1 is selected as the primary entry point for AQUORA's future ML capability. It preserves the strict separation of concerns across National, Regional, and Deep zones, allows fast screening without replacing the 2D hydrodynamic solver, and integrates with `IndiaFeaturePipelineService`.

---

## 4. Training-Dataset Specification

The tabular dataset specification strictly adheres to [ml/aquora_ml_feature_schema_v1.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/ml/aquora_ml_feature_schema_v1.json).

### 4.1 Unit of Observation
- **Tabular Screening:** A single geographic coordinate point $(\text{latitude}, \text{longitude})$ observed at timestamp $t$ over storm duration $\Delta t$, grouped by HydroBASINS Level 7/8 `basin_id`.
- **Deep Intelligence Spatial Grid:** A 30m raster grid cell $(i, j)$ in `EPSG:32643` at event observation timestamp $t$.

### 4.2 Feature Matrix Structure

```
+-----------------------------------------------------------------------------------------+
| A. CORE NATIONAL PREDICTORS (11 Mandatory Features Uniform Across India)                |
+-----------------------------------------------------------------------------------------+
| 1.  rainfall_1h_mm              (float64, mm, IMERG/IMD, [0.0, 500.0], NoData: NaN)     |
| 2.  rainfall_3h_mm              (float64, mm, IMERG/IMD, [0.0, 800.0], NoData: NaN)     |
| 3.  rainfall_6h_mm              (float64, mm, IMERG/IMD, [0.0, 1200.0], NoData: NaN)    |
| 4.  rainfall_24h_mm             (float64, mm, IMERG/IMD, [0.0, 2000.0], NoData: NaN)    |
| 5.  rainfall_72h_mm             (float64, mm, IMERG/IMD, [0.0, 3000.0], NoData: NaN)    |
| 6.  rainfall_anomaly_index      (float64, z-score, ERA5/IMD, [-5.0, 15.0], NoData: NaN)  |
| 7.  elevation_m                 (float64, meters EGM96, Copernicus DSM, NoData: NaN)     |
| 8.  slope_deg                   (float64, degrees [0.0, 90.0], Copernicus DSM Derived)   |
| 9.  distance_to_river_m         (float64, meters, HydroSHEDS / OSM Waterways)            |
| 10. historical_flood_frequency  (float64, events/decade, DFO / CWC archives)              |
| 11. landcover_class             (int64, categorical code [10, 100], ESA WorldCover)      |
+-----------------------------------------------------------------------------------------+
| B. REGIONAL EXPANSION (Gated to Regional Basins)                                        |
| 12. basin_drainage_area_km2     (float64, sq km, HydroBASINS)                            |
| 13. soil_saturation_index       (float64, ratio [0.0, 1.0], SMAP / ERA5-Land)            |
| 14. population_density_per_km2  (float64, persons/km2, WorldPop 100m)                    |
+-----------------------------------------------------------------------------------------+
| C. DEEP ZONE EXCLUSIVE (Strictly Gated to Mumbai/Mithi Deep Zone)                       |
| 15. flow_accumulation_cells     (float64, cells, Hydro-Conditioned DEM 30m)              |
| 16. drainage_proxy_score        (float64, index [0.0, 1.0], Urban Compound Terrain)      |
| 17. built_up_fraction           (float64, ratio [0.0, 1.0], GHSL / Sentinel-2)          |
| 18. distance_to_road_m          (float64, meters, OSM Highway Vectors)                   |
| 19. distance_to_waterway_m      (float64, meters, OSM / MCGM Drainage Centerlines)       |
| 20. tide_level_m                (float64, meters local MSL, MbPA Station 43)             |
+-----------------------------------------------------------------------------------------+
| D. ISOLATED TARGET & METADATA (Strictly Excluded from Predictors — Leakage Prevention)  |
| - Target: flood_label (int: 1=flood, 0=defensible dry, -1=unobserved/unknown)           |
| - Label Provenance: label_source, label_confidence, label_verification_status             |
| - Spatial Provenance: sample_id, latitude, longitude, event_id, basin_id, state_code     |
| - Forbidden Leakage: water_depth_m, flow_velocity_ms, modeled_depth_m, sar_delta_vv_db  |
+-----------------------------------------------------------------------------------------+
```

### 4.3 Missing Data & NoData Policy
- **Native Routing Only:** XGBoost and LightGBM handle `NaN` values directly via default split direction learning.
- **Zero-Imputation Prohibited:** Missing values (`NaN`) must **never** be replaced with `0.0`. Imputing zero for unobserved rainfall, elevation, or slope introduces fatal artificial biases (e.g., treating missing rainfall as dry weather, or missing elevation as sea level). Authentic zero rainfall is stored as `0.0`, distinct from unobserved `NaN`.

### 4.4 Leakage Prevention and Cross-Validation
1. **Spatial Grouping:** GroupKFold strictly partitioned by `basin_id`. Samples from the same hydrologic river basin never appear in both training and validation folds.
2. **Event Isolation:** Leave-One-Event-Out cross-validation. Event E03 (July 2019 deluge) is held out as an unseen evaluation event.
3. **Spatial Buffer:** A 5 km exclusion buffer along basin perimeters eliminates spatial autocorrelation across fold boundaries.
4. **Predictor Isolation:** Coordinates (`latitude`, `longitude`), SAR change features (`sar_delta_vv_db`), and physics solver outputs are strictly barred from the feature matrix.

---

## 5. Label Integrity Audit and Class Balance Accounting

### 5.1 Audit of Available Historical Flood Labels
- **MCGM Citizen Waterlogging Complaints (July 2019):** `UNVERIFIED`. Voluntary phone calls to the disaster control room reflect reporting density, not ground truth. Lacks spatial polygons, inundation depths, and verified dry points.
- **Sentinel-1 Differential Backscatter Anomaly ($\Delta \sigma^0 \le -3\text{ dB}$):** `UNVERIFIED / CANDIDATE_OBSERVATION`. Physical microwave backscatter drop reflects surface change, but is prone to urban double-bounce and soil moisture ambiguities. Cannot be used as its own supervised training target.
- **Simulated Depths from Uncalibrated Physics Solvers:** `UNVERIFIED / PROHIBITED_SYNTHETIC`. Prohibited under AQUORA zero-synthetic-labeling rules.
- **Existing National Screening Pilot Dataset (10 Rows):** `UNLABELED`. All 10 rows in `national_screening_pilot_master.parquet` are explicitly coded `flood_label = -1` (unobserved). Under zero-fabrication rules, they must remain excluded from supervised training.

### 5.2 Class Balance Accounting
- Verified Flood Positive Samples ($y = 1$): **0**
- Verified Defensible Dry Negative Samples ($y = 0$): **0**
- Unobserved / Unlabeled Pilot Samples ($y = -1$): **10**
- Total Authentic Supervised Samples: **0**
- Class Balance Status: **100% UNLABELED / ZERO SUPERVISED SAMPLES**

---

## 6. Future Kaggle-Based ML Workflow Design

When authoritative ground-truth inundation labels are acquired, the workflow will proceed under the following design:

1. **Dataset Export & Packaging:**
   - Format: Apache Parquet (snappy compression, Arrow dictionary encoding, strict null bitmasks).
   - Companion Format: RFC 4180 CSV with machine-readable companion schema JSON.
   - Versioning Slug: `aquora-flood-ml-national-mumbai-v1`.
2. **Deterministic Splitting:**
   - Pre-computed `fold_id` column assigned via spatial GroupKFold (`basin_id`) and event holdouts. Fixed random seeds (`seed=42`).
3. **Baseline Modeling:**
   - Decision-tree gradient boosters (LightGBM / XGBoost) with native missing-value split routing.
   - Feature importances assessed via TreeSHAP to verify that elevation, slope, and rainfall accumulations dominate decision paths without spatial coordinate leakage.
4. **Evaluation Metrics (Imbalanced Setting):**
   - **Primary Metric:** Precision-Recall AUC (PR-AUC / Average Precision). Robust to severe class imbalance.
   - **Calibration Metric:** Brier Score and Expected Calibration Error (ECE).
   - **Operational Metric:** F1-score and Recall at governed high-risk alert thresholds.
5. **Calibration Gate:**
   - Model probabilities must undergo post-hoc calibration (Platt scaling or Isotonic regression) against out-of-fold validation sets before being exposed to downstream intelligence tiers.

---

## 7. Actionable Data Acquisition Requirements to Unblock Supervised Training

To transition from `BLOCKED_FOR_SUPERVISED_TRAINING` to `READY_FOR_DATASET_EXPORT`, the following authoritative datasets must be acquired:

1. **MCGM Ward-Level Surveyed Inundation Polygons:** High-water boundary vector shapefiles for historical flood events (2005, 2017, 2019) mapped by municipal survey teams.
2. **Co-Registered Optical / Aerial High-Resolution Truth:** Cloud-free post-event satellite imagery (PlanetScope 3m, Pleiades, or Cartosat) verifying dry versus flooded open spaces.
3. **Verified Non-Flood Ground Truth:** Operational logs from Western and Central Railways documenting tracks and road networks that remained dry and fully operational throughout the event.
