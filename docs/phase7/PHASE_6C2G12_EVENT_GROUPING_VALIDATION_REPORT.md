# AQUORA — Phase 6C.2G.12: Event Grouping Validation & Rainfall Analysis Readiness Audit Report

## 1. Executive Summary & Auditable Final Decision

**Final Decision:** `GROUPING_VALIDATED_FOR_DESCRIPTIVE_USE`

### Justification & Epistemological Boundaries
- **Grouping Validation**: The Phase 6C.2G.11 provisional event grouping of **6,876 raw IFI records** into **6,484 analytical storm groups** is mathematically reconciled, deterministic, and validated for **descriptive national/regional statistical summaries**.
- **Crucial Clarification on Terminology**: The identifier `storm_id` (or `provisional_group_id`) represents an **analytical convenience grouping** based on exact district string continuity and temporal adjacency ($\le 1.0$ day gap), **not a physically verified meteorological atmospheric storm boundary**.
- **Grouping Sensitivity Bounds**:
  - *Stricter Policy* (Same-day exact duplicates only): **6,803 groups** (merges only identical-date, identical-district reports).
  - *Baseline Policy* (Phase 6C.2G.11 provisional rule): **6,484 groups** (merges same-day duplicates plus consecutive-day slices with identical district strings).
  - *Looser Policy* (State + Any Overlapping District + $\le 1.0$ day gap): **6,109 groups** (merges multi-district regional monsoon systems where adjacent districts report on consecutive days).
- **Date Anomaly Audit**: Exactly **37 records (0.54%)** are date-compromised: **20 missing start dates** and **17 source tabular format inversions** (MM-DD-YYYY swaps in IMD publications). Raw date strings were preserved unmodified, and all 37 records are explicitly flagged to ensure exclusion from strict chronological time-series modeling.
- **Rainfall Comparison Readiness**:
  - The historical comparisons for **Event E03** (221.78 mm IMERG / 375.2 mm Santacruz gauge) and **Event E02** (243.6 mm IMERG) are **fully reproducible from local files**.
  - **National Rainfall Analysis Status: BLOCKED PENDING DATA ACQUISITION**. Two urban case studies in Mumbai cannot define nationwide precipitation-trigger baselines. For the remaining 6,874 national events, rainfall data is cataloged as `NOT_LOCALLY_ACQUIRED`. Zero-filling and synthetic imputation remain strictly prohibited.
- **Supervised Training Safeguards**: **Supervised ML training at the 30m grid scale remains strictly prohibited** (`supervised_training_permitted: false`). Zero models were trained, and no synthetic labels were created.

---

## 2. Preservation of Existing Assets

All foundational assets were cryptographically audited before and after this phase and remain untouched:

| Asset | Local File Path | SHA-256 Checksum | Status |
| :--- | :--- | :--- | :--- |
| **Raw IFI Dataset** | `data/raw/phase7/ground_truth/india_flood_inventory_v3.csv` | `ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108` | **VERIFIED UNMODIFIED** |
| **Raw Copernicus DSM** | `data/raw/phase7/dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif` | `b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd` | **VERIFIED UNMODIFIED** |
| **Working Study DEM** | `data/processed/phase7/terrain/elevation_30m_study_extent.tif` | `25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda` | **VERIFIED UNMODIFIED** |

---

## 3. Audit of Event Grouping

### 3.1 Mathematical Reconciliation
- Total raw source records: **6,876**
- Unique source `UEI` identifiers: **6,876** (100% preservation; zero records dropped)
- Derived records in `national_historical_flood_records_derived.parquet`: **6,876**
- Unique provisional storm groups (`storm_id`): **6,484**
- Merged surplus records: **392**
- Sum of constituent record counts in `national_storm_events_grouped.parquet`: **6,876**
- **Reconciliation Formula**:
  $$\text{Provisional Groups (6,484)} + \text{Merged Records (392)} = \text{Raw Records (6,876)}$$

### 3.2 Multi-Record Group Taxonomy
Of the 6,484 provisional groups, 6,260 are single-record events, and **224 are multi-record groups** (aggregating 616 records):
1. **Same-Day Duplicates / Sub-Incidents** (**24 groups**): Multiple reports issued by IMD for the exact same date and exact same district string (e.g. separate casualty updates or sub-divisional incident reports).
2. **Consecutive-Day Slices** (**187 groups**): Slices of multi-day storms where identical district strings report on consecutive days ($\le 1.0$ day gap).
3. **Mixed Duplicates & Slices** (**13 groups**): Sequences containing both same-day duplicates and consecutive-day updates.

### 3.3 Grouping Sensitivity & Policy Bounds

```
Grouping Policy                                Group Count   Merged Records   Description
---------------------------------------------------------------------------------------------------------------------------------
Zero-Merging Raw Baseline                            6,876                0   Every administrative record treated as an isolated event.
Stricter Policy (Same-Day Duplicates Only)           6,803               73   Merges only records sharing identical date and district string.
Baseline Policy (Phase 6C.2G.11 Provisional Rule)    6,484              392   Merges same-day duplicates + consecutive slices (exact district).
Looser Policy (State + Overlapping District + 1-day) 6,109              767   Merges multi-district monsoon systems across adjacent days.
```

### 3.4 Case Study: Mumbai Event E03 (July 1–2, 2019)
- **Record 1 (`UEI-IMD-FL-2019-0090`)**: Date: `07-01-2019`, Districts: `Mumbai, Nashik, Palghar, Pune` $\to$ Assigned `STORM-MAH-2019-03986`.
- **Record 2 (`UEI-IMD-FL-2019-0091`)**: Date: `07-02-2019`, Districts: ` Mumbai,Thane,Ratnagiri` $\to$ Assigned `STORM-MAH-2019-04012`.
- *Finding*: Under the Phase 6C.2G.11 baseline rule, these two consecutive days received **different provisional storm IDs** because the reported district strings were not identical. Under the Looser Policy (which tests for set intersection of districts), they merge into a single regional storm event.
- *Preservation*: As mandated, alternative grouping policies are preserved as audit outputs, while the baseline derived tables remain unmodified.

---

## 4. Audit of Date Anomalies

### 4.1 Missing Start Dates (20 Records)
- **Breakdown**:
  - 1 historical record from 2001 (`UEI-IMD-FL-2001-0043`, Karnataka).
  - 11 records from 2023 in Madhya Pradesh where primary IMD cause states: `"updated report not yet received"`.
  - 8 records from 2023 (1 in Maharashtra, 7 in Odisha) sourced from email notifications where tabular dates were omitted.
- **Handling**: All 20 records are flagged with `is_missing_date = True` and assigned isolated undated storm IDs (`STORM-***-UNDATED-****`).

### 4.2 Source Date Format Inversions (17 Records)
- **Breakdown**: In 17 records from 2017–2020, the original IMD source swapped day and month fields in the tabular text:
  - Example: `UEI-IMD-FL-2019-0002` (Assam): `Start: 07-10-2019`, `End: 29-07-2019`, `Duration: 20 days` (July 10 to July 29 is exactly 20 days).
  - Example: `UEI-IMD-FL-2017-0009` (Assam): `Start: 07-09-2017`, `End: 13-07-2017`, `Duration: 5 days` (July 9 to July 13 is exactly 5 days).
  - Example: `UEI-IMD-FL-2017-0029` (HP): `Start: 08-06-2018`, `End: 08-07-2017`, `Duration: 2 days` (Typo in source year: 2018 instead of 2017).
- **Rule Enforced**: Raw date strings are **never overwritten or silently swapped**. All 17 records are explicitly flagged with `is_date_inverted_in_source = True`.
- **Exclusion Safeguard**: The **37 date-compromised records (0.54%)** must be strictly excluded from any automated model requiring chronological time-series ordering. 6,839 records are fully validated for strict chronological analysis.

---

## 5. Audit of Summary Statistics

- **Denominators**: National shares use the strictly defined denominator of $N = 6,876$ total source records.
- **Fatality Aggregation**:
  - National reported fatalities sum to 78,895 across 1967–2023.
  - *Double-Counting Warning*: When multiple administrative records describe overlapping multi-district storms (e.g. 1973 multi-state monsoon deluge reporting 90 fatalities across 6 states), summing district-level fatalities without deduplication can introduce double counting. Fatality totals in summary tables must be interpreted as upper-bound administrative loss estimates.
- **Reporting Trend Context**:
  - Event records surged from ~100–150/year (1990–2020) to 338 in 2021, 1,138 in 2022, and 653 in 2023.
  - This trend is primarily driven by administrative digitization, local DDMA incident tracking, and expanded media monitoring—**not an uncritical 10-fold increase in physical cloudburst frequency**.

---

## 6. Audit of Rainfall Comparison Readiness

### 6.1 Benchmark Event E03 (July 1–2, 2019)
- **Local Assets Verified**: 48 half-hourly granules of NASA GPM IMERG Final V07B HDF5 in `data/raw/phase7/rainfall/imerg/final/2019/07/`.
- **Observation Window**: `2019-07-01T03:00:00Z` to `2019-07-02T03:00:00Z` (24.0 hours, corresponding to 08:30 IST 1 July to 08:30 IST 2 July).
- **Variable**: `precipitation` (Units: mm/hr; `_FillValue = -9999.9`; completeness ratio = 1.0).
- **Spatial Aggregation**: Area-averaged across study extent bounding box ($[72.75, 73.05]^\circ\text{E}, [18.95, 19.30]^\circ\text{N}$).
- **Calculated Accumulation**: **221.78 mm**.
- **Gauge Comparison**: IMD Santacruz observatory gauge reported **375.2 mm** over the identical 24-hour observation window.
  - *Discrepancy Explanation*: Santacruz is a single point gauge, while IMERG is a 10 km areal grid average. Convective rainfall peaks are naturally smoothed in 100 sq km satellite pixels.
- **Reproducibility Status**: **FULLY REPRODUCIBLE FROM LOCAL FILES**.

### 6.2 Benchmark Event E02 (August 29–30, 2017)
- **Local Assets Verified**: 0.1° native GeoTIFF, 30m resampled raster, and metadata JSON in `data/processed/phase7/rainfall/`.
- **Observation Window**: 2017-08-29 (24-hour total accumulation).
- **Calculated Mean Depth**: **243.6 mm**.
- **Reproducibility Status**: **FULLY REPRODUCIBLE FROM LOCAL FILES**.

### 6.3 Scientific Boundaries on National Rainfall Trigger Analysis
1. **Sample Size Constraint**: Two urban deluge case studies in Mumbai (E02 and E03) cannot establish nationwide precipitation-trigger thresholds or fragility curves.
2. **Missing Local Data**: For the remaining 6,874 national events, IMERG granules have not been locally acquired. They are cataloged as `NOT_LOCALLY_ACQUIRED`.
3. **Prohibition on Zero-Filling**: Missing satellite rainfall data must strictly remain NULL (never zero-filled).
4. **National Trigger Analysis Readiness**: **BLOCKED PENDING NATIONAL RAINFALL ACQUISITION**. Macro-scale rainfall-trigger analysis across India cannot proceed responsibly until authentic gridded rainfall series are acquired for evaluated national events.

---

## 7. Deliverables Created & Test Results

1. **Audit Pipeline Script**: [`audit_phase6c2g12_event_grouping.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/audit_phase6c2g12_event_grouping.py)
2. **Grouping Audit JSON**: [`phase6c2g12_grouping_audit.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/phase6c2g12_grouping_audit.json)
3. **Date Quality Audit JSON**: [`phase6c2g12_date_quality_audit.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/phase6c2g12_date_quality_audit.json)
4. **Rainfall Readiness Audit JSON**: [`phase6c2g12_rainfall_readiness.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/phase6c2g12_rainfall_readiness.json)
5. **Phase 6C.2G.12 Manifest**: [`phase6c2g12_validation_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase6c2g12_validation_manifest.yaml)
6. **Automated Test Suite**: [`test_phase6c2g12_event_grouping.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase6c2g12_event_grouping.py)
7. **Phase Report**: [`PHASE_6C2G12_EVENT_GROUPING_VALIDATION_REPORT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_6C2G12_EVENT_GROUPING_VALIDATION_REPORT.md)

### Automated Test Execution
- **Focused Phase 6C.2G.12 Suite**:
  ```powershell
  backend\.venv\Scripts\python.exe -m pytest backend\tests\test_phase6c2g12_event_grouping.py -v
  ```
  *Result*: **8 passed in 0.28s** (Exit code 0).
- **Full Phase 6C Regression Suite (All 19 Test Modules)**:
  ```powershell
  backend\.venv\Scripts\python.exe -m pytest (Get-ChildItem -Path backend\tests\test_phase6c*.py).FullName -q
  ```
  *Result*: **137 passed in 35.31s** (Exit code 0, 100% pass rate).

---

## 8. Recommended Next Phase

1. **National Rainfall Data Acquisition Strategy**: To enable defensible national rainfall-trigger modeling, formulate an acquisition strategy for daily gridded precipitation (e.g. IMD 0.25° gridded daily rainfall or NASA IMERG Daily V07B) for evaluated event dates and districts.
2. **Deep Zone Hydraulic Benchmark**: For Mumbai/Mithi, proceed with hydraulic calibration of Event E03 utilizing the verified 221.78 mm IMERG input and Santacruz gauge benchmark, maintaining strict isolation from unverified national extrapolations.
3. **Preserve Supervised Training Block**: Maintain the strict block on supervised 30m ML training until street-scale inundation vectors and verified negative observations are acquired.
