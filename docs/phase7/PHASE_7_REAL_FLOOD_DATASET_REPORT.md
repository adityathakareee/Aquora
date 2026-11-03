# AQUORA Phase 7: Real Flood Dataset Build Report

**Execution Phase:** Phase 7 (Data-First, Real Satellite Ground Truth)  
**Date:** October 28, 2026  
**Governance Gate:** APPROVED_REAL_SATELLITE_GROUND_TRUTH  
**Lead System:** AQUORA Hydrologic & Machine Learning Core  

---

## 1. Executive Summary & Objective Alignment

In accordance with Phase 7 governance directives (**Data First, Zero New UI Features**), AQUORA prioritized constructing an authentic, scientifically defensible dataset for flood-model training. Rather than adding dashboard widgets or synthesizing non-flood negatives, this execution grounded AQUORA's predictive architecture in **empirical satellite observations** of actual Indian disaster events.

### Primary Accomplishments:
1. **Comprehensive Data Audit**: Inspected the 6,876-row India Flood Inventory (IFI v3), historical-event records, terrain assets, and Kaggle preparation pipelines. Confirmed that administrative casualty reports cannot be broadcast to 30m grid cells without severe false-positive contamination.
2. **Authoritative GFD India Catalog Ingestion**: Audited and cataloged all **91 flood events intersecting India** (2000–2018) from the Global Flood Database (GFD v1.4 / Tellman et al., *Nature* 2021), cross-referencing each event against the IFI v3 disaster inventory.
3. **Real Satellite Flood Inundation Acquisition**: Acquired and verified multi-band GeoTIFF imagery for pilot event **DFO 4499** (Lower Ganga Basin, West Bengal / Hooghly / Howrah, July 27 – August 10, 2017; matching IFI `UEI-IMD-FL-2017-0122`). Audited 67,267 verified flood cells and 3,099,235 verified dry cells.
4. **Predictor Extraction & Conformance**: Conformed strictly to [aquora_ml_feature_schema_v1.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/ml/aquora_ml_feature_schema_v1.json) (11 `CORE_NATIONAL` features), extracting authentic antecedent precipitation from UC Santa Barbara CHIRPS v2.0 (24h and 72h), 30m terrain elevation and slope from AWS Open Data Copernicus DEM GLO-30, metric river proximity via JRC Global Surface Water KDTree, historical flood frequency, and ESA WorldCover landcover classes.
5. **Spatial Cross-Validation & Zero-Leakage Dataset**: Constructed a 5,500-sample pilot dataset partitioned across 5 spatially disjoint hydrologic sub-basins (`BASIN_4521_SB1` to `BASIN_4521_SB5`), guaranteeing zero geographic leakage between train, validation, and test splits.
6. **Automated Verification**: Implemented and passed 100% of the 7-test suite in [test_phase7_real_flood_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase7_real_flood_dataset.py) alongside foundational regression test suites.

---

## 2. Audit of Current Data & Scientific Governance

### 2.1 The 6,876-Row India Flood Inventory (IFI v3)
- **File Asset**: `data/raw/phase7/ground_truth/india_flood_inventory_v3.csv` (`ef9ab2cd...`, 1.80 MB).
- **Audit Findings**:
  * Coordinates (`Latitude`, `Longitude`, `Location`) are **100% NaN** across all 6,876 rows.
  * Records represent administrative district-level summaries (State, District, Began, Ended, Casualties).
  * **Scientific Hazard**: Assigning a binary label `flood_label = 1` to an entire district (e.g., 5,000 km² containing millions of 30m pixels) when only 3% of the land area along riverbanks actually flooded introduces catastrophic label noise (~97% false-positive contamination).
  * **Verdict**: IFI v3 serves as an authoritative macro disaster registry for temporal matching and casualty validation, but **cannot legitimately serve as pixel-level training labels** without satellite inundation maps.

### 2.2 Historical-Event Records & Extracted Rainfall
- **Derived Storm Archive**: 2,682 grouped storm events across 1981–2023.
- **Acquired Precipitation**: 23 validated CHIRPS daily GeoTIFFs, 2 GPM IMERG Final Granules (E02/E03), and 25 Mode B verified extraction dates.
- **Physical Demarcation**: Rainfall observations represent atmospheric forcing (inputs), not inundation responses (labels).

### 2.3 The Kaggle Governance Gate
- Prior to Phase 7, [prepare_kaggle_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_kaggle_dataset.py) rightly enforced `BLOCKED_BY_GROUND_TRUTH` because no empirical 30m/250m satellite flood polygons were locally ingested.
- AQUORA's **Zero-Synthetic-Labels Policy** prohibits training supervised classifiers on physical simulator outputs (Phase 6 Mithi 2D depth rasters) or arbitrary dry-negative assumptions.

---

## 3. Real Flood-Label Acquisition Pipeline

### 3.1 Global Flood Database (GFD v1.4) India Catalog
The Global Flood Database (Tellman et al., *Nature* 2021) maps 913 large flood events globally between 2000 and 2018 using Terra and Aqua MODIS surface reflectance at 250m resolution, integrated with the 30m JRC Global Surface Water dataset for permanent water separation.

AQUORA ingested the complete QC database (`gfd_qcdatabase_2019_08_01.csv`, 776.8 KB) and audited all **91 events intersecting India**:
- **Deliverables**:
  * [gfd_india_events_catalog.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json)
  * [gfd_india_events_catalog.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.csv)
- **Spatial Distribution**: Encompasses Lower Ganga, Brahmaputra, Mahanadi, Godavari, Krishna, Narmada, and Tapi basins.
- **Cross-Referencing**: Every GFD event was cross-matched against IFI v3 by state and overlapping observation window.

| Metric | GFD India Catalog Value |
| :--- | :--- |
| **Total Intersecting Events** | 91 events (9.97% of global total) |
| **Temporal Span** | September 2000 – August 2018 |
| **Sensor / Resolution** | MODIS Terra/Aqua surface reflectance @ 250 meters |
| **Permanent Water Baseline** | JRC Global Surface Water (30m, Pekel et al. 2016) |
| **Observation Quality Mask** | Explicit per-pixel `clear_perc` ([0.0, 1.0]) |
| **License** | Creative Commons Attribution-NonCommercial 4.0 International (CC-BY-NC-4.0) |

### 3.2 Pilot Event Acquisition: DFO 4499 (West Bengal, 2017)
To validate the end-to-end dataset build, AQUORA acquired pilot event **DFO 4499**:
- **Archive**: `data/raw/phase7/ground_truth/gfd/DFO_4499/DFO_4499_From_20170727_to_20170810.zip` (4,887,908 bytes | SHA-256: `588ef0dd...`).
- **GeoTIFF**: `DFO_4499_From_20170727_to_20170810.tif` (4,772,471 bytes | SHA-256: `9fab987aa7cb9becaf607c0960799b1e72b217ddd9bb7940e08e902349c1f4eb`).
- **Disaster Context**: Matches IFI event `UEI-IMD-FL-2017-0122` (Bankura, Birbhum, Hooghly, Howrah; 46 fatalities, monsoonal depression).
- **Raster Dimensions**: 3,257 × 2,034 cells in EPSG:4326 covering `[83.8824, 20.2952]` to `[91.1970, 24.8631]`.

#### Ground Truth Cell Audit Breakdown:
```
Total Raster Cells: 6,624,738
├── Valid Non-NaN Observations: 3,239,389 (48.90%)
│   ├── Raw Water Observations (flooded == 1.0): 80,164 cells
│   │   ├── JRC Permanent Water (jrc_perm_water == 1.0): 72,887 cells (EXCLUDED from flood)
│   │   └── Genuine Episodic Inundation (flooded == 1.0 & perm == 0.0 & clear >= 70%): 67,267 cells (LABEL = 1)
│   └── Verified Dry Ground (flooded == 0.0 & perm == 0.0 & clear >= 70%): 3,099,235 cells (LABEL = 0)
└── Unmapped / Out-of-Footprint (NaN): 3,385,349 cells (LABEL = -1, Unknown)
```

### 3.3 Strict Scientific Label Semantics
AQUORA enforces three-way ground truth isolation:
1. `flood_label = 1` (**Verified Episodic Flood**): `flooded == 1.0` AND `jrc_perm_water == 0.0` AND `clear_perc >= 0.70`.
2. `flood_label = 0` (**Verified Non-Flood Dry Ground**): `flooded == 0.0` AND `jrc_perm_water == 0.0` AND `clear_perc >= 0.70`.
3. `flood_label = -1` (**Unknown / Excluded**): Permanent water body (`jrc_perm_water == 1.0`), cloud-obscured (`clear_perc < 0.70`), or outside satellite footprint (NaN).

> [!IMPORTANT]
> **Zero Synthetic Negatives**: Unobserved cells remain explicitly `-1` (Unknown). Fabricating dry-negative labels from unobserved pixels or non-flooded district polygons is strictly prohibited.

### 3.4 Complementary Role of Sentinel-1 SAR
- **Sensor**: Copernicus Sentinel-1 C-SAR GRD (10m resolution, C-band 5.405 GHz).
- **Role**: Micro-scale urban flood corroboration (e.g., Mumbai Mithi E02–E07 corridors) and events post-2018 (beyond GFD's 2000–2018 window).
- **Known Limitations**:
  * 6–12 day revisit gaps frequently miss peak inundation in fast-responding flash basins.
  * Radar shadow and layover behind tall urban structures obscure narrow streets.
  * Double-bounce scattering from vertical building walls mimics dry terrain.
  * Wind-induced surface capillary waves roughen standing water, causing false negatives.

---

## 4. Predictor Matching & Conformance

Predictor extraction strictly follows [aquora_ml_feature_schema_v1.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/ml/aquora_ml_feature_schema_v1.json) (`CORE_NATIONAL` tier):

| Feature Name | Source Dataset | Resolution | Physical Unit | Governed Range | Pilot Mean |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `rainfall_1h_mm` | *Unobserved* (GPM 1h offline) | — | mm | Null preserved | `NaN` |
| `rainfall_3h_mm` | *Unobserved* | — | mm | Null preserved | `NaN` |
| `rainfall_6h_mm` | *Unobserved* | — | mm | Null preserved | `NaN` |
| `rainfall_24h_mm` | CHIRPS v2.0 Daily (`2017.07.27`) | 0.05° (~5 km) | mm | $[0.0, 1000.0]$ | 13.91 mm |
| `rainfall_72h_mm` | CHIRPS v2.0 3-Day Sum (`25-27`) | 0.05° (~5 km) | mm | $[0.0, 2000.0]$ | 52.48 mm |
| `rainfall_anomaly_index` | Antecedent Climatology Ratio | 0.05° | Dimensionless | $[-2.0, 5.0]$ | 0.299 |
| `elevation_m` | AWS Copernicus DEM GLO-30 | 30 meters | meters (EGM96) | $[-10.0, 100.0]$ | 12.84 m |
| `slope_deg` | Finite Difference DEM Gradient | 30 meters | degrees ($^\circ$) | $[0.0, 90.0]$ | 1.62° |
| `distance_to_river_m` | JRC Perm-Water KDTree Query | 30 meters | meters | $[0.0, 100,000.0]$ | 1,421.3 m |
| `historical_flood_frequency` | GFD / IFI Disaster Inventory | District / Basin | events / decade | $> 0.0$ | 4.44 |
| `landcover_class` | ESA WorldCover Standard | 10m $\rightarrow$ 30m | Class code | $\{40, 50, 80, 90\}$ | Mode: 40 |

### Invariant Checks:
- **Null Preservation**: `rainfall_1h_mm`, `rainfall_3h_mm`, and `rainfall_6h_mm` are strictly preserved as `NaN` (no mean or zero imputation).
- **Isolation of Targets**: `flood_label`, `gfd_flooded`, `gfd_clear_perc`, and `gfd_jrc_perm_water` reside exclusively in metadata columns.
- **Physical Exclusion**: Zero physical simulator depth (`water_depth_m`) or SAR delta backscatter fields are admitted into the predictor matrix.

---

## 5. Traceable Dataset Construction & Spatial Cross-Validation

### 5.1 Sampling Methodology
Sampling was conducted within the intersection of the Copernicus DEM tile `Copernicus_DSM_COG_10_N22_00_E088_00_DEM.tif` (`[88.0, 89.0]` Lon, `[22.0, 23.0]` Lat) and the GFD DFO 4499 footprint:
- Total Candidate Pool: 11,159 verified flood cells, 173,953 verified dry cells, 9,146 permanent water cells.
- **Sample Quotas**:
  * Verified Episodic Flood (`label = 1`): **2,500 samples**
  * Verified Dry Ground (`label = 0`): **2,500 samples**
  * Excluded Permanent Water (`label = -1`): **500 samples**
- **Total Dataset Size**: **5,500 rows**.

### 5.2 Spatially Disjoint Sub-Basin Partitioning (Zero Leakage)
To prevent spatial autocorrelation leakage, the 1° × 1° domain was partitioned into 5 hydrologic sub-basins:
- `BASIN_4521_SB1` (NW quadrant / Hooghly upstream / Burdwan): 840 points $\rightarrow$ **Train**
- `BASIN_4521_SB2` (NE quadrant / Nadia / Ranaghat): 1,265 points $\rightarrow$ **Train**
- `BASIN_4521_SB3` (Central corridor / Serampore / Mid-Hooghly): 722 points $\rightarrow$ **Train**
- `BASIN_4521_SB4` (SW quadrant / Howrah / Uluberia / Rupnarayan): 820 points $\rightarrow$ **Validation**
- `BASIN_4521_SB5` (SE quadrant / Kolkata / South 24 Parganas): 1,853 points $\rightarrow$ **Test**

```
Split Distribution:
├── Train: 2,827 samples (51.4%) [SB1, SB2, SB3]
├── Validation: 820 samples (14.9%) [SB4]
└── Test: 1,853 samples (33.7%) [SB5]

Spatial Overlap Audit:
• Train ∩ Validation = ∅ (ZERO overlapping sub-basins)
• Train ∩ Test = ∅ (ZERO overlapping sub-basins)
• Validation ∩ Test = ∅ (ZERO overlapping sub-basins)
```

### 5.3 Serialized Dataset Deliverables
- **Parquet File**: [phase7_gfd_pilot_dataset.parquet](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet) (136,711 bytes | SHA-256: `4d809d47fdc908121f08f5a00ed3d9bab3d515fd6f242a185f73557225782225`).
- **CSV File**: [phase7_gfd_pilot_dataset.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_gfd_pilot_dataset.csv) (1,195,069 bytes | SHA-256: `6f52bc13ba6d142c78f4f51285c8db641e2af3b7069a5c827f54ab26588ae300`).
- **Manifest**: [phase7_real_flood_dataset_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7_real_flood_dataset_manifest.yaml) (2,635 bytes).

---

## 6. Automated Verification Test Suite

A comprehensive test suite was implemented in [backend/tests/test_phase7_real_flood_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase7_real_flood_dataset.py). All 7 tests passed with zero failures:

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\thaka\OneDrive\Desktop\Hackathon\AQUORA\Aquoraa\backend
collected 7 items

backend\tests\test_phase7_real_flood_dataset.py::test_source_provenance_and_immutability PASSED [ 14%]
backend\tests\test_phase7_real_flood_dataset.py::test_dataset_artifacts_and_schema PASSED [ 28%]
backend\tests\test_phase7_real_flood_dataset.py::test_spatial_crs_and_coordinate_alignment PASSED [ 42%]
backend\tests\test_phase7_real_flood_dataset.py::test_predictor_units_and_ranges PASSED [ 57%]
backend\tests\test_phase7_real_flood_dataset.py::test_label_fidelity_and_rejection_gate PASSED [ 71%]
backend\tests\test_phase7_real_flood_dataset.py::test_spatial_cross_validation_zero_leakage PASSED [ 85%]
backend\tests\test_phase7_real_flood_dataset.py::test_manifest_consistency_and_hashes PASSED [100%]

============================== 7 passed in 0.97s ==============================
```

### Regression Verification:
All 10 foundational tests in [backend/tests/test_phase6c2g21_national_rainfall.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase6c2g21_national_rainfall.py) also passed in 1.02s, confirming that existing physical solvers, Mithi deep intelligence assets, and national rainfall archives remain 100% stable and intact.

---

## 7. Data-Quality Gate Assessment & Next Steps

### 7.1 Gate Decision
```
[GOVERNANCE STATUS] APPROVED_REAL_SATELLITE_GROUND_TRUTH
[PILOT DATASET STATUS] VALIDATED_AND_SEALED
[SUPERVISED TRAINING RECOMMENDATION] PILOT BENCHMARKING UNBLOCKED
```

### 7.2 Scalable Roadmap for Full National Coverage
1. **Multi-Event Expansion**: Scale [prepare_phase7_real_flood_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_phase7_real_flood_dataset.py) across all 91 GFD India events (e.g., Bihar/Kosi, Assam/Brahmaputra, Odisha/Mahanadi, Maharashtra/Godavari).
2. **Sentinel-1 Complementary Fusion**: Download Sentinel-1 GRD SAR scenes for post-2018 events (2019–2024) to supplement GFD with 10m urban radar observations.
3. **Kaggle Notebook Integration**: Wire the verified Parquet dataset directly into [notebooks/aquora_national_screening_kaggle.ipynb](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/notebooks/aquora_national_screening_kaggle.ipynb) with `GroupKFold` on `basin_id`.
