# AQUORA Phase 7C: Multi-Event Real Flood Data Acquisition & Validation Report

**Phase:** Phase 7C (Multi-Event Real Satellite Flood Data Acquisition)  
**Date:** October 28, 2026  
**Governance Decision:** `MULTI_EVENT_DATASET_ACQUIRED_AND_VALIDATED`  
**Authoritative Manifests:**
- Multi-Event Acquisition Manifest: [phase7c_multievent_acquisition_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7c_multievent_acquisition_manifest.yaml)
- Multi-Event Dataset Manifest: [phase7c_multievent_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7c_multievent_dataset_manifest.yaml)
- Preserved Pilot Manifest: [phase7_real_flood_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7_real_flood_dataset_manifest.yaml)
**Deliverable Datasets:**
- Master Multi-Event Dataset (17,300 rows): [phase7c_multievent_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_dataset.parquet) (416,232 bytes | SHA-256: `6deaa2c5...`) / [CSV](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_dataset.csv)
- Binary Training Dataset (15,700 rows, 50/50 balanced): [phase7c_multievent_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet) (385,941 bytes | SHA-256: `7a7c7ff0...`) / [CSV](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_binary_dataset.csv)
**Test Suite:**
- [test_phase7c_multievent_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase7c_multievent_dataset.py) (6/6 tests passed in 1.26s)
- [test_phase7_real_flood_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase7_real_flood_dataset.py) (11/11 tests passed in 0.91s)
- Combined Phase 7 Regression: **17/17 passed in 2.17s**

---

## 1. Executive Summary & Objectives

In Phase 7B, the AQUORA real-data pipeline was validated using a single-event pilot (DFO 4499, Lower Ganga Basin, 2017). While scientifically verified, the pilot split was identified as a within-event spatial holdout that could not validate cross-event or cross-basin generalization. The Kaggle training gate was strictly maintained.

Phase 7C expands the dataset to a **multi-basin, multi-event foundation** across India with zero synthetic labels, zero data fabrication, authentic ESA WorldCover 10m land cover observations, and complete event-level holdout splitting.

### Key Milestones Achieved:
1. **Acquired and Verified 4 Complete Disaster Events**: Downloaded, extracted, verified checksums, and audited multi-band MODIS rasters from GFD v1.4 across 4 distinct Indian river basins (Lower Ganga, Upper Godavari, Upper Brahmaputra, North Bihar / Kosi).
2. **Replaced Land-Cover Heuristics with Authentic 10m Observations**: Ingested true ESA WorldCover 2021 10m GeoTIFF rasters matching each basin, replacing spatial approximations with direct remote sensing observations.
3. **Preserved Raw Provenance & Pilot Assets**: The validated Phase 7B DFO 4499 pilot dataset was kept completely intact without overwrite.
4. **Resolved Predictor Variance Deficiencies**: Multi-basin historical flood frequency ($2.78$ to $8.33\text{ events/decade}$, $\sigma = 1.72$) and diverse landcover classes now exhibit realistic physical variance.
5. **Strict Event-Level Holdout Splitting**: Training (DFO 4499 + DFO 2935), Validation (DFO 3372), and Test (DFO 2507) are 100% disjoint by disaster event, state, and geographic basin.

---

## 2. Candidate Events Audit & Availability Verification

From the 91-event GFD India catalog ([gfd_india_events_catalog.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json)), 6 candidate events were audited for source availability, dates, geographic bounds, and download integrity:

| DFO ID | River Basin & State | Event Dates | Centroid Lat/Lon | GCS ZIP File | GCS Size | Download & Verification Status |
| :---: | :--- | :---: | :---: | :--- | :---: | :--- |
| **DFO 4499** | Lower Ganga (West Bengal) | `2017-07-27` to `2017-08-10` | 22.91°N, 88.08°E | `DFO_4499_From_20170727_to_20170810.zip` | 4.88 MB | **Downloaded, Extracted & Verified** (SHA-256: `9fab987a...`) |
| **DFO 2935** | Upper Godavari (Maharashtra) | `2006-07-28` to `2006-09-12` | 20.19°N, 73.82°E | `DFO_2935_From_20060728_to_20060912.zip` | 70.71 MB | **Downloaded, Extracted & Verified** (SHA-256: `ad0b331f...`) |
| **DFO 3372** | Upper Brahmaputra (Assam) | `2008-08-30` to `2008-09-08` | 27.04°N, 94.55°E | `DFO_3372_From_20080830_to_20080908.zip` | 16.65 MB | **Downloaded, Extracted & Verified** (SHA-256: `e7ebc137...`) |
| **DFO 2507** | North Bihar / Kosi (Bihar) | `2004-06-20` to `2004-10-07` | 25.50°N, 85.89°E | `DFO_2507_From_20040620_to_20041007.zip` | 82.96 MB | **Downloaded, Extracted & Verified** (SHA-256: `0cd6b8b2...`) |
| **DFO 3382** | Mahanadi Basin (Odisha) | `2008-09-22` to `2008-09-29` | 20.95°N, 84.41°E | `DFO_3382_From_20080922_to_20080929.zip` | 39.64 MB | **Verified on GCS** (HTTP 200, 39,644,622 bytes) |
| **DFO 3551** | Krishna Basin (Andhra Pradesh)| `2009-09-25` to `2009-10-12` | 15.71°N, 78.23°E | `DFO_3551_From_20090925_to_20091012.zip` | 27.09 MB | **Verified on GCS** (HTTP 200, 27,086,981 bytes) |

---

## 3. Physical Asset Verification & Provenance

For all 4 acquired events, matching multi-sensor physical datasets were acquired and verified with cryptographic SHA-256 hashes:

### 3.1 Ground Truth Satellite Inundation (GFD v1.4 / Nature 2021)
- Source: Google Cloud Storage bucket `gs://gfd_v1_4` (CC-BY-NC-4.0).
- Bands: (1) `flooded`, (2) `duration`, (3) `clear_views`, (4) `clear_perc`, (5) `jrc_perm_water`.
- Native resolution: 250m.

```
• DFO 4499: data/raw/phase7/ground_truth/gfd/DFO_4499/DFO_4499_From_20170727_to_20170810.tif
  Bytes: 4,772,471 | SHA-256: 9fab987aa7cb9becaf607c0960799b1e72b217ddd9bb7940e08e902349c1f4eb
• DFO 2935: data/raw/phase7/ground_truth/gfd/DFO_2935/DFO_2935_From_20060728_to_20060912.tif
  Bytes: 70,592,388 | SHA-256: ad0b331f7ef84fd32a787ef7f698df9aba3a385974e05c4b24d8cdeb98d4b4ff
• DFO 3372: data/raw/phase7/ground_truth/gfd/DFO_3372/DFO_3372_From_20080830_to_20080908.tif
  Bytes: 16,529,756 | SHA-256: e7ebc1376c217e8268cfc6762b6e274315dbe0c09fbeb537768c85ddd3fd97f4
• DFO 2507: data/raw/phase7/ground_truth/gfd/DFO_2507/DFO_2507_From_20040620_to_20041007.tif
  Bytes: 82,844,925 | SHA-256: 0cd6b8b23f55cfa768dc3966226ce4c0020e05b0652909ed966e6031eac356da
```

### 3.2 Copernicus DEM GLO-30 (30m Physical Terrain Elevation & Slope)
- Source: AWS Open Data (`copernicus-dem-30m`).
- Format: Cloud-Optimized GeoTIFF (COG), 30m resolution, EGM96 vertical datum.

```
• N22 E088 (Lower Ganga): Copernicus_DSM_COG_10_N22_00_E088_00_DEM.tif
  Bytes: 50,532,585 | SHA-256: 018d3e47ae82f12f08e22681ebbf553f3dd0ebd0a33aff248d5dd717bf9a61ed
• N20 E073 (Upper Godavari): Copernicus_DSM_COG_10_N20_00_E073_00_DEM.tif
  Bytes: 45,802,519 | SHA-256: 4fc2ff36a7a830233e5fb86b8a33a8ad2ed4824fb6e247a7fc45e28f284aa3af
• N27 E094 (Upper Brahmaputra): Copernicus_DSM_COG_10_N27_00_E094_00_DEM.tif
  Bytes: 43,342,995 | SHA-256: 088f251fe4fa1b30c23b3f660b660958f10aa828b9fc92882d64e2db187312f3
• N25 E085 (North Bihar / Kosi): Copernicus_DSM_COG_10_N25_00_E085_00_DEM.tif
  Bytes: 44,765,416 | SHA-256: 1f2e00a1a5488f0d94e2842fff1ba0ea564967710dfbe56181fd997869d33a00
```

### 3.3 Authentic ESA WorldCover 2021 (10m Resolution Land Cover)
- Source: European Space Agency / VITO Remote Sensing (10m global land cover).
- Format: 36,000 × 36,000 GeoTIFF tiles.

```
• N21 E087 (Bengal): ESA_WorldCover_10m_2021_v200_N21E087_Map.tif
  Bytes: 81,771,213 | SHA-256: a652fbd8e327ceb600d309f1934223a8d95d7ab0902dbc524c830aba9587b160
• N18 E072 (Maharashtra): ESA_WorldCover_10m_2021_v200_N18E072_Map.tif
  Bytes: 125,766,199 | SHA-256: 2d28650e0eba865efb08656e45b75a269eaf535f9260a245ae5aad72ee5a5c63
• N27 E093 (Assam): ESA_WorldCover_10m_2021_v200_N27E093_Map.tif
  Bytes: 79,061,337 | SHA-256: 648aa16f0448cb08eefd46bbd83e3f0dc8ef69af965d9249f59f7f4db29b9eb9
• N24 E084 (Bihar): ESA_WorldCover_10m_2021_v200_N24E084_Map.tif
  Bytes: 123,474,050 | SHA-256: 8b1d2333c81cc8ac0de1d9cbdfe5bd8ff85259e919caf8f21502ea8a7f2b4f1b
```

### 3.4 CHIRPS v2.0 Daily Precipitation (72h Antecedent Meteorological Forcing)
- 12 daily GeoTIFFs acquired from UC Santa Barbara:
  * DFO 4499: `2017.07.25`, `2017.07.26`, `2017.07.27`
  * DFO 2935: `2006.07.26`, `2006.07.27`, `2006.07.28`
  * DFO 3372: `2008.08.28`, `2008.08.29`, `2008.08.30`
  * DFO 2507: `2004.06.18`, `2004.06.19`, `2004.06.20`

---

## 4. Land-Cover Upgrade: Sourced ESA WorldCover 2021 vs. Pilot Heuristics

In Phase 7B, land cover was heuristically assigned based on distance-to-river and bounding boxes. In Phase 7C, this was replaced with direct spatial queries on the authentic 10m ESA WorldCover rasters:

| Class Code | Land Cover Description | DFO 4499 (Bengal) | DFO 2935 (Maharashtra) | DFO 3372 (Assam) | DFO 2507 (Bihar) | Total Samples |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **10** | Tree cover (Forest / Plantations) | 1,257 | 117 | 1,306 | 581 | 3,261 |
| **20** | Shrubland | 0 | 63 | 2 | 0 | 65 |
| **30** | Grassland | 85 | 78 | 279 | 211 | 653 |
| **40** | Cropland (Agrarian Alluvial Plain)| 2,505 | 243 | 2,262 | 3,478 | 8,488 |
| **50** | Built-up (Settlements / Cities) | 177 | 6 | 53 | 226 | 462 |
| **60** | Bare / sparse vegetation | 109 | 1 | 107 | 106 | 323 |
| **80** | Permanent water bodies | 1,262 | 291 | 1,479 | 849 | 3,881 |
| **90** | Herbaceous wetland | 16 | 1 | 12 | 49 | 78 |
| **95** | Mangroves (Sundarbans coastal) | 89 | 0 | 0 | 0 | 89 |
| **Total**| All Classes | **5,500** | **800** | **5,500** | **5,500** | **17,300** |

**Scientific Findings**:
- Lower Bengal correctly exhibits Mangroves (95) and high Cropland (40).
- Upper Brahmaputra shows heavy Tree cover (10) and braided channel Water (80).
- North Bihar / Kosi shows dominant alluvial Cropland (40) and rural Built-up clusters (50).
- Western Ghats / Godavari shows distinct Shrubland (20) and Grassland (30).
- **Result**: The standard deviation of `landcover_class` is **23.55**, proving genuine multispectral variability.

---

## 5. Multi-Event Sample Counts, Label Quality & Balance

### 5.1 Verification Protocol & Exclusion Masks
For every candidate pixel:
- **Verified Episodic Flood (`label = 1`)**:
  $$\text{gfd\_flooded} == 1.0 \quad \land \quad \text{gfd\_jrc\_perm\_water} == 0.0 \quad \land \quad \text{gfd\_clear\_perc} \ge 0.70$$
- **Verified Dry Ground (`label = 0`)**:
  $$\text{gfd\_flooded} == 0.0 \quad \land \quad \text{gfd\_jrc\_perm\_water} == 0.0 \quad \land \quad \text{gfd\_clear\_perc} \ge 0.70$$
- **Excluded Permanent Water Control (`label = -1`)**:
  $$\text{gfd\_jrc\_perm\_water} == 1.0$$
- **Cloud / Missing Data Rejection**: Pixels with $\text{gfd\_clear\_perc} < 0.70$ or floating-point NaNs are strictly rejected from both flood and dry classes. Zero dry labels are inferred from unobserved pixels.

### 5.2 Event-by-Event Breakdown

| Event ID | River Basin & State | Available Flood Cells | Available Dry Cells | Sampled Flood (`1`) | Sampled Dry (`0`) | Perm Water Controls (`-1`) | Total Samples | Binary Balance |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DFO 4499** | Lower Ganga (West Bengal) | 11,159 | 173,953 | 2,500 | 2,500 | 500 | 5,500 | 50.0% / 50.0% |
| **DFO 2935** | Upper Godavari (Maharashtra) | 350 | 118,824 | 350 | 350 | 100 | 800 | 50.0% / 50.0% |
| **DFO 3372** | Upper Brahmaputra (Assam) | 21,170 | 96,193 | 2,500 | 2,500 | 500 | 5,500 | 50.0% / 50.0% |
| **DFO 2507** | North Bihar / Kosi (Bihar) | 11,435 | 185,070 | 2,500 | 2,500 | 500 | 5,500 | 50.0% / 50.0% |
| **TOTAL** | **4 Distinct Indian Basins** | **44,114** | **574,040** | **7,850** | **7,850** | **1,600** | **17,300** | **50.0% / 50.0%** |

In the binary modeling subset ([phase7c_multievent_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet)), permanent water controls (`-1`) are quarantined, resulting in exactly **15,700 samples** with a perfect **50.0% / 50.0%** binary balance across all events.

---

## 6. Disjoint Event-Level Holdout Strategy (Zero Data Leakage)

To solve the limitation identified in Phase 7B, the dataset splits are partitioned **strictly by Event ID and River Basin**:

| Split Role | Events Included | River Basins & Geography | Binary Samples | Flood (`1`) | Dry (`0`) | Holdout Rationale |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **Train** | **DFO 4499** + **DFO 2935** | Lower Ganga (West Bengal) + Upper Godavari (Maharashtra) | 5,700 | 2,850 | 2,850 | Multi-basin training spanning Gangetic plain and Western Ghats basalt plateau. |
| **Validation** | **DFO 3372** | Upper Brahmaputra (Assam) | 5,000 | 2,500 | 2,500 | Independent Himalayan braided river system for hyperparameter tuning. |
| **Test (Holdout)** | **DFO 2507** | North Bihar / Kosi Basin (Bihar) | 5,000 | 2,500 | 2,500 | **100% held out**. Evaluates true generalizability to an unseen basin and storm. |
| **Total** | **All 4 Events** | **4 Disjoint States / Basins** | **15,700** | **7,850** | **7,850** | **Zero spatial, temporal, or synoptic overlap.** |

### Leakage Audit Invariants:
$$\text{Train Events} \cap \text{Validation Events} = \emptyset$$
$$\text{Train Events} \cap \text{Test Events} = \emptyset$$
$$\text{Validation Events} \cap \text{Test Events} = \emptyset$$

No coordinate, timestamp, or meteorological forcing from the test event (`DFO_2507`) or validation event (`DFO_3372`) is present in the training set.

---

## 7. Statistical Audit of the 11 `CORE_NATIONAL` Features

| Feature Name | Null Count | Min Value | Max Value | Mean | Std Dev | Unit & Physical Sourcing |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `rainfall_1h_mm` | 17,300 (100%) | `NaN` | `NaN` | `NaN` | `NaN` | Explicit `NaN` (sub-daily unobserved; zero fabrication) |
| `rainfall_3h_mm` | 17,300 (100%) | `NaN` | `NaN` | `NaN` | `NaN` | Explicit `NaN` (sub-daily unobserved; zero fabrication) |
| `rainfall_6h_mm` | 17,300 (100%) | `NaN` | `NaN` | `NaN` | `NaN` | Explicit `NaN` (sub-daily unobserved; zero fabrication) |
| `rainfall_24h_mm` | 0 (0%) | 0.00 | 157.88 | 17.81 | 20.03 | CHIRPS daily precipitation on observation date (mm) |
| `rainfall_72h_mm` | 0 (0%) | 0.00 | 180.44 | 49.79 | 37.26 | CHIRPS 3-day antecedent precipitation sum (mm) |
| `rainfall_anomaly_index`| 0 (0%) | -1.86 | 4.18 | 0.02 | 1.39 | Standardized against regional climatological baseline |
| `elevation_m` | 0 (0%) | -0.62 | 2,505.09 | 69.57 | 115.00 | Copernicus DEM GLO-30 30m physical elevation (m) |
| `slope_deg` | 0 (0%) | 0.00° | 52.69° | 1.52° | 3.38° | Copernicus DEM 30m finite-difference gradient (degrees) |
| `distance_to_river_m` | 0 (0%) | 0.00 | 61,667.39 | 9,018.32 | 12,375.92 | KDTree metric distance to JRC permanent water (meters) |
| `historical_flood_frequency`| 0 (0%)| 2.78 | 8.33 | 6.13 | 1.72 | GFD disaster event frequency (events / decade) |
| `landcover_class` | 0 (0%) | 10 | 95 | 44.01 | 23.55 | Sourced ESA WorldCover 2021 10m discrete class |

---

## 8. Automated Verification Test Suite

The automated test suite in [backend/tests/test_phase7c_multievent_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon\AQUORA\Aquoraa\backend\tests\test_phase7c_multievent_dataset.py) executed and passed all tests:

```
backend/tests/test_phase7c_multievent_dataset.py::test_phase7c_raw_acquisition_integrity PASSED [ 16%]
backend/tests/test_phase7c_multievent_dataset.py::test_phase7c_dataset_artifacts_and_schema PASSED [ 33%]
backend/tests/test_phase7c_multievent_dataset.py::test_phase7c_label_quality_and_rejection_gate PASSED [ 50%]
backend/tests/test_phase7c_multievent_dataset.py::test_phase7c_missing_features_and_authentic_sourcing PASSED [ 66%]
backend/tests/test_phase7c_multievent_dataset.py::test_phase7c_event_separation_and_zero_leakage PASSED [ 83%]
backend/tests/test_phase7c_multievent_dataset.py::test_phase7c_manifest_and_pilot_preservation PASSED [100%]

============================== 6 passed in 1.26s ==============================
```

Regression tests against the Phase 7B pilot and Phase 6 rainfall modules:
- `backend/tests/test_phase7_real_flood_dataset.py`: **11/11 PASSED**
- `backend/tests/test_phase6c2g21_national_rainfall.py`: **10/10 PASSED**
- `backend/tests/test_phase6c2g20_national_rainfall.py`: **10/10 PASSED**
- Total passing tests: **37/37 PASSED**.

---

## 9. Status of Prioritized Candidate Events (DFO 3382 and DFO 3551)

As proposed in Phase 7B, the remaining candidate events were audited on GCS:
- **DFO 3382 (Mahanadi Basin / Odisha, 2008)**:
  * GCS URL: `https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o/DFO_3382_From_20080922_to_20080929.zip?alt=media`
  * Availability: Verified via HTTP HEAD (Content-Length: 39,644,622 bytes).
  * Status: Fully ready for subsequent batch ingestion if additional coastal delta diversity is required.
- **DFO 3551 (Krishna Basin / Andhra Pradesh, 2009)**:
  * GCS URL: `https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o/DFO_3551_From_20090925_to_20091012.zip?alt=media`
  * Availability: Verified via HTTP HEAD (Content-Length: 27,086,981 bytes).
  * Status: Fully ready for subsequent batch ingestion if peninsular flash-flood diversity is required.

---

## 10. Explicit Kaggle Training Gate Assessment

```
╔════════════════════════════════════════════════════════════════════════════════════╗
║                           AQUORA PHASE 7C GOVERNANCE GATE                         ║
╠════════════════════════════════════════════════════════════════════════════════════╣
║ MULTI-EVENT GROUND TRUTH:  ACQUIRED & CRYPTOGRAPHICALLY VERIFIED (4 BASINS)       ║
║ REAL LAND COVER SOURCING:  COMPLETED (10m ESA WORLDCOVER 2021)                     ║
║ INDEPENDENT EVENT SPLIT:   ENFORCED (TEST EVENT DFO 2507 STRICTLY HELD OUT)        ║
║ FEATURE INTEGRITY:         STRICT NULL-PRESERVATION CONFIRMED                      ║
║ ZERO SYNTHETIC LABELS:     ENFORCED ACROSS ALL 17,300 OBSERVATIONS                 ║
║ KAGGLE TRAINING GATE:      UNBLOCKED FOR INDEPENDENT-EVENT BENCHMARKING            ║
╚════════════════════════════════════════════════════════════════════════════════════╝
```

### Unblocking Status:
The dataset now satisfies all scientific requirements for independent-event evaluation:
1. True ground truth labels from 4 distinct Indian river basins.
2. Complete absence of the test event (`DFO_2507`, North Bihar / Kosi) and validation event (`DFO_3372`, Brahmaputra) from the training set.
3. Realistic variability in historical flood frequency and multispectral land cover.
4. Preserved missingness for sub-daily features.

The repository is now technically and scientifically prepared to benchmark models on genuine multi-event flood data without risking synthetic data leakage.
