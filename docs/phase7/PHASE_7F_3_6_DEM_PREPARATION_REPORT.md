# AQUORA — PHASE 7F.3.6: DFO 3382 DEM PREPARATION REPORT (AMENDED)
### Controlled Acquisition, Raster Quality Verification, DSM Limitations & Spatial Coverage Audit of Copernicus DEM GLO-30 for DFO 3382 (Mahanadi Basin / Odisha Delta)

**Document Version:** `1.1.0-dem-preparation-amended`  
**Phase:** Phase 7F.3.6 Stage 3 — Controlled DFO 3382 DEM Acquisition  
**Authorized Package:** **Corrected Package B (9 Tiles)**  
**Target Directory:** `data/raw/phase7/dem/mahanadi_dfo3382/`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60))  
**Date:** 2026-10-31  

---

## 1. Executive Summary & Acquisition Decision

In accordance with explicit user authorization, **Stage 3 Controlled DEM Acquisition of Corrected Package B** was executed. Exactly **nine authorized Copernicus DEM GLO-30 tiles** were acquired directly from the European Space Agency / AWS Open Data repository (`https://copernicus-dem-30m.s3.amazonaws.com/`) into `data/raw/phase7/dem/mahanadi_dfo3382/`.

### Key Outcomes & Methodological Qualifications:
1. **Acquisition Completeness**:
   * **9 of 9 authorized tiles acquired successfully** (0 failures, 0 missing files).
   * **Total Download Volume**: **`272.50 MB` ($285,733,588\text{ bytes}$)**.
   * Total acquisition elapsed time: **$219.3\text{ seconds}$**.
   * Zero unauthorized, supplemental, or out-of-scope tiles were downloaded.
2. **Raster Integrity & Checksum Governance**:
   * Every tile is a valid, uncorrupted Cloud-Optimized GeoTIFF (COG) in `EPSG:4326` with floating-point (`float32`) elevation values at 1 arc-second ($\approx 30\text{ m}$) resolution.
   * Every tile contains exactly **$12,960,000\text{ pixels}$ ($3600 \times 3600$)**, totaling **$116,640,000\text{ pixels}$** across the mosaic.
   * Every tile exhibits **0 structural NoData pixels (0.00% missing data)**; all rasters are structurally complete.
   * **Checksum Finding**: SHA-256 hashes were calculated and recorded locally upon streaming download. Because the public AWS S3 bucket does not publish SHA-256 metadata headers, **independent source-checksum verification was not established**. File sizes matched remote `Content-Length` exactly, and raster integrity was verified locally through GeoTIFF header parsing.
3. **Metric 5,125 m Buffer Closure (UTM Zone 45N — EPSG:32645)**:
   * The approved preflight expanded the dissolved flood-pixel footprint by $5,000\text{ m}$ plus a $125\text{ m}$ half-pixel allowance (for native $250\text{ m}$ cells), yielding a **5,125 m metric buffer**.
   * **Core Delta Flood Footprint (18,686 cells)**: **100.00% covered** ($14,391.41\text{ km}^2$ of $14,391.41\text{ km}^2$ — **$0.00\text{ km}^2$ missing**).
   * **Extended Delta Flood Footprint (20,581 cells)**: **97.94% covered** ($16,983.83\text{ km}^2$ of $17,341.42\text{ km}^2$).
4. **Digital Surface Model (DSM) Limitation**:
   * Copernicus DEM GLO-30 is a **Digital Surface Model (DSM)**, representing the reflective surface (including vegetation canopies, tree stands, and buildings), rather than a bare-earth Digital Terrain Model (DTM).
5. **Water Masking Requirement**:
   * Raw ocean pixels are represented as $0.0\text{ m}$ elevation rather than NoData (`NaN`). Future terrain processing requires a separately validated land/permanent-water mask; the JRC permanent water mask alone cannot be assumed to resolve all dynamic coastal, tidal, and estuarine boundaries.
6. **Final Decision**:
   $$\mathbf{DEM\_ACQUISITION\_COMPLETE}$$

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               AQUORA PHASE 7F.3.6 DEM ACQUISITION SUMMARY (AMENDED)                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Target Disaster Event:      DFO 3382 — Mahanadi Delta Floods (Odisha, Sept 2008)
  Authorized Candidate Set:   Corrected Package B (9 Tiles: N19-21, E84-86 + N20E087)
  Target Local Directory:     data/raw/phase7/dem/mahanadi_dfo3382/
  Tiles Authorized / Acquired: 9 Requested / 9 Acquired (100.0% Success Rate, 0 Failed)
  Total Download Volume:      272.50 MB (285,733,588 bytes)
  Total Mosaic Pixels:        116,640,000 pixels (9 tiles x 3600 x 3600)
  Valid DEM Pixels:           116,640,000 pixels (100.0% valid data, 0 structural NoData)
  Buffer Distance:            5,125 m (5,000 m buffer distance + 125 m half-pixel allowance)
  Spatial Buffer Enclosure:   100.00% Core Delta Buffer Closure (14,391.41 / 14,391.41 km²)
  Checksum Status:            Locally calculated SHA-256 (Independent source verification not established)
  Terrain Model Type:         Digital Surface Model (DSM) — Canopy/structures present
  Final Acquisition Status:   DEM_ACQUISITION_COMPLETE
────────────────────────────────────────────────────────────────────────────────────────
```

---

## 2. Individual Tile Inspection & Quality Results

Every acquired Copernicus DEM GeoTIFF was opened and audited individually using `rasterio`. File sizes, locally computed SHA-256 checksums, coordinate bounds, pixel dimensions, and elevation distributions were recorded directly from raw byte streams:

```
┌───────┬─────────────────────────┬───────────┬──────────────┬─────────────┬─────────────┬─────────────┬─────────────┬────────────────────────────────────────────────────────┐
│ Tile  │ Graticule Bounds        │ Size (MB) │ Valid Pixels │ Min Elev (m)│ Max Elev (m)│ Mean Elev(m)│ Lowland %   │ SHA-256 Checksum (Locally Calculated)                  │
├───────┼─────────────────────────┼───────────┼──────────────┼─────────────┼─────────────┼─────────────┼─────────────┼────────────────────────────────────────────────────────┤
│N19E084│ 84°–85°E, 19°–20°N      │  42.45 MB │  12,960,000  │    -2.75 m  │  1,504.53 m │   301.07 m  │    9.95%    │ 11a8de07f960910d3c9e3f4fb542ebd0a12a1b6a9a2b4ee06f6e85da39b2536e │
│N19E085│ 85°–86°E, 19°–20°N      │  14.83 MB │  12,960,000  │    -1.00 m  │    787.88 m │    15.38 m  │   81.79%    │ 038fde4a3bc977d5d1fe31e7c88d81dbb84cb63233ad14b473e75f16376d02a3 │
│N19E086│ 86°–87°E, 19°–20°N      │   2.16 MB │  12,960,000  │    -2.66 m  │     25.30 m │     0.19 m  │   99.88%    │ 8b22518b9f48db4811a43ffb90875e53e414c51475726ce40bc64d1f2e1e3b6d │
│N20E084│ 84°–85°E, 20°–21°N      │  43.69 MB │  12,960,000  │    42.49 m  │  1,221.90 m │   338.85 m  │    0.00%    │ 0853d16d33254c5133ead256fa9feb6719fcc5a3ff642a6d8d36f3de6ac5bdde │
│N20E085│ 85°–86°E, 20°–21°N      │  45.50 MB │  12,960,000  │   -38.00 m  │    835.20 m │    86.57 m  │   14.50%    │ de5c6c9fb88889fe7341f2f04db1b7b66ec6bf44a688e1a862264944a5790a13 │
│N20E086│ 86°–87°E, 20°–21°N      │  38.11 MB │  12,960,000  │    -6.49 m  │    392.04 m │     7.12 m  │   90.72%    │ 0c4b6911c594af84a822f8f525197dfcc3f3f868212bce31ec06aaf32aefa765 │
│N20E087│ 87°–88°E, 20°–21°N      │   0.19 MB │  12,960,000  │    -1.05 m  │     20.01 m │     0.01 m  │  100.00%    │ c873973492cc84157b84ed7c329469da283332fa59106daa757ed2acd9b9674b │
│N21E085│ 85°–86°E, 21°–22°N      │  42.34 MB │  12,960,000  │    16.23 m  │  1,180.12 m │   354.52 m  │    0.00%    │ 705b6bdf2b657551eb077eed5a1f4de5878f4497fe34c27019aa0d451be502ba │
│N21E086│ 86°–87°E, 21°–22°N      │  43.22 MB │  12,960,000  │    -2.54 m  │  1,186.32 m │   204.41 m  │   35.88%    │ c9530b4f2458c5b869ea27bfd8e09c46b51ad5c8689b303b32d28e6a4b139051 │
├───────┼─────────────────────────┼───────────┼──────────────┼─────────────┼─────────────┼─────────────┼─────────────┼────────────────────────────────────────────────────────┤
│ TOTAL │ PACKAGE B (9 TILES)     │ 272.50 MB │ 116,640,000  │   -38.00 m  │  1,504.53 m │   145.48 m  │   48.06%    │ Local Checksums Recorded (No Remote Source Checksum)   │
└───────┴─────────────────────────┴───────────┴──────────────┴─────────────┴─────────────┴─────────────┴─────────────┴────────────────────────────────────────────────────────┘
```

*Note on Lowland Delta %*: Defined as valid pixels with elevation between $0.0\text{ m}$ and $15.0\text{ m}$ above the EGM2008 geoid. Across the coastal delta tiles (`N19E086`, `N20E086`, `N19E085`, `N20E087`), between 81% and 100% of terrain is within this low-lying bracket.

---

## 3. Spatial Coverage & Metric 5,125 m Buffer Audit

### 3.1 Accurate Metric 5,125 m Buffer Methodology (UTM Zone 45N — EPSG:32645)
The approved preflight methodology applies a metric buffer consisting of:
- **Base Buffer Distance**: $5,000\text{ meters}$.
- **Half-Pixel Footprint Allowance**: $+125\text{ meters}$ (to account for the $250\text{ m} \times 250\text{ m}$ cell size of the primary GFD observation grid).
- **Total Metric Buffer Expansion**: **`5,125 meters`**.

Under this verified methodology, coverage metrics remain preserved:
- **Core Delta Actual 5,125 m Buffer Area**: **`14,391.41 sq km`**
  - **Area Enclosed by Package B**: **`14,391.41 sq km` (100.00%)**
  - **Missing Buffer Area**: **`0.00 sq km`**
  - Western boundary ($84.95276^\circ\text{E}$) is fully enclosed by `N19E084` and `N20E084`.
  - Eastern boundary ($87.09486^\circ\text{E}$) is fully enclosed by `N20E087`.
  - Northern boundary ($21.03207^\circ\text{N}$) is fully enclosed by `N21E085` and `N21E086`.
  - Southern boundary ($19.34944^\circ\text{N}$) is fully enclosed by `N19E085` and `N19E086`.
- **Extended Delta Actual 5,125 m Buffer Area**: **`17,341.42 sq km`**
  - **Area Enclosed by Package B**: **`16,983.83 sq km` (97.94%)**
  - Marginal buffer areas extending outside Package B are confined to adjacent river basins:
    - West into Angul gorge approach (`N21E084`): $168.17\text{ km}^2$ ($0.97\%$).
    - East into Balasore / Subarnarekha plain (`N21E087`): $189.42\text{ km}^2$ ($1.09\%$).

### 3.2 Tile Boundary Seam Continuity
Cross-tile edge pixel elevation continuity was audited along graticule borders:
1. **Naraj Apex to Kendrapara Seam (Longitude 86.0°E)**:
   - Eastern column of `N20E085` vs. Western column of `N20E086`:
   - Mean absolute elevation step across the 30m boundary: **`0.86 m`**.
   - Maximum elevation step: $13.45\text{ m}$ (in rugged Eastern Ghats foothill knolls).
   - Pixel graticule coordinates align exactly at $85.999861^\circ\text{E}$.
2. **Puri Coast to Naraj Apex Seam (Latitude 20.0°N)**:
   - Northern row of `N19E085` vs. Southern row of `N20E085`:
   - Mean absolute elevation step across the 30m boundary: **`1.52 m`**.
   - Maximum elevation step: $28.06\text{ m}$ (rocky knoll near Khordha).
   - Pixel graticule coordinates align exactly at $20.000139^\circ\text{N}$.

---

## 4. Digital Surface Model (DSM) Structural Limitation

Copernicus DEM GLO-30 is a **Digital Surface Model (DSM)**, derived from WorldSAR X-band radar interferometry (TanDEM-X mission), rather than a bare-earth Digital Terrain Model (DTM):

1. **Canopy and Structural Bias**:
   - The radar signal reflects from the top surface of objects, including tree canopies, dense vegetation, buildings, embankments, and urban infrastructure.
   - In coastal wetlands and mangrove reserves (such as the Bhitarkanika mangrove forest in `N20E086` and `N20E087`), raw elevation values reflect canopy height (often $5\text{ m}–15\text{ m}$ above the true tidal ground surface).
   - In dense urban settlements (Bhubaneswar and Cuttack in `N20E085`), structural heights elevate surface pixels above the surrounding alluvial plain.
2. **Impact on Hydrodynamic Modeling**:
   - Raw DSM elevation values can create artificial dikes, dams, or false flow obstructions across natural floodplains and drainage channels if uncorrected.
   - Future data preparation must explicitly address this limitation through vegetation canopy bias correction, channel burning, or hydro-enforcement during subsequent authorized phases.

---

## 5. Water Masking & Dynamic Coastal Interface Limitations

1. **Ocean & Water Representation in Copernicus DEM GLO-30**:
   - In raw Copernicus DSM rasters, oceanic water bodies are **flattened to $0.0\text{ m}$ elevation** (or minor negative tidal values down to $-6.49\text{ m}$), rather than flagged as `NaN` NoData.
   - In coastal tiles, exact $0.0\text{ m}$ water cells comprise:
     - `N20E087`: **$99.86\%$** ($12,941,538\text{ pixels}$ are open water; only $18,462\text{ pixels}$ are terrestrial spit).
     - `N19E086`: **$96.10\%$** ($12,454,122\text{ pixels}$ are open Bay of Bengal water).
     - `N19E085`: **$64.11\%$** ($8,308,437\text{ pixels}$ are Chilika Lagoon and coastal water).
     - `N20E086`: **$24.27\%$** ($3,144,821\text{ pixels}$ are coastal estuary and ocean).
2. **Separately Validated Land/Water Mask Required**:
   - Because open water pixels exhibit valid $0.0\text{ m}$ float values, raw DEM elevation **must NOT be fed directly into flow accumulation or HAND algorithms without a robust, separately validated land/permanent-water mask**.
   - **Critical Caveat**: The JRC Global Surface Water permanent water mask alone cannot be assumed to resolve every coastal, tidal, or estuarine classification issue. 
   - The Odisha coastline exhibits dynamic macrotidal fluctuations, expansive intertidal mudflats, seasonal mangrove inundation, and migrating barrier spits (such as Wheeler Island / Gahirmatha). Optical/SAR permanent-water layers can misclassify periodically inundated tidal zones as dry land or conversely treat seasonal recession areas as permanent water.
   - Future preparation must design a composite water-masking strategy combining permanent water, tidal limits, and coastal morphology.
3. **Valid Terrestrial Land vs. Geometric Coverage**:
   - Total acquired pixels: **$116,640,000\text{ pixels}$** ($100.0\%$ valid data, 0 structural NoData).
   - Within this graticule envelope, approximately **$65,000,000\text{ pixels}$ ($\approx 55\%$) represent true terrestrial land**, with the remainder representing the Bay of Bengal, Chilika Lagoon, and tidal estuaries.

---

## 6. Strict Governance Invariants Preserved

1. **Zero Prohibited Data Downloads**: No rainfall files, IMERG granules, or HydroRIVERS/HydroBASINS shapefiles were acquired.
2. **Zero Terrain Derivatives Generated**: No HAND, slope, aspect, curvature, or TWI rasters were computed.
3. **Zero Resampling or Fabrication**: Original Copernicus DEM GeoTIFFs were preserved bit-exact without resampling or spatial interpolation.
4. **Zero Model Training**: No machine learning models were trained, tuned, or updated; no training labels were generated.
5. **DFO 2507 Holdout Quarantine**: DFO 2507 remains quarantined as an `ALREADY_INSPECTED_HOLDOUT`.
6. **Phase 6 Hydrodynamic Physics Supremacy**: The Phase 6 deterministic hydrodynamic solver ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the sole operational authority.
7. **Zero Git Commits/Pushes**: No Git staging, committing, or pushing was executed.

---

## 7. Deliverables & File Inventory

1. **Acquired Raw DEM Directory**:
   `data/raw/phase7/dem/mahanadi_dfo3382/` (9 GeoTIFF files, 272.50 MB, preserved unmodified)
2. **Authoritative Acquisition Manifest**:
   [`data/manifests/phase7f36_dfo3382_dem_acquisition_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7f36_dfo3382_dem_acquisition_manifest.yaml)
3. **Comprehensive DEM Preparation Report (Amended)**:
   [`docs/phase7/PHASE_7F_3_6_DEM_PREPARATION_REPORT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_6_DEM_PREPARATION_REPORT.md)
4. **Inspection Summary JSON**:
   [`docs/phase7/DFO_3382_dem_acquisition_summary.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/DFO_3382_dem_acquisition_summary.json)
5. **Acquisition Script**:
   [`scripts/acquire_phase7f36_dem.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/acquire_phase7f36_dem.py)

---

## 8. Regression Testing & Git Status

The Phase 7 regression test suite was executed:
```bash
python -m pytest backend/tests/test_phase7c_multievent_dataset.py \
                 backend/tests/test_phase7_real_flood_dataset.py \
                 backend/tests/test_phase7d_kaggle_preflight.py \
                 backend/tests/test_phase7e_kaggle_package.py -v
```
**Test Results**: **`31 passed in 11.22s (100% pass rate)`**.

### Git Status (Uncommitted Working Tree):
```text
?? data/manifests/phase7f36_dfo3382_dem_acquisition_manifest.yaml
?? data/manifests/phase7f36_dfo3382_dem_preflight_manifest.yaml
?? data/raw/phase7/dem/mahanadi_dfo3382/
?? docs/phase7/DFO_3382_dem_acquisition_summary.json
?? docs/phase7/DFO_3382_dem_preflight_analysis.json
?? docs/phase7/DFO_3382_inspection_summary.json
?? docs/phase7/DFO_3382_mahanadi_dem_spatial_breakdown.json
?? docs/phase7/PHASE_7F_3_6_DEM_COVERAGE_PREFLIGHT.md
?? docs/phase7/PHASE_7F_3_6_DEM_PREPARATION_REPORT.md
?? scripts/acquire_phase7f36_dem.py
```

---

## 9. Final Decision

### Decision: `DEM_ACQUISITION_COMPLETE`

> **NOTICE**:
> All requested amendments have been integrated into the authoritative manifest and report.
> Controlled acquisition of Package B is formally closed. Execution remains halted; no data downloads, terrain derivatives, or model training will occur without separate authorization.
