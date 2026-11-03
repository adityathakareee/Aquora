# AQUORA — Phase 6C.2G.11: National Historical Event Analysis Report

## 1. Executive Summary & Auditable Final Decision

**Final Decision:** `EVENT_ANALYSIS_READY`

### Justification
- **What Was Built & Verified**: A reproducible, non-ML descriptive national historical flood-event analysis has been successfully constructed from the peer-reviewed **India Flood Inventory (IFI v3)** (IIT Delhi / IMD / NCAR; Zenodo DOI: `10.5281/zenodo.4742142`).
- **Event Grouping & Data Integrity**:
  - The raw inventory containing **6,876 daily administrative records** was preserved with 100% byte fidelity (`india_flood_inventory_v3.csv` remains strictly read-only).
  - Multi-day monsoon storms previously fragmented into discrete single-day calendar slices by IMD's reporting conventions were aggregated into **6,484 unique meteorological storm events** (`storm_id`), merging 392 consecutive daily slices and multi-report entries while retaining 100% of constituent `UEI` identifiers and damage notes.
- **Reporting Bias Analysis**: The historical time series reveals pronounced administrative reporting evolution—surging from ~100–150 records/year in the 2000s to 1,138 in 2022. This report documents that this trend is driven by administrative digitization, lower damage reporting thresholds, and multi-agency compilation, rather than an uncritical 10-fold physical hazard increase.
- **Rainfall Comparison Boundaries**: Existing authentic NASA GPM IMERG Final V07B precipitation data validly corroborates benchmark deluges **Event E03** (July 1–2, 2019: 221.78 mm IMERG / 375.2 mm gauge) and **Event E02** (August 29–30, 2017). For the remaining 6,874 national events, rainfall data is cataloged as `NOT_LOCALLY_ACQUIRED`. Zero-filling, synthetic imputation, and claiming rainfall correlation as causation are strictly prohibited.
- **Supervised Training Safeguards**: **Supervised ML training at the 30m grid scale remains strictly prohibited** (`supervised_training_permitted: false`). District records are never broadcast to 30m raster grid cells. Zero models were trained, and no synthetic labels were created.

---

## 2. Dataset Preparation & Provenance Preservation

### 2.1 Raw Dataset Preservation
- **Path**: `data/raw/phase7/ground_truth/india_flood_inventory_v3.csv`
- **File Size**: 1,801,579 bytes
- **SHA-256**: `ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108` (**VERIFIED UNMODIFIED**)
- **Source**: IIT Delhi HydroSense Lab / IMD / NCAR (Zenodo record `16994648`, CC-BY 4.0).

### 2.2 Date Cleaning & Anomaly Audits
1. **Deterministic Parsing**:
   - `Start Date`: 6,856 non-null records parse deterministically under `%d-%m-%Y %H:%M` (0 parse errors).
   - `Missing Dates`: Exactly 20 records (0.29%) from late 2023 unconfirmed reports have null dates. They are explicitly flagged with `is_missing_date = True` and assigned isolated undated storm IDs to preserve reporting uncertainty.
2. **Source Date Format Inversions**:
   - Exactly 17 records from 2017–2019 had swapped day and month fields in the primary IMD text (e.g. `Start: 07-09-2017` for 9 July 2017 while `End: 13-07-2017` with `Duration: 5 days`).
   - Rather than silent alteration or deletion, these 17 records are flagged with `is_date_inverted_in_source = True` and preserved in the derived records dataset.
3. **Single-Day Reporting Slices**:
   - 4,172 records (60.84% of the raw inventory) possess `Duration(Days) = 1.0` due to IMD's convention of issuing single-day disaster situation updates during multi-day monsoon storms.

### 2.3 Event Grouping Methodology
- **Objective**: Aggregate fragmented daily reporting slices and duplicate district entries without force-merging unrelated meteorological storms.
- **Algorithm**:
  - Records are sorted deterministically by State, District corridor, Start Date, and UEI.
  - Where records within the same State and District corridor have $\le 1.0$ calendar day gap between previous end date and current start date, they are merged into a unified `storm_id` (e.g., `STORM-MAH-2019-04457`).
  - Gaps $>1.0$ day, differing states, or distinct non-adjacent administrative regions initiate new storm IDs.
- **Results**:
  - Raw records: **6,876**
  - Unique storm events: **6,484**
  - Consecutive daily slices / duplicate reports merged: **392**
  - All 6,876 original `UEI` strings are tracked and mapped 1-to-1 to their parent storm event.

---

## 3. Descriptive National & Regional Analysis

### 3.1 State-Level Distribution (Top 15 States)

| State | Raw Records | Unique Storms | Total Fatalities | Earliest Event | Latest Event | National Share (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Maharashtra** | 1,012 | 967 | 7,560 | 1969 | 2023 | 14.72% |
| **Assam** | 908 | 671 | 3,492 | 1967 | 2023 | 13.21% |
| **Kerala** | 604 | 592 | 2,387 | 1970 | 2023 | 8.78% |
| **Karnataka** | 492 | 485 | 2,584 | 1972 | 2023 | 7.16% |
| **Uttar Pradesh** | 448 | 437 | 8,474 | 1967 | 2023 | 6.52% |
| **Himachal Pradesh** | 362 | 344 | 2,032 | 1978 | 2023 | 5.26% |
| **West Bengal** | 333 | 331 | 5,238 | 1968 | 2023 | 4.84% |
| **Rajasthan** | 259 | 254 | 2,641 | 1973 | 2023 | 3.77% |
| **Madhya Pradesh** | 249 | 249 | 1,078 | 1973 | 2023 | 3.62% |
| **Tamil Nadu** | 188 | 186 | 2,291 | 1969 | 2022 | 2.73% |
| **Punjab** | 171 | 171 | 934 | 1976 | 2023 | 2.49% |
| **Gujarat** | 168 | 156 | 5,414 | 1968 | 2023 | 2.44% |
| **Bihar** | 154 | 154 | 4,720 | 1975 | 2023 | 2.24% |
| **Odisha** | 151 | 149 | 2,849 | 1970 | 2023 | 2.20% |
| **Arunachal Pradesh**| 150 | 139 | 442 | 1979 | 2023 | 2.18% |

### 3.2 Decadal Evolution & Reporting Coverage Bias

```
Decade     Raw Records   Grouped Storms   Total Fatalities   Context / Reporting Characteristics
------------------------------------------------------------------------------------------------------
1960s               22               22                  0   Catastrophic events only; fatalities unrecorded.
1970s              301              301             11,464   Major riverine floods; high mortality per event.
1980s              855              851             14,488   Expanding IMD network; multi-state monsoon events.
1990s            1,203            1,196             16,104   Systematic disaster documentation begins.
2000s            1,167            1,159             15,310   Stable reporting threshold; state DM cells form.
2010s            1,188            1,182             17,358   Includes Kedarnath (2013) & Kerala (2018).
2020s (4 yrs)    2,140            1,773              3,383   Surge: Digitization, DDMAs, media incident logs.
```

> [!WARNING]
> **Interpretation Warning on Reporting Bias**: The surge in event counts during 2021–2023 (1,138 records in 2022 alone) is **not physical proof of a 10-fold increase in meteorological storm frequency**. Rather, it reflects lower damage reporting thresholds, digital administrative monitoring, and localized waterlogging incident collection. Physical hazard trends must not be conflated with reporting intensity changes.

### 3.3 Mumbai Flood History Specifically (Deep Zone Benchmark)
- Total records referencing Mumbai: **182**
- Earliest documented flood: `1969-09-15` (`UEI-IMD-FL-1969-0008`)
- Latest documented flood: `2023-07-20` (`UEI-IMD-FL-2023-0259`)
- Key historical milestones documented in primary text:
  - **1974-07-05**: 58 cm rainfall in 24 hours at Colaba observatory; 50 fatalities; low-lying areas flooded.
  - **1980-08-21**: Dahisar and Poisor streams overflow; 45 fatalities; 600 rescued from rooftops.
  - **1984-07-02**: 54 cm rainfall in 24 hours; Sassoon dock choked with 500 trawlers.
  - **2005-07-26**: Maharashtra deluge; catastrophic suburban waterlogging.
  - **2017-08-29 (Event E02)**: Suburban rail and road transit halted.
  - **2019-07-01 to 07-02 (Event E03)**: Malad East wall collapse; Kurla evacuations by NDRF/Navy; runway overrun at airport; 45 fatalities.

---

## 4. Rainfall Comparison Feasibility Assessment

### 4.1 Valid Benchmark Comparisons

| Event ID | Time Window | Geographic Extent | Authentic IMERG Data Locally Available | Matched IFI Records | Comparison Feasibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Event E03** | 2019-07-01T03:00Z to 2019-07-02T03:00Z | Mumbai / Mithi River corridor | 48 half-hourly granules (HDF5); 221.78 mm total accumulation (375.2 mm Santacruz gauge) | `UEI-IMD-FL-2019-0090`, `UEI-IMD-FL-2019-0091` | **VALID BENCHMARK COMPARISON** |
| **Event E02** | 2017-08-29 (24-hour total) | Mumbai study extent | 0.1° native GeoTIFF, 30m resampled raster, metadata JSON | `UEI-IMD-FL-2017-0088`, `UEI-IMD-FL-2017-0089` | **VALID BENCHMARK COMPARISON** |

### 4.2 National Rainfall Comparison Boundaries
- **Unacquired National Events**: 6,874 out of 6,876 IFI events do not have local IMERG granules downloaded in the repository.
- **Strict Scientific Prohibitions Enforced**:
  1. *No Zero-Imputation*: Missing satellite rainfall data is **never treated as zero precipitation**, preventing false-drought attribution.
  2. *No Uncolocated Comparisons*: Satellite grid cells from unrelated dates or non-colocated basins are never compared against uncolocated flood records.
  3. *No Correlation as Causation*: A statistical correlation between regional rainfall and an administrative flood report is not claimed as physical hydraulic causation.
  4. *No Synthetic Rain Grids*: Historical rainfall fields are never fabricated or spatially interpolated for unacquired events.

---

## 5. Artifacts Created & Deliverables Registry

All derived datasets, summary tables, quality audits, and manifests have been generated deterministically:

| Deliverable Artifact | Relative File Path | Format / Size | Description |
| :--- | :--- | :--- | :--- |
| **Derived Records Table** | [`national_historical_flood_records_derived.parquet`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/national_historical_flood_records_derived.parquet) | Parquet (796.8 KB)<br>CSV (2.63 MB) | All 6,876 raw rows preserved with `storm_id`, parsed dates, and quality flags. |
| **Grouped Storms Table** | [`national_storm_events_grouped.parquet`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/national_storm_events_grouped.parquet) | Parquet (495.6 KB)<br>CSV (1.49 MB) | 6,484 aggregated meteorological storm events with constituent UEIs and dates. |
| **Annual Flood Frequency** | [`annual_flood_frequency.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/annual_flood_frequency.csv) | CSV (1.3 KB) | Annual summary from 1967 to 2023 (raw vs unique storm counts, fatalities). |
| **State Flood Summary** | [`state_flood_summary.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/state_flood_summary.csv) | CSV (4.4 KB) | State-by-state flood incidence, percentages, and mortality across India. |
| **District Flood Frequency** | [`top_districts_flood_frequency.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/top_districts_flood_frequency.csv) | CSV (214.8 KB) | District-level flood event rankings across all states. |
| **Mumbai Flood History** | [`mumbai_flood_history.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/mumbai_flood_history.csv) | CSV (87.2 KB) | Filtered historical records (182 rows) documenting Mumbai floods (1969–2023). |
| **Data Quality Report** | [`phase6c2g11_data_quality_report.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/phase6c2g11_data_quality_report.json) | JSON (2.0 KB) | Comprehensive audit of completeness, date inversions, and reporting biases. |
| **Rainfall Assessment** | [`phase6c2g11_rainfall_comparison_assessment.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/events/phase6c2g11_rainfall_comparison_assessment.json) | JSON (2.3 KB) | Rigorous evaluation of local IMERG assets and national comparison rules. |
| **Phase 6C.2G.11 Manifest** | [`phase6c2g11_national_event_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase6c2g11_national_event_manifest.yaml) | YAML (2.5 KB) | Machine-readable provenance manifest and governance invariants. |
| **Analysis Script** | [`analyze_phase6c2g11_national_events.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/analyze_phase6c2g11_national_events.py) | Python (18.5 KB) | Fully reproducible analysis and aggregation pipeline. |
| **Automated Test Suite** | [`test_phase6c2g11_national_events.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase6c2g11_national_events.py) | Python (7.6 KB) | Focused pytest validation suite. |

---

## 6. Automated Verification & Regression Testing

### 6.1 Focused Phase 6C.2G.11 Test Suite
Executed test suite [`backend/tests/test_phase6c2g11_national_events.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase6c2g11_national_events.py):
```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_phase6c2g11_national_events.py -v
```
**Results: 9 passed in 0.60s** (Exit code 0):
- `test_source_dem_immutability`: PASSED
- `test_raw_ifi_read_only_and_hash`: PASSED
- `test_derived_dataset_integrity_and_record_preservation`: PASSED
- `test_grouped_storms_consistency`: PASSED
- `test_descriptive_summaries_accuracy`: PASSED
- `test_rainfall_comparison_assessment`: PASSED
- `test_data_quality_report`: PASSED
- `test_manifest_and_governance`: PASSED
- `test_zero_models_trained`: PASSED

### 6.2 Full Phase 6C Test Regressions
Executed all Phase 6C test suites:
```powershell
backend\.venv\Scripts\python.exe -m pytest (Get-ChildItem -Path backend\tests\test_phase6c*.py).FullName -q
```
**Results: 129 passed in 40.42s** (Exit code 0, 100% pass rate across all 18 test modules).

---

## 7. Recommended Next Phase

With the national historical flood-event descriptive analysis complete and benchmark deluge comparisons securely bounded:
1. **National Event-Level Trigger Analysis**: Correlate macro-scale rainfall anomaly indexes (e.g., IMD gridded monsoon rainfall totals or state-level precipitation anomalies) against the 6,484 grouped historical storms to identify regional rainfall-trigger baselines across Indian river basins.
2. **Local Deep Zone Ground-Truth Acquisition**: Maintain strict prohibitions on 30m supervised ML training until street-level waterlogging vectors (e.g. municipal emergency operation logs or verified high-resolution optical deluge masks) and verified dry-ground negative samples are formally acquired.
