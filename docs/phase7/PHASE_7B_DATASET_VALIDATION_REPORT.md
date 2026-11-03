# AQUORA Phase 7B: Real Flood Dataset Audit & Validation Report

**Phase:** Phase 7B (Pre-Kaggle Ground-Truth & Dataset Validation)  
**Date:** October 28, 2026  
**Governance Decision:** `PILOT_PIPELINE_VALIDATED_BUT_CALIBRATION_BLOCKED`  
**Dataset Artifacts Audited:**
- Master Pilot Dataset (5,500 rows): [phase7_gfd_pilot_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet) / [CSV](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.csv)
- Binary Training Dataset (5,000 rows): [phase7_gfd_pilot_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_binary_dataset.parquet) / [CSV](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_binary_dataset.csv)
- Authoritative Manifest: [phase7_real_flood_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7_real_flood_dataset_manifest.yaml)
- Test Suite: [test_phase7_real_flood_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase7_real_flood_dataset.py) (11 tests passed in 3.25s)

---

## 1. Audit of Flood and Dry Labels (DFO 4499)

### 1.1 Band Descriptions, Data Types, and NoData Semantics
The pilot ground-truth raster [DFO_4499_From_20170727_to_20170810.tif](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/DFO_4499/DFO_4499_From_20170727_to_20170810.tif) was independently re-parsed using `rasterio`.

| Band Index | Band Name | Data Type | Native NoData | Min Value | Max Value | NaN Count |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | `flooded` | `float32` | `None` (`np.nan`) | 0.0 | 1.0 | 3,385,349 |
| **2** | `duration` | `float32` | `None` (`np.nan`) | 0.0 | 10.0 | 3,385,349 |
| **3** | `clear_views` | `float32` | `None` (`np.nan`) | 28.0 | 37.0 | 3,385,349 |
| **4** | `clear_perc` | `float32` | `None` (`np.nan`) | 0.8235 | 1.0 | 3,385,349 |
| **5** | `jrc_perm_water`| `float32` | `None` (`np.nan`) | 0.0 | 1.0 | 3,055,009 |

- **NoData Treatment**: In the GeoTIFF header, the `nodata` tag is `None`, but all bands use explicit IEEE 754 floating-point `NaN` outside the processed satellite footprint (3,385,349 cells = 51.10% of the 3,257 × 2,034 grid).
- **Valid Footprint**: Exactly **3,239,389 cells** (48.90%) contain valid, non-NaN observational data across all bands.

### 1.2 Optical Confidence, Cloud Thresholds, and Permanent Water
- **Clear Views**: During the 15-day flood event window (2017-07-27 to 2017-08-10), Terra and Aqua MODIS captured between 28 and 37 valid surface reflectance looks per pixel.
- **Clear Percentage (`clear_perc`)**: The minimum observed `clear_perc` across all valid cells is **0.8235 (82.35%)**, and the maximum is **1.0 (100.0%)**.
- **Cloud-Affected Cells (< 70% threshold)**: Exactly **0 cells** within the valid footprint fall below the standard 70% optical visibility threshold.

### 1.3 Explanation of the Identical 72,887 Count
In preliminary execution logs, the following counts were reported:
```
Permanent Water Cells: 72,887
Cloud-Affected / Permanent Water Excluded: 72,887
```
**Investigation & Root Cause**:
1. In [acquire_phase7_gfd_labels.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/acquire_phase7_gfd_labels.py), the exclusion metric was defined as:
   $$\text{cloud\_or\_perm\_cells} = \text{valid\_cells} - (\text{pure\_flood\_cells} + \text{verified\_dry\_cells})$$
2. Total valid cells = $3,239,389$.
3. Pure flood cells (`flooded == 1.0 & perm == 0.0 & clear >= 0.70`) = $67,267$.
4. Verified dry cells (`flooded == 0.0 & perm == 0.0 & clear >= 0.70`) = $3,099,235$.
5. Their sum: $67,267 + 3,099,235 = 3,166,502$.
6. Subtracting: $3,239,389 - 3,166,502 = \mathbf{72,887}$.
7. The total number of JRC permanent water cells (`jrc_perm_water == 1.0`) inside the valid footprint is exactly **72,887**.
8. Because `clear_perc >= 0.8235` everywhere, the number of cloud-affected cells was **0**.
9. **Conclusion**: The identical figures were an accounting artifact where the composite exclusion metric (which consisted 100% of permanent water) was mistakenly cited under both categories. This has been corrected in [phase7_real_flood_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7_real_flood_dataset_manifest.yaml).

### 1.4 Verification of Dry Ground Samples
- **Verification Rule**: All 2,500 dry samples in the dataset strictly meet:
  $$\text{gfd\_flooded} == 0.0 \quad \land \quad \text{gfd\_jrc\_perm\_water} == 0.0 \quad \land \quad \text{gfd\_clear\_perc} \ge 0.8889$$
- **Confirmation**: Dry samples are **not** unobserved background pixels, edge artifacts, or out-of-footprint NaNs. Every dry sample was observed multiple times with high optical clarity and confirmed non-inundated.

---

## 2. Feature Validity & Schema Conformance

### 2.1 Conformance to `aquora_ml_feature_schema_v1.json`
Every feature in the dataset was audited against the 11 `CORE_NATIONAL` features governed by the schema:

| Feature Name | Type | In Schema? | Null Count | Unit | Source Asset |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `rainfall_1h_mm` | `float32` | Mandatory | 5,500 (100%) | mm | Unobserved (preserved as `NaN`) |
| `rainfall_3h_mm` | `float32` | Mandatory | 5,500 (100%) | mm | Unobserved (preserved as `NaN`) |
| `rainfall_6h_mm` | `float32` | Mandatory | 5,500 (100%) | mm | Unobserved (preserved as `NaN`) |
| `rainfall_24h_mm` | `float32` | Mandatory | 0 (0%) | mm | CHIRPS v2.0 (`2017.07.27`) |
| `rainfall_72h_mm` | `float32` | Mandatory | 0 (0%) | mm | CHIRPS v2.0 (`2017.07.25–27` sum) |
| `rainfall_anomaly_index` | `float32` | Mandatory | 0 (0%) | Dimensionless | Standardized antecedent anomaly |
| `elevation_m` | `float32` | Mandatory | 0 (0%) | m (EGM96) | AWS Copernicus DEM GLO-30 |
| `slope_deg` | `float32` | Mandatory | 0 (0%) | degrees ($^\circ$) | 30m DEM finite difference gradient |
| `distance_to_river_m` | `float32` | Mandatory | 0 (0%) | meters | JRC Permanent Water KDTree query |
| `historical_flood_frequency` | `float32` | Mandatory | 0 (0%) | events / decade | GFD Bengal disaster archive |
| `landcover_class` | `int32` | Mandatory | 0 (0%) | Class code | ESA WorldCover classes (40, 50, 80, 90) |

### 2.2 Investigation of Sub-Daily Rainfall NaNs
- **Why NaNs?**: CHIRPS is a daily precipitation product (0.05° resolution). Sub-daily intervals (1h, 3h, 6h) cannot be resolved without high-temporal satellite sensors (such as GPM IMERG 30-minute granules) or local automatic weather stations.
- **Strict Zero-Fabrication Enforcement**: Under AQUORA governance, missing sub-daily observations **must remain explicit NaNs**. Artificially setting them to `0.0 mm` would falsely assert to the model that no rain fell during peak storm hours. Modern gradient-boosted decision trees (XGBoost, LightGBM) route missing values through default split directions without bias.

### 2.3 Independent Re-Extraction of CHIRPS Precipitation
Independent point queries were executed on raw gzip archives (`chirps-v2.0.2017.07.27.tif.gz`):
- Random sample of 20 coordinates: Maximum absolute numerical discrepancy between on-the-fly raster read and stored dataset value was **$< 0.005\text{ mm}$** (attributable solely to 2-decimal-place rounding).
- Date Windows:
  * `rainfall_24h_mm`: Covers exactly 2017-07-27 (day of disaster declaration).
  * `rainfall_72h_mm`: Cumulative sum of 2017-07-25, 2017-07-26, and 2017-07-27.

### 2.4 Correlation & Information Leakage Audit
1. **Rainfall Anomaly Collinearity**:
   - `rainfall_anomaly_index` was calculated as `(rainfall_72h_mm - 45.0) / 25.0`.
   - In this single-event pilot, this is a fixed linear transformation of `rainfall_72h_mm` ($r = 1.0000$).
   - **Finding**: While structurally compliant with the schema, it provides zero additional split information in a single-event dataset. In multi-event datasets across years, baseline climatology will vary geographically and seasonally.
2. **Historical Flood Frequency Zero-Variance**:
   - In the pilot, `historical_flood_frequency` was set to a regional constant ($4.44\text{ events/decade}$ based on 8 GFD events in Lower Ganga between 2000 and 2018).
   - $\text{Variance} = 0.0000$.
   - **Finding**: In a single-basin pilot, this feature cannot be split on by decision trees. Variance will only emerge when multi-basin events are ingested.
3. **Landcover Assignment**:
   - `landcover_class` was assigned via spatial rules (permanent water $\rightarrow$ 80, urban corridor $\rightarrow$ 50, riverine floodplain $\rightarrow$ 90, alluvial plain $\rightarrow$ 40) rather than a downloaded ESA WorldCover GeoTIFF tile.
   - **Action Item**: National expansion must ingest actual WorldCover tiles rather than heuristic proxies.
4. **Target Isolation**:
   - `flood_label`, `gfd_flooded`, `gfd_clear_perc`, `gfd_jrc_perm_water`, and coordinate fields reside strictly in metadata columns, completely isolated from feature matrices.

---

## 3. Sample and Split Quality

### 3.1 Permanent Water (`label = -1`) Isolation
- In the master dataset ([phase7_gfd_pilot_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet)), 500 samples have `flood_label = -1` (JRC permanent water controls).
- **Remediation**: To prevent downstream models from ingesting `-1` as a target class, AQUORA generated an explicit gated binary training package:
  * [phase7_gfd_pilot_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_binary_dataset.parquet) (128,470 bytes | SHA-256: `608be4e3...`)
  * [phase7_gfd_pilot_binary_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_binary_dataset.csv) (1,087,321 bytes | SHA-256: `dcdd828f...`)
  * Exactly **5,000 samples** (`flood_label in [0, 1]`), perfectly balanced with **2,500 flood (50%)** and **2,500 dry (50%)**.

### 3.2 Binary Class Balance Across Folds

| Split Name | Sub-Basin IDs | Dry Samples (`0`) | Flood Samples (`1`) | Total Samples | Flood Fraction |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Train** | `SB1` (NW), `SB2` (NE), `SB3` (Central) | 1,667 | 1,021 | 2,688 | 38.0% |
| **Validation** | `SB4` (SW / Howrah / Uluberia) | 482 | 249 | 731 | 34.1% |
| **Test** | `SB5` (SE / Kolkata / 24 Parganas) | 351 | 1,230 | 1,581 | 77.8% |
| **Total** | All 5 Sub-Basins | **2,500** | **2,500** | **5,000** | **50.0%** |

### 3.3 Spatial vs. Event Separation (Critical Finding)
> [!WARNING]
> **Spatial Cross-Validation $\neq$ Independent-Event Generalization**  
> All 5,000 samples in this pilot originate from a **single flood event** (DFO 4499, July 27 – August 10, 2017).
> 
> Partitioning pixels into sub-basins (`SB1` through `SB5`) enforces **spatial disjointness** (zero grid-cell coordinate overlap), which prevents spatial autocorrelation leakage across pixels of the *same* storm.
> 
> However, all sub-basins experienced the **same synoptic meteorological event**. Therefore, this pilot split is strictly a **within-event spatial holdout**. It does **not** evaluate whether the model can generalize to:
> - A different monsoon year (e.g., 2004 or 2008).
> - A different precipitation regime (cyclonic storm surge vs. monsoonal depression).
> - An entirely different river morphology (e.g., Brahmaputra braided channels or Godavari plateau).

---

## 4. Dataset Readiness Assessment

### 4.1 Automated Test Execution
Automated verification in [backend/tests/test_phase7_real_flood_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase7_real_flood_dataset.py) was expanded from 7 to **11 exhaustive unit tests**:

```
backend/tests/test_phase7_real_flood_dataset.py::test_source_provenance_and_immutability PASSED [  9%]
backend/tests/test_phase7_real_flood_dataset.py::test_dataset_artifacts_and_schema PASSED [ 18%]
backend/tests/test_phase7_real_flood_dataset.py::test_spatial_crs_and_coordinate_alignment PASSED [ 27%]
backend/tests/test_phase7_real_flood_dataset.py::test_predictor_units_and_ranges PASSED [ 36%]
backend/tests/test_phase7_real_flood_dataset.py::test_label_fidelity_and_rejection_gate PASSED [ 45%]
backend/tests/test_phase7_real_flood_dataset.py::test_spatial_cross_validation_zero_leakage PASSED [ 54%]
backend/tests/test_phase7_real_flood_dataset.py::test_manifest_consistency_and_hashes PASSED [ 63%]
backend/tests/test_phase7_real_flood_dataset.py::test_independent_raw_pixel_extraction_tolerance PASSED [ 72%]
backend/tests/test_phase7_real_flood_dataset.py::test_binary_training_dataset_isolation PASSED [ 81%]
backend/tests/test_phase7_real_flood_dataset.py::test_optical_confidence_and_cloud_accounting PASSED [ 90%]
backend/tests/test_phase7_real_flood_dataset.py::test_event_isolation_and_within_event_limitation PASSED [100%]

============================= 11 passed in 3.25s ==============================
```

### 4.2 Explicit Readiness Verdict
```
╔════════════════════════════════════════════════════════════════════════════════════╗
║                           AQUORA PHASE 7B GOVERNANCE GATE                         ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║ PIPELINE READINESS:       READY AND VERIFIED                                       ║
║ FEATURE INTEGRITY:        STRICT NULL-PRESERVATION CONFIRMED                       ║
║ LEAKAGE AUDIT:            PASSED (ZERO SPATIAL LEAKAGE ACROSS SUB-BASINS)          ║
║ MODEL CALIBRATION GATE:   BLOCKED_FOR_STANDALONE_EVALUATION                        ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```
**Conclusion**: The current pilot dataset is **suitable for data-contract testing, pipeline verification, and model code smoke-testing**. It is **not sufficiently representative for standalone model evaluation or production calibration** because it lacks multi-event and multi-basin diversity. The Kaggle training gate remains active.

---

## 5. Next Data Acquisition: Prioritized Indian Events

From the audited 91-event GFD India catalog ([gfd_india_events_catalog.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.csv)), the following **5 independent, high-severity disaster events** are prioritized for acquisition across distinct geographical basins:

| Priority | DFO ID | River Basin / Region | Dates | Dead | Matching IFI Events | Rationale & Basin Distinctiveness |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | **DFO 2507** | **Ganga / Kosi Basin (North Bihar)** | `2004-06-20` to `2004-10-07` | 3,000 | 58 | North Bihar Himalayan alluvial fan; high-silt, dynamic embankment breaching; independent from Lower Ganga. |
| **2** | **DFO 3372** | **Brahmaputra Basin (Upper Assam)** | `2008-08-30` to `2008-09-08` | 900 | 19 | High-energy braided Himalayan river valley; distinct precipitation regime and physiography. |
| **3** | **DFO 2935** | **Godavari Basin (Nashik / Maharashtra)** | `2006-07-28` to `2006-09-12` | 457 | 50 | Directly intersects AQUORA registered regional corridor `godavari_nashik`; Western Ghats basalt plateau. |
| **4** | **DFO 3551** | **Krishna Basin (Kurnool / Andhra Pradesh)**| `2009-09-25` to `2009-10-12` | 303 | 16 | Semi-arid peninsular river basin; flash dam release flood; distinct soil and slope characteristics. |
| **5** | **DFO 3382** | **Mahanadi Basin (Odisha Delta)** | `2008-09-22` to `2008-09-29` | 2,400 | 9 | Coastal deltaic plain; cyclonic monsoonal storm interaction; independent eastern river network. |

### Acquisition Protocol:
1. Download GFD multi-band GeoTIFF archives from `gs://gfd_v1_4` via HTTPS.
2. Verify byte checksums against catalog manifests before extracting.
3. Ingest corresponding AWS Copernicus DEM GLO-30 30m tiles (`N25_E085`, `N27_E094`, `N20_E073`, `N15_E078`, `N20_E084`).
4. Ingest UC Santa Barbara CHIRPS daily precipitation for the respective 72h antecedent windows.
5. Ingest true ESA WorldCover 2021 10m rasters for authentic land cover classification.
6. Assemble multi-event dataset with **GroupKFold by `event_id`**, guaranteeing genuine independent-event validation before unblocking production model training.
