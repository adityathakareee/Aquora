# AQUORA — Phase 6C.2G.10: Ground-Truth Validation and Training Dataset Feasibility Report

## 1. Executive Summary & Governance Decision

**Final Decision:** `EVENT_LEVEL_ANALYSIS_FEASIBLE`

- **Core Finding**: The acquired peer-reviewed **India Flood Inventory (IFI v3)** (IIT Delhi / IMD / NCAR) contains **6,876 verified disaster records** across India (1967–2023), including 1,017 in Maharashtra and 182 in Mumbai. These records provide authentic, independently documented disaster occurrences, dates, primary causes, and casualty figures that **genuinely support macro-scale event-level analysis, district hazard frequency baselines, and regional precipitation validation**.
- **Critical Spatial & Epistemological Boundaries**:
  1. **Coordinate Absence**: Coordinates (`Latitude` and `Longitude`) and specific `Location` fields in IFI are **100% NaN (6,876 out of 6,876 records)**. The dataset operates strictly at administrative State and District levels (with Local Government Directory codes for 6,572 rows). It contains zero 30-metre pixel coordinates and zero inundation boundary polygons.
  2. **DFO Masterlist Temporal Cutoff**: The Dartmouth Flood Observatory masterlist shapefile is 100% point centroids (zero polygons) and its historical records **cut off in August 2010**. It contains **zero records for Event E02 (2017) or Event E03 (2019)**.
  3. **The Negative-Sampling Gap**: Both IFI and DFO are disaster damage registers. They document where severe harm occurred; they **never record confirmed dry ground**. Treating an unlisted district or cell as "dry" introduces severe false-negative bias.
  4. **Strict Prohibition on District-to-Pixel Broadcasting**: A district-level positive label cannot be broadcast to every 30m grid cell in that district. Assigning $y=1$ across Mumbai would falsely classify the 450m elevated ridges of Sanjay Gandhi National Park as flooded, creating catastrophic label error.
- **Supervised Training Decision**: **Supervised training at the 30m grid scale for the Mithi River catchment remains STRICTLY BLOCKED** (`pixel_level_supervised_training_permitted: false`). Zero models were trained, and no synthetic labels were created.

---

## 2. File Verification & Checksum Audit

Both ground-truth datasets were audited locally on disk. File sizes and SHA-256 hashes match the Phase 6C.2G.9 acquisition manifest with 100% byte fidelity:

| Dataset | Relative Path | File Size (Bytes) | SHA-256 Checksum | Match with 6C.2G.9 | Provider & License |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **India Flood Inventory v3** | `data/raw/phase7/ground_truth/india_flood_inventory_v3.csv` | 1,801,579 | `ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108` | **VERIFIED MATCH** | IIT Delhi / IMD / NCAR<br>Zenodo DOI: `10.5281/zenodo.4742142`<br>License: CC-BY-4.0 |
| **DFO Global Masterlist** | `data/raw/phase7/ground_truth/dfo_masterlist_20190418.zip` | 610,578 | `976f0904c603ba31e8aa62f6d1b55cec4c153be783495593ed247d01629ffe09` | **VERIFIED MATCH** | Dartmouth Flood Observatory / WFP / HDX<br>License: Open Public Domain |

### Source DEM Immutability Audit
- **Raw Copernicus 30m DSM**: `b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd` (**VERIFIED UNMODIFIED**)
- **Working Study Extent DEM**: `25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda` (**VERIFIED UNMODIFIED**)

---

## 3. Schema, Missing Value, and Precision Audits

### 3.1 India Flood Inventory (IFI v3) Schema Audit
- **Structure**: 6,876 rows $\times$ 23 columns.
- **100% Missing Attribute Columns**:
  - `Latitude`: 6,876 missing (100% NaN).
  - `Longitude`: 6,876 missing (100% NaN).
  - `Location`: 6,876 missing (100% NaN).
  - `Severity`: 6,876 missing (100% NaN).
  - `Area Affected`: 6,876 missing (100% NaN).
  - `Event Souce ID`: 6,876 missing (100% NaN).
- **Date Parsing Audit**:
  - `Start Date`: 6,856 non-null entries parse deterministically under `%d-%m-%Y %H:%M` (0 parse errors). 20 entries are null (late 2023 unconfirmed reports).
  - `Temporal Range`: `1967-07-02` to `2023-09-12`.
  - `Duration(Days)`: Mean 3.61 days. 4,172 records (60.84%) are single-day entries (`Duration = 1.0`).
- **Geographic Precision**:
  - `State`: 82 distinct state/UT strings (0 missing).
  - `Districts`: 6,817 populated rows (59 missing), formatted as comma-separated lists.
  - `District_LGD_Codes`: 6,572 populated rows (304 missing) providing standard Local Government Directory identifiers.
- **Source Homogeneity**:
  - `Event Source`: 100% of all 6,876 records are compiled from India Meteorological Department (IMD) annual *Disastrous Weather Events* (DWE) reports.

### 3.2 Dartmouth Flood Observatory (DFO) Audit
- **Structure**: ESRI Shapefile with 4,029 features in `EPSG:4326`.
- **Geometry Type**: **100% Point** (all 4,029 features are point centroids; zero polygons exist).
- **Temporal Cutoff**: The historical registry begins on `1985-01-01` and **ends on `2010-08-10`**.
- **Event Coverage Limitation**: DFO contains **zero records for 2017 or 2019**. It cannot provide corroboration for AQUORA's target benchmark events E02 and E03.
- **Spatial Precision**: Points are regional centroids. 188 records mention India, of which 18 mention Mumbai/Maharashtra (between 1985 and 2007). Many older records set `Centroid_X = 0.0, Centroid_Y = 0.0`.

---

## 4. Historical Event Validation & Overlap Audit

AQUORA's benchmark historical rainfall events were validated against the primary IFI records:

### 4.1 Event E03 (Mumbai Deluge: July 1–2, 2019)
- **IFI Record 1**: `UEI-IMD-FL-2019-0090`
  - *Date*: `07-01-2019 00:00` | *Duration*: 1.0 day
  - *Districts*: Mumbai, Nashik, Palghar, Pune | *State*: Maharashtra
  - *Cause*: Heavy rains | *Human Fatalities*: 12.0
- **IFI Record 2**: `UEI-IMD-FL-2019-0091`
  - *Date*: `07-02-2019 00:00` | *Duration*: 1.0 day
  - *Districts*: Mumbai, Thane, Ratnagiri | *State*: Maharashtra
  - *Cause*: Heavy rains, Incessant rains leading to flood-like situation | *Human Fatalities*: 45.0
  - *Documented Damage Details*:
    > "i) A wall collapsed on hutments in Pimpripada area of Malad East. ii) About 1,000 people shifted to temporary shelters by joint evacuation operation in suburban Kurla with the NDRF, Navy, fire brigade shifting. iii) Many parts of the financial capital Mumbai waterlogged. iv) Rail, Air, Road traffic disrupted with several trains, flights cancelled. Altogether 54 flights diverted, 52 cancelled at Mumbai's Chhatrapati Shivaji Maharaj International Airport... Tiware Dam in Chiplun block of Ratnagiri District breached."

#### Non-Independence & Overlap Safeguard
Records `UEI-IMD-FL-2019-0090` (July 1) and `UEI-IMD-FL-2019-0091` (July 2) are **not independent events**. They represent consecutive daily reporting slices of the same 48-hour continuous monsoon cloudburst, published in the same IMD DWE report. **Treating them as independent samples across train/test splits would cause severe temporal data leakage.** Grouping by storm event window is mandatory.

### 4.2 Event E02 (Mumbai Deluge: August 29–30, 2017)
- **IFI Record 1**: `UEI-IMD-FL-2017-0088` (2017-08-29, Thane, Heavy Rains; 2 fatalities; "Rail, air, road transport affected in Mumbai").
- **IFI Record 2**: `UEI-IMD-FL-2017-0089` (2017-08-30, Palghar, Thane, Mumbai, Heavy Rains; 15 fatalities).
- Consecutive single-day slices of the same August 2017 regional storm.

---

## 5. Geographic Scale Applicability Assessment

| Administrative / Hydrological Tier | Usability Assessment | Supported Analytical Task |
| :--- | :--- | :--- |
| **NATIONAL** | **USABLE FOR MACRO ANALYSIS** | Macro-scale disaster frequency analysis, national hazard recurrence baselines, and multi-decadal trends across India (6,876 records across 36 States/UTs). |
| **STATE** | **USABLE FOR STATE SCREENING** | Comparative multi-district vulnerability ranking across Maharashtra (1,017 records). |
| **DISTRICT** | **USABLE FOR DISTRICT BENCHMARKING** | District-level historical flood incidence modeling (182 records in Mumbai; 6,572 records with LGD codes). |
| **BASIN** | **PARTIALLY USABLE** | Can be mapped to HydroBASINS Level 5/6/7 units via spatial overlay with district boundaries, subject to boundary attribution error. |
| **LOCAL MITHI DEEP ZONE (30m)** | **COMPLETELY UNUSABLE** | **Incompatible**. District-level event records cannot resolve 30m grid cells. Assigning $y=1$ across Mumbai would falsely label dry ridges and hilltops as flooded. |

### Critical Safeguard Rules Enforced
1. **No District-to-Pixel Broadcasting**: Never broadcast a district-level event label to 30m raster grid cells.
2. **No Centroid-to-Polygon Synthesis**: Never convert DFO point centroids into synthetic flood inundation polygons.
3. **No Naive Absence as Negative**: Never treat the absence of a disaster report as evidence of dry ground.

---

## 6. Training Feasibility & Feature Schema Alignment

Comparison against `ml/aquora_ml_feature_schema_v1.json` and `phase6c2g8_training_dataset_spec.json`:

```
+-----------------------------------------------------------------------------------------+
| Feature / Label Component          | Authentic Source Available? | Feasibility Status   |
+------------------------------------+-----------------------------+----------------------+
| Terrain Features (8 Core features) | YES (Copernicus DSM, 30m)   | USABLE               |
| Rainfall Features (3 IMERG Core)   | YES (NASA GPM IMERG V07B)   | USABLE               |
| SAR Features (Backscatter / Coher) | YES (Sentinel-1A IW GRDH)   | OBSERVATION ONLY     |
| Flood Positive Labels (30m pixel)  | NO (District scale only)    | UNAVAILABLE (0 cells)|
| Flood Negative Labels (30m pixel)  | NO (Incident bias barrier)  | UNAVAILABLE (0 cells)|
+-----------------------------------------------------------------------------------------+
```

### Analytical Feasibility Matrix
- **Event-Level National Analysis**: **FEASIBLE**.
  - Historical flood frequency screening by district.
  - Empirical correlation of IMERG satellite precipitation extremes against documented flood dates.
  - Multi-decadal casualty and disruption impact trends across Indian states.
- **Pixel-Level Supervised Training**: **STRICTLY BLOCKED**.
  - Supervised binary classification requires both verified positive ($y=1$) and verified negative ($y=0$) samples at the model's native spatial resolution (30m).
  - Neither exists in the acquired inventory.

---

## 7. Automated Test Suite & Regression Verification

### 7.1 Focused Phase 6C.2G.10 Test Suite
Executed test suite [`backend/tests/test_phase6c2g10_validation.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase6c2g10_validation.py):
```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_phase6c2g10_validation.py -v
```
**Results: 8 passed in 1.15s** (Exit code 0):
- `test_source_dem_immutability`: PASSED
- `test_file_integrity_and_manifest_hash_match`: PASSED
- `test_ifi_schema_and_coordinate_gap`: PASSED
- `test_dfo_schema_and_temporal_cutoff`: PASSED
- `test_event_records_validation_and_overlap_safeguards`: PASSED
- `test_geographic_applicability_safeguards`: PASSED
- `test_training_feasibility_decision_and_governance`: PASSED
- `test_safety_and_schema_preservation`: PASSED

### 7.2 Full Phase 6C Test Regressions
Executed all Phase 6C test suites:
```powershell
backend\.venv\Scripts\python.exe -m pytest (Get-ChildItem -Path backend\tests\test_phase6c*.py).FullName -q
```
**Results: 120 passed in 34.61s** (Exit code 0, 100% clean across all 17 test modules).

---

## 8. Deliverables & Artifact Inventory

1. **Validation Script**: [`scripts/validate_phase6c2g10_ground_truth.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/validate_phase6c2g10_ground_truth.py)
2. **Validation Assessment JSON**: [`data/processed/phase7/ml/phase6c2g10_validation_assessment.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase6c2g10_validation_assessment.json)
3. **Updated Label Provenance JSON**: [`data/processed/phase7/ml/phase6c2g10_label_provenance.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase6c2g10_label_provenance.json)
4. **Validation Manifest**: [`data/manifests/phase6c2g10_validation_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase6c2g10_validation_manifest.yaml)
5. **Phase Report**: [`docs/phase7/PHASE_6C2G10_VALIDATION_REPORT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_6C2G10_VALIDATION_REPORT.md)
6. **Automated Test Suite**: [`backend/tests/test_phase6c2g10_validation.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase6c2g10_validation.py)

---

## 9. Recommended Next Phase

**Recommended Next Step:**
1. **National Event-Level Susceptibility Screening**: Utilize the 6,876 authentic IFI records to build an event-level district hazard frequency and rainfall-trigger validation baseline (macro-scale, non-pixel).
2. **Local Deep Zone Ground Truth**: Maintain the strict block on supervised 30m training in the Mithi River catchment until authentic street-level inundation vectors (e.g., MCGM Ward waterlogging surveys or validated high-resolution optical deluge masks) and defensible negative operational ground-truth observations are acquired.
