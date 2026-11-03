# AQUORA — PHASE 7F.3.7: TERRAIN PREPARATION PLANNING AND DATA READINESS AUDIT
### Technical Readiness Audit, Auxiliary Hydrographic Inventory & Hydrologic Conditioning Workflow Design for the DFO 3382 Mahanadi Study Region

**Document Version:** `1.0.0-terrain-readiness`  
**Phase:** Phase 7F.3.7 Terrain Preparation Planning & Data Readiness Audit  
**Target Study Domain:** Mahanadi Basin / Odisha Delta ($19.0^\circ–22.0^\circ\text{N}, 84.0^\circ–88.0^\circ\text{E}$)  
**Task Type:** READ-ONLY INVENTORY AUDIT & WORKFLOW DESIGN (Zero data downloads, zero DEM modifications, zero terrain derivatives, zero ML training, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60))  
**Date:** 2026-10-31  

---

## 1. Executive Summary & Readiness Determination

Following the successful controlled acquisition and validation of **Package B (9 Copernicus DEM GLO-30 tiles, 272.50 MB)** in Phase 7F.3.6 ([docs/phase7/PHASE_7F_3_6_DEM_PREPARATION_REPORT.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_6_DEM_PREPARATION_REPORT.md)), this document establishes the **READ-ONLY Planning and Data Readiness Audit** for future terrain preparation.

### Key Audit Findings:
1. **DEM Mosaic Status (Complete)**:
   * All 9 required Copernicus DEM GLO-30 tiles (`N19-21, E84-86` + `N20E087`) are locally stored in `data/raw/phase7/dem/mahanadi_dfo3382/`, achieving 100.00% geometric coverage of the Core Delta 5,125 m buffer ($14,391.41\text{ km}^2$).
2. **Authoritative Drainage & Basin Data Deficit (Locally Missing)**:
   * An exhaustive audit reveals that **no true hydrologic watershed boundary for Mahanadi exists locally**. The local boundary in `data/processed/boundaries/hydrobasins_india.geojson` (Feature 6) is merely a 5-point rectangular bounding box ($[80.4^\circ\text{E}, 19.3^\circ\text{N}, 86.9^\circ\text{E}, 23.6^\circ\text{N}]$), not a topographic ridgeline boundary.
   * **Zero river network vectors exist locally for the Mahanadi Basin**. While river files exist for Brahmaputra, Ganga, Godavari, and Narmada in `data/processed/hydrography/`, `hydrorivers_mahanadi.geojson` is completely missing.
3. **Land-Cover & Water-Masking Deficit (Locally Missing)**:
   * The $3^\circ \times 3^\circ$ tile covering the Mahanadi Delta (**`ESA_WorldCover_10m_2021_v200_N18E084_Map.tif`**) is **completely missing locally**. The only nearby tile (`N21E087`) covers latitude 21°–24°N and longitude 87°–90°E, touching only the extreme northeast coastal margin.
   * **No standalone 30m JRC Global Surface Water rasters exist locally**. JRC permanent water is currently available only as a 250m proxy band (`jrc_perm`) embedded in the DFO 3382 GFD raster.
4. **Digital Surface Model (DSM) Structural Limitation**:
   * Copernicus DEM GLO-30 is a **Digital Surface Model (DSM)** reflecting X-band radar returns from vegetation canopies (mangrove forests, casuarina belts) and building structures. Unconditioned DSM data will create "vegetation dams" across floodplain channels, distorting flow accumulation and HAND calculations unless stream burning and breach-depression algorithms are applied.
5. **Final Readiness Decision**:
   $$\mathbf{PARTIAL\_READINESS}$$

> **READINESS NOTICE**:
> Although the DEM raster tiles are 100% acquired, verified, and ready for mosaicing, **physical hydrologic conditioning cannot be executed responsibly** without acquiring authoritative river centerlines (for stream burning) and a validated land/permanent-water mask. Execution of terrain processing remains strictly deferred.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               AQUORA PHASE 7F.3.7 TERRAIN READINESS AUDIT SUMMARY                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Target Event:               DFO 3382 — Mahanadi Delta Floods (Odisha, Sept 2008)
  Study Domain:               19.0°N–22.0°N, 84.0°E–88.0°E (4° Lon x 3° Lat)
  DEM Raster Readiness:       COMPLETE (9 of 9 Tiles Local, 272.50 MB, 100% Core Buffer Closure)
  Authoritative Basin Vector: DEFICIENT (Local file is a 5-point bounding box; CWC vector missing)
  Drainage Network Vector:    DEFICIENT (Zero local river vectors for Mahanadi; HydroRIVERS missing)
  Land-Cover (WorldCover):    DEFICIENT (N18E084 missing locally; N21E087 touches only NE margin)
  Surface Water Mask:         DEFICIENT (Standalone 30m JRC missing; only 250m GFD proxy exists)
  DSM Hydrologic Risk:        HIGH (Canopy bias in Bhitarkanika mangroves & Cuttack/Bhubaneswar)
  Readiness Determination:    PARTIAL_READINESS (Planning complete; execution deferred)
────────────────────────────────────────────────────────────────────────────────────────
```

---

## 2. Drainage & Basin Data Inventory: Local Assets vs. External Sources

### 2.1 Audit of Existing Local Assets
A recursive file audit of `data/` was conducted to establish exact local availability:

| Dataset / File Path | Local File Present? | Description / Inspected Content | Readiness Evaluation |
| :--- | :---: | :--- | :--- |
| `data/processed/boundaries/hydrobasins_india.geojson` | **YES** | Contains 8 features. Feature 6 is labeled `BASIN-MAHANADI`. **Geometry inspection reveals exactly 5 coordinates**: `[[80.4, 19.3], [80.4, 23.6], [86.9, 23.6], [86.9, 19.3], [80.4, 19.3]]`. | **INADEQUATE**: Merely a coarse rectangular bounding box. Cannot be used for watershed delineation or drainage area clipping. |
| `data/processed/hydrography/hydrorivers_*.geojson` | **PARTIAL** | Contains river networks for Brahmaputra (`Guwahati`), Ganga (`Patna`), Godavari (`Nashik`), and Narmada (`Bharuch`). | **DEFICIENT**: `hydrorivers_mahanadi.geojson` is **completely absent locally**. Zero stream vectors exist for Odisha. |
| `MERIT Hydro` Assets | **NO** | No flow direction, flow accumulation, or hydrography files from MERIT Hydro exist in the repository. | **MISSING LOCALLY**. |
| `India-WRIS / CWC` Vector Boundaries | **NO** | No official shapefiles or GeoJSONs from the Central Water Commission exist locally. | **MISSING LOCALLY**. |

### 2.2 Authoritative External Sources Identified for Future Acquisition
To perform scientifically valid hydrologic conditioning, the following authoritative sources must be targeted in a future authorized acquisition:

1. **Central Water Commission (CWC) / India-WRIS Basin & Sub-basin Boundaries**:
   - **Issuing Authority**: Ministry of Jal Shakti, Government of India.
   - **Required Layers**: Mahanadi Basin Boundary (`Basin_Code: 04`), Delta Sub-basin boundary, and official river reach lines (Mahanadi, Kathajodi, Birupa, Kuakhai, Daya, Bhargavi, Kushabhadra, Devi, Chitratpala, Luna).
   - **Relevance**: National legal and hydrologic authority for river management in India.
2. **HydroSHEDS / HydroBASINS (Level 7 & Level 8 Asia Extract)**:
   - **Issuing Authority**: USGS / WWF / McGill University (`hybas_as_lev07-08_v1c`).
   - **Required Layers**: Pfafstetter Level 7 sub-basin polygons partitioning the delta below the Naraj Barrage bifurcation (`HYBAS_ID 4050xxxxxx`).
   - **Relevance**: Topographically consistent watershed boundaries derived from conditioned SRTM elevation.
3. **HydroRIVERS (Asia v1.0)**:
   - **Issuing Authority**: HydroSHEDS Project.
   - **Required Layers**: Vector river reach lines with Strahler stream orders ($\ge 3$), reach lengths, and upstream contributing drainage areas ($A_{up}$ in $\text{km}^2$).
   - **Relevance**: Indispensable for burning stream channels into the Copernicus DSM to enforce correct flow routing.

---

## 3. Land-Cover & Permanent-Water Masking Audit

### 3.1 Audit of Existing Local Land-Cover Assets
An inspection of `data/raw/phase7/landcover/` was conducted:
- Existing local tiles:
  - `ESA_WorldCover_10m_2021_v200_N18E072_Map.tif` (Mumbai / Mithi)
  - `ESA_WorldCover_10m_2021_v200_N21E087_Map.tif` (Balasore / WB Coast: bounds $[87.0^\circ–90.0^\circ\text{E}, 21.0^\circ–24.0^\circ\text{N}]$)
  - `ESA_WorldCover_10m_2021_v200_N24E084_Map.tif` (Bihar / Kosi)
  - `ESA_WorldCover_10m_2021_v200_N27E093_Map.tif` (Assam / Brahmaputra)
- **Deficit Identified**:
  - The $3^\circ \times 3^\circ$ tile required to cover the Core Mahanadi Delta ($18^\circ–21^\circ\text{N}, 84^\circ–87^\circ\text{E}$) is **`ESA_WorldCover_10m_2021_v200_N18E084_Map.tif`**.
  - **This tile is completely missing locally**.
  - The local tile `N21E087` only intersects latitude $21.0^\circ–22.0^\circ\text{N}$ and longitude $87.0^\circ–88.0^\circ\text{E}$ (touching only the extreme northeast coastal corner).

### 3.2 Audit of Existing Local Surface Water Assets
- **No standalone 30m JRC Global Surface Water rasters** (e.g. Occurrence, Permanence, Seasonality tiles `80E_20N`, `80E_30N`) exist in the repository.
- JRC permanent water is currently available only as **Band 5 (`jrc_perm`) inside the DFO 3382 GFD raster**, which is downsampled to nominal $\approx 250\text{ m}$ resolution.
- Using a 250m proxy to mask 30m DEM terrain introduces spatial quantization errors of up to $\pm 125\text{ m}$ along meandering river channels.

### 3.3 Dynamic Coastal, Estuarine & Tidal Risk Analysis
The Mahanadi Delta presents extreme coastal hydrodynamic complexities that prohibit simple static masking:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                 MAHANADI DELTA COASTAL & TIDAL RISK MATRIX                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

1. **Ocean Representation at $0.0\text{ m}$**:
   - In raw Copernicus DSM rasters, open ocean water in the Bay of Bengal is assigned an elevation of **$0.0\text{ m}$** (or negative tidal elevation down to $-6.49\text{ m}$), rather than structural NoData (`NaN`).
   - In coastal tiles, ocean cells comprise **$99.86\%$ of `N20E087`**, **$96.10\%$ of `N19E086`**, and **$64.11\%$ of `N19E085`**.
   - If unmasked, standard hydrological routing algorithms (D8/D-infinity) will treat the Bay of Bengal as an expansive, flat terrestrial basin, generating spurious flow networks and invalid depressions across the ocean.
2. **Macrotidal Range & Intertidal Mudflats**:
   - The northern Odisha coast experiences semi-diurnal tides with a macrotidal range of **$3.0\text{ m}–4.0\text{ m}$** (e.g. Dhamra Estuary and Chandbali).
   - Low tides expose kilometers of intertidal mudflats; high tides submerge them.
   - Optical permanent-water layers (like JRC permanent water $>80\%$) classify intertidal mudflats as non-water (land), while high-tide scenes classify them as water. A dynamic, separately validated tidal limit mask is required.
3. **Mangrove Canopy Flooding (Bhitarkanika & Gahirmatha)**:
   - Bhitarkanika is India's second-largest mangrove ecosystem. The dense mangrove forest is subject to regular tidal inundation beneath a closed forest canopy.
   - Optical satellite sensors cannot detect floodwater under dense tree cover. Radar sensors experience complex double-bounce scattering. Static water masks frequently classify these wetlands as dense terrestrial vegetation, severing tidal exchange channels.
4. **Migrating Estuarine Sandbars & Barrier Islands**:
   - River mouths (Dhamra, Devi, Mahanadi) and barrier spits (Wheeler Island, Gahirmatha spit) undergo rapid post-monsoon morphodynamic shifts.
   - A single static water mask from 2021 does not accurately match the coastal morphology of September 2008.

**Conclusion**: Future terrain preparation **cannot rely solely on JRC permanent water**. A multi-source composite mask (combining permanent water, tidal limits, and coastal morphology) must be established.

---

## 4. Digital Surface Model (DSM) Technical Implications & Mitigation

### 4.1 DSM Structural Characteristics
Copernicus DEM GLO-30 is a **Digital Surface Model (DSM)** derived from TanDEM-X X-band ($\lambda \approx 3.1\text{ cm}$) radar interferometry. X-band radar reflections occur at or near the top of the canopy and artificial structures, rather than the bare ground surface:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DSM CANOPY & STRUCTURAL CONTAMINATION                           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Terrain Feature     │ Elevation Bias   │ Geographical Location / Impact                 │
├─────────────────────┼──────────────────┼────────────────────────────────────────────────┤
│ Mangrove Canopy     │ +5 m to +15 m    │ Bhitarkanika (N20E086, N20E087); false dams   │
│ Casuarina Belts     │ +8 m to +18 m    │ Puri-Konark coastal dunes; blocks storm surge  │
│ Urban Settlements   │ +3 m to +12 m    │ Cuttack & Bhubaneswar (N20E085); urban barriers│
│ Embankments/Roads   │ +2 m to +5 m     │ NH-16 & flood protection bunds; flow dividers  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Hydrological Failure Modes if Unconditioned
1. **Vegetation Damming**: When a natural distributary channel passes through a forested riparian reach or mangrove stand, the raw DSM reflects tree-top elevation. Flow routing algorithms interpret this as a solid ridge, artificially diverting the modeled river into adjacent dry agricultural depressions.
2. **Artificial Sinks**: True floodplain depressions located behind raised road embankments or urban structures are interpreted as deep sinks. Traditional sink-filling algorithms (e.g. Wang & Liu) fill these depressions up to the level of the road embankment, obliterating actual flood storage capacity.
3. **Distorted HAND (Height Above Nearest Drainage)**: HAND calculations depend on the elevation difference between a pixel and its nearest drainage channel. If the drainage channel's elevation is elevated by dense canopy, adjacent bare fields will receive artificially negative or suppressed HAND values.

### 4.3 Mandatory Hydrologic Conditioning Mitigations
Before computing terrain derivatives, the following checks and conditioning steps must be executed:
- **Stream Burning (AGREE / Synthetic Trenching)**: Authoritative vector river lines (HydroRIVERS / CWC) must be buffered and hydraulically burned into the DEM by $2\text{ m}–5\text{ m}$ to enforce river flow through forested reaches.
- **Depression Breaching over Filling**: Priority must be given to *depression breaching* (carving narrow trenches through artificial dams like roads and tree belts) rather than sink filling, to preserve natural floodplain topography.
- **Canopy Bias Comparison**: Where feasible, cross-reference Copernicus DSM elevation against bare-earth products (such as FABDEM or MERIT DEM) to identify and adjust anomalous canopy heights in the Bhitarkanika reserve.

---

## 5. Proposed Terrain Preparation Workflow (Design Only)

The following multi-step workflow is designed for future execution once auxiliary data acquisition is separately authorized:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   PROPOSED 5-STAGE TERRAIN PREPARATION WORKFLOW                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Composite Land/Water Mask Preparation
- Ingest standalone 30m JRC Surface Water (Occurrence and Seasonality), coastal high-water boundary line, and DFO 3382 permanent water layer.
- Classify pixels into five discrete categories:
  1. `OCEAN_WATER` (Set to NoData / outer boundary).
  2. `TIDAL_INTERTIDAL_ZONE` (Dynamic coastal margin).
  3. `PERMANENT_INLAND_WATER` (Lakes, reservoirs, Chilika Lagoon).
  4. `RIVER_CHANNEL` (Active fluvial distributaries).
  5. `TERRESTRIAL_LAND` (Terrain available for runoff and inundation modeling).

### Stage 2: Virtual Mosaic (VRT) Construction & Seam Verification
- Build a virtual raster mosaic (`mahanadi_dem_mosaic_30m.vrt`) referencing all 9 raw COG GeoTIFFs without duplicating or altering raw files.
- Verify that seam continuity across integer degree boundaries exhibits $<1.5\text{ m}$ mean vertical step.
- Clip the virtual mosaic to the official Mahanadi Delta study domain.

### Stage 3: Hydro-Enforcement & Stream Burning
- Re-project authoritative river vectors (HydroRIVERS / CWC) to `EPSG:32645` (UTM Zone 45N).
- Burn stream channels into the DEM using a smooth drop function ($3\text{ m}$ trenching along primary distributaries, $1.5\text{ m}$ along secondary canals).
- Execute depression breaching (Lindsay algorithm) to breach road embankments and mangrove canopy dams without over-filling natural floodplain depressions.

### Stage 4: High-Resolution Terrain Feature Derivation (30m)
Compute standard hydrodynamic and terrain indices at native 30m resolution in UTM Zone 45N:
1. **Slope** ($\beta$, in degrees): Horn's 8-neighbor gradient method.
2. **Aspect** ($\alpha$, in degrees azimuth): Downslope direction.
3. **Plan & Profile Curvature**: Flow divergence and acceleration components.
4. **Flow Direction & Accumulation**: Deterministic 8-node (D8) and D-infinity flow routing.
5. **Topographic Wetness Index (TWI)**: $\text{TWI} = \ln(a / \tan \beta)$, where $a$ is specific contributing area.
6. **Height Above Nearest Drainage (HAND)**: Normalized elevation above the hydraulically connected river channel.

### Stage 5: Spatial Alignment & Multi-Scale Aggregation to DFO 3382 Grid
- **Preserve Native 30m Derivatives**: Native 30m rasters remain the primary high-resolution input for the Phase 6 deterministic hydrodynamic physics engine.
- **Compute Exact 250m Spatial Aggregates**: For machine learning evaluation on the DFO 3382 grid, project 30m cells into the exact bounding box of the GFD grid ($0.002245788^\circ \times 0.002245788^\circ$):
  - `elevation_mean_m`, `elevation_min_m`, `elevation_std_m`
  - `slope_mean_deg`, `slope_max_deg`
  - `hand_mean_m`, `hand_min_m`
  - `twi_mean`
- **Zero Label Resampling**: Observation labels (`flooded == 1.0`) must remain strictly untouched on their native grid; zero synthetic 30m labels will be fabricated.

---

## 6. Strict Governance Invariants Preserved

In strict compliance with project governance throughout Phase 7F.3.7:

1. **Zero Data Downloads**: No rasters, vectors, rainfall granules, or HydroRIVERS shapefiles were downloaded.
2. **Zero DEM Modifications**: The nine acquired Copernicus DEM COG files remain bit-exact, unaltered, and preserved in `data/raw/phase7/dem/mahanadi_dfo3382/`.
3. **Zero Terrain Derivatives Generated**: No slope, aspect, curvature, TWI, or HAND rasters were computed or written to disk.
4. **Zero Model Training**: No machine learning models were trained, tuned, or updated; no labels were fabricated.
5. **DFO 2507 Holdout Quarantine**: DFO 2507 remains quarantined as an `ALREADY_INSPECTED_HOLDOUT`.
6. **Phase 6 Hydrodynamic Physics Supremacy**: The Phase 6 deterministic hydrodynamic solver ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the **sole operational authority**.
7. **Zero Git Commits/Pushes**: No Git staging, committing, or pushing was executed.

---

## 7. Deliverables & File Inventory

1. **Authoritative Terrain Readiness Manifest**:
   [`data/manifests/phase7f37_terrain_readiness_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7f37_terrain_readiness_manifest.yaml)
2. **Comprehensive Terrain Readiness Audit Report**:
   [`docs/phase7/PHASE_7F_3_7_TERRAIN_READINESS_AUDIT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_7_TERRAIN_READINESS_AUDIT.md) (this document)

---

## 8. Regression Testing & Git Status

The Phase 7 regression test suite was executed:
```bash
python -m pytest backend/tests/test_phase7c_multievent_dataset.py \
                 backend/tests/test_phase7_real_flood_dataset.py \
                 backend/tests/test_phase7d_kaggle_preflight.py \
                 backend/tests/test_phase7e_kaggle_package.py -v
```
**Test Results**: **`31 passed in 8.21s (100% pass rate)`**.

### Git Working Tree Status (Uncommitted):
```text
?? data/manifests/phase7f36_dfo3382_dem_acquisition_manifest.yaml
?? data/manifests/phase7f36_dfo3382_dem_preflight_manifest.yaml
?? data/manifests/phase7f37_terrain_readiness_manifest.yaml
?? data/raw/phase7/dem/mahanadi_dfo3382/
?? docs/phase7/DFO_3382_dem_acquisition_summary.json
?? docs/phase7/DFO_3382_dem_preflight_analysis.json
?? docs/phase7/DFO_3382_inspection_summary.json
?? docs/phase7/DFO_3382_mahanadi_dem_spatial_breakdown.json
?? docs/phase7/PHASE_7F_3_6_DEM_COVERAGE_PREFLIGHT.md
?? docs/phase7/PHASE_7F_3_6_DEM_PREPARATION_REPORT.md
?? docs/phase7/PHASE_7F_3_7_TERRAIN_READINESS_AUDIT.md
?? scripts/acquire_phase7f36_dem.py
```

---

## 9. Final Readiness Determination

### Decision: `PARTIAL_READINESS`

> **OPERATIONAL SUMMARY**:
> - **DEM Rasters**: FULLY ACQUIRED, INSPECTED, AND READY.
> - **Auxiliary Hydrography & Masking**: MISSING LOCALLY (Requires HydroRIVERS Mahanadi extract, CWC basin boundaries, and 30m coastal land/water mask).
> - **Execution Status**: HALTED. No terrain processing, mosaicking, resampling, or derivative generation will proceed until auxiliary data acquisition is separately authorized.
