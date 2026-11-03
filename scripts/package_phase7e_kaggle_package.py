"""
AQUORA Phase 7E: Kaggle Package Generation Pipeline.

Assembles the complete, reproducible Kaggle package for Phase 7E experimental ML:
1. Binary training dataset (phase7c_multievent_binary_dataset.parquet / .csv)
2. Governed feature schema (aquora_ml_feature_schema_v1.json)
3. Kaggle notebook (AQUORA_Phase_7E_Experimental_ML.ipynb)
4. Comprehensive Data Dictionary (DATA_DICTIONARY.md)
5. Target Label Documentation (TARGET_LABEL_DOCUMENTATION.md)
6. Event-Level Split Documentation (SPLIT_DOCUMENTATION.md)
7. Data Quality & Limitations Documentation (DATA_QUALITY_AND_LIMITATIONS.md)
8. README and Kaggle Upload Guide (README.md)
9. Authoritative Manifest with SHA-256 checksums (phase7e_kaggle_package_manifest.yaml)
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

# Source Paths
PROCESSED_ML_DIR = REPO_ROOT / "data" / "processed" / "phase7" / "ml"
SRC_BINARY_PARQUET = PROCESSED_ML_DIR / "phase7c_multievent_binary_dataset.parquet"
SRC_BINARY_CSV = PROCESSED_ML_DIR / "phase7c_multievent_binary_dataset.csv"
SRC_MASTER_PARQUET = PROCESSED_ML_DIR / "phase7c_multievent_dataset.parquet"
SRC_MASTER_CSV = PROCESSED_ML_DIR / "phase7c_multievent_dataset.csv"
SRC_SCHEMA = REPO_ROOT / "ml" / "aquora_ml_feature_schema_v1.json"
SRC_NOTEBOOK = REPO_ROOT / "notebooks" / "AQUORA_Phase_7E_Experimental_ML.ipynb"

# Target Package Directory
PACKAGE_DIR = REPO_ROOT / "data" / "packages" / "phase7e_kaggle_package"
PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

DEST_BINARY_PARQUET = PACKAGE_DIR / "phase7c_multievent_binary_dataset.parquet"
DEST_BINARY_CSV = PACKAGE_DIR / "phase7c_multievent_binary_dataset.csv"
DEST_SCHEMA = PACKAGE_DIR / "aquora_ml_feature_schema_v1.json"
DEST_NOTEBOOK = PACKAGE_DIR / "AQUORA_Phase_7E_Experimental_ML.ipynb"
DEST_DATA_DICT = PACKAGE_DIR / "DATA_DICTIONARY.md"
DEST_TARGET_DOC = PACKAGE_DIR / "TARGET_LABEL_DOCUMENTATION.md"
DEST_SPLIT_DOC = PACKAGE_DIR / "SPLIT_DOCUMENTATION.md"
DEST_QUALITY_DOC = PACKAGE_DIR / "DATA_QUALITY_AND_LIMITATIONS.md"
DEST_MANIFEST = PACKAGE_DIR / "phase7e_kaggle_package_manifest.yaml"
DEST_README = PACKAGE_DIR / "README.md"

PROJECT_MANIFEST = REPO_ROOT / "data" / "manifests" / "phase7e_kaggle_package_manifest.yaml"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def write_data_dictionary():
    content = r"""# AQUORA Phase 7E: Dataset Data Dictionary

**Document Version:** `1.0.0-phase7e`  
**Governed Schema:** `ml/aquora_ml_feature_schema_v1.json` (v1.0.0)  
**Target Table:** `phase7c_multievent_binary_dataset.parquet` / `.csv`  
**Row Count:** 207,205 rows | **Column Count:** 24 columns  

---

## 1. Column Inventory and Specifications

| Column Name | Data Type | Physical Units | Valid Range / Categories | Missing Policy | Description & Provenance |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `point_id` | `string` | Identifier | `pt_<hash>` | Mandatory | Unique deterministic alphanumeric grid point identifier. |
| `event_id` | `string` | Categorical | `DFO_4499`, `DFO_2935`, `DFO_3372`, `DFO_2507` | Mandatory | Global Flood Database (GFD) disaster catalog event identifier. |
| `event_region` | `string` | Geographic | Basin & State name | Mandatory | River basin and Indian state administrative region of the disaster scene. |
| `observation_date`| `string` | ISO Date | `YYYY-MM-DD` | Mandatory | Peak satellite observation date corresponding to optical MODIS acquisition. |
| `latitude` | `float64` | Degrees N | [21.5, 27.5] | Mandatory | Geographic WGS84 coordinate (EPSG:4326). **FORBIDDEN AS MODEL PREDICTOR**. |
| `longitude` | `float64` | Degrees E | [74.0, 93.5] | Mandatory | Geographic WGS84 coordinate (EPSG:4326). **FORBIDDEN AS MODEL PREDICTOR**. |
| `basin_id` | `string` | HydroBASINS | HydroBASINS Pfafstetter code | Mandatory | Level 5/6 hydrological catchment boundary identifier. |
| `split` | `string` | Partition | `train`, `validation`, `test` | Mandatory | Event-level holdout partition. Strictly disjoint by `event_id`. |
| `gfd_flooded` | `float32` | Inundation | `{0.0, 1.0}` | Mandatory | Raw GFD v1.4 Band 1 observation (1 = flood inundation, 0 = non-flooded). |
| `gfd_clear_perc` | `float32` | Fraction | [0.70, 1.00] | Mandatory | GFD v1.4 Band 4 clear view fraction ($\text{clear\_passes} / \text{total\_passes}$). |
| `gfd_jrc_perm_water`| `float32`| Surface Water | `0.0` (Binary set) | Mandatory | GFD v1.4 Band 5 JRC permanent surface water mask (1 = water, 0 = land). |
| `flood_label` | `int64` | Binary Target | `{0, 1}` | Mandatory | Supervised target: **0 = Verified Dry Ground**, **1 = Verified Flood Inundation**. |
| `label_quality_flag`| `string` | Audit Status | `VERIFIED_OBSERVATION` | Mandatory | Optical quality assurance status. Clear observation fraction $\ge 70\%$. |
| `rainfall_1h_mm` | `float32` | mm | `NaN` | Explicit NaN | 1-hour sub-daily rainfall accumulation. **Unobserved in daily CHIRPS; zero-filling strictly prohibited.** |
| `rainfall_3h_mm` | `float32` | mm | `NaN` | Explicit NaN | 3-hour sub-daily rainfall accumulation. **Unobserved in daily CHIRPS; zero-filling strictly prohibited.** |
| `rainfall_6h_mm` | `float32` | mm | `NaN` | Explicit NaN | 6-hour sub-daily rainfall accumulation. **Unobserved in daily CHIRPS; zero-filling strictly prohibited.** |
| `rainfall_24h_mm` | `float32` | mm | [0.0, 300.0] | Observed | CHIRPS 0.05° daily precipitation on the peak event observation date. |
| `rainfall_72h_mm` | `float32` | mm | [0.0, 750.0] | Observed | CHIRPS 3-day antecedent rainfall accumulation preceding observation scene. |
| `rainfall_anomaly_index`| `float32`| Index | [0.0, 10.0] | Observed | Normalized rainfall anomaly. Verified collinear with `rainfall_72h_mm` ($r = 1.0000$). |
| `elevation_m` | `float32` | Meters | [-10.0, 1200.0] | Observed | Copernicus DEM GLO-30 topographic elevation above mean sea level. |
| `slope_deg` | `float32` | Degrees | [0.0, 90.0] | Observed | Copernicus DEM 30m terrain gradient calculated via Horn algorithm. |
| `distance_to_river_m`| `float32`| Meters | [0.0, 50000.0] | Observed | Euclidean distance to nearest JRC permanent open surface water body. |
| `historical_flood_frequency`| `float32`| Count | [0.0, 20.0] | Observed | **STRICTLY EXCLUDED FROM MODEL TRAINING**. Computed from GFD 2000-2018 catalog; introduces future data leakage. |
| `landcover_class` | `int32` | Discrete Code | `{10, 20, 30, ..., 100}` | Observed | ESA WorldCover 2021 10m discrete land cover classification code. |

---

## 2. Governed Feature Subsets

### A. Core National Predictors (`CORE_11_PREDICTORS`)
Defined in `ml/aquora_ml_feature_schema_v1.json`:
1. `rainfall_1h_mm`
2. `rainfall_3h_mm`
3. `rainfall_6h_mm`
4. `rainfall_24h_mm`
5. `rainfall_72h_mm`
6. `rainfall_anomaly_index`
7. `elevation_m`
8. `slope_deg`
9. `distance_to_river_m`
10. `historical_flood_frequency`
11. `landcover_class`

### B. Model Training Features (`MODEL_TRAINING_FEATURES` - Exactly 10)
Excludes `historical_flood_frequency` due to confirmed future catalog leakage and zero intra-basin spatial variance:
1. `rainfall_1h_mm` (explicit NaN)
2. `rainfall_3h_mm` (explicit NaN)
3. `rainfall_6h_mm` (explicit NaN)
4. `rainfall_24h_mm`
5. `rainfall_72h_mm`
6. `rainfall_anomaly_index`
7. `elevation_m`
8. `slope_deg`
9. `distance_to_river_m`
10. `landcover_class`

### C. Forbidden Columns (`FORBIDDEN_LEAKAGE_COLUMNS`)
Must never be passed to model training:
`flood_label`, `candidate_flood_label`, `sar_delta_vv_db`, `sar_scene_id`, `water_depth_m`, `flow_velocity_ms`, `modeled_depth_m`, `latitude`, `longitude`.
"""
    DEST_DATA_DICT.write_text(content, encoding="utf-8")
    print(f"Written: {DEST_DATA_DICT.name}")


def write_target_label_documentation():
    content = r"""# AQUORA Phase 7E: Target Label Documentation

**Target Column:** `flood_label`  
**Dataset:** `phase7c_multievent_binary_dataset.parquet` / `.csv`  

---

## 1. Ground Truth Source & Physics
Target labels are derived directly from the **Global Flood Database v1.4** (Tellman et al., *Nature* 2021). The GFD maps inundation extents using MODIS Terra and Aqua satellite surface reflectance at 250m spatial resolution across large-scale historical flood disasters.

### Raster Band Architecture:
- **Band 1 (`flooded`):** 1 = Inundated flood pixel; 0 = Non-inundated land.
- **Band 3 (`clear_views`):** Count of cloud-free MODIS satellite overpasses during the event window.
- **Band 4 (`clear_perc`):** Clear observation fraction ($\text{clear\_views} / \text{total\_passes}$), verified mathematically to be in $[0.0, 1.0]$.
- **Band 5 (`jrc_perm_water`):** JRC Global Surface Water permanent water mask (1 = permanent open water body; 0 = land).

---

## 2. Supervised Target Label Encoding

| Value | Semantic Definition | Raster Filter Criteria | Role in Phase 7E |
| :---: | :--- | :--- | :--- |
| **`0`** | **Verified Dry Ground** | `(flooded == 0) & (jrc_perm == 0) & (clear_perc >= 0.70)` | True negative ground truth. |
| **`1`** | **Verified Flood Inundation** | `(flooded == 1) & (jrc_perm == 0) & (clear_perc >= 0.70)` | True positive episodic flood ground truth. |
| **`-1`** | **Permanent Surface Water** | `(jrc_perm == 1)` | **QUARANTINED CONTROL**. Excluded from binary training dataset. Preserved only in master reference dataset. |

---

## 3. Strict Quarantine of Permanent Water Controls (`-1`)
Permanent water bodies (lakes, reservoirs, perennial river channels) are naturally filled with water year-round regardless of rainfall or flash flooding. Including permanent water bodies in binary supervised flood classification creates artificial shortcuts where models learn to detect standing water rather than dynamic episodic inundation.

In accordance with AQUORA scientific governance:
- **Binary Training Dataset (`phase7c_multievent_binary_dataset`):** Strictly excludes all 1,911 permanent water samples (`flood_label == -1` count = **0**).
- **Master Dataset (`phase7c_multievent_dataset`):** Retains permanent water controls separately for geomorphic boundary audits.

---

## 4. Optical Quality Gate (`clear_perc >= 0.70`)
Satellite optical sensors cannot observe the ground through cloud cover. Following Tellman et al. (2021), a strict quality gate is enforced:
- Only pixels with $\ge 70.0\%$ cloud-free satellite overpasses during the event duration are accepted.
- Across all 4 event windows, observed `clear_perc` exceeds $0.8148$ (81.5% to 100.0% clear views).
- **Zero cloud-obscured pixels (< 70%) exist in the dataset.**
"""
    DEST_TARGET_DOC.write_text(content, encoding="utf-8")
    print(f"Written: {DEST_TARGET_DOC.name}")


def write_split_documentation():
    content = r"""# AQUORA Phase 7E: Event-Level Split Documentation & Holdout Policy

**Governance Principle:** Complete Disjoint Event Holdouts.  
**Target Table:** `phase7c_multievent_binary_dataset.parquet` / `.csv`  

---

## 1. Event Partitioning Summary

| Split Role | Event ID | River Basin & State | Event Date | Binary Samples | Flood (`1`) | Dry (`0`) | Class Balance Strategy |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **Train** | **DFO 4499** | Lower Ganga Basin (West Bengal) | `2017-07-27` | 5,000 | 2,500 | 2,500 | 50.0% / 50.0% balanced training subset |
| **Train** | **DFO 2935** | Upper Godavari Basin (Maharashtra) | `2006-07-28` | 700 | 350 | 350 | 50.0% / 50.0% balanced training subset |
| **Validation**| **DFO 3372** | Upper Brahmaputra Basin (Assam) | `2008-08-30` | 5,000 | 2,500 | 2,500 | 50.0% / 50.0% balanced validation subset |
| **Test** | **DFO 2507** | North Bihar / Kosi Basin (Bihar) | `2004-06-20` | **196,505** | **11,435** | **185,070** | **NATURAL POPULATION (5.819% prevalence; zero artificial rebalancing)** |
| **Total** | — | — | — | **207,205** | **16,785** | **190,420** | — |

---

## 2. Anti-Leakage Split Isolation Rules

1. **Strictly Disjoint Event Sets**:
   $$\text{Train Events} \cap \text{Validation Events} = \emptyset$$
   $$\text{Train Events} \cap \text{Test Events} = \emptyset$$
   $$\text{Validation Events} \cap \text{Test Events} = \emptyset$$
2. **Zero Spatial Coordinate Overlap**:
   The four event footprints are geographically separated across distinct hydrographic regimes across India:
   - DFO 4499: Coastal deltaic Bengal (Lat 22.0°–23.0°N, Lon 88.0°–89.0°E)
   - DFO 2935: Deccan plateau upland Maharashtra (Lat 19.5°–20.5°N, Lon 74.5°–75.5°E)
   - DFO 3372: Alluvial eastern Assam valley (Lat 26.5°–27.5°N, Lon 92.5°–93.5°E)
   - DFO 2507: North Bihar Gangetic / Kosi alluvial fan (Lat 25.5°–26.5°N, Lon 86.0°–87.0°E)
   There is zero coordinate overlap across splits.
3. **Training-Only Preprocessing**:
   Imputation statistics, scalers, and elevation bounds are fit exclusively on `X_train`. Validation and test sets are transformed without refitting.

---

## 3. Mandatory Test-Set Restriction: `ALREADY_INSPECTED_HOLDOUT`

> **GOVERNANCE MANDATE**:
> The test event **DFO 2507** was previously inspected and evaluated during the Phase 7D closure audit.
>
> Consequently:
> 1. DFO 2507 is formally designated as an **`ALREADY_INSPECTED_HOLDOUT`**.
> 2. It must **NEVER** be used for feature selection, hyperparameter tuning, model selection, or decision threshold selection.
> 3. All model selection decisions must be made strictly using training and validation data (DFO 3372).
> 4. DFO 2507 is held frozen for a final, qualified benchmark comparison.
> 5. Reports must explicitly disclose that DFO 2507 is an already-inspected holdout, not a blind operational deployment test.
"""
    DEST_SPLIT_DOC.write_text(content, encoding="utf-8")
    print(f"Written: {DEST_SPLIT_DOC.name}")


def write_data_quality_and_limitations():
    content = r"""# AQUORA Phase 7E: Data Quality, Audit Findings & Scientific Limitations

**Document Version:** `1.0.0-phase7e`  
**Governance Verdict:** `EXPERIMENTAL_EVALUATION_ONLY`  

---

## 1. Feature Audit & Provenance Register

| Predictor Feature | Authoritative Source | Resolution / Scale | Audit Finding & Governance Treatment |
| :--- | :--- | :---: | :--- |
| `rainfall_1h_mm`, `3h_mm`, `6h_mm` | Daily CHIRPS (UCSB) | 0.05° (~5.5 km) | **UNOBSERVED AT SUB-DAILY SCALE**: Daily CHIRPS cannot resolve sub-daily rainfall bursts. Preserved strictly as explicit `NaN`. Zero-filling is strictly prohibited. |
| `rainfall_24h_mm`, `72h_mm` | Daily CHIRPS (UCSB) | 0.05° (~5.5 km) | **AUTHENTIC & VALID**: Coincides with and precedes satellite observation date. Retained as primary atmospheric forcings. |
| `rainfall_anomaly_index` | Normalized CHIRPS | 0.05° (~5.5 km) | **EXACT COLLINEARITY**: Exact affine transformation ($r = 1.0000$) of `rainfall_72h_mm` within each event scene. Retained for schema compliance. |
| `elevation_m` | Copernicus DEM GLO-30 | 30m | **PHYSICAL TOPOGRAPHY**: Copernicus DEM elevation above sea level. Retained as core geomorphic predictor. |
| `slope_deg` | Copernicus DEM GLO-30 | 30m | **TERRAIN GRADIENT**: 30m Horn slope in degrees. Retained as core runoff predictor. |
| `distance_to_river_m` | JRC Surface Water | 30m | **PERENNIAL WATER BODY DISTANCE**: Represents Euclidean distance to JRC permanent water bodies, not an explicit vector streamline centerline network. |
| `historical_flood_frequency` | GFD 2000–2018 Catalog | Regional | **FUTURE LEAKAGE & EVENT SHORTCUT**: Includes disasters occurring up to 14 years after DFO 2507. Has zero intra-basin spatial variance. **STRICTLY EXCLUDED FROM MODEL TRAINING**. |
| `landcover_class` | ESA WorldCover 2021 | 10m | **TEMPORAL MISMATCH**: Represents 2021 land cover; carries a 4-to-17 year offset relative to historical flood events (2004–2017). Retained as best available authentic baseline. |

---

## 2. Core Scientific Limitations

### A. Absolute Elevation Cross-Basin Domain Shift
Decision trees trained on absolute elevation meters cannot generalize across basins with differing baseline altitudes:
- West Bengal training scene: elevations range from 0m to 25m.
- Maharashtra training scene: elevations range from 500m to 1000m.
- Bihar test scene: elevations range from 38m to 75m.
When a tree trained on coastal Bengal and Deccan uplands is evaluated on North Bihar, it misclassifies flat alluvial terrain. In fact, an **unsupervised physical inverted elevation ranking baseline within the test basin (ROC-AUC 0.8038)** outperforms the cross-basin trained machine learning model (**ROC-AUC 0.5867**).

### B. Natural Imbalance and the False Alarm Problem
In real-world landscapes, flood inundation is a rare event (5.82% natural prevalence in DFO 2507; 94.18% dry land):
- On an artificial 50/50 test set, precision appeared to be 92.9%.
- On the authentic natural landscape, a small false-positive rate ($\text{FPR} = 1.45\%$) generates 2,681 false alarms across 185,070 dry pixels, reducing precision to **48.21%**.
- At validation-tuned low thresholds, precision drops to **12.98%**.

### C. Absence of Sub-Daily Convective Precipitation
CHIRPS daily precipitation cannot resolve 1-hour or 3-hour storm bursts. Without sub-daily radar or IMERG Early Run data, flash floods driven by localized convective downpours cannot be captured at hourly granularity.

---

## 3. Operational Governance Invariants

1. **Phase 6 Hydrodynamic Authority**: The Phase 6 deterministic physics engine remains the primary authority for flood depth, velocity, and hazard calculation. Machine learning is secondary, exploratory, and for large-scale screening only.
2. **Deep Intelligence Boundary**: Mumbai / Mithi River remains the ONLY validated Deep Intelligence Zone. National models must never require Deep Zone high-resolution features.
3. **No Automated Public Alerts**: Machine learning predictions must **NEVER** be used to trigger automated civil defense evacuation alerts or public warnings.
"""
    DEST_QUALITY_DOC.write_text(content, encoding="utf-8")
    print(f"Written: {DEST_QUALITY_DOC.name}")


def write_readme():
    content = """# AQUORA Phase 7E: Reproducible Kaggle ML Training Package

**Dataset Name:** `aquora-phase7e-kaggle-package`  
**Governance Decision:** `EXPERIMENTAL_EVALUATION_ONLY`  
**License:** CC-BY-NC-4.0 (GFD v1.4 / Copernicus DEM / CHIRPS / ESA WorldCover)  
**Package Version:** `1.0.0-phase7e`  

---

## 1. Package Purpose & Overview
This package contains the complete, reproducible assets for Phase 7E experimental machine learning training, validation-based threshold selection, and held-out benchmark evaluation.

It is prepared strictly in accordance with AQUORA scientific governance:
- **Zero Synthetic Labels**: Sourced from authentic satellite ground truth (Global Flood Database v1.4, Nature 2021).
- **Zero Data Leakage**: Disjoint event holdout partitioning; `historical_flood_frequency` strictly excluded; sub-daily rainfall NaNs preserved.
- **Natural Test Distribution**: Held-out test split (DFO 2507) preserves authentic 5.82% natural prevalence (zero artificial balancing).
- **Holdout Restriction**: DFO 2507 is designated as `ALREADY_INSPECTED_HOLDOUT` and is quarantined from model and threshold selection.

---

## 2. Package Asset Inventory

| File Name | Description | Size | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| `phase7c_multievent_binary_dataset.parquet` | Authoritative binary modeling dataset | 2.7 MB | `f31591cf39cd4c542d842128c6782d5206dd7b52449928e674d340acfed4d2f7` |
| `phase7c_multievent_binary_dataset.csv` | CSV export of binary modeling dataset | 42.5 MB | `754724649d8e856093d21986fcce0e383b21bacf922c333f9b64dcdea2fb27cb` |
| `aquora_ml_feature_schema_v1.json` | Governed feature schema v1.0.0 | 1.6 KB | `47ffdeedc73ee602f6ea1349347323b5ee3d58180fdc3b20261b94b9afee5911` |
| `AQUORA_Phase_7E_Experimental_ML.ipynb` | Complete Kaggle training harness (15 sections) | Notebook | Computed in manifest |
| `DATA_DICTIONARY.md` | Feature definitions, types, physical units | Markdown | Computed in manifest |
| `TARGET_LABEL_DOCUMENTATION.md` | Label definitions and optical quality gates | Markdown | Computed in manifest |
| `SPLIT_DOCUMENTATION.md` | Event partition details and holdout rules | Markdown | Computed in manifest |
| `DATA_QUALITY_AND_LIMITATIONS.md`| Scientific audit findings and domain shifts | Markdown | Computed in manifest |
| `phase7e_kaggle_package_manifest.yaml` | Machine-readable SHA-256 asset manifest | YAML | Computed in manifest |

*(Note: Master dataset containing permanent water controls `-1` is preserved separately at `data/processed/phase7/ml/phase7c_multievent_dataset.parquet` for audit reference).*

---

## 3. Step-by-Step Kaggle Upload Instructions

### Step 1: Create New Kaggle Dataset
1. Log into your Kaggle account and navigate to [kaggle.com/datasets](https://www.kaggle.com/datasets).
2. Click **New Dataset** (top right).
3. Set the Dataset Title to: **`aquora-phase7e-kaggle-package`**.
4. Drag and drop all files from this directory (`data/packages/phase7e_kaggle_package/`).
5. Click **Create**.

### Step 2: Create or Open a Kaggle Notebook
1. In Kaggle, click **New Notebook** (Python 3, CPU or GPU runtime).
2. In the right-hand panel, click **Add Input**.
3. Search for your dataset **`aquora-phase7e-kaggle-package`** and click **Add**.
4. The dataset files will mount at `/kaggle/input/aquora-phase7e-kaggle-package/`.

### Step 3: Run the Official Phase 7E Notebook
1. In the notebook editor, click **File -> Import Notebook** and upload `AQUORA_Phase_7E_Experimental_ML.ipynb` (or copy and paste its cells).
2. The notebook will automatically:
   - Detect the input dataset and verify its SHA-256 cryptographic checksums.
   - Train Random Forest and XGBoost models strictly on `split == 'train'`.
   - Select decision thresholds strictly on validation data (`DFO_3372`).
   - Evaluate against the Constant Prior and Physical Elevation Ranking baselines.
   - Generate evaluation metrics and export governance-tagged model artifacts.
"""
    DEST_README.write_text(content, encoding="utf-8")
    print(f"Written: {DEST_README.name}")


def assemble_package():
    print("=" * 80)
    print("AQUORA PHASE 7E: ASSEMBLING REPRODUCIBLE KAGGLE PACKAGE")
    print("=" * 80)

    # 1. Verify sources exist
    for src in [SRC_BINARY_PARQUET, SRC_BINARY_CSV, SRC_SCHEMA, SRC_NOTEBOOK]:
        if not src.exists():
            raise FileNotFoundError(f"Missing required source file: {src}")

    # 2. Copy datasets and schema into package directory
    print("[1/5] Copying core binary dataset and schema to package directory...")
    shutil.copy2(SRC_BINARY_PARQUET, DEST_BINARY_PARQUET)
    shutil.copy2(SRC_BINARY_CSV, DEST_BINARY_CSV)
    shutil.copy2(SRC_SCHEMA, DEST_SCHEMA)
    shutil.copy2(SRC_NOTEBOOK, DEST_NOTEBOOK)

    # 3. Write documentation files
    print("[2/5] Generating comprehensive governance and documentation files...")
    write_data_dictionary()
    write_target_label_documentation()
    write_split_documentation()
    write_data_quality_and_limitations()
    write_readme()

    # 4. Compute cryptographic hashes
    print("[3/5] Computing SHA-256 cryptographic hashes for all packaged files...")
    package_files = [
        DEST_BINARY_PARQUET,
        DEST_BINARY_CSV,
        DEST_SCHEMA,
        DEST_NOTEBOOK,
        DEST_DATA_DICT,
        DEST_TARGET_DOC,
        DEST_SPLIT_DOC,
        DEST_QUALITY_DOC,
        DEST_README,
    ]

    assets_dict = {}
    for f in package_files:
        sha = compute_sha256(f)
        assets_dict[f.name] = {
            "path": f.name,
            "bytes": f.stat().st_size,
            "sha256": sha,
        }

    # Verify binary dataset hash matches source
    assert assets_dict[DEST_BINARY_PARQUET.name]["sha256"] == compute_sha256(SRC_BINARY_PARQUET)
    assert assets_dict[DEST_BINARY_CSV.name]["sha256"] == compute_sha256(SRC_BINARY_CSV)

    # 5. Build and write manifest
    print("[4/5] Building authoritative Phase 7E package manifest...")
    manifest_data = {
        "manifest_version": "1.0.0",
        "phase": "PHASE_7E_EXPERIMENTAL_ML_PACKAGE",
        "package_name": "aquora-phase7e-kaggle-package",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "governance_status": "EXPERIMENTAL_EVALUATION_ONLY",
        "holdout_policy": {
            "test_event_id": "DFO_2507",
            "designation": "ALREADY_INSPECTED_HOLDOUT",
            "rule": "Frozen for final qualified benchmark evaluation only. Model selection and threshold tuning restricted strictly to validation data."
        },
        "package_assets": assets_dict,
        "dataset_structure": {
            "binary_dataset_rows": 207205,
            "columns_count": 24,
            "label_column": "flood_label",
            "event_id_column": "event_id",
            "split_column": "split",
            "supervised_labels": [0, 1],
            "excluded_controls": [-1],
        },
        "split_summary": {
            "train": {
                "events": ["DFO_4499", "DFO_2935"],
                "regions": ["Lower Ganga Basin (West Bengal)", "Upper Godavari Basin (Maharashtra)"],
                "binary_samples": 5700,
                "flood_samples": 2850,
                "dry_samples": 2850,
                "class_balance": "50.0% / 50.0% balanced training subset",
            },
            "validation": {
                "events": ["DFO_3372"],
                "regions": ["Upper Brahmaputra Basin (Assam)"],
                "binary_samples": 5000,
                "flood_samples": 2500,
                "dry_samples": 2500,
                "class_balance": "50.0% / 50.0% balanced validation subset",
            },
            "test": {
                "events": ["DFO_2507"],
                "regions": ["North Bihar / Kosi Basin (Bihar)"],
                "binary_samples": 196505,
                "flood_samples": 11435,
                "dry_samples": 185070,
                "class_balance": "NATURAL_POPULATION (5.819% flood prevalence; zero artificial rebalancing)",
                "holdout_status": "ALREADY_INSPECTED_HOLDOUT",
            },
        },
        "governed_features": {
            "schema_name": "aquora_ml_feature_schema_v1",
            "core_11_features": [
                "rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm",
                "rainfall_24h_mm", "rainfall_72h_mm", "rainfall_anomaly_index",
                "elevation_m", "slope_deg", "distance_to_river_m",
                "historical_flood_frequency", "landcover_class",
            ],
            "model_training_features_10": [
                "rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm",
                "rainfall_24h_mm", "rainfall_72h_mm", "rainfall_anomaly_index",
                "elevation_m", "slope_deg", "distance_to_river_m",
                "landcover_class",
            ],
            "excluded_leakage_features": ["historical_flood_frequency"],
            "forbidden_columns": [
                "flood_label", "candidate_flood_label", "sar_delta_vv_db",
                "sar_scene_id", "water_depth_m", "flow_velocity_ms",
                "modeled_depth_m", "latitude", "longitude",
            ],
        },
        "reference_datasets": {
            "master_dataset_parquet": {
                "path": "data/processed/phase7/ml/phase7c_multievent_dataset.parquet",
                "rows": 209116,
                "permanent_water_controls": 1911,
                "purpose": "Preserved separately for reference and audit purposes without training package duplication."
            }
        }
    }

    with open(DEST_MANIFEST, "w", encoding="utf-8") as f:
        yaml.dump(manifest_data, f, sort_keys=False)

    PROJECT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(PROJECT_MANIFEST, "w", encoding="utf-8") as f:
        yaml.dump(manifest_data, f, sort_keys=False)

    print(f"Written package manifest: {DEST_MANIFEST}")
    print(f"Written project manifest: {PROJECT_MANIFEST}")
    print("[5/5] Package assembly successfully completed.")


if __name__ == "__main__":
    assemble_package()
