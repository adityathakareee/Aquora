# AQUORA — PHASE 7F.3.1: EXISTING DATA INVENTORY REPORT
### Comprehensive Read-Only Audit of Geospatial, Hydrometeorological, Terrain & Machine Learning Assets

**Document Version:** `1.0.0-phase7f31-inventory`  
**Phase:** Phase 7F.3.1 Existing Data Inventory & Asset Verification  
**Task Type:** READ-ONLY GEOSPATIAL & ASSET AUDIT (Zero source code changes, zero dataset modifications, zero downloads, zero model training, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine ([engines/flood/](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/))  
**Date:** 2026-10-31  

---

## 1. Executive Summary & Audit Overview

In accordance with Phase 7F requirements, an exhaustive, read-only physical audit of the local filesystem was conducted across all data storage directories: `data/raw/`, `data/interim/`, `data/processed/`, `data/packages/`, and `data/manifests/`.

Every file was checked for physical presence on disk, format, exact byte size, spatial bounding box, coordinate reference system (CRS), temporal coverage, feature schema, and manifest provenance.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PHYSICAL DATA STORAGE AUDIT SUMMARY                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Directory           Status      Files     Total Size       Description
  ────────────────────────────────────────────────────────────────────────────────────────
  data/raw/           PRESENT       193       3.93 GB        Raw satellite rasters, DEMs, GFD GeoTIFFs, IMERG/CHIRPS
  data/interim/       ABSENT          0          0 MB        Directory DOES NOT EXIST in workspace
  data/processed/     PRESENT    10,702       6.55 GB        *10,570 digital twin / hydrodynamic slices (6.53 GB)
                                                              + 132 processed GIS/ML assets (174.4 MB)
  data/packages/      PRESENT        17     129.85 MB        Phase 7D & 7E reproducible Kaggle packages & Parquets
  data/manifests/     PRESENT        44       0.24 MB        Authoritative provenance & audit manifests (Phase 2 to 7E)
  ────────────────────────────────────────────────────────────────────────────────────────
  TOTAL AUDITED                  10,956      10.61 GB        Fully verified on physical storage
```

### High-Level Audit Findings

1. **`data/interim/` is completely absent**: No interim processing directory exists. Processing scripts output directly into `data/processed/` or `data/packages/`.
2. **HAND (Height Above Nearest Drainage) is 100% ABSENT**: Zero HAND rasters or precomputed relative drainage relief datasets exist in the repository.
3. **Sub-Daily IMERG Precipitation is Severely Fragmented**: While 96 half-hourly IMERG V07B HDF5 files exist (789 MB), they cover **only two dates**: August 29, 2017 (Mumbai cloudburst) and July 1–2, 2019 (Assam E03). **Zero sub-daily IMERG files exist for the Phase 7C/7E historical training and evaluation flood disasters** (2004 DFO 2507, 2006 DFO 2935, 2008 DFO 3372, or July 2017 DFO 4499).
4. **HydroRIVERS South Asia is Locally Incomplete**: The full continental HydroRIVERS vector polyline database is **NOT present** on disk (`data/raw/hydrography/hydrorivers/` is empty). Only 4 localized 4-point LineString pilot GeoJSON snippets (totaling 3.1 KB) exist in `data/processed/hydrography/`.
5. **Copernicus DEM GLO-30 is Tile-Restricted**: Only 5 authentic 1°×1° Copernicus 30m DEM tiles exist in `data/raw/phase7/dem/` (Mumbai, Nashik, Kolkata, Patna, Guwahati). There is no continuous national DEM mosaic.
6. **ESA WorldCover 2021 Has Temporal Offset**: Four authentic 10m tiles exist in `data/raw/phase7/landcover/` matching the 4 event footprints, but represent calendar year 2021—introducing a **4-to-17-year temporal offset** from the historical floods (2004–2017).
7. **MODIS / ESA CCI Historical Land Cover is 100% ABSENT**: Zero historical land cover datasets exist locally.
8. **Phase 7E ML Dataset State**: `phase7c_multievent_binary_dataset.parquet` (207,205 rows, 24 columns) contains **100% missing values (`NaN`) for `rainfall_1h_mm`, `rainfall_3h_mm`, and `rainfall_6h_mm`**, and features severe target class imbalance (DFO 2507 holdout has 5.82% flood prevalence).

---

## 2. Investigation of the 9 Key Target Datasets

| Target Dataset Category | Local Presence | File Count & Size | Spatial Resolution & Extent | Temporal Scope | Used in Phase 7E? | Can Support Phase 7F Proposals? |
| :--- | :---: | :---: | :--- | :--- | :---: | :--- |
| **1. Copernicus DEM (GLO-30)** | **PARTIAL** | 5 unique tiles (6 files, 211.1 MB) | 30m (1 arc-sec, EPSG:4326), 5 isolated 1°×1° tiles | Static baseline | **YES** (Source of `elevation_m` & `slope_deg`) | **YES (for local basins)**; cannot support un-downloaded national basins without new tiles. |
| **2. HAND (Height Above Nearest Drainage)** | **COMPLETELY ABSENT** | 0 files (0 bytes) | None | None | **NO** | **NO** (Must be derived from conditioned DEM + flow accumulation or acquired externally). |
| **3. CHIRPS Precipitation** | **PRESENT** | 35 daily `.tif.gz` files (115.6 MB) | 0.05° (~5.5 km), Quasi-global / India | 35 discrete days (1981–2022) | **YES** (Source of `rainfall_24h_mm` & `rainfall_72h_mm`) | **PARTIAL** (Only daily totals; cannot provide sub-daily `1h`/`3h`/`6h` convective rain). |
| **4. GPM IMERG Precipitation** | **PARTIAL** | 13 daily `.nc4` (422.3 MB) + 96 half-hourly `.HDF5` (789.2 MB) | 0.1° (~10 km), Global 60°N–60°S | 13 daily dates (2001–2022); 30-min data ONLY on 2017-08-29 & 2019-07-01/02 | **NO** (Dropped in Phase 7C due to date gaps) | **PARTIAL (Pilot only)**; missing historical dates for DFO 2507, 2935, 3372, 4499. |
| **5. HydroRIVERS River Network** | **PARTIAL (MINIMAL)** | 4 pilot GeoJSON snippets (3.1 KB); Raw folder empty | Vector LineStrings (4 vertices each, 4 cities) | Static hydrography | **NO** (`distance_to_river_m` used JRC permanent water instead) | **NO** (Snippets too tiny; full continental HydroRIVERS shapefile missing from raw storage). |
| **6. ESA WorldCover 2021** | **PRESENT** | 4 raw 10m tiles (410.1 MB) + 4 cropped 30m rasters | 10m native / 30m resampled (EPSG:4326), 4 3°×3° tiles | Calendar Year 2021 | **YES** (Source of `landcover_class`) | **YES (with caveat)**; usable, but exhibits 4–17 yr temporal mismatch with 2004–2017 floods. |
| **7. MODIS / ESA CCI Historical Land Cover** | **COMPLETELY ABSENT** | 0 files (0 bytes) | None | None | **NO** | **NO** (Proposed external dataset; requires acquisition). |
| **8. Flow Direction, Accumulation & Terrain Derivatives** | **PARTIAL** | 16 rasters in `data/processed/terrain/` & `phase7/terrain/` | 30m UTM43N (Mithi) / 30m WGS84 (4 cities) | Static geomorphology | **NO** (Not ingested into Phase 7C/7E cross-basin ML table) | **PARTIAL (Mithi/Pilot only)**; absent for DFO 2507 (Bihar), DFO 2935, DFO 3372, DFO 4499. |
| **9. DFO Flood Labels & Event Catalogs** | **PRESENT** | 4 multi-band GeoTIFFs (174.7 MB) + 3 catalogs (3.1 MB) | 250m native MODIS / 30m resampled grid, 4 regional event footprints | 2004 (DFO 2507), 2006 (DFO 2935), 2008 (DFO 3372), 2017 (DFO 4499) | **YES** (Ground truth target `flood_label` in Phase 7E) | **YES** (Fully authentic ground truth; 87 additional Indian events cataloged but un-downloaded). |

---

## 3. Directory-by-Directory Detailed Inventory

### A. Raw Data Assets (`data/raw/`)

Total Size: **4,222,093,223 bytes (3.93 GB)** across **193 files**.

#### 1. Digital Elevation Models (Copernicus DEM GLO-30)
* **Directory**: [`data/raw/phase7/dem/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/dem/)
* **Source**: ESA / Copernicus AWS Open Data (`s3://copernicus-dem-30m/`)
* **Format**: Cloud-Optimized GeoTIFF (COG), Single-band float32, EPSG:4326, pixel size $0.00027777778^\circ \times 0.00027777778^\circ$ ($\approx 30.8\text{ m}$).
* **Asset Table**:

| Exact File Path | Size (Bytes) | Bounding Box (Lat/Lon) | Geographic Region | Phase 7E Role |
| :--- | :---: | :--- | :--- | :--- |
| `data/raw/phase7/dem/Copernicus_DSM_COG_10_N19_00_E072_00.tif` | 13,336,459 | 19.00°N–20.00°N, 72.00°E–73.00°E | Mumbai & Coastal Maharashtra | Pilot elevation / Deep Zone |
| `data/raw/phase7/dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif` | 13,336,459 | 19.00°N–20.00°N, 72.00°E–73.00°E | Mumbai & Coastal Maharashtra | Exact duplicate copy of above |
| `data/raw/phase7/dem/Copernicus_DSM_COG_10_N20_00_E073_00_DEM.tif` | 45,802,519 | 20.00°N–21.00°N, 73.00°E–74.00°E | Nashik / Upper Godavari Basin | Ingested for DFO 2935 |
| `data/raw/phase7/dem/Copernicus_DSM_COG_10_N22_00_E088_00_DEM.tif` | 50,532,585 | 22.00°N–23.00°N, 88.00°E–89.00°E | Kolkata / Lower Ganga Delta | Ingested for DFO 4499 |
| `data/raw/phase7/dem/Copernicus_DSM_COG_10_N25_00_E085_00_DEM.tif` | 44,765,416 | 25.00°N–26.00°N, 85.00°E–86.00°E | Patna / Kosi Mega-Fan (Bihar) | Ingested for DFO 2507 (Test) |
| `data/raw/phase7/dem/Copernicus_DSM_COG_10_N27_00_E094_00_DEM.tif` | 43,342,995 | 27.00°N–28.00°N, 94.00°E–95.00°E | Lakhimpur / Brahmaputra (Assam) | Ingested for DFO 3372 (Val) |

* **Audit Finding**: `data/raw/dem/copernicus_glo30/` is an empty folder (`0 files`). All active DEM tiles reside in `data/raw/phase7/dem/`.

#### 2. Land Cover Datasets (ESA WorldCover 2021)
* **Directory**: [`data/raw/phase7/landcover/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/landcover/)
* **Source**: ESA WorldCover 10m 2021 v200
* **Format**: GeoTIFF, uint8, EPSG:4326, pixel size $0.00008333333^\circ \times 0.00008333333^\circ$ ($\approx 10\text{ m}$), $36,000 \times 36,000$ pixels per $3^\circ \times 3^\circ$ tile.
* **Asset Table**:

| Exact File Path | Size (Bytes) | Bounding Box (Lat/Lon) | Geographic Region | Phase 7E Role |
| :--- | :---: | :--- | :--- | :--- |
| `data/raw/phase7/landcover/ESA_WorldCover_10m_2021_v200_N18E072_Map.tif` | 125,766,199 | 18.00°N–21.00°N, 72.00°E–75.00°E | Maharashtra (Mumbai, Nashik) | Ingested for DFO 2935 |
| `data/raw/phase7/landcover/ESA_WorldCover_10m_2021_v200_N21E087_Map.tif` | 81,771,213 | 21.00°N–24.00°N, 87.00°E–90.00°E | West Bengal / Sundarbans | Ingested for DFO 4499 |
| `data/raw/phase7/landcover/ESA_WorldCover_10m_2021_v200_N24E084_Map.tif` | 123,474,050 | 24.00°N–27.00°N, 84.00°E–87.00°E | Bihar / Gangetic Plain | Ingested for DFO 2507 (Test) |
| `data/raw/phase7/landcover/ESA_WorldCover_10m_2021_v200_N27E093_Map.tif` | 79,061,337 | 27.00°N–30.00°N, 93.00°E–96.00°E | Assam / Arunachal Foothills | Ingested for DFO 3372 (Val) |

* **Audit Finding**: `data/raw/landcover/worldcover/` is an empty folder (`0 files`). All tiles reside in `data/raw/phase7/landcover/`.

#### 3. Flood Ground Truth (Global Flood Database v1.4 / DFO)
* **Directory**: [`data/raw/phase7/ground_truth/gfd/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/)
* **Source**: Cloud-to-Street / Global Flood Database v1.4 (Tellman et al. 2021, Nature)
* **Format**: Multi-band GeoTIFF (5 bands: `flooded`, `duration`, `clear_views`, `clear_perc`, `jrc_perm_water`), EPSG:4326, pixel size $\approx 0.0022458^\circ$ ($\approx 250\text{ m}$).
* **Asset Table**:

| Event ID | Exact File Path | Size (Bytes) | Valid Cells | Flooded Cells | Permanent Water |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **DFO 2507** | `data/raw/phase7/ground_truth/gfd/DFO_2507/DFO_2507_From_20040620_to_20041007.tif` | 82,844,925 | 40,782,192 | 872,014 | 1,842,912 |
| **DFO 2935** | `data/raw/phase7/ground_truth/gfd/DFO_2935/DFO_2935_From_20060728_to_20060912.tif` | 70,592,388 | 34,220,119 | 1,104,291 | 1,412,088 |
| **DFO 3372** | `data/raw/phase7/ground_truth/gfd/DFO_3372/DFO_3372_From_20080830_to_20080908.tif` | 16,529,756 | 8,110,422 | 312,890 | 451,200 |
| **DFO 4499** | `data/raw/phase7/ground_truth/gfd/DFO_4499/DFO_4499_From_20170727_to_20170810.tif` | 4,772,471 | 3,239,389 | 80,164 | 72,887 |

* **Event Catalogs & Masterlists in `data/raw/phase7/ground_truth/`**:
  * [`dfo_masterlist_20190418.zip`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/dfo_masterlist_20190418.zip) (610,578 bytes): Global shapefile of historical DFO inundation polygons from 1985 to 2019.
  * [`gfd_qcdatabase_2019_08_01.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd_qcdatabase_2019_08_01.csv) (776,797 bytes): 913 global quality-checked disaster events.
  * [`india_flood_inventory_v3.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/india_flood_inventory_v3.csv) (1,801,579 bytes): 6,876 administrative event records across India.

#### 4. Daily CHIRPS Rainfall
* **Directory**: [`data/raw/phase7/rainfall/chirps/daily/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/rainfall/chirps/daily/)
* **Format**: Gzipped GeoTIFF (`.tif.gz`), Float32, 0.05° (~5.5 km), Quasi-global (50°S–50°N).
* **Count & Size**: 35 files totaling **115,595,215 bytes (110.24 MB)**.
* **Dates Covered**: 1981 (Jan 8, Jan 18, Mar 22, Apr 3, May 1, May 27, Jun 1), 1984 (Jul 17), 1993 (Jul 8, Jul 18), 2001 (Jul 4), 2004 (Jun 18, 19, 20), 2005 (Jul 26), 2006 (Jul 26, 27, 28, Aug 7), 2008 (Aug 18, 28, 29, 30), 2009 (Oct 2), 2013 (Jun 16), 2014 (Sep 4), 2015 (Dec 1), 2017 (Jul 25, 26, 27, Aug 29), 2018 (Aug 16), 2019 (Jul 1, Jul 10), 2022 (Sep 5).
* **Role in Phase 7E**: Provided `rainfall_24h_mm` and `rainfall_72h_mm`. Because daily rasters only provide 24h totals, sub-daily columns (`1h`, `3h`, `6h`) remained completely unpopulated (`NaN`).

#### 5. GPM IMERG Satellite Precipitation
* **Directory**: [`data/raw/phase7/rainfall/imerg/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/rainfall/imerg/)
* **Format & Subdirectories**:
  1. `daily/` (NetCDF4 `.nc4`): 13 files totaling **422,333,089 bytes (402.77 MB)**. Single daily accumulations for 13 specific dates (2001, 2005, 2006, 2008, 2009, 2013, 2014, 2015, 2017, 2018, 2019, 2022).
  2. `final/` (HDF5 `.HDF5`): 96 half-hourly IMERG Final Run V07B files totaling **789,173,027 bytes (752.61 MB)**.
     - `2017/08/`: 48 half-hourly files for August 29, 2017 (00:00 to 23:30 UTC, Mumbai cloudburst).
     - `2019/07/`: 48 half-hourly files for July 1, 2019 (42 files) and July 2, 2019 (6 files, Assam E03).
* **Audit Finding**: `data/raw/rainfall/imerg/` is an empty folder (`0 files`). Zero half-hourly IMERG files exist for DFO 2507 (June 2004), DFO 2935 (July 2006), DFO 3372 (August 2008), or DFO 4499 (July 2017).

#### 6. Sentinel-1 SAR Backscatter Archives
* **Directory**: [`data/raw/phase7/sentinel1/E03/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/sentinel1/E03/)
* **Format**: Raw ZIP archives of Sentinel-1 Level-1 GRDH products.
* **Asset Table**:

| Exact File Path | Size (Bytes) | Acquisition Timestamp | Orbit / Polarization |
| :--- | :---: | :---: | :---: |
| `data/raw/phase7/sentinel1/E03/S1A_IW_GRDH_1SDV_20190608T010256_20190608T010321_027581_031CCA_FBE2.zip` | 925,313,923 | 2019-06-08 01:02:56 UTC (Pre-flood) | Relative Orbit 121, VV+VH |
| `data/raw/phase7/sentinel1/E03/S1A_IW_GRDH_1SDV_20190702T010258_20190702T010323_027931_03274B_DDDA.zip` | 981,880,378 | 2019-07-02 01:02:58 UTC (Co-flood) | Relative Orbit 121, VV+VH |

* **Role**: Used exclusively in Phase 6B.4 / Phase 6B.5 for satellite SAR flood extent corroboration in Assam. Not ingested into Phase 7E supervised training tables.

#### 7. Critical Infrastructure & Facilities
* **Directory**: [`data/raw/facilities/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/facilities/)
* **Files**:
  * [`mithi_critical_facilities.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/facilities/mithi_critical_facilities.json) (4,050 bytes): 11 curated emergency facilities (hospitals, fire stations) in Mumbai.
  * [`osm_critical_facilities.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/facilities/osm_critical_facilities.json) (241,455 bytes): 603 OpenStreetMap emergency facilities across Mumbai.
* **Role**: Operational critical access routing for Phase 5 / Phase 6 hydrodynamic emergency services.

---

### B. Interim Storage (`data/interim/`)

* **Audit Status**: **DOES NOT EXIST**.
* **Finding**: The folder `data/interim/` was never created in the repository. Preprocessing scripts write final feature representations directly to `data/processed/` or create transient in-memory buffers.

---

### C. Processed Data Assets (`data/processed/`)

Total Directory Count: **10 subdirectories**, Total Size: **6.55 GB**.  
*(Note: 6.53 GB consists of Phase 6 deterministic hydrodynamic simulation rasters in `digital_twin/` and `flood/`; the remaining 174.4 MB contains GIS and ML assets)*.

#### 1. Administrative & Basin Boundaries
* **Directory**: [`data/processed/boundaries/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/boundaries/)
* **Assets**:
  * [`hydrobasins_india.geojson`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/boundaries/hydrobasins_india.geojson) (9,423 bytes): 8 major river basin polygons (Ganga, Brahmaputra, Godavari, Krishna, Narmada, Tapi, Mahanadi, Mithi).
  * [`hydrobasins_india.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/boundaries/hydrobasins_india.json) (4,967 bytes): JSON metadata schema for HydroBASINS.
  * [`india_administrative_boundaries.geojson`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/boundaries/india_administrative_boundaries.geojson) (44,939 bytes): 45 state and district boundary polygons.
  * [`india_administrative_hierarchy.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/boundaries/india_administrative_hierarchy.json) (19,696 bytes): Complete national administrative hierarchy.

#### 2. Hydrography & River Centerlines
* **Directory**: [`data/processed/hydrography/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/hydrography/)
* **Assets**:
  * [`hydrorivers_brahmaputra_guwahati.geojson`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/hydrography/hydrorivers_brahmaputra_guwahati.geojson) (785 bytes): 4-point LineString polyline.
  * [`hydrorivers_ganga_patna.geojson`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/hydrography/hydrorivers_ganga_patna.geojson) (764 bytes): 4-point LineString polyline.
  * [`hydrorivers_godavari_nashik.geojson`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/hydrography/hydrorivers_godavari_nashik.geojson) (771 bytes): 4-point LineString polyline.
  * [`hydrorivers_narmada_bharuch.geojson`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/hydrography/hydrorivers_narmada_bharuch.geojson) (769 bytes): 4-point LineString polyline.
* **Audit Finding**: These files are isolated pilot snippets from Phase 2B. They do not cover any regional flood disaster footprints. In Phase 7C, `distance_to_river_m` did not use these polylines; it queried JRC standing water.

#### 3. Processed Elevation Models
* **Directory**: [`data/processed/dem/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/dem/)
* **Assets**: 4 cropped 30m DEM GeoTIFFs (1.62 MB each) covering pilot city bounding boxes:
  * `brahmaputra_guwahati_elevation_30m.tif` (91.65°E–91.85°E, 26.10°N–26.25°N)
  * `ganga_patna_elevation_30m.tif` (85.05°E–85.25°E, 25.55°N–25.70°N)
  * `godavari_nashik_elevation_30m.tif` (73.70°E–73.90°E, 19.90°N–20.05°N)
  * `narmada_bharuch_elevation_30m.tif` (72.90°E–73.10°E, 21.65°N–21.80°N)

#### 4. Terrain Derivatives & Hydrological Flow Proxies
* **Directory**: [`data/processed/terrain/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/terrain/) and [`data/processed/phase7/terrain/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/terrain/)
* **Pilot City Derivatives** (`data/processed/terrain/`):
  * 4 `*_distance_to_river_30m.tif` rasters (1.62 MB each)
  * 4 `*_slope_30m.tif` rasters (1.62 MB each)
* **Mumbai / Mithi Study Extent Derivatives** (`data/processed/phase7/terrain/`):
  * All rasters are in **EPSG:32643 (UTM 43N)** with $476 \times 392$ cells at 30m resolution (Study bounds: 272671.93E to 284431.93E, 2101151.70N to 2115431.70N):
    * `aspect_30m.tif` (747,322 bytes)
    * `slope_30m.tif` (747,322 bytes)
    * `elevation_30m.tif` (747,322 bytes)
    * `elevation_30m_study_extent.tif` (1,658,902 bytes, $746 \times 536$)
    * `flow_accumulation_30m.tif` (747,322 bytes)
    * `drainage_proxy_30m.tif` (747,322 bytes)
    * `drainage_proxy_score.tif` (747,322 bytes)
    * `scratch/elevation_30m_exploratory_fdir.tif` (145,905 bytes)
    * `scratch/elevation_30m_exploratory_filled.tif` (1,600,013 bytes)
* **Audit Finding**: Flow accumulation and flow direction exist **exclusively for Mumbai / Mithi**. Zero flow direction or accumulation grids exist for DFO 2507, 2935, 3372, or 4499.

#### 5. Processed Land Cover
* **Directory**: [`data/processed/landcover/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/landcover/)
* **Assets**: 4 `*_landcover_30m.tif` and 4 `*_built_up_fraction_30m.tif` for the 4 pilot screening cities (1.62 MB each).

#### 6. Processed Rainfall Parquets & Benchmarks
* **Directory**: [`data/processed/rainfall/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/rainfall/)
* **Assets**:
  * `accumulations/pilot_basins_rainfall_accumulations.parquet` (14,049 bytes): 5 rows of multi-window rainfall totals for pilot cities.
  * `normalized/*_imerg_v07b_normalized.parquet`: 5 parquets (48 rows each, single 24h event).

#### 7. Processed SAR Corroboration Products (Phase 6B.4)
* **Directory**: [`data/processed/phase6b4/sar/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase6b4/sar/)
* **Assets**: 5 GeoTIFFs (E03 co-event, pre-event, delta backscatter, quality masks, candidate flood evidence) projected to EPSG:32643 at 30m resolution.

#### 8. Tabular Machine Learning Datasets (Phase 7A–7E)
* **Directory**: [`data/processed/phase7/ml/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/)
* **Active Parquet & CSV Datasets**:

| Dataset Name | File Format | Size (Bytes) | Row Count | Column Count | Events Included |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `phase7_gfd_pilot_dataset` | Parquet / CSV | 136.7 KB / 1.19 MB | 5,500 | 24 | DFO 4499 only |
| `phase7_gfd_pilot_binary_dataset` | Parquet / CSV | 128.5 KB / 1.09 MB | 5,000 | 24 | DFO 4499 only (balanced train/val/test) |
| `phase7c_multievent_dataset` | Parquet / CSV | 2.77 MB / 42.87 MB | 209,116 | 24 | DFO 2507, DFO 2935, DFO 3372, DFO 4499 |
| **`phase7c_multievent_binary_dataset`** | Parquet / CSV | **2.74 MB / 42.48 MB** | **207,205** | **24** | **Authoritative Phase 7E ML Dataset** |

* **Backup Archive**: [`data/processed/phase7/ml/backups_phase7d_original/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/backups_phase7d_original/) contains preserved pre-Phase 7D correction datasets with uncorrected cloud-filter thresholds.

---

### D. Exported Packages (`data/packages/`)

#### 1. `phase7d_kaggle_dataset/`
* **Directory**: [`data/packages/phase7d_kaggle_dataset/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7d_kaggle_dataset/)
* **Assets**:
  * `phase7c_multievent_binary_dataset.parquet` (2,742,428 bytes, SHA256: `f31591cf...`)
  * `phase7c_multievent_binary_dataset.csv` (42,479,340 bytes, SHA256: `75472464...`)
  * `phase7c_multievent_dataset.parquet` & `.csv` (master datasets with non-binary controls)
  * `aquora_ml_feature_schema_v1.json` (1,558 bytes)
  * `phase7d_kaggle_dataset_manifest.yaml` (5,241 bytes)
  * `README.md` (4,368 bytes)

#### 2. `phase7e_kaggle_package/`
* **Directory**: [`data/packages/phase7e_kaggle_package/`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/packages/phase7e_kaggle_package/)
* **Assets**:
  * `phase7c_multievent_binary_dataset.parquet` (2,742,428 bytes)
  * `phase7c_multievent_binary_dataset.csv` (42,479,340 bytes)
  * `AQUORA_Phase_7E_Experimental_ML.ipynb` (39,922 bytes): Executable Kaggle training notebook.
  * `aquora_ml_feature_schema_v1.json` (1,558 bytes)
  * Complete documentation suite: `DATA_DICTIONARY.md`, `DATA_QUALITY_AND_LIMITATIONS.md`, `SPLIT_DOCUMENTATION.md`, `TARGET_LABEL_DOCUMENTATION.md`, `README.md`.
  * `phase7e_kaggle_package_manifest.yaml` (4,158 bytes)

---

### E. Authoritative Manifests (`data/manifests/`)

There are **44 YAML manifest files** in `data/manifests/` auditing every progression of data preparation from Phase 2B through Phase 7E.

Key manifests for Phase 7F reference:
* [`data/manifests/phase7e_kaggle_package_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7e_kaggle_package_manifest.yaml): Authoritative record of the Phase 7E Kaggle package assets, hashes, and holdout policy.
* [`data/manifests/phase7d_kaggle_dataset_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7d_kaggle_dataset_manifest.yaml): Record of row count reconciliations and cloud filter corrections.
* [`data/manifests/phase7c_multievent_acquisition_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7c_multievent_acquisition_manifest.yaml): Provenance of the 4 raw GFD raster tiles.
* [`data/manifests/phase7c_multievent_dataset_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7c_multievent_dataset_manifest.yaml): Feature extraction provenance and split definitions.
* [`data/manifests/phase7_real_flood_dataset_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7_real_flood_dataset_manifest.yaml): Pilot DFO 4499 dataset manifest.

---

## 4. Phase 7A–7E Flood Dataset & Schema Deep Dive

### Authoritative Dataset Profile: `phase7c_multievent_binary_dataset.parquet`

* **Total Row Count**: **207,205 rows**
* **Total Columns**: **24 columns**
* **Event Breakdown**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   PHASE 7E MULTI-EVENT BINARY DATASET COMPOSITION                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Event ID   Split        Flood Pixels (1)   Dry Pixels (0)    Total Rows   Prevalence
  ────────────────────────────────────────────────────────────────────────────────────────
  DFO_4499   Train                   2,500            2,500         5,000       50.00%
  DFO_2935   Train                     350              350           700       50.00%
  DFO_3372   Validation              2,500            2,500         5,000       50.00%
  DFO_2507   Test (Holdout)         11,435          185,070       196,505        5.82%
  ────────────────────────────────────────────────────────────────────────────────────────
  TOTAL                             16,785          190,420       207,205        8.10%
```

### Complete Column Inventory & Null Analysis

| Column Name | Data Type | Null Count | Null % | Physical Meaning & Source | Used in Phase 7E? |
| :--- | :---: | :---: | :---: | :--- | :---: |
| `point_id` | string | 0 | 0.0% | Unique point identifier | No (Identifier) |
| `event_id` | string | 0 | 0.0% | GFD/DFO flood disaster identifier | No (Group identifier) |
| `event_region` | string | 0 | 0.0% | Human-readable basin/state name | No (Metadata) |
| `observation_date` | string | 0 | 0.0% | Inundation observation timestamp | No (Metadata) |
| `latitude` | float64 | 0 | 0.0% | WGS84 latitude coordinate | No (Leakage forbidden) |
| `longitude` | float64 | 0 | 0.0% | WGS84 longitude coordinate | No (Leakage forbidden) |
| `basin_id` | string | 0 | 0.0% | HydroBASINS Level 5/6 basin code | No (Spatial CV grouping) |
| `split` | string | 0 | 0.0% | Dataset partition (`train`, `validation`, `test`) | No (Partition column) |
| `gfd_flooded` | float64 | 0 | 0.0% | Raw GFD flooded band value (0.0 or 1.0) | No (Intermediate) |
| `gfd_clear_perc` | float64 | 0 | 0.0% | Clear-observation fraction ($\ge 0.70$) | No (Quality gate) |
| `gfd_jrc_perm_water` | float64 | 0 | 0.0% | JRC permanent water mask (0.0 or 1.0) | No (Exclusion mask) |
| **`flood_label`** | int64 | 0 | 0.0% | **Supervised binary target (1 = Flood, 0 = Dry)** | **TARGET** |
| `label_quality_flag` | string | 0 | 0.0% | Quality indicator (`VERIFIED_EPISODIC_FLOOD`, etc.) | No (Audit filter) |
| `rainfall_1h_mm` | float64 | **207,205** | **100.0%** | 1-hour rainfall accumulation | **DROPPED (100% NaN)** |
| `rainfall_3h_mm` | float64 | **207,205** | **100.0%** | 3-hour rainfall accumulation | **DROPPED (100% NaN)** |
| `rainfall_6h_mm` | float64 | **207,205** | **100.0%** | 6-hour rainfall accumulation | **DROPPED (100% NaN)** |
| `rainfall_24h_mm` | float64 | 0 | 0.0% | 24-hour rainfall accumulation (CHIRPS daily) | **YES (Active Feature)** |
| `rainfall_72h_mm` | float64 | 0 | 0.0% | 72-hour rainfall accumulation (CHIRPS 3-day sum) | **YES (Active Feature)** |
| `rainfall_anomaly_index` | float64 | 0 | 0.0% | Standardized rainfall anomaly ($r = 1.000$ with 72h) | **YES (Redundant)** |
| `elevation_m` | float64 | 0 | 0.0% | Raw Copernicus DEM elevation meters | **YES (Domain Shift)** |
| `slope_deg` | float64 | 0 | 0.0% | Topographic slope in degrees | **YES (Active Feature)** |
| `distance_to_river_m` | float64 | 0 | 0.0% | KDTree distance to JRC permanent water | **YES (Semantic Error)** |
| `historical_flood_frequency` | int64 | 0 | 0.0% | Multi-decade district flood count (IFI v3) | **YES (Future Leakage)** |
| `landcover_class` | int64 | 0 | 0.0% | ESA WorldCover 2021 land cover class code | **YES (Temporal Offset)** |

---

## 5. Critical Data Gaps & Proposed Source Discrepancies

This section explicitly documents the disparity between datasets **actually available on physical disk** versus **proposed external data sources** discussed in literature and improvement plans:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DATA AVAILABILITY DISCREPANCY MATRIX                            │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Target Data Class         Proposed External Source       Actual Physical State on Disk
  ────────────────────────────────────────────────────────────────────────────────────────
  Topographic Relief (HAND) MERIT-Hydro / Yamazaki 2019    COMPLETELY MISSING (0 rasters)
  Sub-Daily Precipitation   NASA GPM IMERG Final V07       PARTIAL (Only 2 dates; missing all
                                                           Phase 7C/7E historical event dates)
  Stream Hydrography        HydroRIVERS South Asia v1.0    RAW ABSENT (Folder empty; only 4 tiny
                                                           pilot city snippets exist)
  Historical Land Cover     MODIS MCD12Q1 / ESA CCI        COMPLETELY MISSING (0 rasters)
  Topographic Wetness (TWI) Hydro-conditioned SAGA TWI     COMPLETELY MISSING for 4 DFO basins
  National Ground Truth     GFD v1.4 Indian Catalog        4 events downloaded; 87 cataloged
                                                           events remain un-downloaded
```

### Gap 1: The HAND Void
* **Documentation Assertion**: Phase 7F strategy identifies HAND as the primary physical candidate to resolve elevation domain shift.
* **Physical Reality**: No HAND layer has ever been downloaded or processed. Copernicus DEM tiles in `data/raw/phase7/dem/` are unconditioned raw surface models. Deriving HAND locally requires depression-filling algorithms, D8/D-infinity flow routing, and stream burning against vector river centerlines.

### Gap 2: The Sub-Daily IMERG Temporal Disconnect
* **Documentation Assertion**: GPM IMERG V07 provides 30-minute precipitation to eliminate missing `1h`, `3h`, `6h` rainfall.
* **Physical Reality**: Half-hourly IMERG files on disk only cover August 2017 (Mumbai) and July 2019 (Assam E03). The training events occurred in:
  * June 2004 (DFO 2507, Kosi) $\rightarrow$ 0 IMERG files on disk.
  * July 2006 (DFO 2935, Godavari) $\rightarrow$ 0 IMERG files on disk.
  * August 2008 (DFO 3372, Assam) $\rightarrow$ 0 IMERG files on disk.
  * July 2017 (DFO 4499, Bengal) $\rightarrow$ 0 IMERG files on disk.
* **Impact**: Sub-daily rainfall cannot be populated for existing training/test datasets without acquiring historical IMERG Final Run half-hourly archives from NASA GES DISC for those specific disaster windows.

### Gap 3: Missing Continental HydroRIVERS Network
* **Documentation Assertion**: HydroRIVERS South Asia v1.0 replaces permanent standing water distance with stream centerlines.
* **Physical Reality**: `data/raw/hydrography/hydrorivers/` is empty. The four snippets in `data/processed/hydrography/` contain only 4 vertices each and are confined to tiny $0.20^\circ \times 0.15^\circ$ pilot boxes around Guwahati, Patna, Nashik, and Bharuch. No streamline network exists for the rural floodplains of North Bihar (DFO 2507) or West Bengal (DFO 4499).

### Gap 4: Temporal Land Cover Mismatch
* **Documentation Assertion**: ESA WorldCover provides 10m land cover.
* **Physical Reality**: The four tiles on disk represent 2021. For DFO 2507 (June 2004), this creates a **17-year temporal gap**. River avulsions, embankment construction, and agricultural conversion over two decades mean 2021 land cover does not reflect the geomorphic reality of 2004. Contemporaneous MODIS (MCD12Q1) or ESA CCI land cover is not present on disk.

---

## 6. Phase 7F Feasibility Assessment & Scientific Guidance

Based on this physical audit, we evaluate the immediate feasibility of Phase 7F architectural proposals:

| Proposed Phase 7F Enhancement | Feasibility with Existing Local Assets | Required Un-Downloaded Assets | Actionable Immediate Next Step |
| :--- | :---: | :--- | :--- |
| **1. Inverted Elevation Heuristic Evaluation** | **100% FEASIBLE** | None. Local DEM tiles and test Parquet already exist. | Formalize within-basin inverted elevation baseline across all 4 events. |
| **2. Probability Calibration on Natural Splits** | **100% FEASIBLE** | None. Existing training/validation splits can be evaluated without artificial 50/50 rebalancing. | Implement Platt scaling / Isotonic regression on naturally distributed validation splits. |
| **3. Elimination of Redundant / Leaking Features** | **100% FEASIBLE** | None. Pure feature selection on existing table. | Drop `rainfall_anomaly_index`, `historical_flood_frequency`, and `distance_to_river_m`. |
| **4. HAND Feature Engineering** | **BLOCKED (Requires Processing or Data)** | Requires either downloading global HAND (MERIT Hydro) or running hydrological conditioning on existing 5 DEM tiles. | Design DEM conditioning and D8 drainage python workflow for the 5 existing tiles. |
| **5. Sub-Daily Rainfall Imputation** | **BLOCKED (Requires Acquisition)** | Requires NASA GES DISC half-hourly IMERG V07 HDF5 files for 2004, 2006, 2008, and July 2017. | Catalog exact granule IDs required for the 4 historical event time windows. |
| **6. HydroRIVERS Centerline Distance** | **BLOCKED (Requires Acquisition)** | Requires WWF HydroRIVERS South Asia v1.0 vector shapefile. | Stage HydroRIVERS South Asia acquisition request. |
| **7. Multi-Event LOPZO Expansion** | **BLOCKED (Requires Acquisition)** | Existing catalog has 91 Indian events, but only 4 are downloaded. LOPZO requires 10–15 events across physiographic regimes. | Prepare prioritized acquisition list from `gfd_india_events_catalog.csv`. |

### Architectural Boundary Affirmation
* **Phase 6 Physics Engine Authority**: The Phase 6 deterministic hydrodynamic physics engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the sole operational authority for flood depths, velocities, and critical access routing.
* **Deep Zone Invariant**: Mumbai / Mithi (`deep_mumbai_mithi`) remains the ONLY active Deep Zone.
* **Zero Synthetic Data Invariant**: All supervised flood labels must originate strictly from verified satellite observations (GFD / Sentinel-1).
* **Experimental Governance**: All machine learning screening models remain categorized: `PROTOTYPE_ONLY`, `NOT_CALIBRATED`, `NOT_FOR_PUBLIC_ALERTS`.
