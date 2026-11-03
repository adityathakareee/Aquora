# AQUORA — PHASE 7F.3.8: AUTHORITATIVE HYDROGRAPHY AND MASK SOURCE VERIFICATION REPORT (AMENDED)
### Technical Source Verification, Methodological Qualifications & Dual AUX Package Formulation for the DFO 3382 Mahanadi Study Region

**Document Version:** `1.1.0-source-verification-amended`  
**Phase:** Phase 7F.3.8 Authoritative Hydrography & Mask Source Verification  
**Target Study Domain:** Mahanadi Basin / Odisha Delta ($19.0^\circ–22.0^\circ\text{N}, 84.0^\circ–88.0^\circ\text{E}$)  
**Task Type:** READ-ONLY SOURCE VERIFICATION & PLANNING (Zero data downloads, zero DEM modifications, zero terrain derivatives, zero ML training, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60))  
**Date:** 2026-11-01  

---

## 1. Executive Summary & Verification Decision

Following the Phase 7F.3.7 Terrain Readiness Audit which identified that local storage lacks valid watershed boundaries, river network centerlines, and 30m coastal water masks, this amended document establishes the **authoritative source verification, rigorous methodological qualifications, and dual auxiliary package formulation**.

Every candidate external data source was investigated directly against its official provider, URL endpoint, licensing, coordinate reference system, spatial resolution, and actual programmatic downloadability. Direct HTTP HEAD requests and remote GeoTIFF header queries were executed to verify remote endpoint availability, content headers, and exact byte counts.

### Key Audit & Methodological Outcomes:
1. **HydroBASINS Integration for Watershed Delineation**:
   * The existing local file (`data/processed/boundaries/hydrobasins_india.geojson`, Feature 6) is an invalid 5-point rectangular bounding box ($[80.4^\circ\text{E}, 19.3^\circ\text{N}, 86.9^\circ\text{E}, 23.6^\circ\text{N}]$).
   * Because Central Water Commission (CWC) bulk vector shapefiles require Indian mobile number OTP authentication and are non-programmatic, **HydroBASINS Asia v1c (`hybas_as_lev01-12_v1c.zip`, $376.39\text{ MB}$ decimal)** is verified as the sole open, programmatic, topographically consistent watershed source. Level 7 and Level 8 sub-basins cleanly isolate the delta distributaries below the Naraj Barrage apex. A post-acquisition regional clipping workflow is established to retain only the Mahanadi sub-basins and purge continental excess.
2. **Correct Interpretation of JRC Global Surface Water**:
   * **Occurrence ($0–100\%$)** represents multi-decadal water frequency (1984–2021) and is used exclusively for persistent/permanent water masking (`occurrence >= 80%`).
   * **Seasonality ($0–12\text{ months}$)** represents multi-annual average monsoonal inundation duration.
   * **Methodological Invariant**: These aggregate layers **CANNOT** reconstruct the episodic flood extent of September 2008. The transient 8-day flood pulse caused by Hirakud Dam spillway discharge is obscured in 38-year aggregate statistics. Zero synthetic 2008 flood labels will be inferred or fabricated from these aggregate layers.
3. **WorldCover Spatial Coverage Disaggregation**:
   * `ESA_WorldCover_10m_2021_v200_N18E084_Map.tif` ($54.27\text{ MB}$ decimal) covers 100% of the Core Mahanadi Delta ($19^\circ–21^\circ\text{N}, 84^\circ–87^\circ\text{E}$).
   * The northern tier of the Extended Delta ($21^\circ–22^\circ\text{N}$, Jajpur and Bhadrak) requires `N21E084` ($127.99\text{ MB}$ decimal), verified available on AWS S3. If only `N18E084` is acquired, land-cover analysis is explicitly restricted to the Core Delta footprint.
4. **Global Mangrove Watch (GMW v3.0) 2008 Verification**:
   * Verified available on Zenodo (DOI: `10.5281/zenodo.6894273`) with an **exact contemporaneous 2008 epoch** (`gmw_v3_2008_gtiff.zip`, $66.66\text{ MB}$ decimal). Provides authentic 2008 mangrove canopy baseline data for Bhitarkanika and the coastal estuaries.
5. **Dual AUX Package Formulation (Decimal MB Arithmetic)**:
   * **Package AUX-MIN (Minimal, 4 files)**: **`254.20 MB`** ($254,200,523\text{ bytes}$) — Core stream burning and permanent water baseline for Core Delta only.
   * **Package AUX-EXT (Comprehensive, 9 files)**: **`868.46 MB`** ($868,457,452\text{ bytes}$) — Adds HydroBASINS watershed boundaries, Extended Delta land cover, seasonal waterlogging duration, and 2008 mangrove baseline.
6. **Final Decision**:
   $$\mathbf{AUX\_PACKAGE\_READY\_FOR\_APPROVAL}$$

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               AQUORA PHASE 7F.3.8 SOURCE VERIFICATION SUMMARY (AMENDED)                │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Target Event:               DFO 3382 — Mahanadi Delta Floods (Odisha, Sept 2008)
  Study Domain:               19.0°N–22.0°N, 84.0°E–88.0°E (Core & Extended Delta)
  Hydrographic Boundaries:    HydroBASINS Asia v1c (Verified HTTP 200, 376.39 MB decimal)
  Drainage Network:           HydroRIVERS Asia v1.0 (Verified HTTP 200, 90.51 MB decimal)
  Core Delta Land Cover:      ESA WorldCover 2021 N18E084 (Verified HTTP 200, 54.27 MB decimal)
  Extended Delta Land Cover:  ESA WorldCover 2021 N21E084 (Verified HTTP 200, 127.99 MB decimal)
  Surface Water (30m):        JRC GSW v1.4 Occurrence & Seasonality (Verified HTTP 200, 152.64 MB total)
  Mangrove Baseline (2008):   Global Mangrove Watch v3.0 2008 Epoch (Verified HTTP 200, 66.66 MB decimal)
  Package AUX-MIN (Minimal):  4 Files, 254.20 MB decimal (242.42 MiB binary)
  Package AUX-EXT (Extended): 9 Files, 868.46 MB decimal (828.23 MiB binary)
  Final Status:               AUX_PACKAGE_READY_FOR_APPROVAL (Execution strictly deferred)
────────────────────────────────────────────────────────────────────────────────────────
```

---

## 2. Hydrographic Boundaries: Candidate Source Evaluation & Watershed Delineation

To replace the invalid 5-point rectangular bounding box currently stored in `data/processed/boundaries/hydrobasins_india.geojson`, candidate watershed boundary datasets were audited:

### 2.1 HydroBASINS Standard Product — Asia (v1c)
- **Official Provider**: U.S. Geological Survey (USGS) / World Wildlife Fund (WWF) / McGill University.
- **Exact Product Name**: `hybas_as_lev01-12_v1c.zip`
- **Official Download URL**: `https://data.hydrosheds.org/file/HydroBASINS/standard/hybas_as_lev01-12_v1c.zip`
- **Verification Status**: **`HTTP 200 OK`**, Content-Length: `376,386,706 bytes` ($376.39\text{ MB}$ decimal, $358.95\text{ MiB}$ binary).
- **Geographic Coverage**: Continental Asia. Encompasses the complete Mahanadi Basin (`MAIN_BAS = 405001`, Pfafstetter Level 5 code `4527`).
- **Spatial Resolution & Scale**: Derived from hydrologically conditioned 15 arc-second ($\approx 500\text{ m}$) SRTM elevation data.
- **Coordinate Reference System**: Geographic 2D (`EPSG:4326`, WGS 84).
- **Licensing & Access**: Creative Commons Attribution 4.0 International (CC BY 4.0). Completely open, direct unauthenticated HTTP download.
- **Suitability & Extraction Workflow for DFO 3382**:
  - *Delta Isolation*: Pfafstetter Level 7 and Level 8 sub-basin polygons partition the coastal delta plain downstream of the Naraj Barrage bifurcation (`HYBAS_ID 4050xxxxxx`), allowing clean exclusion of unrelated upstream tributaries.
  - *Post-Acquisition Regional Extraction*: The continental archive ($376.39\text{ MB}$) is acquired once. A regional clipping script filters polygons intersecting the Mahanadi bounding box ($[80.0^\circ–87.0^\circ\text{E}, 19.0^\circ–24.0^\circ\text{N}]$) for Levels 5, 7, and 8 into `data/raw/phase7/boundaries/mahanadi_hydrobasins/` ($\approx 2\text{ MB}$ local footprint). The continental zip can then be archived or purged.
  - *Authoritative Identifiers & Topology Validation*: Every extracted polygon must satisfy:
    1. Valid non-self-intersecting topology (`is_valid == True`).
    2. Attribute integrity: `HYBAS_ID`, `MAIN_BAS == 405001`, `PFAF_ID == 4527*`, and `SUB_AREA`.
    3. Basin area reconciliation against published hydrological literature ($\approx 141,589\text{ km}^2 \pm 2\%$).
  - *Operational Status*: **Mandatory** if an authoritative watershed boundary is required, as open alternatives do not exist.

### 2.2 Central Water Commission (CWC) / India-WRIS
- **Official Provider**: Central Water Commission, Ministry of Jal Shakti, Government of India / National Water Informatics Centre (NWIC).
- **Exact Product Name**: India-WRIS Basin and Sub-basin GIS Layers (`Basin_Code: 04` — Mahanadi Basin).
- **Official Portal URL**: `https://indiawris.gov.in/wris/`
- **Verification Status**: **`HTTP 200 OK`** (HTML web portal wrapper).
- **Licensing & Access Conditions**: **RESTRICTED / NON-PROGRAMMATIC**. Bulk vector export requires Indian citizen mobile number registration and OTP verification, or formal data request to NWIC under the National Data Sharing and Accessibility Policy (NDSAP).
- **Distinction from HydroBASINS**: CWC defines legally designated administrative river management jurisdictions; HydroBASINS provides topographically consistent watershed ridgeline boundaries derived from satellite elevation. CWC is retained as a benchmark reference, while HydroBASINS provides the programmatic operational boundary.

---

## 3. River Networks: Candidate Source Evaluation

### 3.1 HydroRIVERS Asia v1.0
- **Official Provider**: World Wildlife Fund (WWF) / McGill University.
- **Exact Product Name**: `HydroRIVERS_v10_as_shp.zip` (Shapefile) / `HydroRIVERS_v10_as.gdb.zip` (File Geodatabase).
- **Official Download URL**: 
  - Shapefile: `https://data.hydrosheds.org/file/hydrorivers/HydroRIVERS_v10_as_shp.zip`
  - Geodatabase: `https://data.hydrosheds.org/file/hydrorivers/HydroRIVERS_v10_as.gdb.zip`
- **Verification Status**:
  - Shapefile: **`HTTP 200 OK`**, Content-Length: `90,510,995 bytes` ($90.51\text{ MB}$ decimal, $86.32\text{ MiB}$ binary).
  - Geodatabase: **`HTTP 200 OK`**, Content-Length: `102,543,400 bytes` ($102.54\text{ MB}$ decimal, $97.79\text{ MiB}$ binary).
- **Attributes & Resolution**: River reaches with upstream catchment area $\ge 10\text{ km}^2$ or discharge $\ge 0.1\text{ m}^3/\text{s}$. Attributes include Strahler stream order (`ORD_STRA`), upstream catchment area (`UPLAND_SKM`), reach length (`LENGTH_KM`), and estimated discharge (`DIS_AV_CMS`).
- **Coordinate Reference System**: WGS 84 (`EPSG:4326`).
- **Licensing & Access**: CC BY 4.0. Direct unauthenticated HTTP download.
- **Scientific Limitations in Delta Settings**:
  - *Dendritic D8 Structure*: HydroRIVERS routes flow along a single downstream branch. In an anabranching delta (Mahanadi splitting into Kathajodi, Birupa, Kuakhai, Daya, Bhargavi, Devi, Chitratpala), D8 routes flow only down the primary channel at each fork, omitting minor distributary branches.
  - *Missing Anthropogenic Channels*: Urban storm drains in Cuttack/Bhubaneswar and major agricultural irrigation canals (Puri Main Canal, Kendrapara Canal, High-Level Canal) are not mapped.
- **Stream-Burning Parameter Status**:
  - **Universal stream-burning depths (e.g. 1.5m or 3.0m) are NOT approved operational parameters**.
  - Any hydraulic trenching depth applied to the Copernicus DSM must remain explicitly designated as an **experimental conditioning hypothesis** requiring sensitivity analysis and empirical calibration against local ground-truth.

---

## 4. Land-Cover & Water Mask Source Verification

### 4.1 ESA WorldCover 10m 2021 Spatial Disaggregation
- **Official Provider**: European Space Agency (ESA) / VITO Remote Sensing Consortium.
- **Coordinate Reference System & Resolution**: EPSG:4326, 10 meters ($0.00008333^\circ \times 0.00008333^\circ$). CC BY 4.0 license.
- **Tile Coverage & Verification**:
  1. **Core Delta Tile (`N18E084`)**:
     - *URL*: `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N18E084_Map.tif`
     - *Verification*: **`HTTP 200 OK`**, Content-Length: `54,269,282 bytes` ($54.27\text{ MB}$ decimal, $51.76\text{ MiB}$ binary).
     - *Bounds*: Latitude $18.0^\circ–21.0^\circ\text{N}$, Longitude $84.0^\circ–87.0^\circ\text{E}$.
     - *Coverage*: Covers 100% of the Core Mahanadi Delta (Cuttack, Bhubaneswar, Puri, Kendrapara, Jagatsinghpur, Chilika Lagoon, Devi estuary).
  2. **Extended Delta Northern Tile (`N21E084`)**:
     - *URL*: `https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N21E084_Map.tif`
     - *Verification*: **`HTTP 200 OK`**, Content-Length: `127,991,194 bytes` ($127.99\text{ MB}$ decimal, $122.06\text{ MiB}$ binary).
     - *Bounds*: Latitude $21.0^\circ–24.0^\circ\text{N}$, Longitude $84.0^\circ–87.0^\circ\text{E}$.
     - *Coverage*: Covers the northern tier of the Extended Delta (Jajpur, Baitarani-Brahmani confluence, and Bhadrak).
- **Scope Restriction**: If only `N18E084` is acquired (Package AUX-MIN), supported land-cover analysis is strictly restricted to the Core Delta footprint ($19^\circ–21^\circ\text{N}$). Full Extended Delta analysis requires both tiles (staged in Package AUX-EXT).
- **Temporal Mismatch Qualification**: Reflects calendar year 2021 (13-year decadal gap from September 2008). While coastal geomorphology and mangrove forest bounds are broadly stable, urban sprawl in Bhubaneswar/Cuttack and commercial prawn aquaculture along Chilika Lagoon have expanded since 2008.

### 4.2 JRC Global Surface Water (GSW v1.4) Scientific Interpretation
- **Official Provider**: European Commission Joint Research Centre (JRC). Open Access (Decision 2011/833/EU).
- **Tile Architecture**: $10^\circ \times 10^\circ$ blocks indexed by their **top-left corner**:
  - **`80E_20N`**: Bounding box $[80.0^\circ–90.0^\circ\text{E}, 10.0^\circ–20.0^\circ\text{N}]$. Covers Southern Delta ($19.0^\circ–20.0^\circ\text{N}$).
  - **`80E_30N`**: Bounding box $[80.0^\circ–90.0^\circ\text{E}, 20.0^\circ–30.0^\circ\text{N}]$. Covers Northern Delta ($20.0^\circ–22.0^\circ\text{N}$).
- **Verified Download Endpoints & Exact Sizes**:
  - `Occurrence 80E_20N`: `https://storage.googleapis.com/global-surface-water/downloads/occurrence/occurrence_80E_20N.tif` — **`HTTP 200 OK` (27.24 MB decimal, 25.98 MiB binary)**
  - `Occurrence 80E_30N`: `https://storage.googleapis.com/global-surface-water/downloads/occurrence/occurrence_80E_30N.tif` — **`HTTP 200 OK` (82.18 MB decimal, 78.37 MiB binary)**
  - `Seasonality 80E_20N`: `https://storage.googleapis.com/global-surface-water/downloads/seasonality/seasonality_80E_20N.tif` — **`HTTP 200 OK` (13.98 MB decimal, 13.33 MiB binary)**
  - `Seasonality 80E_30N`: `https://storage.googleapis.com/global-surface-water/downloads/seasonality/seasonality_80E_30N.tif` — **`HTTP 200 OK` (29.24 MB decimal, 27.88 MiB binary)**
- **Scientific Interpretation & Critical Limitations**:
  - *Occurrence ($0–100\%$)*: Indicates multi-decadal frequency of water detection across 1984–2021. Essential for permanent water baseline masking (`occurrence >= 80%`).
  - *Seasonality ($0–12\text{ months}$)*: Indicates annual duration of water presence, discriminating recurring monsoonal waterlogging from dry land.
  - *Prohibition on Event Reconstruction*: **These aggregate multi-decadal layers CANNOT reconstruct the episodic flood extent of September 2008**. The transient 8-day flood pulse caused by Hirakud Dam spillway discharge is obscured in 38-year aggregate statistics. Zero synthetic 2008 flood labels will be inferred from these layers.

### 4.3 Global Mangrove Watch (GMW v3.0) 2008 Epoch Verification
- **Official Provider**: Aberystwyth University / soloEO / Wetlands International / JAXA / UNEP-WCMC.
- **Product & Version**: Global Mangrove Watch (1996–2020) Version 3.0 Dataset.
- **Zenodo Record**: `https://zenodo.org/records/6894273` (DOI: `10.5281/zenodo.6894273`).
- **Verified Download URLs & Sizes**:
  - GeoTIFF: `https://zenodo.org/api/records/6894273/files/gmw_v3_2008_gtiff.zip/content` — **`HTTP 200 OK` (66.66 MB decimal, 63.58 MiB binary)**.
  - Vector Shapefile: `https://zenodo.org/api/records/6894273/files/gmw_v3_2008_vec.zip/content` — **`HTTP 200 OK` (191.30 MB decimal, 182.43 MiB binary)**.
- **Spatial Resolution & CRS**: $\approx 25\text{ m}$, EPSG:4326. License: CC BY 4.0.
- **Mahanadi Coverage & Temporal Suitability**: Covers Bhitarkanika National Park, Dhamra estuary, Mahanadi mouth, and Devi estuary. Crucially, the **2008 epoch provides an authentic contemporaneous baseline** coinciding directly with the September 2008 disaster.
- **Coastal Classification Limitation**: GMW maps mangrove canopy extent; it cannot serve as a complete tidal flat or shoreline mask.

---

## 5. Candidate Source Comparison & Dual Package Formulation

### 5.1 Source Comparison Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              AUTHORITATIVE AUXILIARY DATA COMPARISON MATRIX                                            │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

| Source Dataset | Layer Type | Resolution | Geographic Bounds | File Size (Decimal MB) | Access Mode | Licensing | Status for DFO 3382 Pipeline |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **HydroRIVERS Asia** | River Centerlines | Reach vector | Continental Asia | **90.51 MB** | Direct HTTP | CC BY 4.0 | **ESSENTIAL (AUX-MIN & AUX-EXT)** |
| **HydroBASINS Asia** | Basin/Sub-basins | Pfafstetter 1–12 | Continental Asia | **376.39 MB** | Direct HTTP | CC BY 4.0 | **ESSENTIAL FOR WATERSHEDS (AUX-EXT)** |
| **India-WRIS Basin 04**| Official Basin | 1:50,000 vector | National India | Web-GIS | Restricted / OTP | NDSAP | Secondary Reference Benchmark |
| **ESA WorldCover N18E084**| Land Cover | 10 meters | $84^\circ–87^\circ\text{E}, 18^\circ–21^\circ\text{N}$ | **54.27 MB** | Direct S3 | CC BY 4.0 | **ESSENTIAL CORE (AUX-MIN & AUX-EXT)** |
| **ESA WorldCover N21E084**| Land Cover | 10 meters | $84^\circ–87^\circ\text{E}, 21^\circ–24^\circ\text{N}$ | **127.99 MB** | Direct S3 | CC BY 4.0 | **OPTIONAL EXTENDED (AUX-EXT)** |
| **JRC GSW Occurrence** | Water Occurrence | 30 meters | $80^\circ–90^\circ\text{E}, 10^\circ–30^\circ\text{N}$ | **109.42 MB** (2 tiles) | Direct GCS | EU Open | **ESSENTIAL (AUX-MIN & AUX-EXT)** |
| **JRC GSW Seasonality**| Monthly Duration | 30 meters | $80^\circ–90^\circ\text{E}, 10^\circ–30^\circ\text{N}$ | **43.21 MB** (2 tiles) | Direct GCS | EU Open | **RECOMMENDED (AUX-EXT)** |
| **GMW 2008 GeoTIFF**   | Mangrove Extent  | 25 meters | Global Coastal | **66.66 MB** | Direct Zenodo | CC BY 4.0 | **RECOMMENDED (AUX-EXT)** |

---

### 5.2 Dual Auxiliary Packages (Consistent Decimal MB Arithmetic)

#### A. Package AUX-MIN: Minimal Auxiliary Package (4 Files — Core Delta Only)
Designed for the smallest defensible footprint required for initial stream burning and persistent water masking in the Core Delta:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               PACKAGE AUX-MIN: MINIMAL COMPONENT BREAKDOWN                             │
├────────────────────────────────────────────────────────┬─────────────┬─────────────────┤
│ Component File                                         │ Size (MB)   │ Role            │
├────────────────────────────────────────────────────────┼─────────────┼─────────────────┤
│ 1. HydroRIVERS_v10_as_shp.zip                          │   90.51 MB  │ Stream Burning  │
│ 2. ESA_WorldCover_10m_2021_v200_N18E084_Map.tif        │   54.27 MB  │ Core Land Cover │
│ 3. occurrence_80E_20N.tif                              │   27.24 MB  │ Southern Water  │
│ 4. occurrence_80E_30N.tif                              │   82.18 MB  │ Northern Water  │
├────────────────────────────────────────────────────────┼─────────────┼─────────────────┤
│ TOTAL (Package AUX-MIN)                                │  254.20 MB  │ 4 Core Files    │
└────────────────────────────────────────────────────────┴─────────────┴─────────────────┘
```
*Exact Byte Count*: $90,510,995 + 54,269,282 + 27,240,640 + 82,179,606 = \mathbf{254,200,523\text{ bytes}}$ (**`254.20 MB` decimal** / $242.42\text{ MiB}$ binary).  
*Scope Limitation*: Restricts analysis strictly to the Core Delta ($19^\circ–21^\circ\text{N}$). Does not include watershed boundaries, Extended Delta land cover, seasonal inundation duration, or 2008 mangrove baseline.

#### B. Package AUX-EXT: Comprehensive Extended Package (9 Files — Full Delta & Catchments)
Designed for complete hydrologic conditioning, true watershed boundary delineation, seasonal waterlogging discrimination, and 2008 mangrove baseline across both Core and Extended Delta:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               PACKAGE AUX-EXT: COMPREHENSIVE COMPONENT BREAKDOWN                       │
├────────────────────────────────────────────────────────┬─────────────┬─────────────────┤
│ Component File                                         │ Size (MB)   │ Role            │
├────────────────────────────────────────────────────────┼─────────────┼─────────────────┤
│ 1. HydroRIVERS_v10_as_shp.zip                          │   90.51 MB  │ Stream Burning  │
│ 2. hybas_as_lev01-12_v1c.zip (HydroBASINS Asia)        │  376.39 MB  │ Watershed Deline│
│ 3. ESA_WorldCover_10m_2021_v200_N18E084_Map.tif        │   54.27 MB  │ Core Land Cover │
│ 4. ESA_WorldCover_10m_2021_v200_N21E084_Map.tif        │  127.99 MB  │ Ext Land Cover  │
│ 5. occurrence_80E_20N.tif                              │   27.24 MB  │ Southern Water  │
│ 6. occurrence_80E_30N.tif                              │   82.18 MB  │ Northern Water  │
│ 7. seasonality_80E_20N.tif                             │   13.98 MB  │ Southern Season │
│ 8. seasonality_80E_30N.tif                             │   29.24 MB  │ Northern Season │
│ 9. gmw_v3_2008_gtiff.zip (Global Mangrove Watch)       │   66.66 MB  │ 2008 Mangroves  │
├────────────────────────────────────────────────────────┼─────────────┼─────────────────┤
│ TOTAL (Package AUX-EXT)                                │  868.46 MB  │ 9 Files         │
└────────────────────────────────────────────────────────┴─────────────┴─────────────────┘
```
*Exact Byte Count*:
$90,510,995 + 376,386,706 + 54,269,282 + 127,991,194 + 27,240,640 + 82,179,606 + 13,975,950 + 29,238,608 + 66,664,471 = \mathbf{868,457,452\text{ bytes}}$ (**`868.46 MB` decimal** / $828.23\text{ MiB}$ binary).

---

## 6. Scientific & Governance Limitations

1. **HydroRIVERS vs. Delta Distributaries**: HydroRIVERS provides primary stream centerlines ($\ge 10\text{ km}^2$), but its D8 dendritic structure omits loop bifurcations, irrigation canals, and tidal creeks. Supplemental manual or canal lines will be required during hydro-conditioning.
2. **HydroBASINS vs. CWC Boundaries**: HydroBASINS provides topographically consistent watershed boundaries derived from SRTM elevation, which differ slightly from the administrative river basin boundaries published by CWC.
3. **Permanent Water vs. Dynamic Tidal Water**: JRC permanent water (`occurrence >= 80%`) defines permanent deep-water channels, but cannot resolve macrotidal mudflats or seasonal coastal flooding.
4. **DSM vs. Bare-Earth DTM**: Copernicus DEM GLO-30 reflects canopy and structural heights. Stream burning and depression breaching are experimental techniques to mitigate vegetation dams, not a true bare-earth conversion.
5. **Experimental Conditioning Parameters**: Universal stream-burning depths (e.g. 1.5m or 3.0m) are **uncalibrated hypotheses**, not approved parameters.

---

## 7. Unresolved Scientific Questions

1. **Question 1**: Will HydroRIVERS D8 single-flow dendritic reaches sufficiently capture anabranching distributaries below Naraj Barrage, or will supplemental canal centerlines be mandatory?
2. **Question 2**: What empirical stream-burning depth (e.g. 1.5m vs 3.0m) avoids over-excavating alluvial delta flats while overcoming DSM canopy damming in Bhitarkanika?
3. **Question 3**: How will dynamic tidal flats and seasonal aquaculture ponds along Chilika Lagoon be validated without concurrent SAR ground-truth?

---

## 8. Strict Governance Invariants Preserved

1. **Zero Data Downloads**: No rasters, vectors, rainfall granules, or shapefiles were acquired.
2. **Zero DEM Modifications**: The nine raw Copernicus DEM GeoTIFFs in `data/raw/phase7/dem/mahanadi_dfo3382/` remain bit-exact, unaltered, and intact.
3. **Zero Terrain Derivatives Generated**: No slope, aspect, curvature, TWI, or HAND rasters were computed.
4. **Zero Model Training**: No machine learning models were trained, tuned, or updated; no labels were fabricated.
5. **DFO 2507 Holdout Quarantine**: DFO 2507 remains quarantined as an `ALREADY_INSPECTED_HOLDOUT`.
6. **Phase 6 Hydrodynamic Physics Supremacy**: The Phase 6 deterministic hydrodynamic solver ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the **sole authorized operational authority**.
7. **Zero Git Commits/Pushes**: No Git staging, committing, or pushing was executed.

---

## 9. Deliverables & Regression Testing

1. **Authoritative Source Verification Manifest**:
   [`data/manifests/phase7f38_source_verification_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7f38_source_verification_manifest.yaml)
2. **Comprehensive Source Verification Report (Amended)**:
   [`docs/phase7/PHASE_7F_3_8_SOURCE_VERIFICATION_REPORT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_8_SOURCE_VERIFICATION_REPORT.md)

The Phase 7 regression test suite was executed:
```bash
python -m pytest backend/tests/test_phase7c_multievent_dataset.py \
                 backend/tests/test_phase7_real_flood_dataset.py \
                 backend/tests/test_phase7d_kaggle_preflight.py \
                 backend/tests/test_phase7e_kaggle_package.py -v
```
**Test Results**: **`31 passed in 10.36s (100% pass rate)`**.

### Git Working Tree Status (Uncommitted):
```text
?? data/manifests/phase7f36_dfo3382_dem_acquisition_manifest.yaml
?? data/manifests/phase7f36_dfo3382_dem_preflight_manifest.yaml
?? data/manifests/phase7f37_terrain_readiness_manifest.yaml
?? data/manifests/phase7f38_source_verification_manifest.yaml
?? data/raw/phase7/dem/mahanadi_dfo3382/
?? docs/phase7/DFO_3382_dem_acquisition_summary.json
?? docs/phase7/DFO_3382_dem_preflight_analysis.json
?? docs/phase7/DFO_3382_inspection_summary.json
?? docs/phase7/DFO_3382_mahanadi_dem_spatial_breakdown.json
?? docs/phase7/PHASE_7F_3_6_DEM_COVERAGE_PREFLIGHT.md
?? docs/phase7/PHASE_7F_3_6_DEM_PREPARATION_REPORT.md
?? docs/phase7/PHASE_7F_3_7_TERRAIN_READINESS_AUDIT.md
?? docs/phase7/PHASE_7F_3_8_SOURCE_VERIFICATION_REPORT.md
?? scripts/acquire_phase7f36_dem.py
```

---

## 10. Final Decision

### Decision: `AUX_PACKAGE_READY_FOR_APPROVAL`

> **APPROVAL GATE NOTICE**:
> Both candidate auxiliary packages—**Package AUX-MIN ($254.20\text{ MB}$ decimal)** and **Package AUX-EXT ($868.46\text{ MB}$ decimal)**—are fully verified with exact byte counts, download URLs, and methodological qualifications.
>
> In accordance with strict governance rules, execution remains halted; **no data acquisition or processing will occur until separately authorized**.
