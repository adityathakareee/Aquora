# AQUORA — Phase 6C.2G.9: Authentic Flood Ground-Truth Acquisition Report

---

## 1. Executive Summary and Governance Decision

```
========================================================================================
FINAL GROUND-TRUTH ACQUISITION DECISION:
PARTIAL_DATA_ACQUIRED
(SUPERVISED_TRAINING_REMAINS_BLOCKED — ZERO MODEL TRAINING IN THIS PHASE)
========================================================================================
```

**Epistemological Summary:**
1. **Authentic Ground-Truth Data Acquired:**
   - **India Flood Inventory (IFI-Impacts) [1967–2023]**: Acquired locally on disk from Zenodo (`DOI: 10.5281/zenodo.4742142`), compiled by IIT Delhi (Dr. Manabendra Saharia) and the India Meteorological Department (IMD). Contains **6,876 verified historical flood events** across India, including 1,017 records in Maharashtra and 182 records in Mumbai.
   - **Dartmouth Flood Observatory (DFO) Master List**: Acquired locally on disk from HDX (`976f0904...`, 610.6 KB), providing global master flood polygons and attributes.
2. **Exact Temporal and Spatial Correspondence:**
   - Both target historical deluge events in AQUORA have exact matches in the acquired national inventory:
     - **Event E03 (1–2 July 2019 Mumbai Cloudburst)**: Matched by `UEI-IMD-FL-2019-0090` (01-07-2019) and `UEI-IMD-FL-2019-0091` (02-07-2019), documenting severe waterlogging across Mumbai, Thane, and Palghar caused by incessant monsoon downpours.
     - **Event E02 (29–30 August 2017 Mumbai Deluge)**: Matched by `UEI-IMD-FL-2017-0088` (29-08-2017) and `UEI-IMD-FL-2017-0089` (30-08-2017).
3. **Why the Decision is `PARTIAL_DATA_ACQUIRED` (and Supervised Training Remains Blocked):**
   - **Spatial Granularity Mismatch:** The acquired IFI dataset records flood events at the **District and Sub-District / City administrative scale**. It does NOT provide 30m georeferenced polygon extents or flood depth grids along the Mithi River corridor.
   - **The Negative-Sampling Gap:** Like all disaster registries (DFO, EM-DAT, DesInventar), IFI is an *incident-reporting database*. It exclusively documents where flooding occurred; it **never systematically records locations that remained dry**. In accordance with AQUORA data-integrity principles, the absence of an incident report cannot be interpreted as verified dry ground ($y = 0$).
   - **Supervised Training Blocked:** Without defensible non-flood observations ($y = 0$) and street-scale vector inundation polygons, supervised ML classification cannot proceed without severe false-negative bias or synthetic fabrication.

---

## 2. Acquired Authentic Ground-Truth Inventory

| Dataset Asset | Source Authority | Format & Size | SHA-256 Checksum | Spatial & Temporal Scope | Licensing & Usability | Status |
| :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| **India Flood Inventory (IFI-Impacts)** | HydroSense Lab, IIT Delhi / IMD / NCAR (Zenodo 4742142) | CSV (1.80 MB, 6,876 rows) | `ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108` | National India (82 state/UT units, 1,017 in Maharashtra, 182 in Mumbai); 1967–2023 | Creative Commons Attribution 4.0 (CC-BY 4.0) | **ACQUIRED & PARSED** |
| **DFO Master List Shapefile** | Dartmouth Flood Observatory / WFP / HDX | ZIP archive (610.6 KB, 4,029 global rows) | `976f0904c603ba31e8aa62f6d1b55cec4c153be783495593ed247d01629ffe09` | Global (12 large India flood events); 1985–2019 | Open Data Commons Open Database License (ODbL) | **ACQUIRED & PARSED** |
| **UNOSAT Rapid Mapping** | UNITAR / UNOSAT | Vector GDB / SHP | N/A | Regional India (Kerala 2018, Assam 2019/2020); **No Mumbai 2019 activation** | Open Humanitarian | **INVESTIGATED (NO MUMBAI ACTIVATION)** |
| **Copernicus EMS** | European Commission | GeoTIFF / Vector | N/A | Regional India (EMSR229 Kerala, EMSR370 Assam/Bihar); **No Mumbai 2019 activation** | Open Copernicus | **INVESTIGATED (NO MUMBAI ACTIVATION)** |
| **MCGM Ward Inundation Vectors** | Brihanmumbai Municipal Corporation (BMC) | Surveyed GIS Polygons | N/A | Mumbai City & Suburban wards (street-level) | Municipal Internal / Confidential | **PENDING FORMAL DATA REQUEST** |

---

## 3. Detailed Examination of Acquired India Flood Inventory Records

The India Flood Inventory (IFI) was compiled from the official *Annual Disaster Reports* and *Annual Flood Reports* published by the India Meteorological Department (IMD) and the Central Water Commission (CWC), supplemented by media corroboration and state disaster management records.

### 3.1 Event E03 Corroboration (July 2019 Cloudburst)
- **Primary Event 1:**
  - `UEI`: `UEI-IMD-FL-2019-0090`
  - `Start Date`: `07-01-2019 00:00` | `End Date`: `07-01-2019 00:00` | `Duration`: 1.0 day
  - `Districts Affected`: `Mumbai, Nashik, Palghar, Pune` | `State`: `Maharashtra`
  - `Main Cause`: `Heavy rains`
  - `Documented Impacts`: Submergence of low-lying areas, disruption of suburban train services on Central and Western Railways, traffic diversions.
- **Primary Event 2:**
  - `UEI`: `UEI-IMD-FL-2019-0091`
  - `Start Date`: `07-02-2019 00:00` | `End Date`: `07-02-2019 00:00` | `Duration`: 1.0 day
  - `Districts Affected`: `Mumbai, Thane, Ratnagiri` | `State`: `Maharashtra`
  - `Main Cause`: `Heavy rains , Incessant rains leading to flood-like situation.`
  - `Documented Impacts`: Extreme urban flooding, breach of Mithi River banks at Kranti Nagar, Malad reservoir wall collapse (>25 fatalities), road closures along Western Express Highway (WEH) and SV Road.

### 3.2 Event E02 Corroboration (August 2017 Cloudburst)
- **Primary Event 1:** `UEI-IMD-FL-2017-0088` (29-08-2017): Heavy rains causing flash floods in Thane and eastern Mumbai suburbs.
- **Primary Event 2:** `UEI-IMD-FL-2017-0089` (30-08-2017): Severe flooding across Palghar, Thane, and Mumbai with rail paralysis and widespread waterlogging.

---

## 4. Label Provenance & The Negative Sampling Problem

### 4.1 Label Taxonomy Application
1. **VERIFIED ($y = 1$ Macro-Presence):** The occurrence of flooding in Mumbai on 1–2 July 2019 is verified by official IMD records (`UEI-IMD-FL-2019-0090` and `UEI-IMD-FL-2019-0091`).
2. **PARTIALLY_VERIFIED (Spatial Localization):** The records specify the district (`Mumbai`) and major metropolitan sub-areas, but lack sub-catchment polygon geometry.
3. **UNVERIFIED (Candidate Remote Sensing):** Sentinel-1 differential microwave drops ($\Delta \sigma^0 \le -3\text{ dB}$) remain candidate observational responses, NOT ground truth.
4. **UNLABELED ($y = -1$):** Defensible dry conditions remain completely unobserved across India during storm windows.

### 4.2 The "Incident Reporting Bias" Problem
Natural hazard inventories record disaster incidents. If a district or basin is not listed during a storm, that non-appearance does **not** prove that zero surface water accumulated. Converting unmentioned areas into negative samples ($y = 0$) would introduce false negatives:
- Unpopulated or rural areas without reporting stations are systematically undercounted.
- Poorly drained rural fields with waterlogging that caused no infrastructure loss are omitted.
- Conversely, urban centers with heavy media coverage are over-reported.

To establish defensible non-flood ($y = 0$) ground truth without bias, AQUORA requires:
1. Operational transport logs (e.g. railway track circuits confirming dry rails).
2. Continuous hydrometric gauges confirming water levels stayed below bankfull stage.
3. Cloud-free optical satellite imagery confirming dry ground during the event.

---

## 5. Spatial & Temporal Alignment Analysis

```
+-----------------------------------------------------------------------------------------+
| Spatial Hierarchy Mapping                                                               |
+-----------------------------------------------------------------------------------------+
| National Level (Country):     INDIA                                                     |
| State Level:                  MAHARASHTRA                                               |
| District Level:               MUMBAI / MUMBAI SUBURBAN (Matched in IFI)                 |
| Basin Level (HydroBASINS):    Kalu-Ulhas-Mithi Coastal Complex (Matched in IFI)         |
| Deep Zone Corridor:           MITHI RIVER (Missing 30m Survey Vector Polygons)          |
+-----------------------------------------------------------------------------------------+
```

### 5.1 Temporal Alignment
The temporal alignment between AQUORA's target events and IFI records is an **exact match**:
- Event E03: 1–2 July 2019 is corroborated by two separate daily entries in IFI.
- Event E02: 29–30 August 2017 is corroborated by two separate daily entries in IFI.

### 5.2 Leakage Prevention Rules
Because the cloudburst of 1–2 July 2019 was recorded as two consecutive days in IFI, these records belong to the same synoptic monsoon depression. Under AQUORA governance:
1. **Event Holdout:** July 1 and July 2 2019 must **never** be split across training and testing folds. The entire event window must be held out as a block.
2. **Spatial Grouping:** All training and validation splits must be grouped by HydroBASINS `basin_id` using `GroupKFold`. Samples from the same river basin must never leak across folds.

---

## 6. DEM Immutability Verification

| DEM Asset | Expected SHA-256 | Actual SHA-256 | Status |
| :--- | :--- | :--- | :---: |
| **Raw Copernicus DSM** | `b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd` | `b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd` | **UNMODIFIED** |
| **Working Study Extent DEM** | `25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda` | `25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda` | **UNMODIFIED** |

---

## 7. Next Steps to Enable Supervised ML Dataset Construction

1. **Defensible Negative Sampling Strategy:** Develop an evidence-backed protocol for non-flood samples (e.g. pairing confirmed dry railway/airport logs with low-rainfall, high-elevation terrain during non-cloudburst dates).
2. **Review Municipal Acquisition Package:** Formalize institutional requests to MCGM Disaster Management and MMRDA for ward-level inundation survey maps.
3. **Exploratory Regional Model Benchmarking:** Use IFI records for macro-scale district-level flood frequency screening benchmarking, without claiming street-level 30m pixel resolution.
