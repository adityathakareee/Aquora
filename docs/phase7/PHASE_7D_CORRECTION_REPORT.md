# AQUORA — PHASE 7D CORRECTION REPORT: TEST INTEGRITY, FEATURE LEAKAGE & EVALUATION

**Document Version:** `1.3.0-final-closure-audit`  
**Phase:** Phase 7D Correction & Final Verification (Test Integrity, Feature Leakage & Multi-Event Evaluation)  
**Date:** 2026-10-28  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**License:** CC-BY-NC-4.0 (GFD v1.4 / Copernicus DEM / CHIRPS / ESA WorldCover)  

---

## 1. Executive Summary & Core Verification Findings

This report documents the final closure audit of the Phase 7D multi-event satellite flood dataset and experimental machine learning preflight harness. Every finding is verified through direct inspection of physical GeoTIFF rasters, Parquet/CSV tables, package manifests, and live model recomputations.

### Core Verified Outcomes:
1. **GFD Clear-Observation Units Verified**:
   - Band 4 (`clear_perc`) values in GFD GeoTIFF rasters are mathematically proven to be **fractions in the range `[0.0, 1.0]`**, calculated as $\text{clear\_views} / \text{total\_satellite\_passes}$.
   - The filtering threshold `clear_perc >= 0.70` used in the dataset generation code is **mathematically and semantically correct**, representing $\ge 70.0\%$ clear satellite overpasses.
   - Within the evaluation window of the held-out test event (DFO 2507), observed `clear_perc` ranges from **0.9104 to 1.0000** (91.0% to 100.0% cloud-free), confirming **zero cloud-obscured pixels (< 70%)** in the evaluated footprint.
2. **Reconciliation of All Row Counts**:
   - Master Multi-Event Dataset: **209,116 rows** across 24 columns (Parquet and CSV identical).
   - Binary Supervised Dataset: **207,205 rows** across 24 columns (Parquet and CSV identical).
   - Packaged files in [data/packages/phase7d_kaggle_dataset/](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7d_kaggle_dataset/) match prepared datasets row-for-row with **100% SHA-256 cryptographic parity**.
   - Held-Out Test Split ([DFO 2507](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/DFO_2507/DFO_2507_From_20040620_to_20041007.tif)): **196,505 valid binary cells** (11,435 flood, 185,070 dry) with an authentic natural flood prevalence of **5.819%**. Zero artificial balancing or resampling.
   - Permanent water controls: 1,911 JRC permanent water cells (`flood_label = -1`) are strictly quarantined in the master dataset and excluded from binary training/evaluation.
3. **Phase 7B Pilot Dataset Byte-for-Byte Preservation**:
   - The original Phase 7B pilot dataset ([phase7_gfd_pilot_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet)) remains completely preserved on disk: **136,711 bytes**, SHA-256 `4d809d47fdc908121f08f5a00ed3d9bab3d515fd6f242a185f73557225782225`, exactly matching the Phase 7B manifest.
4. **Feature Leakage Elimination**:
   - `historical_flood_frequency` was proven to introduce **future data leakage** (computed from the 2000–2018 GFD catalog, covering events up to 14 years after the 2004 test event) and has **zero intra-basin spatial variance** (acting as an event ID shortcut). It has been **strictly excluded from ML model training**.
   - `rainfall_anomaly_index` was verified to be an exact collinear affine transformation ($r = 1.0000$) of `rainfall_72h_mm`.
   - `distance_to_river_m` semantics were verified as distance to perennial surface water bodies (JRC permanent water mask), not a vector streamline network.
   - `landcover_class` (ESA WorldCover 2021 10m) temporal offset (4 to 17 years relative to 2004–2017 historical events) is explicitly documented.
   - Sub-daily rainfall (`1h`, `3h`, `6h`) is preserved as explicit `NaN` (unobserved in daily CHIRPS data; zero-filling prohibited).
5. **Empirical Baseline & Model Recomputation**:
   - On the natural test population, the cross-basin trained XGBoost model achieved **ROC-AUC of 0.5867**, **PR-AUC of 0.1888**, **Precision of 0.4821**, and **Recall of 0.2183** (F1 = 0.3005).
   - An unsupervised physical inverted elevation ranking baseline within the test basin achieved **ROC-AUC of 0.8038** and **PR-AUC of 0.2210**, outperforming the cross-basin trained XGBoost model.
   - The elevation baseline's Brier score is marked **N/A** because an inverted elevation ranking score is not a calibrated probability estimate.
6. **Final Governance Verdict**:
   **`EXPERIMENTAL_EVALUATION_ONLY`**. The dataset, preflight guards, and software pipeline pass all integrity checks, but cross-basin generalization is weak. The model must NOT be deployed for operational civil defense or automated alerting.

---

## 2. GFD Raster Clear-Observation Units & Threshold Verification

### A. Raster Metadata & Band Layout Inspection
Direct inspection of Global Flood Database v1.4 GeoTIFF files across all four event directories (`DFO_2507`, `DFO_4499`, `DFO_2935`, `DFO_3372`) established the following 5-band structure:
- **Band 1 (`flooded`):** `float32`, values in `{0.0, 1.0, NaN}`. (1 = inundated flood, 0 = non-inundated land, NaN = unmapped/NoData).
- **Band 2 (`duration`):** `float32`, inundation duration in days.
- **Band 3 (`clear_views`):** `float32`, integer count of cloud-free MODIS satellite observations during the event window.
- **Band 4 (`clear_perc`):** `float32`, clear observation ratio.
- **Band 5 (`jrc_perm_water`):** `float32`, JRC Global Surface Water permanent water mask (`1.0 = permanent water, 0.0 = non-permanent`).

### B. Mathematical Proof of Band 4 Units (Fraction vs. Percentage)
To establish whether `clear_perc` represents a percentage (0–100) or a fraction (0–1), we evaluated the mathematical relationship between Band 3 (`clear_views`) and Band 4 (`clear_perc`) across valid pixels in DFO 2507:

$$\text{total\_passes} = \text{round}\left(\frac{\text{clear\_views}}{\text{clear\_perc}}\right)$$

$$\text{max\_abs\_difference} = \max \left| \frac{\text{clear\_views}}{\text{total\_passes}} - \text{clear\_perc} \right| = 0.00 \times 10^{-0}$$

The calculation yielded **exact integer total overpasses** ranging from **212 to 227 passes** across the 109-day event window (June 20, 2004 to October 7, 2004), precisely matching the ~2 daily overpasses of the Terra and Aqua MODIS sensors.

**Conclusion:**
Band 4 (`clear_perc`) values are **floating-point fractions in the range `[0.0, 1.0]`**, NOT integer percentages in `[0, 100]`.

### C. Verification of Dataset Generation Threshold (`clear_perc >= 0.70`)
In [scripts/prepare_phase7c_multievent_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_phase7c_multievent_dataset.py), the observation quality gate is defined as:
```python
mask_flood = (flooded == 1.0) & (jrc_perm == 0.0) & (clear_perc >= 0.70)
mask_dry = (flooded == 0.0) & (jrc_perm == 0.0) & (clear_perc >= 0.70)
```
Because `clear_perc` is encoded as a fraction in `[0.0, 1.0]`, the threshold `0.70` represents **$\ge 70.0\%$ cloud-free satellite passes**, which is the official quality gate established by Tellman et al. (Nature 2021) for the Global Flood Database.

Empirical distribution of Band 4 (`clear_perc`) across all 4 event evaluation windows:
- **DFO 2507 (Bihar - Test):** Minimum = **0.9104** (91.0%), Median = **0.9778**, Maximum = **1.0000**
- **DFO 4499 (Bengal - Train):** Minimum = **0.8611** (86.1%), Median = **1.0000**, Maximum = **1.0000**
- **DFO 2935 (Maharashtra - Train):** Minimum = **0.9368** (93.7%), Median = **0.9895**, Maximum = **1.0000**
- **DFO 3372 (Assam - Val):** Minimum = **0.8148** (81.5%), Median = **1.0000**, Maximum = **1.0000**

Because the minimum `clear_perc` in the evaluation window across all four events is **0.8148** (well above 0.70), **zero cloud-obscured pixels (< 70%) exist within the valid observed footprints**. The threshold `0.70` is verified as mathematically correct and semantically sound.

---

## 3. Comprehensive Row Count Reconciliation

Every row count has been traced from the raw satellite raster grids down to the packaged training artifacts and manifests.

### A. Raw Raster Grid Breakdown in 1° Bounding Windows

Each event footprint corresponds to a 1° × 1° bounding box containing 445 × 445 = **198,025 grid cells**:

| Event ID | River Basin & State | Total Raster Cells | NoData / Unmapped | Cloud Obscured (`< 0.70`) | Permanent Water (`perm == 1`) | Episodic Flood (`flood == 1`) | Dry Ground (`dry == 0`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **DFO 4499** | Lower Ganga (West Bengal) | 198,025 | 3,767 | 0 | 9,146 | 11,159 | 173,953 |
| **DFO 2935** | Upper Godavari (Maharashtra) | 198,025 | 77,998 | 0 | 853 | 350 | 118,824 |
| **DFO 3372** | Upper Brahmaputra (Assam) | 198,025 | 79,455 | 0 | 1,207 | 21,170 | 96,193 |
| **DFO 2507** | North Bihar / Kosi (Bihar) | 198,025 | 709 | 0 | 811 | 11,435 | 185,070 |

### B. Master Dataset Composition (209,116 Rows Total)
The master dataset ([phase7c_multievent_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_dataset.parquet) / `.csv`) contains 24 columns and includes permanent water controls (`flood_label = -1`):

| Split Role | Event ID | Permanent Water (`-1`) | Dry Ground (`0`) | Episodic Flood (`1`) | Split Subtotal |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Train** | **DFO 4499** | 500 | 2,500 | 2,500 | 5,500 |
| **Train** | **DFO 2935** | 100 | 350 | 350 | 800 |
| **Validation** | **DFO 3372** | 500 | 2,500 | 2,500 | 5,500 |
| **Test (Held-Out)** | **DFO 2507** | **811** | **185,070** | **11,435** | **197,316** |
| **Total Master Rows** | — | **1,911** | **190,420** | **16,785** | **209,116** |

### C. Binary Supervised Dataset Composition (207,205 Rows Total)
The binary modeling dataset ([phase7c_multievent_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet) / `.csv`) contains 24 columns and **strictly excludes all 1,911 permanent water controls (`flood_label = -1`)**:

| Split Role | Event ID | Dry Ground (`0`) | Episodic Flood (`1`) | Binary Samples | Class Balance Strategy |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **Train** | **DFO 4499** | 2,500 | 2,500 | 5,000 | 50.0% / 50.0% balanced training subset |
| **Train** | **DFO 2935** | 350 | 350 | 700 | 50.0% / 50.0% balanced training subset |
| **Validation** | **DFO 3372** | 2,500 | 2,500 | 5,000 | 50.0% / 50.0% balanced validation subset |
| **Test (Held-Out)** | **DFO 2507** | **185,070** | **11,435** | **196,505** | **NATURAL POPULATION (5.819% prevalence; zero artificial balance)** |
| **Total Binary Rows** | — | **190,420** | **16,785** | **207,205** | — |

### D. Package & Manifest Cross-Reconciliation

```
PREPARED DATASETS (data/processed/phase7/ml/)
├── phase7c_multievent_binary_dataset.parquet: 207,205 rows | SHA-256: f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7
├── phase7c_multievent_binary_dataset.csv:     207,205 rows | SHA-256: 754724649d8e856093d21986fcce0e383b21bacf922c333f9b64dcdea2fb27cb
├── phase7c_multievent_dataset.parquet:        209,116 rows | SHA-256: a3ed9802640551c54566a117fdf9c7c0a187a68cb7d78405bde3f3772b85e4e3
└── phase7c_multievent_dataset.csv:            209,116 rows | SHA-256: e2e26d03ccd590bb21caa2de95a812e934f646a13118f7c2a449e54c0d3dc4b0
        │                                                           │
        │ (Exact bitwise file copy)                                 │ (100% Cryptographic Parity)
        ▼                                                           ▼
PACKAGED DELIVERABLES (data/packages/phase7d_kaggle_dataset/)
├── phase7c_multievent_binary_dataset.parquet: 207,205 rows | SHA-256: f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7
├── phase7c_multievent_binary_dataset.csv:     207,205 rows | SHA-256: 754724649d8e856093d21986fcce0e383b21bacf922c333f9b64dcdea2fb27cb
├── phase7c_multievent_dataset.parquet:        209,116 rows | SHA-256: a3ed9802640551c54566a117fdf9c7c0a187a68cb7d78405bde3f3772b85e4e3
└── phase7c_multievent_dataset.csv:            209,116 rows | SHA-256: e2e26d03ccd590bb21caa2de95a812e934f646a13118f7c2a449e54c0d3dc4b0
```

Both [data/manifests/phase7c_multievent_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7c_multievent_dataset_manifest.yaml) and [data/manifests/phase7d_kaggle_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7d_kaggle_dataset_manifest.yaml) record these exact SHA-256 hashes and sample counts.

---

## 4. Phase 7B Pilot Dataset Byte-for-Byte Preservation

We audited the physical Phase 7B pilot dataset file on disk against the authoritative Phase 7B manifest:

| Attribute | Authoritative Phase 7B Manifest | Physical File on Disk | Reconciliation Status |
| :--- | :--- | :--- | :---: |
| **File Path** | `data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet` | `data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet` | Verified |
| **Row Count** | 5,500 samples | 5,500 samples (2,500 flood, 2,500 dry, 500 perm) | **MATCH (100%)** |
| **Column Count** | 24 columns | 24 columns | **MATCH (100%)** |
| **File Size** | 136,711 bytes | 136,711 bytes | **MATCH (100%)** |
| **SHA-256 Checksum** | `4d809d47fdc908121f08f5a00ed3d9bab3d515fd6f242a185f73557225782225` | `4d809d47fdc908121f08f5a00ed3d9bab3d515fd6f242a185f73557225782225` | **MATCH (100%)** |
| **Event Source** | DFO 4499 (West Bengal, July 2017) | DFO 4499 | Verified |

**Conclusion:**
The Phase 7B pilot dataset was **preserved byte-for-byte** without modification or overwrite. (An earlier report draft contained a typographical error listing 149,850 bytes; direct file inspection confirms that the original 136,711-byte artifact remained untouched).

---

## 5. Feature Leakage & Semantics Audit Register

| Feature Name | Source & Provenance | Leakage / Redundancy Audit Finding | Final Treatment |
| :--- | :--- | :--- | :--- |
| `historical_flood_frequency` | GFD 2000–2018 national disaster catalog | **CONFIRMED FUTURE LEAKAGE & EVENT PROXY**: Includes disaster occurrences up to 14 years after DFO 2507 (June 2004) and includes the target disaster itself. Has zero intra-basin spatial variance. | **STRICTLY EXCLUDED FROM MODEL TRAINING**. Retained in dataset file for Schema v1 compliance, omitted from `MODEL_TRAINING_FEATURES`. |
| `rainfall_anomaly_index` | Derived from `rainfall_72h_mm` and constants | **EXACT MATHEMATICAL COLLINEARITY**: Linear affine transformation ($r = 1.0000$) within each basin. | **RETAINED** as non-leaking, documented in manifest. |
| `distance_to_river_m` | GFD Band 5 (JRC Surface Water mask) | **SEMANTIC MISMATCH**: Represents Euclidean distance to perennial surface water bodies, not an explicit vector river network. | **RETAINED** for schema compliance with clarified semantics. |
| `landcover_class` | ESA WorldCover 2021 (10m) | **TEMPORAL GAP**: 4-to-17 year offset relative to historical event landscapes (2004–2017). | **RETAINED** as authentic; documented as scientific limitation. |
| Sub-daily Rainfall (`1h`, `3h`, `6h`) | Daily CHIRPS precipitation (0.05°) | **UNOBSERVED AT SUB-DAILY SCALE**: Daily CHIRPS cannot resolve sub-daily storm bursts. | **PRESERVED AS STRICT EXPLICIT `NaN`**. Native tree routing handles NaNs; zero-filling prohibited. |
| `rainfall_24h_mm`, `72h_mm` | Daily CHIRPS precipitation | **AUTHENTIC & VALID**: Coincides with or precedes satellite observation scene. | **RETAINED** as core physical forcing. |
| `elevation_m`, `slope_deg` | Copernicus DEM GLO-30 (30m) | **AUTHENTIC & VALID**: Physical elevation and terrain gradient. | **RETAINED** as geomorphic predictors. |

---

## 6. Recomputed Fair Baselines & Model Evaluation

All metrics were independently recomputed from the live dataset ([phase7c_multievent_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet)) using [scripts/verify_evaluation_metrics.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/verify_evaluation_metrics.py).

Preflight conditions:
- Preprocessing fit strictly on training data (`DFO_4499`, `DFO_2935`).
- Threshold tuning performed strictly on validation data (`DFO_3372`).
- Final evaluation conducted strictly on the natural held-out test split (`DFO_2507`, **196,505 rows**, 5.82% prevalence).

### Detailed Metric Comparison Table:

| Metric | Baseline 1: Prior ($P = 0.50$) | Baseline 2: Inverted Elevation Ranking | Baseline 2: Elevation (Validation Th = 0.8910) | Primary Model: XGBoost (Default Th = 0.50) | Primary Model: XGBoost (Val-Tuned Th = 0.10) | Primary Model: XGBoost (Val-Tuned Th = 0.05) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ROC-AUC** | 0.5000 | **0.8038** | 0.8038 | 0.5867 | 0.5867 | 0.5867 |
| **PR-AUC** | 0.0582 | **0.2210** | 0.2210 | 0.1888 | 0.1888 | 0.1888 |
| **Precision** | 0.0582 | N/A | 0.0582 | **0.4821** | 0.2065 | 0.1298 |
| **Recall** | **1.0000** | N/A | **1.0000** | 0.2183 | 0.3043 | 0.3697 |
| **F1-Score** | 0.1100 | N/A | 0.1100 | **0.3005** | 0.2461 | 0.1921 |
| **Brier Score** | 0.2500 | **N/A\*** | **N/A\*** | **0.0553** | 0.0553 | 0.0553 |
| **False Positive Rate (FPR)** | 1.0000 | N/A | 0.9997 | **0.0145** | 0.0722 | 0.1532 |
| **False Negative Rate (FNR)** | **0.0000** | N/A | **0.0000** | 0.7817 | 0.6957 | 0.6303 |
| **False Positives (FP)** | 185,070 | N/A | 185,007 | **2,681** | 13,371 | 28,350 |
| **True Positives (TP)** | 11,435 | N/A | 11,435 | 2,496 | 3,480 | 4,228 |
| **False Negatives (FN)** | 0 | N/A | 0 | 8,939 | 7,955 | 7,207 |
| **True Negatives (TN)** | 0 | N/A | 63 | 182,389 | 171,699 | 156,720 |
| **Total Test Support** | 196,505 | 196,505 | 196,505 | 196,505 | 196,505 | 196,505 |

*\*Note on Brier Score for Elevation Heuristic: Brier score is defined strictly on calibrated probability estimates. Because raw inverted elevation $1 - \frac{z - z_{\min}}{z_{\max} - z_{\min}}$ is an ordinal ranking score rather than a probability $P(\text{flood} \mid z)$, computing a Brier score on it is mathematically invalid and marked N/A.*

### Confusion Matrix Reconciliation:
All confusion matrices sum strictly to their respective supports:
- **Total Support:** $\text{TP} + \text{FP} + \text{TN} + \text{FN} = 196,505$
- **Positive Support (Flood):** $\text{TP} + \text{FN} = 11,435$ (5.819%)
- **Negative Support (Dry):** $\text{TN} + \text{FP} = 185,070$ (94.181%)

$$\text{XGBoost (Th = 0.50): } \begin{pmatrix} \text{TN: } 182,389 & \text{FP: } 2,681 \\ \text{FN: } 8,939 & \text{TP: } 2,496 \end{pmatrix}$$

$$\text{FPR} = \frac{2,681}{2,681 + 182,389} = 0.014486 \approx 1.45\%$$

$$\text{FNR} = \frac{8,939}{8,939 + 2,496} = 0.781722 \approx 78.17\%$$

$$\text{Precision} = \frac{2,496}{2,496 + 2,681} = 0.482132 \approx 48.21\%$$

$$\text{Recall} = \frac{2,496}{11,435} = 0.218277 \approx 21.83\%$$

### Scientific Assessment:
1. **The 92.9% Precision Illusion**: Under the old 50/50 test set, precision appeared to be 92.9%. On the real natural landscape (94.18% dry ground), an FPR of 1.45% produces 2,681 false alarms, cutting Precision to **48.21%**.
2. **Elevation Heuristic Outperforms ML**: The unsupervised physical inverted elevation ranking baseline achieved **ROC-AUC of 0.8038** and **PR-AUC of 0.2210**, beating the cross-basin trained XGBoost model (**0.5867** and **0.1888**).
3. **Cross-Basin Domain Shift**: The model was trained on coastal West Bengal (0–25m elevation) and upland Maharashtra (500–1000m elevation). When applied to North Bihar (Kosi alluvial fan, 38–75m elevation), absolute elevation and local rainfall thresholds fail to transfer.
4. **Poor Recall (FNR = 78.17%)**: The model missed 8,939 of 11,435 flood pixels.

---

## 7. Authoritative Artifact Register & SHA-256 Checksums

### A. Core Deliverable Datasets & Schema

| Artifact File | Size (Bytes) | SHA-256 Cryptographic Checksum | Role & Split Count |
| :--- | :---: | :--- | :--- |
| [phase7c_multievent_binary_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet) | 2,742,428 | `f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7` | Binary supervised set (207,205 rows) |
| [phase7c_multievent_binary_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_binary_dataset.csv) | 42,479,340 | `754724649d8e856093d21986fcce0e383b21bacf922c333f9b64dcdea2fb27cb` | Binary CSV export (207,205 rows) |
| [phase7c_multievent_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_dataset.parquet) | 2,766,983 | `a3ed9802640551c54566a117fdf9c7c0a187a68cb7d78405bde3f3772b85e4e3` | Master dataset with -1 controls (209,116 rows) |
| [phase7c_multievent_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7c_multievent_dataset.csv) | 42,869,635 | `e2e26d03ccd590bb21caa2de95a812e934f646a13118f7c2a449e54c0d3dc4b0` | Master CSV export (209,116 rows) |
| [aquora_ml_feature_schema_v1.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/ml/aquora_ml_feature_schema_v1.json) | 1,558 | `47ffdeedc73ee602f6ea1349347323b5ee3d58180fdc3b20261b94b9afee5911` | Governed feature schema v1.0.0 |
| [phase7c_multievent_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7c_multievent_dataset_manifest.yaml) | 5,885 | `2f9f592fc62734e56c5443fa4ce816e87905d6cbdfa5a0d58309c68061ce2ceb` | Preparation manifest |
| [phase7d_kaggle_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7d_kaggle_dataset_manifest.yaml) | 5,241 | `4e6a0ea5c1b690c2830fca56653ea6f0a3ec62b08fa176a6d63897c9b0e1e6db` | Package manifest |

### B. Preserved Phase 7B Pilot & Original Backups

| Artifact File | Size (Bytes) | SHA-256 Checksum | Integrity Status |
| :--- | :---: | :--- | :--- |
| [phase7_gfd_pilot_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet) | 136,711 | `4d809d47fdc908121f08f5a00ed3d9bab3d515fd6f242a185f73557225782225` | Preserved untouched (5,500 rows, DFO 4499) |
| `backups_phase7d_original/phase7c_multievent_binary_dataset.parquet` | 385,941 | `7a7c7ff07a5dccd64d333f3b545fa51ddb6cd80b15d3de9366c375668ec4be1e` | Original Phase 7D backup |
| `backups_phase7d_original/phase7c_multievent_dataset.parquet` | 416,232 | `6deaa2c5829ab0edd3df6036059ad462a5115922946b9ae393b6bbbb374385de` | Original Phase 7D backup |

---

## 8. Automated Test Suite Execution & Outcomes

Executed using `backend\.venv\Scripts\python.exe`:

| Test Suite | Command Line | Tests Executed | Passed | Failed | Execution Time |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Phase 7D Kaggle Preflight** | `pytest backend/tests/test_phase7d_kaggle_preflight.py -v` | 6 | **6** | 0 | 1.82s |
| **Phase 7C Multi-Event Dataset** | `pytest backend/tests/test_phase7c_multievent_dataset.py -v` | 6 | **6** | 0 | 3.65s |
| **Phase 7B Pilot Dataset** | `pytest backend/tests/test_phase7_real_flood_dataset.py -v` | 11 | **11** | 0 | 1.40s |
| **Phase 6 Terrain Engine Suite** | `pytest backend/tests/test_terrain_engine.py -v` | 16 | **16** | 0 | 8.65s |
| **Consolidated Regression** | `pytest (all 4 suites consolidated) -v` | **39** | **39** | **0** | **13.64s** |

All 39 relevant automated software tests passed with 100% success.

---

## 9. Remaining Scientific Limitations

1. **Absolute Elevation Domain Shift**: Decision trees trained on raw elevation meters do not transfer across basins. Future phases must incorporate relative hydrologic terrain metrics (Height Above Nearest Drainage, HAND).
2. **Land Cover Temporal Mismatch**: ESA WorldCover 2021 introduces a 4-to-17 year temporal gap relative to historical flood occurrences.
3. **Sub-Daily Rainfall Gap**: Daily CHIRPS rainfall cannot resolve 1h, 3h, or 6h flash storm peaks; sub-daily features must remain unobserved (`NaN`) until verified sub-daily satellite products are integrated.
4. **Permanent Water Representation**: Distance to river is derived from permanent surface water bodies (JRC Global Surface Water), not an explicit vector streamline centerline network.

---

## 10. Final GO / NO-GO Governance Decision

$$\mathbf{FINAL\ DECISION:\ EXPERIMENTAL\_EVALUATION\_ONLY}$$

### Decision Breakdown:
- **DATA INTEGRITY & KAGGLE PREFLIGHT: GO (APPROVED FOR EXPERIMENTAL BENCHMARKING)**
  * GFD clear observation units verified as fractions in `[0.0, 1.0]`.
  * Threshold `clear_perc >= 0.70` verified as exact 70% quality gate.
  * Held-out test set preserves the unskewed natural population (196,505 rows, 5.82% flood prevalence).
  * Checksums reconciled across prepared and packaged assets with 100% cryptographic parity.
  * Phase 7B pilot preserved byte-for-byte (`136,711 bytes`, SHA-256 `4d809d47...`).
  * Feature leakage (`historical_flood_frequency`) strictly excluded from model training.
- **CIVIL DEFENSE & PRODUCTION DEPLOYMENT: NO-GO (STRICTLY PROHIBITED)**
  * The model underperforms simple elevation ranking (ROC-AUC 0.5867 vs 0.8038).
  * High false negative rate (78.17%) and moderate precision (48.21%) make the model unsafe for automated flood alerts or evacuation routing.
