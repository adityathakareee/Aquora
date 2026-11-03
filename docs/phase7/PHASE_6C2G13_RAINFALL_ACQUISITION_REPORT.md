# AQUORA — Phase 6C.2G.13: National Rainfall Data Acquisition & Event Matching Report

## 1. Executive Summary & Auditable Final Decision

**Final Decision:** `PARTIAL_ACQUISITION_READY`

### Justification & Epistemological Boundaries
- **Benchmark Revalidation (E02 vs. E03)**:
  - **Event E03 (July 1–2, 2019)** is **100% verified and reproducible** from 48 local NASA GPM IMERG Final V07B HDF5 granules (`221.78 mm` point accumulation at $72.85^\circ\text{E}, 19.05^\circ\text{N}$; `218.62 mm` study extent areal mean; `32.35 mm/hr` peak half-hour rate). The IMD Santacruz gauge reading of `375.2 mm` is documented with distinct point-versus-areal smoothing analysis.
  - **Event E02 (August 29–30, 2017)** has been audited and **downgraded to `PARTIAL_TEMPORAL_COVERAGE`**. The local archive contains only a single 30-minute post-event trailing granule (`2017-08-29 23:30:00Z to 23:59:59Z`, yielding only `0.215 mm` accumulation). The daytime peak cloudburst that paralysed Mumbai occurred between 03:00 and 18:00 UTC and remains unacquired locally. The previously reported 243.6 mm figure cannot be calculated from local files and was an external benchmark citation.
- **Auditable Event-Match Inventory**: All **6,876 IFI historical disaster records** were cataloged into a machine-readable event-matching inventory (`phase6c2g13_event_match_inventory.csv`):
  - `MATCHED`: **2 records** (`UEI-IMD-FL-2019-0090`, `UEI-IMD-FL-2019-0091` for E03).
  - `PARTIAL_TEMPORAL_COVERAGE`: **2 records** (`UEI-IMD-FL-2017-0088`, `UEI-IMD-FL-2017-0089` for E02).
  - `DATE_UNCERTAIN`: **37 records** (20 missing start dates, 17 source format inversions).
  - `NOT_ACQUIRED`: **6,835 records**.
  - Total: $2 + 2 + 37 + 6,835 = \mathbf{6,876}$ records. Missing rainfall is preserved strictly as NULL (never zero-filled).
- **Candidate Sources Assessment**: NASA GPM IMERG Final V07B is prioritized as the primary satellite candidate; IMD 0.25° gridded daily rainfall is evaluated as a secondary candidate requiring manual portal approval; CHIRPS v2.0 (5 km daily) is evaluated for automated public download; ERA5-Land (hourly) is evaluated for reanalysis benchmarking.
- **Prioritized Pilot Plan**: An 8-event pilot plan spanning diverse Indian states (Maharashtra, Kerala, Uttarakhand, Assam, Tamil Nadu, Karnataka) was established, complete with exact manual authentication instructions for NASA Earthdata and IMD portals.
- **Supervised Training Safeguards**: **Supervised ML training at the 30m grid scale remains strictly prohibited** (`supervised_training_permitted: false`), and nationwide rainfall-trigger modeling is blocked until authentic rainfall is acquired. Zero models were trained, and no synthetic rainfall was generated.

---

## 2. Asset Immutability Audit

Cryptographic checksums were audited before and after this phase and remain untouched:

| Asset | Local File Path | SHA-256 Checksum | Status |
| :--- | :--- | :--- | :--- |
| **Raw IFI Dataset** | `data/raw/phase7/ground_truth/india_flood_inventory_v3.csv` | `ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108` | **VERIFIED UNMODIFIED** |
| **Raw Copernicus DSM** | `data/raw/phase7/dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif` | `b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd` | **VERIFIED UNMODIFIED** |
| **Working Study DEM** | `data/processed/phase7/terrain/elevation_30m_study_extent.tif` | `25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda` | **VERIFIED UNMODIFIED** |

---

## 3. Revalidation of Benchmark Deluges (E02 and E03)

### 3.1 Event E03 (July 1–2, 2019): Validated Benchmark Deluge
- **Local Granules Present**: 48 half-hourly granules of NASA GPM IMERG Final V07B (`GPM_3IMERGHH.07`) in `data/raw/phase7/rainfall/imerg/final/2019/07/`.
- **Temporal Window**: `2019-07-01T03:00:00Z` to `2019-07-02T03:00:00Z` (24.0 hours, corresponding to 08:30 IST 1 July to 08:30 IST 2 July, the exact IMD rainfall day).
- **Recalculated Metrics**:
  - *Point Accumulation at Nearest Grid Centroid ($72.85^\circ\text{E}, 19.05^\circ\text{N}$)*: **221.775 mm** $\to$ matches reported `221.78 mm` ($\Delta = 0.005\text{ mm}$).
  - *Study Extent Areal Mean Accumulation*: **218.62 mm** across 12 grid cells ($[72.75, 73.05]^\circ\text{E}, [18.95, 19.30]^\circ\text{N}$).
  - *Peak Half-Hour Precipitation Rate*: **32.35 mm/hr** at step index 40 (2019-07-01T23:00:00Z).
  - *Data Completeness Ratio*: 1.0 (zero missing half-hour intervals).
- **Point vs. Satellite Gauge Comparison**:
  - IMD Santacruz observatory gauge reported **375.2 mm** over the identical 24-hour observation window.
  - *Scientific Explanation*: Santacruz is a single point collector, whereas IMERG is a 0.1° (~10 km) areal average. Extreme convective cloudburst cores have steep spatial gradients that are smoothed across a 100 sq km satellite pixel footprint.
- **Status**: **100% REPRODUCIBLE FROM LOCAL HDF5 GRANULES** (`MATCHED`).

### 3.2 Event E02 (August 29–30, 2017): Downgraded to Partial Coverage
- **Local Granules Present**: Exactly **ONE 30-minute granule** (`3B-HHR.MS.MRG.3IMERG.20170829-S233000-E235959.1410.V07B.HDF5`, SHA-256: `fafd7e6cb238d925e744a89f3457c508b0ff7bb2f5290337ca7e6364e0ab6625`).
- **Temporal Coverage**: `2017-08-29T23:30:00Z` to `2017-08-29T23:59:59Z` (05:00 to 05:30 IST on August 30).
- **Calculated Granule Accumulation**: **0.215 mm** (post-event trailing dissipation rate: 0.43 mm/hr).
- **Audit Finding**: The daytime peak storm of August 29 (03:00 to 18:00 UTC) that caused catastrophic urban flooding is **ABSENT from the local granule archive**. The previously cited 243.6 mm total was derived from external secondary literature, not local raw files.
- **Status**: **DOWNGRADED TO `PARTIAL_TEMPORAL_COVERAGE`**.

---

## 4. Evaluation of Candidate Rainfall Sources

| Candidate Source | Spatial Resolution | Temporal Resolution | Covered Period & Extent | Licensing & Access Mechanism | Known Limitations for Urban Deluges | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NASA GPM IMERG Final V07B** | 0.1° $\times$ 0.1° (~10 km) | Half-hourly (3B-HHR) & Daily (3B-DAY) | 2000-06-01 to Present (Global 60°S–60°N) | Open Data. Free NASA Earthdata Login account required (`.netrc` or Bearer Token). | Areal averaging smooths urban convective cloudburst peaks; pre-2000 events not covered. | **Primary Candidate** (for post-2000 events and sub-daily deep dives). |
| **IMD Gridded Daily Rainfall** | 0.25° $\times$ 0.25° (~27 km) or 1.0° | Daily (ending 08:30 IST) | 1901 to Present (India Land Only) | Restricted / Non-commercial Academic. Web download via IMD Pune requiring manual registration/approval. | Coarse 27 km grid cannot resolve micro-watersheds; daily accumulation only; no automated unattended API. | **Secondary Candidate** (Best for long-term historical coverage via bulk request). |
| **CHIRPS v2.0** | 0.05° $\times$ 0.05° (~5 km) | Daily | 1981 to Present (50°S–50°N) | Public Domain. Open HTTP / FTP download (zero credentials required). | Daily only; thermal-IR proxy has higher uncertainty in coastal Western Ghats / Himalayan terrain. | **Viable Open Candidate** (Best for automated unauthenticated pilot downloads). |
| **ERA5-Land (ECMWF)** | 0.1° $\times$ 0.1° (~9 km) | Hourly | 1950 to Present (Global Land) | CC-BY 4.0. Copernicus Climate Data Store (CDS API with free API key). | Reanalysis model tends to underestimate localized convective rainfall extremes; queued API. | **Benchmark Reanalysis** (Useful for pre-1981 hourly benchmarking). |

---

## 5. Event-Match Inventory Reconciliation

All 6,876 IFI historical disaster records were audited and classified in [`phase6c2g13_event_match_inventory.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/rainfall/phase6c2g13_event_match_inventory.csv):

```
+------------------------------------+---------------+---------------------------------------------------------+
| Match Status                       | Record Count  | Description & Governance Handling                       |
+------------------------------------+---------------+---------------------------------------------------------+
| MATCHED                            |             2 | Event E03 records (July 1-2, 2019 Mumbai Deluge).       |
| PARTIAL_TEMPORAL_COVERAGE          |             2 | Event E02 records (August 29-30, 2017 Mumbai Deluge).   |
| DATE_UNCERTAIN                     |            37 | 20 missing start dates + 17 source tabular inversions.  |
| NOT_ACQUIRED                       |         6,835 | Authentic gridded precipitation unacquired locally.     |
+------------------------------------+---------------+---------------------------------------------------------+
| Total Reconciled Records           |         6,876 | Exactly matches raw IFI inventory (100% accounted for). |
+------------------------------------+---------------+---------------------------------------------------------+
```

### Critical Safeguards Enforced
1. **Preservation of Nulls**: For the 6,874 records without local rainfall, precipitation fields are strictly NULL. Zero-filling is strictly prohibited to avoid false-drought attribution.
2. **No Conflation of Correlation and Causation**: Statistical association between rainfall and flood reports is never claimed as physical hydraulic causation.
3. **No Synthetic Grids**: Historical rainfall grids are never fabricated or spatially interpolated for unacquired events.

---

## 6. Prioritized Pilot Acquisition Plan

To validate the acquisition pipeline before downloading large national archives, a representative **8-event pilot plan** was designed spanning diverse geographic regions, topographies, and historical eras:

| Pilot ID | Disaster Event | State | Date | Priority Candidate Source | Current Local Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PILOT-01** | Mumbai Deluge (July 2019) | Maharashtra | 2019-07-02 | NASA GPM IMERG Final V07B (Half-Hourly) | **ACQUIRED & VERIFIED (48 granules)** |
| **PILOT-02** | Mumbai Deluge (August 2017) | Maharashtra | 2017-08-30 | NASA GPM IMERG Final V07B (Full 24h Sequence) | **PLANNED COMPLETION (47 granules missing)** |
| **PILOT-03** | Maharashtra 26 July Deluge (2005) | Maharashtra | 2005-07-26 | NASA GPM IMERG Final V07B (Daily / Half-Hourly) | **PLANNED DOWNLOAD** |
| **PILOT-04** | Kerala Deluge (August 2018) | Kerala | 2018-08-16 | NASA GPM IMERG Daily V07B & CHIRPS Daily | **PLANNED DOWNLOAD** |
| **PILOT-05** | Kedarnath Cloudburst (June 2013) | Uttarakhand | 2013-06-16 | NASA GPM IMERG Daily V07B & ERA5-Land | **PLANNED DOWNLOAD** |
| **PILOT-06** | Assam Brahmaputra Flood (July 2019) | Assam | 2019-07-10 | NASA GPM IMERG Daily V07B | **PLANNED DOWNLOAD** |
| **PILOT-07** | Chennai Deluge (December 2015) | Tamil Nadu | 2015-12-01 | NASA GPM IMERG Daily V07B | **PLANNED DOWNLOAD** |
| **PILOT-08** | Bengaluru Urban Flooding (Sept 2022) | Karnataka | 2022-09-05 | NASA GPM IMERG Daily V07B | **PLANNED DOWNLOAD** |

### Manual Authentication Protocol
- **NASA Earthdata Login**:
  1. Register free credentials at `https://urs.earthdata.nasa.gov/`.
  2. Authorize the `NASA GESDISC DATA ARCHIVE` application in profile.
  3. Create local `~/.netrc` with: `machine urs.earthdata.nasa.gov login <USER> password <PASS>`. Automated scripts will read `.netrc` without exposing credentials in code.
- **IMD Data Portal**:
  1. Submit academic research request at `https://imdpune.gov.in/`.
  2. Accept non-commercial licensing terms for 0.25° gridded daily rainfall.
  3. Store downloaded packages in `data/raw/phase7/rainfall/imd/`.

---

## 7. Deliverables Created & Test Results

1. **Planning Script**: [`plan_phase6c2g13_rainfall_acquisition.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/plan_phase6c2g13_rainfall_acquisition.py)
2. **E02/E03 Revalidation JSON**: [`phase6c2g13_e02_e03_revalidation.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/rainfall/phase6c2g13_e02_e03_revalidation.json)
3. **Source Assessment JSON**: [`phase6c2g13_source_assessment.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/rainfall/phase6c2g13_source_assessment.json)
4. **Event Match Inventory CSV**: [`phase6c2g13_event_match_inventory.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/rainfall/phase6c2g13_event_match_inventory.csv)
5. **Phase 6C.2G.13 Manifest**: [`phase6c2g13_rainfall_acquisition_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase6c2g13_rainfall_acquisition_manifest.yaml)
6. **Automated Test Suite**: [`test_phase6c2g13_rainfall_acquisition.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase6c2g13_rainfall_acquisition.py)
7. **Phase Report**: [`PHASE_6C2G13_RAINFALL_ACQUISITION_REPORT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_6C2G13_RAINFALL_ACQUISITION_REPORT.md)

### Automated Test Execution
- **Focused Phase 6C.2G.13 Suite**:
  ```powershell
  backend\.venv\Scripts\python.exe -m pytest backend\tests\test_phase6c2g13_rainfall_acquisition.py -v
  ```
  *Result*: **8 passed in 0.50s** (Exit code 0).
- **Full Phase 6C Regression Suite (All 20 Test Modules)**:
  ```powershell
  backend\.venv\Scripts\python.exe -m pytest (Get-ChildItem -Path backend\tests\test_phase6c*.py).FullName -q
  ```
  *Result*: **145 passed in 37.79s** (Exit code 0, 100% pass rate).

---

## 8. Recommended Next Phase

1. **Execute Pilot Acquisition**: Implement the acquisition of NASA GPM IMERG Daily V07B or unauthenticated CHIRPS v2.0 for the 8 landmark pilot disaster events using `.netrc` authentication.
2. **Complete Event E02 Daytime Granules**: Download the remaining 47 half-hourly granules for August 29, 2017 (00:00 to 23:29 UTC) to upgrade Event E02 to fully validated status.
3. **Preserve Supervised Training Block**: Maintain the strict block on supervised 30m ML training until street-scale inundation vectors and verified negative observations are acquired.
