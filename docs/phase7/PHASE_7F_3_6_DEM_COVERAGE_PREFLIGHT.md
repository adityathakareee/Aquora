# AQUORA — PHASE 7F.3.6: DFO 3382 DEM SPATIAL COVERAGE PREFLIGHT (FINAL VALIDATION)
### Technical Spatial Intersect, Metric Buffer Validation & Copernicus DEM 30m Tile Requirements for DFO 3382

**Document Version:** `1.2.0-validated`  
**Phase:** Phase 7F.3.6 DFO 3382 DEM Spatial Coverage Preflight  
**Task Type:** READ-ONLY SPATIAL VALIDATION (Zero data downloads, zero feature generation, zero model training, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60))  
**Date:** 2026-10-31  

---

## 1. Executive Summary

Following the accepted acquisition of **DFO 3382** in Phase 7F.3.5 ([docs/phase7/PHASE_7F_3_5_DFO3382_ACQUISITION_REPORT.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_5_DFO3382_ACQUISITION_REPORT.md)), this document establishes the **final validated READ-ONLY DEM Spatial Coverage Preflight**.

This validation incorporates metric geodesic buffering in the official regional projected coordinate system (**WGS 84 / UTM Zone 45N — EPSG:32645**), accounts for full $250\text{ m} \times 250\text{ m}$ pixel footprints, resolves the classification contradiction for Package A, performs an authoritative audit of catchment claims, and verifies Git and file integrity for the DFO 3382 acquisition records.

### Key Preflight Determinations:
1. **Package A Reclassified as `PARTIAL_BUFFER_COVERAGE`**:
   * Package A (7 tiles: `N19-20, E84-86` + `N20E087`) fully encloses the western, eastern, and southern buffers.
   * However, because its northern graticule boundary stops at latitude $21.0000^\circ\text{N}$, it omits **$45.07\text{ km}^2$ ($0.31\%$)** of the northern 5 km buffer ($11.36\text{ km}^2$ in `N21E085` and $33.71\text{ km}^2$ in `N21E086`).
   * **Contradiction Resolved**: Package A is formally reclassified as **`PARTIAL_BUFFER_COVERAGE` (99.69% actual Core Delta buffer coverage)**. It cannot and must not be described as fully buffered.
2. **Package B Confirmed as `COMPLETE_GEOMETRIC_BUFFER_COVERAGE`**:
   * Package B (9 tiles: Package A plus `N21E085` and `N21E086`) covers **$14,391.41\text{ km}^2$ of $14,391.41\text{ km}^2$ (100.00%)** of the actual Core Delta flood footprint buffer in UTM Zone 45N.
   * **Zero square kilometers missing** for the Core Delta flood buffer.
   * It is formally established as the **Recommended Planning Baseline** for complete geometric buffer enclosure.
   * **Scientific Disclaimer**: Geometrical tile coverage does **NOT guarantee valid terrain coverage**, because actual DEM pixel validity (absence of NoData voids, coastal masking, or invalid water bodies) can only be confirmed after physical COG download and inspection.
3. **Catchment Claims Reclassified as `UNVERIFIED_ESTIMATE`**:
   * Previous percentage claims (e.g. "10% gorge approach", "85% mainstem", "98% full catchment") were tile-based flood cell distributions, NOT true catchment area intersections.
   * No authoritative catchment boundary polygon (India-WRIS / Central Water Commission CWC basin shapefile or HydroBASINS Level 5/6 polygon `BasinID 405001`) is currently ingested or available in repository storage.
   * All upstream catchment percentages are formally designated **`UNVERIFIED_ESTIMATE`**.
4. **Git and File Integrity of DFO 3382 Records Verified**:
   * `docs/phase7/DFO_3382_inspection_summary.json` is intentionally untracked in Git because strict project governance prohibited git commits in Phase 7F.3.5 and Phase 7F.3.6.
   * All extracted files on disk were verified against the authoritative inspection record via SHA-256: **100% bit-exact match confirmed**.
5. **Final Status**:
   * Formally assigned **`FINAL_PREFLIGHT_READY_FOR_APPROVAL`**.
   * Controlled acquisition remains strictly paused at the Stage 2 Approval Gate.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│           AQUORA PHASE 7F.3.6 FINAL DEM VALIDATION SUMMARY                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Target Disaster Event:      DFO 3382 — Mahanadi Delta Floods (Odisha, Sept 2008)
  Administrative Record:      UEI-IMD-FL-2008-0095 (140 fatalities; Cuttack, Puri, Kendrapara)
  Ground Truth Raster:        data/raw/phase7/ground_truth/gfd/DFO_3382/DFO_3382_...tif
  Verified Flood Cells (Full): 339,963 cells (South Asian monsoonal regional composite)
  Verified Flood Cells (Delta): 18,686 cells (Core Delta + Gahirmatha coastal spit)
  Metric Projection:          WGS 84 / UTM Zone 45N (EPSG:32645)
  Core Actual 5km Buffer Area: 14,391.41 sq km (UTM Zone 45N dissolved metric buffer)
  Package A (7 tiles, 186.9MB): PARTIAL_BUFFER_COVERAGE (99.69% buffer cov; omits 45.07 km2 in N21)
  Package B (9 tiles, 272.5MB): COMPLETE_GEOMETRIC_BUFFER_COVERAGE (100.00% core buffer closure)
  Package C (12 tiles, 397.4MB): SEPARATE CATCHMENT OBJECTIVE (Hirakud to ocean; unverified boundary)
  Catchment Area Claims:      UNVERIFIED_ESTIMATE (Pending CWC / HydroBASINS vector boundary ingestion)
  DFO 3382 File Integrity:    VERIFIED_BIT_EXACT_MATCH (All extracted files and SHA256 hashes intact)
  Final Validation Status:    FINAL_PREFLIGHT_READY_FOR_APPROVAL
────────────────────────────────────────────────────────────────────────────────────────
```

---

## 2. Metric Buffer Validation in UTM Zone 45N (EPSG:32645)

### 2.1 Methodology & Pixel Footprint Accounting
Previous preflight drafts buffered cell center coordinates, undercounting the true footprint by half a pixel width ($\approx 125\text{ m}$). 

In this validation:
1. Native GFD grid resolution is exactly **$0.002245788^\circ \times 0.002245788^\circ$ ($\approx 250.0\text{ m} \times 250.0\text{ m}$)**.
2. Every verified episodic flood cell (`flooded == 1.0 & jrc_perm == 0.0 & clear_perc >= 0.70`) was expanded to its complete rectangular footprint envelope $[x \pm \Delta x/2, y \pm \Delta y/2]$.
3. Pixel coordinates were projected into the official regional metric projection: **WGS 84 / UTM Zone 45N (EPSG:32645)**.
4. An exact metric geodesic buffer of **$5,000\text{ meters}$ (plus $125\text{ m}$ half-pixel expansion = $5,125\text{ m}$)** was generated around all dissolved pixel polygons.

### 2.2 Accurate Metric Buffer Areas & Envelopes
- **Core Delta Actual Flood Footprint**:
  - Cell Count: **18,686 verified flood cells**
  - Pixel Footprint Bounding Box (WGS 84): $[85.00084^\circ\text{E}, 19.39463^\circ\text{N}]$ to $[87.04675^\circ\text{E}, 20.98689^\circ\text{N}]$
  - 5 km Buffered Bounding Box (WGS 84): $[84.95276^\circ\text{E}, 19.34944^\circ\text{N}]$ to $[87.09486^\circ\text{E}, 21.03207^\circ\text{N}]$
  - **Total 5 km Metric Buffer Area**: **`14,391.41 sq km`**
- **Extended Delta Actual Flood Footprint** (incorporating Jajpur and Bhadrak distributaries):
  - Cell Count: **20,581 verified flood cells**
  - Pixel Footprint Bounding Box (WGS 84): $[85.00084^\circ\text{E}, 19.39463^\circ\text{N}]$ to $[87.09840^\circ\text{E}, 21.79762^\circ\text{N}]$
  - 5 km Buffered Bounding Box (WGS 84): $[84.95249^\circ\text{E}, 19.34944^\circ\text{N}]$ to $[87.14678^\circ\text{E}, 21.84279^\circ\text{N}]$
  - **Total 5 km Metric Buffer Area**: **`17,341.42 sq km`**

### 2.3 Tile-by-Tile Buffer Spatial Intersections

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│          TILE-BY-TILE 5 KM BUFFER SPATIAL INTERSECTION MATRIX (UTM ZONE 45N)           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

| Tile ID | Geographic Bounds | Core Delta Buffer Area | % of Core Buffer | Ext. Delta Buffer Area | % of Ext. Buffer | Buffer Role |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`N19E084`** | $84^\circ–85^\circ\text{E}, 19^\circ–20^\circ\text{N}$ | **$12.00\text{ km}^2$** | 0.08% | **$12.00\text{ km}^2$** | 0.07% | Southwestern buffer closure for `N19E085` |
| **`N20E084`** | $84^\circ–85^\circ\text{E}, 20^\circ–21^\circ\text{N}$ | **$88.53\text{ km}^2$** | 0.62% | **$88.53\text{ km}^2$** | 0.51% | Western buffer closure & Banki gorge reach |
| **`N21E084`** | $84^\circ–85^\circ\text{E}, 21^\circ–22^\circ\text{N}$ | **$0.00\text{ km}^2$** | 0.00% | **$168.17\text{ km}^2$** | 0.97% | Western buffer for Jajpur reach / Angul approach |
| **`N19E085`** | $85^\circ–86^\circ\text{E}, 19^\circ–20^\circ\text{N}$ | **$3,334.86\text{ km}^2$** | 23.17% | **$3,334.86\text{ km}^2$** | 19.23% | Southern delta plain / Puri / Chilika |
| **`N20E085`** | $85^\circ–86^\circ\text{E}, 20^\circ–21^\circ\text{N}$ | **$3,617.57\text{ km}^2$** | 25.14% | **$3,625.11\text{ km}^2$** | 20.90% | Delta apex / Cuttack / Naraj barrage |
| **`N21E085`** | $85^\circ–86^\circ\text{E}, 21^\circ–22^\circ\text{N}$ | **$11.36\text{ km}^2$** | 0.08% | **$1,494.74\text{ km}^2$** | 8.62% | Northern buffer for Cuttack & Jajpur floodplain |
| **`N19E086`** | $86^\circ–87^\circ\text{E}, 19^\circ–20^\circ\text{N}$ | **$523.83\text{ km}^2$** | 3.64% | **$523.83\text{ km}^2$** | 3.02% | Coastal fringe / Devi river estuary |
| **`N20E086`** | $86^\circ–87^\circ\text{E}, 20^\circ–21^\circ\text{N}$ | **$6,631.86\text{ km}^2$** | 46.08% | **$6,631.90\text{ km}^2$** | 38.24% | Eastern delta plain / Kendrapara / Jagatsinghpur |
| **`N21E086`** | $86^\circ–87^\circ\text{E}, 21^\circ–22^\circ\text{N}$ | **$33.71\text{ km}^2$** | 0.23% | **$1,135.16\text{ km}^2$** | 6.55% | Northern buffer for Kendrapara & Bhadrak estuary |
| **`N20E087`** | $87^\circ–88^\circ\text{E}, 20^\circ–21^\circ\text{N}$ | **$137.69\text{ km}^2$** | 0.96% | **$137.69\text{ km}^2$** | 0.79% | Eastern spit / Gahirmatha / Bhitarkanika |
| **`N21E087`** | $87^\circ–88^\circ\text{E}, 21^\circ–22^\circ\text{N}$ | **$0.00\text{ km}^2$** | 0.00% | **$189.42\text{ km}^2$** | 1.09% | Balasore coastal margin (Separate drainage) |
| **TOTAL** | — | **$14,391.41\text{ km}^2$** | **100.00%** | **$17,341.42\text{ km}^2$** | **100.00%** | Dissolved 5 km Geodesic Buffer |

---

## 3. Package Classification & Reassessment

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              VALIDATED DEM PACKAGE CLASSIFICATION MATRIX                                               │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

| Evaluation Parameter | Package 1 (As Proposed) | Package 2 (As Proposed) | Corrected Package A | Corrected Package B | Corrected Package C |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tile Count** | **4 tiles** | **6 tiles** | **7 tiles** | **9 tiles** | **12 tiles** |
| **Tile Identifiers** | `N19-20, E85-86` | `N19-21, E85-86` | `N19-20, E84-86` + `N20E087` | Pkg A + `N21E085`, `N21E086` | Pkg B + `N21E084`, `N21E083`, `N20E083` |
| **Download Volume** | **100.60 MB** | **186.16 MB** | **186.93 MB** | **272.49 MB** | **397.44 MB** |
| **Verified Flood Cells** | **18,682 cells** | **20,532 cells** | **20,207 cells** | **22,057 cells** | **31,154 cells** |
| **Core Buffer Area Covered**| **$14,108.12\text{ km}^2$** | **$14,153.19\text{ km}^2$** | **$14,346.34\text{ km}^2$** | **$14,391.41\text{ km}^2$** | **$14,391.41\text{ km}^2$** |
| **Core Buffer Coverage %** | **98.03%** | **98.34%** | **99.69%** | **100.00%** | **100.00%** |
| **Missing Core Buffer Area**| **$283.29\text{ km}^2$** | **$238.22\text{ km}^2$** | **$45.07\text{ km}^2$** | **$0.00\text{ km}^2$** | **$0.00\text{ km}^2$** |
| **Directional Buffer Gaps** | West (100.5), North (45.1), East (137.7) | West (100.5), East (137.7) | North only ($45.07\text{ km}^2$ in `N21`) | **Zero Gaps (100% W, E, N, S)** | **Zero Gaps** |
| **Ext. Buffer Area Covered**| **$14,115.70\text{ km}^2$** | **$16,745.61\text{ km}^2$** | **$14,353.93\text{ km}^2$** | **$16,983.83\text{ km}^2$** | **$17,152.00\text{ km}^2$** |
| **Ext. Buffer Coverage %** | **81.40%** | **96.56%** | **82.77%** | **97.94%** | **98.91%** |
| **Formal Classification** | `INADEQUATE_TRUNCATED` | `INADEQUATE_TRUNCATED` | **`PARTIAL_BUFFER_COVERAGE`** | **`COMPLETE_GEOMETRIC_BUFFER`**| `SEPARATE_CATCHMENT_SET` |
| **Operational Recommendation**| **REJECTED** | **REJECTED** | **Valid Minimal Option** | **RECOMMENDED BASELINE** | **Separate Hydro Corridor** |

### 3.1 Resolution of Package A Classification Contradiction
- In previous drafts, Package A was colloquially labeled "fully buffered" while simultaneously reporting 96% northern buffer coverage.
- **Correction Applied**: Package A is formally designated as **`PARTIAL_BUFFER_COVERAGE`**.
- It provides 100% closure of the western buffer (`N19E084`, `N20E084`), 100% closure of the eastern spit buffer (`N20E087`), and 100% closure of the southern ocean/lagoon buffer.
- However, because it caps latitude at $21.0000^\circ\text{N}$, it misses **$45.07\text{ km}^2$** of the northern 5 km buffer ($11.36\text{ km}^2$ in `N21E085` and $33.71\text{ km}^2$ in `N21E086`).
- It is accepted as the **smallest staged package** (186.93 MB), but its partial buffer limitation is explicitly documented.

### 3.2 Final Validation of Package B
- Package B adds `N21E085` and `N21E086` to Package A (total 9 tiles, 272.49 MB).
- It captures the missing $45.07\text{ km}^2$, achieving **exact 100.00% geometric coverage of the Core Delta actual 5 km buffer ($14,391.41\text{ km}^2$ covered, $0.00\text{ km}^2$ missing)**.
- For the Extended Delta (including Jajpur and Bhadrak), it captures **$16,983.83\text{ km}^2$ (97.94%)**, missing only outside marginal buffers in `N21E084` ($168.17\text{ km}^2$) and `N21E087` ($189.42\text{ km}^2$).
- **Scientific Caveat**: Complete geometric graticule coverage does **not guarantee valid DEM terrain pixels**. While COG bounding boxes align with the target footprint, local voids, coastline sea-level masking, or cloud-filled areas in raw Copernicus DSM can only be quantified after physical download and valid-data masking.

---

## 4. Authoritative Audit of Catchment Claims

In compliance with strict scientific standards, all previous catchment coverage claims have been audited:

### 4.1 Audit Findings:
1. **Lack of Defined Catchment Geometry**:
   - Previous claims of "10% gorge approach", "85% mainstem", and "98% full catchment" were heuristic ratios based on flood cell counts in specific tiles.
   - Flood cells do **not** delineate a hydrologic catchment. A catchment is defined by the topographic contributing area upstream of a hydrological pour point (e.g. Hirakud Dam $\approx 83,400\text{ km}^2$, Naraj delta apex $\approx 133,000\text{ km}^2$, total Mahanadi basin $\approx 141,589\text{ km}^2$).
   - No authoritative vector boundary shapefile or GeoJSON (such as India-WRIS / Central Water Commission CWC Mahanadi Basin boundary or HydroSHEDS / HydroBASINS Level 5/6 polygon `BasinID 405001`) has been ingested into repository storage.
2. **Preflight Boundary Governance**:
   - Ingesting HydroRIVERS, HydroBASINS, or CWC vector hydrography is explicitly prohibited under the Phase 7F.3.6 preflight restrictions ("Do not download rainfall, IMERG or HydroRIVERS during this phase").
3. **Formal Determination**:
   - All catchment coverage claims are designated:
     $$\mathbf{UNVERIFIED\_ESTIMATE}$$
4. **Data Required for Future Verification**:
   - Authoritative CWC Mahanadi Basin vector boundary polygon (India-WRIS).
   - HydroBASINS Level 5/6 contributing area polygon.
   - Authoritative CWC stream network lines to compute actual upstream river reach length coverage.
   - Upstream catchment coverage will remain separate and unverified until vector catchment ingestion is authorized.

---

## 5. Git and File Integrity Audit (`DFO_3382_inspection_summary.json`)

### 5.1 Investigation of Untracked Status:
- `docs/phase7/DFO_3382_inspection_summary.json` was generated on `2026-10-31T13:16:27 UTC` during the Phase 7F.3.5 controlled acquisition.
- Under Phase 7F.3.5 governance instructions, the agent was explicitly commanded:
  `"- Do not commit or push."`
- The file was intentionally left uncommitted in the Git working tree, alongside other Phase 7F deliverables, in strict adherence to user restrictions.

### 5.2 Bit-Exact Hash Verification:
All files on disk were audited against `docs/phase7/DFO_3382_inspection_summary.json` using SHA-256:

| Extracted Archive Member | Authoritative SHA-256 in Summary | Actual SHA-256 on Disk | Verification Result |
| :--- | :---: | :---: | :---: |
| `DFO_3382_From_20080922_to_20080929.tif` | `4c8c8f6e3927d71f3e7db3f6762c91c22b8de2bffa633b47f34df73d70c663de` | `4c8c8f6e...63de` | **VERIFIED BIT-EXACT MATCH** |
| `DFO_3382_properties.json` | `3f5471b3020f2abb5e41d9249f02ea2ccf91ba4129d91b9c8061f63b3ec43dca` | `3f5471b3...3dca` | **VERIFIED BIT-EXACT MATCH** |
| `LICENSE.txt` | `c2ca2f08eac60f04f65403daa6997e9a3bf254a18ba2f75a4500e23329fa4f4b` | `c2ca2f08...4f4b` | **VERIFIED BIT-EXACT MATCH** |
| `README_GFD.pdf` | `d87f838b260a3d7164449dc0b7408c7ffb317ccab3f5897ad186bcea09bb3fd9` | `d87f838b...3fd9` | **VERIFIED BIT-EXACT MATCH** |

The authoritative inspection summary and all underlying GFD data files are **100% intact, uncorrupted, and preserved without modification**.

---

## 6. Strict Governance Invariants Maintained

In strict compliance with project governance:

1. **Zero Data Downloads**: Zero DEM tiles, rainfall rasters, IMERG files, or HydroRIVERS shapefiles were acquired.
2. **Zero Terrain Derivatives Generated**: No slope, aspect, curvature, TWI, or HAND rasters were generated.
3. **Zero Resampling or Fabrication**: No missing terrain data was interpolated or simulated.
4. **Zero Model Training**: No machine learning models were trained, tuned, or updated.
5. **DFO 2507 Holdout Quarantine**: DFO 2507 remains quarantined as an `ALREADY_INSPECTED_HOLDOUT`.
6. **Phase 6 Hydrodynamic Physics Supremacy**: The Phase 6 deterministic hydrodynamic solver ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the **sole operational authority**.
7. **Zero Git Commits/Pushes**: No Git staging, committing, or pushing was executed.

---

## 7. Deliverables Updated

1. **Validated Preflight Report**:
   [`docs/phase7/PHASE_7F_3_6_DEM_COVERAGE_PREFLIGHT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_6_DEM_COVERAGE_PREFLIGHT.md)
2. **Validated Preflight Manifest**:
   [`data/manifests/phase7f36_dfo3382_dem_preflight_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7f36_dfo3382_dem_preflight_manifest.yaml)
3. **Validated Spatial Breakdown (JSON)**:
   [`docs/phase7/DFO_3382_mahanadi_dem_spatial_breakdown.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/DFO_3382_mahanadi_dem_spatial_breakdown.json)

---

## 8. Regression Testing & Git Status

The Phase 7 regression test suite was executed:
```bash
python -m pytest backend/tests/test_phase7c_multievent_dataset.py \
                 backend/tests/test_phase7_real_flood_dataset.py \
                 backend/tests/test_phase7d_kaggle_preflight.py \
                 backend/tests/test_phase7e_kaggle_package.py -v
```
**Test Results**: **`31 passed in 10.94s (100% pass rate)`**.

### Git Status:
```text
?? data/manifests/phase7f36_dfo3382_dem_preflight_manifest.yaml
?? docs/phase7/DFO_3382_dem_preflight_analysis.json
?? docs/phase7/DFO_3382_inspection_summary.json
?? docs/phase7/DFO_3382_mahanadi_dem_spatial_breakdown.json
?? docs/phase7/PHASE_7F_3_6_DEM_COVERAGE_PREFLIGHT.md
```

---

## 9. Final Preflight Decision

### Decision: `FINAL_PREFLIGHT_READY_FOR_APPROVAL`

> **APPROVAL GATE NOTICE**:
> Stages 1 and 2 are fully validated. Controlled acquisition remains paused at the Stage 2 Approval Gate.
>
> Two scientifically validated candidate packages are staged for user authorization:
> 1. **Package A (7 tiles, 186.93 MB)**: `N19E084`, `N19E085`, `N19E086`, `N20E084`, `N20E085`, `N20E086`, `N20E087` — *Classified as `PARTIAL_BUFFER_COVERAGE` (99.69% buffer coverage; omits 45.07 km² in northern margin)*.
> 2. **Package B (9 tiles, 272.49 MB — RECOMMENDED BASELINE)**: Package A plus `N21E085`, `N21E086` — *Classified as `COMPLETE_GEOMETRIC_BUFFER_COVERAGE` (100.00% Core Delta actual buffer closure; 0.00 km² missing)*.
>
> Awaiting explicit user authorization before acquiring any Copernicus DEM tiles.
