# AQUORA — PHASE 7F.3.4: CANDIDATE DATA ACQUISITION PREFLIGHT
### Technical Source Availability, Geospatial Compatibility & Preflight Assessment for Priority Flood Candidates

**Document Version:** `2.0.0-phase7f34-acquisition-preflight`  
**Phase:** Phase 7F.3.4 Candidate Data Acquisition Preflight (with Final Technical Clarifications)  
**Task Type:** READ-ONLY ACQUISITION PREFLIGHT (Zero data downloads, zero full-archive retrievals, zero dataset modifications, zero model training, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine ([engines/flood/](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/))  
**Date:** 2026-10-31  

---

## 1. Executive Summary

Following the Data Acquisition Strategy formulated in [`docs/phase7/PHASE_7F_3_3_DATA_ACQUISITION_STRATEGY.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_3_DATA_ACQUISITION_STRATEGY.md), this document presents the **READ-ONLY Acquisition Preflight** for the three top priority candidate events:

1. **DFO 3382** — Mahanadi Basin / Odisha Delta (September 2008) — *East Coast Deltaic Plain*
2. **DFO 3551** — Krishna & Tungabhadra Basins / Andhra Pradesh & Karnataka (October 2009) — *Semi-Arid Deccan Plateau*
3. **Great Kerala Floods (2018)** — Periyar & Pamba Basins / Western Ghats (August 2018) — *High-Relief Escarpment to Coastal Plain (Sentinel-1 SAR Candidate)*

### Core Objectives Established in this Preflight:
* **Verify Source Availability Without Downloading**: Confirm exact archive paths, provider URLs, file sizes, and HTTP response headers without pulling data payloads or modifying repository storage.
* **Distinguish Provider Metadata from Actual Valid Data**: Explicitly document that verifying an archive's existence (e.g. HTTP 200 or catalog entry) does **not** establish the validity, cloud-free fraction, or absence of internal NoData masks within the rasters.
* **Evaluate Terrain Mosaicking Requirements**: Identify exact Copernicus DEM 30m degree tiles required for continuous basin coverage and determine feasibility.
* **Audit Precipitation Windows**: Contrast locally existing CHIRPS dates against required 3-day antecedent windows and investigate event-specific NASA GPM IMERG Final Run half-hourly granule identifiers.
* **Qualify Sentinel-1 SAR Label Readiness**: Detail the orbital parameters, pass geometries, and baseline requirements for Kerala 2018, explicitly confirming that raw SAR imagery is **not** validated ground truth.
* **Review Technical Screening Gates**: Re-examine the 10 provisional acceptance criteria from Phase 7F.3.3, ensuring provisional thresholds (e.g. 95% DEM coverage, 5 km buffer, $-3\text{ dB}$ VH backscatter change, $> 5^\circ$ slope shadow mask) are treated as scientific hypotheses requiring local validation rather than mandatory dogmatic rules.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 7F.3.4 PREFLIGHT ASSESSMENT SUMMARY                         │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Candidate Event    Basin / State        Ground Truth Source   Preflight Readiness Status   Recommendation
  ────────────────────────────────────────────────────────────────────────────────────────
  DFO 3382 (2008)    Mahanadi, Odisha     GFD v1.4 (MODIS 250m) PROMISING_SOURCE_PREFLIGHT   CONDITIONAL GO (Priority 1)
  DFO 3551 (2009)    Krishna, AP/KA       GFD v1.4 (MODIS 250m) PROMISING_SOURCE_PREFLIGHT   CONDITIONAL GO (Priority 2)
  Kerala Floods 2018 Periyar/Pamba, KL    Sentinel-1 C-SAR GRD  SAR_LABEL_DEVELOPMENT_PENDING NO-GO FOR DIRECT ACQ
                                                                                            (Requires SAR Pipeline)
  ────────────────────────────────────────────────────────────────────────────────────────
```

---

## 2. DFO 3382 Source Preflight (Mahanadi Basin / Odisha, 2008)

### 2.1 GFD Archive & Metadata Verification
* **Authoritative Identifier**: DFO ID `3382` in Dartmouth Flood Observatory catalog; entry in Global Flood Database (GFD v1.4, Tellman et al. 2021).
* **Source Archive Location**: Google Cloud Storage public repository:
  `gs://gfd_v1_4/DFO_3382_From_20080922_to_20080929.zip`
* **Direct Access URL**:
  `https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o/DFO_3382_From_20080922_to_20080929.zip?alt=media`
* **HTTP Metadata Status**:
  * HTTP status: `200 OK` (Preflight checked in Phase 7C acquisition audit, [PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md:L45](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md#L45)).
  * Archive size: **39,644,622 bytes (39.64 MB)**.
* **Documented Event Attributes**:
  * Documented dates: `began: 2008-09-22`, `ended: 2008-09-29`.
  * Centroid: $20.9522^\circ\text{N}, 84.4064^\circ\text{E}$.
  * Mapped area in catalog: $464,318\text{ km}^2$.
  * Primary reported cause: Monsoonal depression and emergency dam release from Hirakud Dam.
* **Local Corroboration & Temporal Discrepancy**:
  * Validated in [`data/raw/phase7/ground_truth/india_flood_inventory_v3.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/india_flood_inventory_v3.csv) under record `UEI-IMD-FL-2008-0095` (administrative disaster window: **15-09-2008 to 28-09-2008**; affected districts: Cuttack, Kendrapara, Jagatsinghpur, Puri, Khordha; 140 fatalities).
  * **Temporal Discrepancy**: The GFD archive window covers **2008-09-22 to 2008-09-29**, whereas the administrative/IMD flood period spans **2008-09-15 to 2008-09-28**. While there is a 7-day temporal overlap during the severe inundation phase, this overlap does **not** establish that GFD observations capture the full flood evolution (e.g. initial rising limb, embankment breaches, or peak inundation extent between 15 and 21 September). Flood-phase compatibility is formally classified as **PENDING RASTER INSPECTION**.
* **Metadata vs. Content Qualification**:
  * The HTTP 200 response and file size establish that the ZIP container exists on Google Cloud Storage.
  * **Archive contents have NOT been unpacked or inspected**. The actual internal multi-band GeoTIFF dimensions, valid observation counts, permanent water fraction, and cloud-mask percentage (`clear_perc`) remain **UNVERIFIED**.

### 2.2 Terrain Requirements (Copernicus DEM GLO-30)
* **Target Basin Bounding Footprint**:
  The core Mahanadi Delta plain spans approximately $19.5^\circ\text{N}–21.0^\circ\text{N}$ and $85.0^\circ\text{E}–87.0^\circ\text{E}$.
* **Required DEM Tiles (1° × 1° Copernicus COG 30m)**:
  1. `Copernicus_DSM_COG_10_N20_00_E085_00_DEM.tif` (Bhubaneswar, Cuttack, Khordha)
  2. `Copernicus_DSM_COG_10_N20_00_E086_00_DEM.tif` (Kendrapara, Jagatsinghpur, delta mouth)
  3. `Copernicus_DSM_COG_10_N19_00_E085_00_DEM.tif` (Puri, northern Chilika)
  4. `Copernicus_DSM_COG_10_N19_00_E086_00_DEM.tif` (Coastal Bay of Bengal margin)
* **Local Verification**: **Zero** of these 4 tiles currently exist on local disk in `data/raw/phase7/dem/`.
* **Mosaic Feasibility**: All 4 tiles exist on AWS Open Data (`s3://copernicus-dem-30m/`). A seamless $2^\circ \times 2^\circ$ mosaic ($7,200 \times 7,200$ cells at 30m, $\approx 200\text{ MB}$ uncompressed Float32) is technically feasible and eliminates boundary clipping across the delta.

### 2.3 Precipitation Requirements
* **Local CHIRPS Verification**:
  * Date check: In `data/raw/phase7/rainfall/chirps/daily/`, zero daily CHIRPS files exist for September 2008. (Existing 2008 files are confined to August 2008 for DFO 3372 Assam).
  * Missing daily files required: `chirps-v2.0.2008.09.20.tif.gz` ($t_{-2}$), `2008.09.21` ($t_{-1}$), and `2008.09.22` ($t_0$) through `2008.09.26`.
* **NASA GPM IMERG Half-Hourly Status**:
  * Event occurred in September 2008, which predates the GPM Core Observatory launch (February 2014).
  * Data exists only in the retroactive TRMM-era reprocessed IMERG V07B archive (`GPM_3IMERGHH`).
  * Target granule window: `2008-09-20 00:00 UTC` to `2008-09-26 23:30 UTC` (336 half-hourly granules).
  * Granule availability, spatial grid validity over the Bay of Bengal coast, and microwave calibration remain **completely unverified**. Sub-daily rainfall remains **UNAVAILABLE**.

---

## 3. DFO 3551 Source Preflight (Krishna & Tungabhadra Basins, 2009)

### 3.1 GFD Archive & Metadata Verification
* **Authoritative Identifier**: DFO ID `3551`; GFD v1.4 event catalog.
* **Source Archive Location**:
  `gs://gfd_v1_4/DFO_3551_From_20090925_to_20091012.zip`
* **Direct Access URL**:
  `https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o/DFO_3551_From_20090925_to_20091012.zip?alt=media`
* **HTTP Metadata Status**:
  * HTTP status: `200 OK` (Verified in Phase 7C preflight, [PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md:L46](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md#L46)).
  * Archive size: **27,086,981 bytes (27.09 MB)**.
* **Documented Event Attributes**:
  * Documented dates: `began: 2009-09-25`, `ended: 2009-10-12`.
  * Centroid: $15.7081^\circ\text{N}, 78.2330^\circ\text{E}$.
  * Mapped area in catalog: $309,689\text{ km}^2$.
  * Documented casualties: 303 fatalities in GFD; 49 fatalities in Kurnool/Krishna in IMD record.
* **Local Corroboration**:
  * Validated in [`data/raw/phase7/ground_truth/india_flood_inventory_v3.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/india_flood_inventory_v3.csv) under `UEI-IMD-FL-2009-0001` (01-10-2009 to 07-10-2009; districts: Guntur, Krishna, Kurnool, Prakasam; peak historical flood of Kurnool city).
* **Metadata vs. Content Qualification**:
  * HTTP metadata confirms archive existence on GCS.
  * **Archive contents have NOT been unpacked**. Internal valid pixel counts, extent of cloud cover, and episodic flood counts remain **UNVERIFIED**.

### 3.2 Terrain Requirements (Copernicus DEM GLO-30)
* **Target Basin Bounding Footprint**:
  The Kurnool city confluence (Krishna and Tungabhadra rivers) upstream of Srisailam Dam spans $15.0^\circ\text{N}–17.0^\circ\text{N}$ and $77.0^\circ\text{E}–79.0^\circ\text{E}$.
* **Required DEM Tiles (1° × 1° Copernicus COG 30m)**:
  1. `Copernicus_DSM_COG_10_N15_00_E077_00_DEM.tif` (Western Kurnool / Tungabhadra inflow)
  2. `Copernicus_DSM_COG_10_N15_00_E078_00_DEM.tif` (Kurnool municipal core, confluence)
  3. `Copernicus_DSM_COG_10_N16_00_E077_00_DEM.tif` (Northern upstream Krishna approach)
  4. `Copernicus_DSM_COG_10_N16_00_E078_00_DEM.tif` (Srisailam reservoir gorge entrance)
* **Local Verification**: **Zero** of these 4 tiles exist on local disk in `data/raw/phase7/dem/`.
* **Mosaic Feasibility**: High. The semi-arid Deccan plateau exhibits incised bedrock river valleys with slopes between $1^\circ$ and $15^\circ$, which are well-represented by Copernicus DEM without flat-alluvial sink looping.

### 3.3 Precipitation Requirements
* **Local CHIRPS Verification**:
  * Peak date file **exists on local disk**:
    [`data/raw/phase7/rainfall/chirps/daily/chirps-v2.0.2009.10.02.tif.gz`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/rainfall/chirps/daily/chirps-v2.0.2009.10.02.tif.gz) (2,785,152 bytes | SHA-256: `955a16d8...`).
  * Missing antecedent files required for 72h window: `2009.09.30` ($t_{-2}$) and `2009.10.01` ($t_{-1}$) are **NOT on local disk**.
* **NASA GPM IMERG Half-Hourly Status**:
  * Pre-GPM TRMM retro-archive.
  * Target granule window: `2009-09-30 00:00 UTC` to `2009-10-04 23:30 UTC` (240 half-hourly granules).
  * Data availability and sensor microwave quality flags remain uninspected. Sub-daily rainfall remains **UNAVAILABLE**.

---

## 4. Kerala 2018 SAR Preflight (Periyar & Pamba Basins)

### 4.1 Satellite Platform & Orbital Parameters
* **Satellites**: European Space Agency Copernicus Sentinel-1A and Sentinel-1B constellation.
* **Instrument Mode**: C-Band Synthetic Aperture Radar (CSAR) in Interferometric Wide (IW) swath mode.
* **Product Level**: Ground Range Detected (GRD), High Resolution ($10\text{ m} \times 10\text{ m}$ pixel spacing, $20\text{ m} \times 22\text{ m}$ spatial resolution).
* **Polarization**: Dual-polarization ($\text{VV} + \text{VH}$). Cross-polarized $\text{VH}$ channel is optimal for open-water specular reflection detection.

### 4.2 Orbit Tracks & Acquisition Geometry Over Kerala
Two candidate relative orbital tracks covering parts of the affected river basins in Kerala were identified in preliminary screening:

*(Preliminary Evidence Note: The orbits listed below represent preliminary screening evidence only and do NOT constitute an exhaustive catalog search across the entire Periyar, Pamba, and Chalakudy catchments. A complete event-area acquisition search—evaluating all intersecting relative orbits, pass directions, acquisition timestamps, ground footprints, and pre-event baseline pairs—is mandatory prior to any future SAR acquisition authorization).*

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               SENTINEL-1 PRELIMINARY ORBITS & AUGUST 2018 PASS DATES                   │
└────────────────────────────────────────────────────────────────────────────────────────┘

  TRACK 1: Relative Orbit 63 (Ascending Pass) — Preliminary Candidate
  ├── Geographic Coverage: Northern and Central Kerala (Zone 1: Thrissur, Ernakulam, Idukki).
  ├── Baseline Dry Pass: 2018-07-21 / 2018-08-02 (Pre-event reference).
  ├── Critical Inundation Pass: 2018-08-14 ~12:45 UTC (Rising limb / reservoir spill onset).
  └── Post-Flood Pass: 2018-08-26 ~12:45 UTC (Recession stage).

  TRACK 2: Relative Orbit 165 (Descending Pass) — Preliminary Candidate
  ├── Geographic Coverage: Central and Southern Kerala (Zone 2/3: Alappuzha, Kottayam, Pathanamthitta).
  ├── Baseline Dry Pass: 2018-07-28 / 2018-08-09 (Pre-event reference).
  ├── Peak Flood Pass: 2018-08-21 ~00:55 UTC (Capturing backwater flooding in Kuttanad).
  └── Subsequent Pass: 2018-09-02 ~00:55 UTC (Recession stage).
```

### 4.3 Critical Temporal Revisit & Coverage Constraints:
* The catastrophic flood peak in the Periyar and Chalakudy river basins occurred between **August 15 and August 17, 2018**.
* Orbit 63 flew on **August 14, 2018** (capturing rising flood stages and initial riparian inundation prior to peak cresting).
* Orbit 165 flew on **August 21, 2018** (capturing massive inundation in the low-lying agricultural polders of Kuttanad / Alappuzha, 5 days after peak cresting).
* **Finding**: Preliminary Sentinel-1 orbits did **not** capture a satellite pass at the absolute peak cresting hour (August 16). This temporal revisit gap is a physical constraint of spaceborne radar.
* **Exhaustive Search Prerequisite**: Before approving any SAR acquisition, a full catalog query across all Sentinel-1A and Sentinel-1B datatakes must confirm whether adjacent swaths or alternate look angles captured intermediate flood phases, and whether identical viewing geometries exist for pre-event baselines.

### 4.4 Status of Ground Truth:
* **Raw SAR Imagery is NOT Validated Ground Truth**: Raw `.SAFE` or GRD `.tif` files contain speckle noise, wind roughening over open water, and layover/shadow across the steep Western Ghats escarpment.
* **International Charter Activation 584 & ISRO/NRSC Bhuvan Maps**:
  * International Charter Call ID 671 (Activation 584 on August 16, 2018) produced semi-automated rapid mapping inundation vectors.
  * ISRO NRSC published daily flood inundation maps on the Bhuvan portal.
  * These vector maps serve as candidate independent validation references, but must be cross-checked before being ingested as authoritative training labels.
* **Preflight Verdict**: **`SAR_LABEL_DEVELOPMENT_PENDING`**. The event cannot be admitted directly as a training or validation set until the five-stage SAR processing workflow is implemented and validated.

---

## 5. Terrain Tile and Coverage Requirements

### 5.1 Geographic Coverage Analysis

| Candidate Event | Basin / Region | Core Inundation Bounding Box | Topographic Relief Range | Copernicus DEM 30m Tiles Required | Local Tile Status | Multi-Tile Mosaic Feasibility |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DFO 3382** | Mahanadi Delta, Odisha | $19.5^\circ\text{N}–21.0^\circ\text{N}, 85.0^\circ\text{E}–87.0^\circ\text{E}$ | $0\text{ m}$ (Coast) to $85\text{ m}$ (Delta apex) | `N19E085`, `N19E086`, `N20E085`, `N20E086` | **0 of 4 present** | Feasible ($2^\circ \times 2^\circ$ mosaic, AWS Open Data) |
| **DFO 3551** | Krishna Basin, AP/KA | $15.0^\circ\text{N}–17.0^\circ\text{N}, 77.0^\circ\text{E}–79.0^\circ\text{E}$ | $240\text{ m}$ (Kurnool) to $650\text{ m}$ (Uplands) | `N15E077`, `N15E078`, `N16E077`, `N16E078` | **0 of 4 present** | Feasible ($2^\circ \times 2^\circ$ mosaic, AWS Open Data) |
| **Kerala 2018**| Periyar/Pamba, Kerala | $9.0^\circ\text{N}–11.0^\circ\text{N}, 76.0^\circ\text{E}–78.0^\circ\text{E}$ | $0\text{ m}$ (Coast) to $2,695\text{ m}$ (Anamudi) | `N09E076`, `N09E077`, `N10E076`, `N10E077` | **0 of 4 present** | Feasible ($2^\circ \times 2^\circ$ mosaic, AWS Open Data) |
*(Critical Coverage Qualification: The four-tile $2^\circ \times 2^\circ$ sets listed above represent **candidate tile requirements** based on known administrative and inundation bounding boxes, **NOT verified complete hydrological catchment coverage**. Complete catchment verification requires evaluating whether upper contributing headwaters (e.g. Western Ghats ridge lines for Kerala, Western Ghats / Bhima-Krishna headwaters for Krishna, or upper Mahanadi tributaries upstream of Naraj/Cuttack) fall outside the 4-tile boundaries. Actual tile-footprint intersection and upstream contributing catchment boundary assessment are mandatory prior to accepting terrain coverage).*

### 5.2 Mosaicking Safeguards & Catchment Verification
1. **Zero Resampling Distortion**: Mosaicking adjacent $1^\circ \times 1^\circ$ COG tiles must preserve native $30\text{ m}$ pixel resolution ($0.00027778^\circ$) using GDAL VRT or `rasterio.merge` with identical coordinate references (`EPSG:4326`).
2. **Boundary Buffer & Catchment Integrity**: The mosaic domain must extend beyond the core mapped flood polygon to prevent boundary clipping when computing derivative kernels (Sobel/Horn slope, planar curvature). However, arbitrary buffers (e.g. 5 km) must be superseded by true ridge divides and hydrological catchment boundaries to avoid truncating contributing drainage areas.
3. **Pre-Acquisition Intersection Check**: Prior to approving any DEM download, the exact ground-truth flood polygon must be spatially intersected with the proposed tile footprints to quantify the precise percentage of flood cells covered and verify zero tile-edge clipping.

---

## 6. CHIRPS and IMERG Event-Date Availability

### 6.1 Daily CHIRPS Physical File Audit

| Candidate Event | Event Date Window | Required 72h Antecedent Dates | Local File Status in `data/raw/phase7/rainfall/chirps/daily/` | Remote Source Availability |
| :--- | :--- | :--- | :--- | :--- |
| **DFO 3382** (Mahanadi) | 2008-09-22 to 2008-09-29 | 2008-09-20, 2008-09-21, 2008-09-22 | **0 of 3 files present on local disk** | Available on UCSB CHC FTP/HTTP archive |
| **DFO 3551** (Krishna) | 2009-09-25 to 2009-10-12 | 2009-09-30, 2009-10-01, 2009-10-02 | **1 of 3 files present**: `chirps-v2.0.2009.10.02.tif.gz` present; $t_{-1}, t_{-2}$ missing | Antecedent files available on UCSB CHC |
| **Kerala 2018** | 2018-08-08 to 2018-08-20 | 2018-08-14, 2018-08-15, 2018-08-16 | **1 of 3 files present**: `chirps-v2.0.2018.08.16.tif.gz` present; $t_{-1}, t_{-2}$ missing | Antecedent files available on UCSB CHC |

*Conclusion*: While peak-day files for DFO 3551 and Kerala 2018 are physically present on local disk, **complete 72h antecedent sequences cannot currently be constructed from disk assets alone**.

### 6.2 NASA GPM IMERG Half-Hourly Final Run Status

| Candidate Event | Target IMERG Window | Estimated Half-Hourly Granules | Estimated Size (HDF5) | Archive Host | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DFO 3382** (2008) | 2008-09-20 to 2008-09-26 | 336 granules | $\approx 2.75\text{ GB}$ | NASA GES DISC (TRMM era retro-archive) | Catalog entry exists; granules **uninspected** |
| **DFO 3551** (2009) | 2009-09-30 to 2009-10-04 | 240 granules | $\approx 1.95\text{ GB}$ | NASA GES DISC (TRMM era retro-archive) | Catalog entry exists; granules **uninspected** |
| **Kerala 2018** | 2018-08-13 to 2018-08-18 | 288 granules | $\approx 2.35\text{ GB}$ | NASA GES DISC (GPM operational era) | Catalog entry exists; granules **uninspected** |

*Important Finding*: General catalog availability does **not** prove data quality. Until actual HDF5 granules are downloaded and inspected under a separately authorized phase, valid precipitation rates, spatial beam filling, and microwave quality flags remain unverified. Sub-daily rainfall features remain **UNAVAILABLE**.

---

## 7. Historical Land-Cover Compatibility

| Candidate Event | Disaster Year | Available Local Land Cover | Local Temporal Gap | Candidate Historical Source | Spatial Res | Historical Year Match | Geomorphic Stability Assessment |
| :--- | :---: | :--- | :---: | :--- | :---: | :---: | :--- |
| **DFO 3382** (Odisha) | 2008 | ESA WorldCover 2021 | **13 years** | MODIS MCD12Q1 / ESA CCI | $500\text{ m} / 300\text{ m}$ | 2008 (Exact) | Moderate: Delta coastal mangroves and polders subject to coastal erosion and shrimp farm conversion. |
| **DFO 3551** (Krishna) | 2009 | ESA WorldCover 2021 | **12 years** | MODIS MCD12Q1 / ESA CCI | $500\text{ m} / 300\text{ m}$ | 2009 (Exact) | **High**: Semi-arid hard-rock Deccan plateau; rocky valleys and rainfed agriculture exhibit minimal geomorphic change. |
| **Kerala 2018** | 2018 | ESA WorldCover 2020 | **2 years** | ESA WorldCover 2020 | $10\text{ m}$ | 2020 (Close) | **High**: Western Ghats forest boundaries and coastal settlement footprints are highly stable over 24 months. |

*Finding*:
* For Kerala 2018, ESA WorldCover 2020 (10m) is temporally compatible (2-year offset).
* For DFO 3382 (2008) and DFO 3551 (2009), the 12–13 year offset of ESA WorldCover 2021 requires screening. For the stable Deccan plateau of DFO 3551, modern land cover is largely acceptable; for the dynamic delta of DFO 3382, contemporaneous 300m ESA CCI land cover should be considered.

---

## 8. Hydrography & River Network Availability

* **HydroRIVERS v1.0 (HydroSHEDS / WWF)**:
  * *Coverage*: Vector streamline network of river reaches with catchment area $\ge 10\text{ km}^2$.
  * *Status on Local Disk*: `data/raw/hydrography/hydrorivers/` is empty (`0 files`).
  * *Public Availability*: Freely downloadable as a global shapefile from HydroSHEDS portal under CC-BY-4.0.
  * *Limitation*: Omits small distributary channels in the Mahanadi Delta and Kuttanad backwaters.
* **MERIT-Hydro 90m (Yamazaki et al. 2019)**:
  * *Coverage*: Continental hydrography and precomputed Height Above Nearest Drainage (HAND) at 3 arc-second ($\approx 90\text{ m}$) resolution.
  * *Status on Local Disk*: Absent from local storage.
  * *Public Availability*: Available via University of Tokyo portal and Google Earth Engine.
  * *Advantage*: Precomputed HAND eliminates tile-boundary truncation and artificial sink loops.
* **Governance Status**: HAND generation remains a **STRICT CONSERVATIVE NO-GO** until continental MERIT-Hydro or hydro-enforced HydroRIVERS vectors are formally staged.

---

## 9. Technical Acceptance Review: Refining the Screening Gates

The provisional screening gates proposed in Phase 7F.3.3 have been re-evaluated to ensure they reflect scientific reality rather than arbitrary thresholds:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               REFINED SCIENTIFIC SCREENING CRITERIA QUALIFICATIONS                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **DEM Coverage: Core Inundation vs. Terrain Buffer**:
   * *Provisional Rule*: $\ge 95\%$ of core mapped flood polygon plus $5\text{ km}$ buffer.
   * *Scientific Qualification*: The $5\text{ km}$ buffer is **provisional and terrain-dependent**. In steep terrain (e.g. Kerala Western Ghats), a $1\text{ to }2\text{ km}$ buffer reaches the mountain ridge divide immediately. In flat coastal deltas (Mahanadi), elevation gradients extend over tens of kilometers, but ocean boundaries require no land buffer.
   * *Refinement*: Coverage must be evaluated as $\ge 90\%$ of the core contiguous flood polygon, with the buffer defined by the nearest topographic ridge or coastal boundary.

2. **SAR Backscatter Change Threshold ($\Delta \sigma^0 \le -3.0\text{ dB}$)**:
   * *Provisional Rule*: Assigning flood labels where cross-polarized backscatter drops by $\ge 3\text{ dB}$.
   * *Scientific Qualification*: $-3\text{ dB}$ is an **empirical hypothesis requiring local calibration**, NOT a universal physical law. In calm water over bare soil, backscatter drops often exceed $-8\text{ dB}$. In flooded vegetation (mangroves, paddy fields), double-bounce scattering can actually *increase* backscatter ($\Delta \sigma^0 > 0\text{ dB}$).
   * *Refinement*: Threshold selection must be determined per event using bimodal histogram thresholding (Otsu or Kittler-Illingworth) and cross-validated against optical patches.

3. **Slope Shadow Mask ($> 5^\circ$)**:
   * *Provisional Rule*: Masking all terrain slopes $> 5^\circ$ to prevent radar shadow false positives.
   * *Scientific Qualification*: In steep terrain (Kerala, Kashmir), radar shadow is governed by the satellite incidence angle ($29^\circ–46^\circ$), look direction (ascending vs. descending), and local terrain aspect—not an arbitrary $5^\circ$ ground slope. Blindly masking slopes $> 5^\circ$ discards genuine flood channels in narrow mountain valleys.
   * *Refinement*: Shadow masks must be computed using true geometric line-of-sight ray-tracing from the sensor position, rather than simple slope cutoffs.

4. **Rainfall Missing Data ($0\%$ Missing Pixels)**:
   * *Provisional Rule*: Requiring strictly 0% missing precipitation pixels over the catchment.
   * *Scientific Qualification*: While a rigid 0% missing requirement may be overly restrictive for satellite precipitation products with isolated coastal or border NoData flags, missing precipitation pixels cannot automatically be filled using bilinear interpolation. Automatic spatial interpolation risks dampening convective precipitation extremes, obscuring true sensor dropouts, and propagating errors across land-sea boundaries. Missing rainfall values must remain explicitly identifiable in data pipelines rather than silently imputed.
   * *Refinement*: Do not assume 0% missing is universally necessary, but prohibit automatic interpolation. Any future handling of missing rainfall data requires formal spatial gap assessment, quantitative missing-data reporting, and feature-specific hydrologic justification before any imputation strategy could be considered. In this preflight, zero rainfall data is generated or interpolated.

---

## 10. Unverified Evidence & Outstanding Gaps

1. **Internal GFD Archive Rasters**: GCS HTTP 200 metadata confirms archive existence, but pixel dimensions, valid counts, and optical cloud percentages remain unverified until unpacked.
2. **Antecedent Rainfall Sequences**: While peak-day CHIRPS files exist for DFO 3551 and Kerala 2018, the $t_{-1}$ and $t_{-2}$ antecedent daily files are absent on local disk.
3. **Event-Specific IMERG Granules**: Half-hourly IMERG granules have not been downloaded or inspected; valid precipitation rates and microwave sensor flags remain unverified.
4. **SAR Inundation Algorithm**: No validated flood mask exists on local disk for Kerala 2018. Producing ground truth requires executing the 5-stage SAR calibration and change-detection pipeline.
5. **Continental Hydrography**: HydroRIVERS and MERIT-Hydro products are absent from local repository storage.

---

## 11. Exact Files and Source Metadata Required for Future Acquisition

If a future acquisition phase is authorized, the exact files and source endpoints to stage are:

### A. Ground-Truth Inundation Targets:
* **DFO 3382**: `https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o/DFO_3382_From_20080922_to_20080929.zip?alt=media` (39.64 MB)
* **DFO 3551**: `https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o/DFO_3551_From_20090925_to_20091012.zip?alt=media` (27.09 MB)
* **Kerala 2018 (Sentinel-1)**:
  * Orbit 63 (Ascending): `S1A_IW_GRDH_1SDV_20180814T1245...` (Event) & `S1A_IW_GRDH_1SDV_20180802T1245...` (Baseline)
  * Orbit 165 (Descending): `S1A_IW_GRDH_1SDV_20180821T0055...` (Event) & `S1A_IW_GRDH_1SDV_20180809T0055...` (Baseline)

### B. Copernicus DEM GLO-30 30m COG Tiles (AWS Open Data):
* **Mahanadi Delta (DFO 3382)**: `N19_00_E085_00`, `N19_00_E086_00`, `N20_00_E085_00`, `N20_00_E086_00`
* **Krishna Basin (DFO 3551)**: `N15_00_E077_00`, `N15_00_E078_00`, `N16_00_E077_00`, `N16_00_E078_00`
* **Kerala Basins (Kerala 2018)**: `N09_00_E076_00`, `N09_00_E077_00`, `N10_00_E076_00`, `N10_00_E077_00`

### C. Daily CHIRPS v2.0 GeoTIFFs (UCSB CHC):
* **DFO 3382**: `chirps-v2.0.2008.09.20.tif.gz` to `2008.09.26.tif.gz` (7 daily files)
* **DFO 3551**: `chirps-v2.0.2009.09.30.tif.gz` & `chirps-v2.0.2009.10.01.tif.gz` (2 antecedent daily files)
* **Kerala 2018**: `chirps-v2.0.2018.08.13.tif.gz` to `2018.08.18.tif.gz` (6 daily files)

---

## 12. Final GO / CONDITIONAL GO / NO-GO Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   AQUORA PHASE 7F.3.4 FINAL PREFLIGHT DECISION MATRIX                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

| Candidate Event | Basin / State | Physical Disaster Reality | Ground-Truth Verification | Terrain Mosaicking Feasibility | Precipitation Window Completeness | Preflight Recommendation | Operational Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **DFO 3382** (2008) | Mahanadi Delta, Odisha | **VERIFIED** (CWC, OSDMA, 140 deaths in IMD record) | Verified GCS ZIP (39.64 MB); internal rasters uninspected | **HIGH** (4 tiles form contiguous delta mosaic) | **PARTIAL** (CHIRPS files unacquired on local disk) | **CONDITIONAL GO (Priority 1)** | Recommended first for future authorized download. |
| **DFO 3551** (2009) | Krishna Basin, AP/KA | **VERIFIED** (CWC Srisailam inflow, AP SDMA, 49 deaths) | Verified GCS ZIP (27.09 MB); internal rasters uninspected | **HIGH** (4 tiles cover Kurnool bedrock valley) | **PARTIAL** (Peak day on disk; antecedent days unacquired) | **CONDITIONAL GO (Priority 2)** | Highly viable; hard-rock terrain minimizes geomorphic drift. |
| **Kerala Floods 2018**| Periyar/Pamba, Kerala | **VERIFIED** (CWC, Charter 584, 339 deaths in IMD record) | Raw SAR exists; **validated flood mask UNPRODUCED** | **HIGH** (4 tiles cover steep escarpment to coast) | **PARTIAL** (Peak day on disk; antecedent days unacquired) | **NO-GO FOR DIRECT ACQ** | **DEFERRED TO SAR LABEL PIPELINE**. Cannot acquire as ready ground truth. |

---

## 13. Final Technical Clarifications

Following technical acceptance review of the Phase 7F.3.4 preflight analysis, the following technical clarifications, constraints, and methodological standards are formally incorporated into this preflight report:

### 13.1 Rainfall Interpolation & Missing Data Policy
* **Prohibition of Automatic Imputation**: Any implication that up to 3% missing precipitation pixels could automatically or routinely be filled using bilinear interpolation is formally removed. Automatic spatial interpolation across satellite precipitation grids risks attenuating localized convective precipitation peaks, masking sensor retrieval dropouts, and introducing artificial non-zero precipitation artifacts across complex terrain and coastal boundaries.
* **Persistent Identifiability of Missing Values**: Missing or invalid rainfall pixels must remain strictly identifiable (as explicit `NaN`, bitmask flags, or dedicated quality bands) throughout the data pipeline rather than being silently imputed or overwritten.
* **Prerequisites for Any Future Imputation**: Prior to applying any spatial or temporal imputation to precipitation data in future phases, the pipeline must provide:
  1. A formal spatial gap assessment characterizing the distribution, spatial extent, and clustering of missing pixels.
  2. Quantitative missing-data reporting documenting the exact missing fraction over both the event bounding box and the contributing hydrological catchment.
  3. Feature-specific and hydrologic justification demonstrating that the proposed imputation method does not distort peak runoff, hydrograph shape, or antecedent precipitation index calculations.
* **Preflight Data Restriction**: In accordance with the read-only mandate of this preflight, zero rainfall data has been downloaded, extracted, generated, or interpolated.

### 13.2 DFO 3382 Temporal Compatibility & Flood Evolution
* **Administrative vs. Archive Period Distinction**:
  * *Administrative / Disaster Inventory Window*: **15–28 September 2008** (CWC reports, IMD disaster record `UEI-IMD-FL-2008-0095`, documenting monsoon depression landfall, intense catchment precipitation, emergency Hirakud Dam releases, and progressive downstream flooding).
  * *GFD v1.4 Archive Coverage*: **22–29 September 2008** (`DFO_3382_From_20080922_to_20080929.zip`).
* **Flood Evolution and Observation Timing**:
  * While the 7-day overlap (22–28 September) confirms that GFD captures a period of major inundation, this temporal overlap **does not establish** that GFD satellite observations capture the complete flood evolution. Specifically, the onset, rising limb, peak discharges, and initial levee breaches that occurred between 15 and 21 September may not be reflected in the MODIS composite rasters.
  * **Classification**: Flood-phase compatibility for DFO 3382 is formally classified as **PENDING RASTER INSPECTION**. The exact temporal representation and observation days can only be determined by inspecting the internal multi-temporal observation bands once archive extraction is authorized.

### 13.3 Sentinel-1 Coverage & Exhaustive Search Prerequisite (Kerala 2018)
* **Preliminary Nature of Identified Orbits**:
  * The pass dates identified for Relative Orbit 63 (Ascending: 2018-08-02, 2018-08-14, 2018-08-26) and Relative Orbit 165 (Descending: 2018-08-09, 2018-08-21, 2018-09-02) represent preliminary orbital screening evidence only.
  * They do **not** constitute an exhaustive or complete Sentinel-1 coverage audit of the Periyar, Pamba, and Chalakudy river basins.
* **Prerequisites for SAR Acquisition Approval**:
  * Prior to approving any Sentinel-1 data acquisition for Kerala 2018, a comprehensive event-area acquisition search must be performed across the complete Copernicus Open Access / Alaska Satellite Facility catalog, explicitly documenting:
    1. All intersecting relative orbits (both Ascending and Descending swaths).
    2. Pass directions, beam incidence angles ($29^\circ–46^\circ$), and spatial ground footprints relative to the steep Western Ghats relief.
    3. Exact acquisition timestamps compared against river gauge crest hydrographs and dam gate opening records.
    4. Availability of pre-event baseline acquisitions acquired under identical orbital track, pass direction, and seasonal soil moisture conditions.
* **Ground Truth Distinction**: Raw SAR backscatter imagery is strictly distinct from validated flood extents, and producing analysis-ready ground truth requires the full 5-stage SAR processing workflow.

### 13.4 DEM Coverage: Candidate Tile Requirements vs. Catchment Boundaries
* **Candidate Tile Footprints**:
  * The proposed four-tile $2^\circ \times 2^\circ$ mosaics (`N19E085`–`N20E086` for Mahanadi; `N15E077`–`N16E078` for Krishna; `N09E076`–`N10E077` for Kerala) represent **candidate tile requirements based on known administrative inundation bounding boxes**.
  * They do **not** guarantee complete hydrological catchment coverage.
* **Catchment Assessment Prerequisites**:
  * Before accepting terrain coverage as complete for any candidate event, the pipeline must:
    1. Perform an actual spatial intersection between the uncompressed flood label raster and the candidate DEM tile footprints.
    2. Conduct an upstream hydrological catchment assessment (using HydroSHEDS / HydroRIVERS basin boundaries) to determine whether contributing headwater drainage areas are truncated by the tile boundaries, which would distort flow accumulation and HAND calculations.

### 13.5 Preservation of Acquisition Decisions & Governance Hierarchy
All operational verdicts and candidate prioritizations established in Section 1 and Section 12 remain strictly preserved:
1. **DFO 3382 (Mahanadi Basin, Odisha)**: Remains **Priority 1 (CONDITIONAL GO)** for future authorized acquisition.
2. **DFO 3551 (Krishna Basin, AP/KA)**: Remains **Priority 2 (CONDITIONAL GO)** for future authorized acquisition.
3. **Kerala Floods 2018 (Periyar/Pamba Basins)**: Remains **NO-GO FOR DIRECT ACQUISITION**, deferred to a dedicated SAR label-development workflow.
4. **Immediate Download Ban**: **No candidate is approved for immediate download**. All external data retrieval remains prohibited until explicit, separate user authorization is granted.

---

## 14. Governance Invariants Maintained

1. **Zero Data Downloads**: No bytes were downloaded or retrieved during this preflight.
2. **Zero Model Training**: No machine learning models were trained, tuned, or calibrated.
3. **Zero Dataset/Manifest Modifications**: Existing datasets, manifests, schemas, and Phase 7E model artifacts remain completely unaltered.
4. **Permanent Holdout Quarantine**: DFO 2507 (North Bihar / Kosi, 2004) remains strictly quarantined as an `ALREADY_INSPECTED_HOLDOUT`.
5. **Phase 6 Hydrodynamic Authority**: The Phase 6 deterministic hydrodynamic physics engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the **sole authorized operational authority** for flood depths, velocities, and evacuation routing.
