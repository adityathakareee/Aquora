# AQUORA — PHASE 7F.3.2: GEOSPATIAL COVERAGE & EVENT COMPATIBILITY AUDIT
### Spatial Footprint Intersections, Pixel-Level Verifications, Temporal Synchronization & Physical Feasibility Assessment

**Document Version:** `2.0.0-phase7f32-audit-correction`  
**Phase:** Phase 7F.3.2 Geospatial Coverage & Event Compatibility Audit (Corrected & Validated)  
**Task Type:** READ-ONLY GEOSPATIAL & EVENT COMPATIBILITY AUDIT (Zero source code changes, zero dataset modifications, zero downloads, zero model training, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine ([engines/flood/](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/))  
**Date:** 2026-10-31  

---

## 1. Executive Summary

Following the existing data inventory in [`docs/phase7/PHASE_7F_3_1_EXISTING_DATA_INVENTORY.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_1_EXISTING_DATA_INVENTORY.md), this audit evaluates the **spatial footprint overlap, pixel-level label coverage, temporal synchronization, and physical feasibility** of the four historical flood events present in the AQUORA repository:

* **DFO 2507** — North Bihar / Kosi Basin (June 2004) — *Already-Inspected Holdout*
* **DFO 2935** — Upper Godavari Basin / Maharashtra (July 2006) — *Training Subset*
* **DFO 3372** — Upper Brahmaputra Basin / Assam (August 2008) — *Validation Subset*
* **DFO 4499** — Lower Ganga Basin / West Bengal (July 2017) — *Training Subset*

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               REVISED FOUR-EVENT FEASIBILITY & COMPATIBILITY MATRIX                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Event ID   Basin / State      Study Box DEM   Full Flood Cells Covered   IMERG Sub-Daily   Governance Verdict
  ────────────────────────────────────────────────────────────────────────────────────────
  DFO 4499   Lower Ganga, WB    100.0% (1°×1°)  16.58% (11,152 / 67,267)   0.0% (Missing)    PARTIALLY_SUPPORTED
  DFO 2935   Up. Godavari, MH   100.0% (1°×1°)   0.069% (355 / 511,655)    0.0% (Missing)    PARTIALLY_SUPPORTED
  DFO 3372   Up. Brahmaputra, AS 100.0% (1°×1°)   7.01% (21,170 / 302,186)  0.0% (Missing)    PARTIALLY_SUPPORTED
  DFO 2507   North Bihar, BR    100.0% (1°×1°)   0.839% (11,435 / 1,362,413) 0.0% (Missing)  BLOCKED_BY_DATA_GAPS
                                                                                             (HOLDOUT QUARANTINE)
  ────────────────────────────────────────────────────────────────────────────────────────
```

### Critical Methodological Corrections Adopted in this Audit:

1. **Strict Separation of Study-Box Coverage from Full-Event Coverage**:
   * Complete DEM coverage across an arbitrarily selected $1^\circ \times 1^\circ$ study window must **never be described as 100% full-event coverage**.
   * In reality, the available Copernicus DEM tiles cover only **0.069% to 16.58% of the verified episodic flood pixels** documented in the full regional disaster rasters. Between **83.4% and 99.93%** of all flood pixels occurred *outside* the cropped $1^\circ \times 1^\circ$ DEM windows.
2. **Preservation of Native Ground-Truth Spatial Resolution**:
   * The Global Flood Database / MODIS flood masks have a native spatial resolution of **$\approx 250\text{ m} \times 250\text{ m}$**.
   * Resampling or point-sampling a 250m label mask at 30m grid intervals (as conducted in Phase 7C/7E) duplicates each observation $\approx 65$ times. **Resampling does NOT produce genuine 30m ground-truth accuracy**, and introduces significant sub-grid topographic mismatch and artificial sample inflation.
3. **Correction of DFO 3372 Validation Status**:
   * The existing Phase 7E DFO 3372 validation dataset (5,000 samples) was **artificially subsampled to a 50.0% flood / 50.0% dry balance** (2,500 flood, 2,500 dry). It is **NOT naturally imbalanced validation data**.
   * The actual event-level natural flood prevalence inside the DEM window is **18.038%** (21,170 flood / 117,363 total valid binary cells), and across the full disaster raster is **5.210%**.
   * Probability calibration and operational threshold selection must not use the existing balanced sample without explicit reweighting and independent validation.
4. **Complete Sub-Daily Precipitation Deficit**:
   * Daily CHIRPS rainfall exists for the 24h and 72h antecedent windows across all 4 events.
   * However, **0.0% of the required sub-daily precipitation (`1h`, `3h`, `6h`) exists on physical disk** for any of the 4 disaster dates.
5. **HAND Feasibility Boundary**:
   * Computing HAND from isolated $1^\circ \times 1^\circ$ DEM tiles produces severe boundary truncation artifacts (trunk rivers entering tiles have zero accumulated area). Without continental DEM coverage and HydroRIVERS stream burning, HAND generation remains a **STRICT CONSERVATIVE NO-GO**.

---

## 2. Four-Event Geospatial & Verification Matrix

| Evaluation Dimension | DFO 4499 (West Bengal) | DFO 2935 (Maharashtra) | DFO 3372 (Assam) | DFO 2507 (Bihar - Holdout) |
| :--- | :--- | :--- | :--- | :--- |
| **Disaster Interval** | 2017-07-27 to 2017-08-10 | 2006-07-28 to 2006-09-12 | 2008-08-30 to 2008-09-08 | 2004-06-20 to 2004-10-07 |
| **Observation Timestamp** | 2017-07-27 | 2006-07-28 | 2008-08-30 | 2004-06-20 |
| **Study Bounding Box ($1^\circ \times 1^\circ$)** | `[88.0–89.0°E, 22.0–23.0°N]` | `[73.0–74.0°E, 20.0–21.0°N]` | `[94.0–95.0°E, 27.0–28.0°N]` | `[85.0–86.0°E, 25.0–26.0°N]` |
| **Full Raw GFD Bounding Box** | `[83.88–91.20°E, 20.30–24.86°N]` | `[67.99–89.75°E, 8.07–31.46°N]` | `[82.01–98.83°E, 16.35–31.28°N]` | `[73.39–100.23°E, 15.67–32.77°N]` |
| **Full Raster Dimensions (Cells)** | $3,257 \times 2,034 = 6,624,738$ | $9,687 \times 10,413 = 100,870,731$ | $7,490 \times 6,648 = 49,793,520$ | $11,953 \times 7,616 = 91,034,048$ |
| **Full GFD Episodic Flood Cells** | **67,267 cells** | **511,655 cells** | **302,186 cells** | **1,362,413 cells** |
| **Full GFD Verified Dry Cells** | **3,099,235 cells** | **33,929,073 cells** | **5,497,842 cells** | **24,077,905 cells** |
| **Full Event Natural Prevalence** | **2.124%** (67k / 3.17M) | **1.486%** (512k / 34.44M) | **5.210%** (302k / 5.80M) | **5.355%** (1.36M / 25.44M) |
| **DEM Window Total Cells (250m)** | 198,025 cells ($445 \times 445$) | 198,025 cells ($445 \times 445$) | 198,025 cells ($445 \times 445$) | 198,025 cells ($445 \times 445$) |
| **DEM Window Episodic Flood** | **11,152 cells** | **355 cells** | **21,170 cells** | **11,435 cells** |
| **DEM Window Verified Dry** | **173,909 cells** | **118,835 cells** | **96,193 cells** | **185,070 cells** |
| **DEM Window Valid Binary Total** | **185,061 cells** | **119,190 cells** | **117,363 cells** | **196,505 cells** |
| **DEM Window Natural Prevalence** | **6.026%** | **0.298%** | **18.038%** | **5.819%** |
| **Actual Flood Pixel Coverage** | **16.58%** (11,152 / 67,267) | **0.069%** (355 / 511,655) | **7.01%** (21,170 / 302,186) | **0.839%** (11,435 / 1,362,413) |
| **Actual Dry Pixel Coverage** | **5.61%** (173.9k / 3.10M) | **0.350%** (118.8k / 33.93M) | **1.75%** (96.2k / 5.50M) | **0.769%** (185.1k / 24.08M) |
| **1°×1° Study Box DEM Coverage** | **100.0%** ($3600 \times 3600$) | **100.0%** ($3600 \times 3600$) | **100.0%** ($3600 \times 3600$) | **100.0%** ($3600 \times 3600$) |
| **Full Bounding-Box DEM Overlap** | **2.99%** of geographic area | **0.20%** of geographic area | **0.40%** of geographic area | **0.22%** of geographic area |
| **CHIRPS Daily (24h/72h)** | **100.0%** (Jul 25, 26, 27) | **100.0%** (Jul 26, 27, 28) | **100.0%** (Aug 28, 29, 30) | **100.0%** (Jun 18, 19, 20) |
| **GPM IMERG 30-min Final Run** | **0.0%** (Missing) | **0.0%** (Missing) | **0.0%** (Missing) | **0.0%** (Missing) |
| **HydroRIVERS Vector Network** | **0.0%** (Missing) | **< 0.1%** (Nashik edge only) | **0.0%** (Missing) | **< 0.5%** (Patna segment only) |
| **ESA WorldCover 2021** | 100% of study box (4-yr gap) | 100% of study box (15-yr gap) | 100% of study box (13-yr gap) | 100% of study box (17-yr gap) |
| **MODIS/CCI Historical LC** | **0.0%** (Absent) | **0.0%** (Absent) | **0.0%** (Absent) | **0.0%** (Absent) |
| **Phase 7E Sample Distribution** | 2,500 F / 2,500 D (50.0%) | 350 F / 350 D (50.0%) | 2,500 F / 2,500 D (50.0%) | 11,435 F / 185,070 D (5.82%) |
| **Phase 7E Split Role** | Train | Train | Validation | Test (Holdout) |
| **Revised Governance Verdict** | `PARTIALLY_SUPPORTED` | `PARTIALLY_SUPPORTED` | `PARTIALLY_SUPPORTED` | `BLOCKED_BY_DATA_GAPS` |

---

## 3. Spatial Compatibility: Study-Box vs. Full-Event Distinction

### Geometric Overlap vs. Actual Pixel Support

A critical distinction must be enforced between **geographic bounding-box intersections** and **actual physical pixel support**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│             GEOMETRIC BOUNDS vs. ACTUAL EPISODIC FLOOD PIXEL SUPPORT                   │
└────────────────────────────────────────────────────────────────────────────────────────┘

  DFO 4499 (West Bengal, 2017):
  ├── Selected 1°×1° Study Box Area: 100.0% DEM coverage
  ├── Full Bounding-Box Area Overlap: 2.99% of regional bounding rectangle
  └── ACTUAL EPISODIC FLOOD PIXEL COVERAGE: 16.58% (11,152 of 67,267 flood cells)

  DFO 2935 (Maharashtra, 2006):
  ├── Selected 1°×1° Study Box Area: 100.0% DEM coverage
  ├── Full Bounding-Box Area Overlap: 0.20% of regional bounding rectangle
  └── ACTUAL EPISODIC FLOOD PIXEL COVERAGE: 0.069% (355 of 511,655 flood cells)

  DFO 3372 (Assam, 2008):
  ├── Selected 1°×1° Study Box Area: 100.0% DEM coverage
  ├── Full Bounding-Box Area Overlap: 0.40% of regional bounding rectangle
  └── ACTUAL EPISODIC FLOOD PIXEL COVERAGE: 7.01% (21,170 of 302,186 flood cells)

  DFO 2507 (North Bihar, 2004):
  ├── Selected 1°×1° Study Box Area: 100.0% DEM coverage
  ├── Full Bounding-Box Area Overlap: 0.22% of regional bounding rectangle
  └── ACTUAL EPISODIC FLOOD PIXEL COVERAGE: 0.839% (11,435 of 1,362,413 flood cells)
```

#### Analytical Implications of Spatial Truncation:
1. **Severe Undersampling of Peninsular Floods (DFO 2935)**:
   In Phase 7C, DFO 2935 provided only 700 binary rows. The pixel-level verification confirms the physical reason: the single DEM tile in Nashik ($20^\circ\text{N}–21^\circ\text{N}, 73^\circ\text{E}–74^\circ\text{E}$) intercepted **only 355 episodic flood cells out of 511,655 cells** across the central Indian plateau (**0.069%**). Over 99.9% of the flood event occurred in Vidarbha, Telangana, and coastal Andhra Pradesh where zero DEM tiles were acquired.
2. **Kosi Mega-Fan Displacement (DFO 2507)**:
   The 196,505 rows in the DFO 2507 test set represent **only 0.839% of the flood cells** in the 2004 Bihar disaster (11,435 out of 1,362,413 cells). The tile was centered on Patna / Begusarai ($85^\circ\text{E}–86^\circ\text{E}$), missing the epicentral Kosi avulsion fan in Supaul, Saharsa, and Madhepura ($86.5^\circ\text{E}–87.5^\circ\text{E}$).

---

## 4. Preservation of Native Ground-Truth Spatial Resolution

### The 250m to 30m Downsampling Fallacy

The GFD flood labels originate from the **MODIS MOD09GA / MYD09GA surface reflectance sensors**, which operate at a native spatial resolution of **$\approx 250\text{ m} \times 250\text{ m}$**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     RESOLUTION SCALE & PIXEL INFLATION RATIO                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Sensor / Dataset         Pixel Dimension (deg)   Linear Res (m)    Cell Area (m²)
  ────────────────────────────────────────────────────────────────────────────────────────
  Copernicus DEM GLO-30    0.00027777778°          ~30.8 m            ~950 m²
  GFD / MODIS Ground Truth 0.00224578821°          ~249.5 m         ~62,250 m²
  ────────────────────────────────────────────────────────────────────────────────────────
  RATIO (MODIS / DEM)      8.085× linear           8.085× linear     65.4× cell area
```

#### Implications for Modeling and Feature Extraction:

1. **Synthetic Sample Inflation**:
   When a 250m MODIS pixel is resampled to 30m (or points sampled at 30m intervals), **approximately 65 identical binary labels** are created for a single physical observation. The 196,505 rows in DFO 2507 represent at most **$\approx 3,023$ independent satellite observations**. Treating these 196,505 rows as independent identically distributed (i.i.d.) observations severely underestimates confidence intervals and inflates apparent statistical support.
2. **Sub-Grid Topographic Contamination**:
   A single $250\text{ m} \times 250\text{ m}$ area in an alluvial floodplain frequently contains both low-lying river channels and elevated river embankments or road crests. If MODIS detects water within that 6.2-hectare pixel, assigning a label of $1$ to every 30m cell within it marks the elevated road crest as flooded. Decision trees trained on 30m DEM elevation paired with 250m flood masks learn that elevated features flood, directly increasing false-positive rates.
3. **Requirement for Phase 8 Architecture**:
   Future feature pipelines must either:
   * Aggregate 30m DEM and terrain predictors up to the authentic 250m MODIS footprint (e.g. mean, min, and variance of elevation within each 250m cell), or
   * Acquire authentic high-resolution ground truth (e.g. **Sentinel-1 SAR at 10m/30m** or Sentinel-2 MSI at 10m/20m).

---

## 5. Correction of DFO 3372 Validation Claims

### Balanced Artifact vs. Natural Population Prevalence

The Phase 7E Kaggle Version 2 training package documented DFO 3372 as its validation split ([data/manifests/phase7e_kaggle_package_manifest.yaml:L72-L79](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7e_kaggle_package_manifest.yaml#L72-L79)).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   DFO 3372 VALIDATION PREVALENCE DISCREPANCY                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Data Entity                       Flood Pixels (1)   Dry Pixels (0)   Total Valid   Prevalence
  ────────────────────────────────────────────────────────────────────────────────────────
  1. Existing Phase 7E Sample                  2,500            2,500         5,000      50.000%
  2. Native DEM Window (Actual)               21,170           96,193       117,363      18.038%
  3. Full Disaster Raster (Regional)         302,186        5,497,842     5,800,028       5.210%
  4. Test Holdout (DFO 2507 Bihar)            11,435          185,070       196,505       5.819%
```

#### Methodological Findings & Safeguards:

1. **DFO 3372 is Artificially Balanced**:
   The existing Phase 7E validation dataset contains an exact 50.0% / 50.0% balance. Describing it as naturally imbalanced validation data is **empirically false**.
2. **The Decision Cutoff Distortion**:
   Optimizing the classification threshold $\tau$ to maximize $F_1$ on this 50/50 balanced validation set chose $\tau = 0.01$. Because the validation set had 10 times higher flood prevalence than the real landscape (50% vs. 5.8%), lowering $\tau$ captured all positives while masking the false alarm explosion.
3. **Governance Restriction on Calibration**:
   * Probability calibration (Platt scaling, Isotonic regression) and threshold tuning must **NOT be performed on the existing balanced 5,000-sample validation table**.
   * Calibration must be fitted on an unskewed, naturally distributed sample that preserves the authentic $18.04\%$ natural prevalence of the basin (or weighted using inverse sampling probabilities).
   * **Quarantine Enforcement**: DFO 2507 remains an `ALREADY_INSPECTED_HOLDOUT`. Calibration parameters must **never be fitted or selected against DFO 2507**.

---

## 6. Complete CHIRPS Date Availability Audit

The physical availability of daily CHIRPS GeoTIFFs (`.tif.gz`) was audited across all event dates:

| Event ID | Primary Date | Required Antecedent Dates | Available Files in `data/raw/phase7/rainfall/chirps/daily/` | Antecedent Windows Valid? | Sub-Daily Intra-Day Available? |
| :--- | :---: | :--- | :--- | :---: | :---: |
| **DFO 4499** | 2017-07-27 | 2017-07-25, 2017-07-26, 2017-07-27 | `chirps-v2.0.2017.07.25.tif.gz` (2.81 MB)<br>`chirps-v2.0.2017.07.26.tif.gz` (2.69 MB)<br>`chirps-v2.0.2017.07.27.tif.gz` (2.67 MB) | **YES** (24h & 72h valid) | **NO (0.0%)** |
| **DFO 2935** | 2006-07-28 | 2006-07-26, 2006-07-27, 2006-07-28 | `chirps-v2.0.2006.07.26.tif.gz` (2.96 MB)<br>`chirps-v2.0.2006.07.27.tif.gz` (3.32 MB)<br>`chirps-v2.0.2006.07.28.tif.gz` (3.28 MB) | **YES** (24h & 72h valid) | **NO (0.0%)** |
| **DFO 3372** | 2008-08-30 | 2008-08-28, 2008-08-29, 2008-08-30 | `chirps-v2.0.2008.08.28.tif.gz` (3.07 MB)<br>`chirps-v2.0.2008.08.29.tif.gz` (3.34 MB)<br>`chirps-v2.0.2008.08.30.tif.gz` (3.26 MB) | **YES** (24h & 72h valid) | **NO (0.0%)** |
| **DFO 2507** | 2004-06-20 | 2004-06-18, 2004-06-19, 2004-06-20 | `chirps-v2.0.2004.06.18.tif.gz` (2.61 MB)<br>`chirps-v2.0.2004.06.19.tif.gz` (2.57 MB)<br>`chirps-v2.0.2004.06.20.tif.gz` (2.60 MB) | **YES** (24h & 72h valid) | **NO (0.0%)** |

### Additional CHIRPS Files Audit:
The remaining 23 CHIRPS files in `data/raw/` represent single event days (e.g. 2005.07.26 for Mumbai, 2013.06.16 for Uttarakhand, 2015.12.01 for Chennai, 2018.08.16 for Kerala). **Antecedent 72h windows cannot be constructed for those other historical disasters** because $t_{-1}$ and $t_{-2}$ files were never acquired. Only the four Phase 7C events possess continuous 3-day sequences.

---

## 7. HAND Feasibility: Retaining the Conservative NO-GO

The proposal to compute Height Above Nearest Drainage (HAND) directly from the existing disk assets is confirmed as a **STRICT CONSERVATIVE NO-GO**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HAND COMPUTATIONAL BOTTLENECKS                                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
  1. BOUNDARY TRUNCATION ARTIFACTS  ──► Upstream flow accumulation reset to 0 at tile edges.
  2. FLAT ALLUVIAL FAN LOOPING      ──► Supaul/Kosi slopes < 0.1° trapped in artificial sinks.
  3. MISSING STREAM BURN-IN         ──► HydroRIVERS vector network missing from raw storage.
```

### Technical Obstacles:
1. **Flow Clipping on Isolated 1° Tiles**:
   Flow accumulation requires tracking precipitation across the entire upstream watershed. For North Bihar, the Kosi catchment drains thousands of square kilometers of the Nepalese Himalayas. A $1^\circ \times 1^\circ$ tile clips this flow at $26.0^\circ\text{N}$, assigning zero upstream area to the main river channel entering the tile.
2. **DEM Elevation Noise in Low Relief**:
   In low-relief deltaic and alluvial plains (slopes $< 0.1^\circ$), raw Copernicus DEM elevation noise ($\pm 1.5\text{ m}$) exceeds the regional hydraulic gradient. Depressions cannot be solved by simple priority-flood filling without **hydro-enforced stream burning**.
3. **Absence of Vector Centerlines**:
   HydroRIVERS South Asia is absent from `data/raw/hydrography/hydrorivers/`. Without river polylines, hydro-enforcement is impossible.
4. **Conclusion**:
   No HAND calculation should be attempted on local raw tiles. Phase 8 must acquire precomputed continental HAND (e.g., **MERIT-Hydro 90m HAND**) or complete multi-tile regional DEMs paired with HydroRIVERS.

---

## 8. Audit Corrections and Pixel-Level Verification

This section explicitly documents the technical calculations performed during this audit versus measurements that remain unverified:

### Calculations Performed and Physically Verified:
1. **CRS and Grid Alignment**: Verified via `rasterio` that all 4 DEM tiles, 4 ESA WorldCover tiles, and 4 DFO flood rasters share the identical coordinate reference system: **EPSG:4326 (WGS84 lat/long)**.
2. **Exact Resolution Ratio**: Verified that Copernicus DEM resolution is $0.00027778^\circ$ ($\approx 30.8\text{ m}$) and DFO resolution is $0.00224579^\circ$ ($\approx 249.5\text{ m}$), establishing an exact pixel area ratio of **$65.4\times$**.
3. **Valid DEM Pixels**: Verified that all 4 DEM tiles have **$3,600 \times 3,600 = 12,960,000$ valid data pixels** (0% NoData within the tile bounds).
4. **Native 250m DFO Window Pixel Counts**:
   Computed the exact pixel counts within the DEM bounding windows:
   * **DFO 4499**: 11,152 flood / 173,909 dry (Total valid binary: 185,061; natural prevalence: 6.026%).
   * **DFO 2935**: 355 flood / 118,835 dry (Total valid binary: 119,190; natural prevalence: 0.298%).
   * **DFO 3372**: 21,170 flood / 96,193 dry (Total valid binary: 117,363; natural prevalence: 18.038%).
   * **DFO 2507**: 11,435 flood / 185,070 dry (Total valid binary: 196,505; natural prevalence: 5.819%).
5. **Full Raster Coverage Percentages**:
   Verified against the full disaster rasters that the DEM tiles cover:
   * DFO 4499: **16.58%** of flood pixels, **5.61%** of dry pixels.
   * DFO 2935: **0.069%** of flood pixels, **0.350%** of dry pixels.
   * DFO 3372: **7.01%** of flood pixels, **1.75%** of dry pixels.
   * DFO 2507: **0.839%** of flood pixels, **0.769%** of dry pixels.
6. **HydroRIVERS Spatial Gaps**:
   Verified via `shapely` that existing pilot snippets have **0.0% overlap** with DFO 4499 and DFO 3372, and only minor isolated line segments (< 0.5%) in DFO 2935 and DFO 2507.
7. **Precipitation Date Sequences**:
   Verified that daily CHIRPS files cover the exact 3-day antecedent windows for all 4 events, while half-hourly IMERG files cover **0.0%** of the event dates.

### Measurements and Assets that Remain Unverified / Incalculable:
1. **Upstream Watershed Runoff**:
   Runoff generation outside the $1^\circ \times 1^\circ$ DEM tiles cannot be calculated because regional contributing terrain is not downloaded.
2. **True Distance to River Centerline**:
   Because HydroRIVERS is missing for rural floodplains, actual flow-path distance to river channels remains unverified across all 4 events.
3. **Sub-Daily Cloudburst Intensity**:
   Maximum 1-hour and 3-hour precipitation rates during historical peak flood stages remain unverified due to the absence of IMERG Final Run granules.

---

## 9. Revised Four-Event Feasibility Classifications

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        REVISED EVENT FEASIBILITY VERDICTS                              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1. DFO 4499 — Lower Ganga Basin (West Bengal, 2017)
* **Classification**: `PARTIALLY_SUPPORTED`
* **Feasibility Verdict**: **CONDITIONAL PROTOTYPE GO (Static Terrain & Daily Rain Only)**
* **Evidence**:
  * 100% DEM and WorldCover across the $1^\circ \times 1^\circ$ study window.
  * Captures 11,152 flood pixels (16.58% of regional flood extent).
  * Lowest temporal land-cover offset (4 years).
  * CHIRPS daily rainfall synchronized (2017.07.25–27).
  * **Restrictions**: Sub-daily rain and HAND are blocked. Model prototyping must be restricted to static terrain derivatives and daily rainfall.

### 2. DFO 2935 — Upper Godavari Basin (Maharashtra, 2006)
* **Classification**: `PARTIALLY_SUPPORTED`
* **Feasibility Verdict**: **SEVERELY CONSTRAINED (Exploratory Only)**
* **Evidence**:
  * Captures only 355 episodic flood cells out of 511,655 cells across central India (**0.069%**).
  * Yields only 700 balanced rows in Phase 7C/7E.
  * 15-year land-cover gap (2021 vs. 2006).
  * CHIRPS daily rainfall synchronized (2006.07.26–28).
  * **Restrictions**: Sample support is too small to serve as an independent training backbone without multi-tile DEM expansion.

### 3. DFO 3372 — Upper Brahmaputra Basin (Assam, 2008)
* **Classification**: `PARTIALLY_SUPPORTED`
* **Feasibility Verdict**: **VALIDATION DESIGN GO (Requires Sampling Correction)**
* **Evidence**:
  * Captures 21,170 flood pixels (7.01% of regional flood extent).
  * Natural prevalence in DEM window is **18.038%**.
  * Existing Phase 7E sample is artificially balanced (50/50, 5,000 rows).
  * CHIRPS daily rainfall synchronized (2008.08.28–30).
  * **Restrictions**: Must NOT be treated as naturally imbalanced validation data in its current 5,000-row format. Threshold selection and probability calibration require reweighting or sampling from the unskewed 117,363-cell population.

### 4. DFO 2507 — North Bihar / Kosi Basin (Bihar, 2004)
* **Classification**: `BLOCKED_BY_DATA_GAPS`
* **Feasibility Verdict**: **STRICT NO-GO FOR TRAINING (QUARANTINED HOLDOUT BENCHMARK ONLY)**
* **Evidence**:
  * Severe physical geomorphic invalidation: the August 2008 Kosi embankment breach shifted river courses by $> 100\text{ km}$, making 2021 WorldCover unrepresentative of 2004 geomorphology.
  * Single DEM tile omits 99.16% of the regional flood extent (covers only 11,435 of 1,362,413 flood cells).
  * Flat alluvial fan terrain creates DEM sink looping.
  * **Governance Mandate**: DFO 2507 is designated as an **ALREADY_INSPECTED_HOLDOUT**. It must **NEVER be accessed for feature prototyping, model training, threshold selection, or calibration fitting**. It remains quarantined strictly as an unadjusted historical benchmark.

---

## 10. Architectural Safeguards Preserved

1. **Deterministic Authority**:
   The Phase 6 deterministic hydrodynamic physics engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the **sole authorized operational authority** for physical flood depths, velocities, and evacuation routing.
2. **Deep Zone Invariant**:
   Mumbai / Mithi (`deep_mumbai_mithi`) remains the ONLY active Deep Zone. National machine learning outputs must NEVER overwrite hydrodynamic simulations.
3. **Zero Synthetic Target Policy**:
   All supervised flood targets must originate strictly from authentic satellite observations.
4. **Experimental Status**:
   All screening models remain categorized: `EXPERIMENTAL_EVALUATION_ONLY` / `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`.

---

## 11. Final Methodological Clarifications & Count Reconciliation

### 11.1 Nature of DEM-Window DFO Cell Counts
* **Native Grid Footprint**: The reported DEM-window DFO cell counts (11,152 for DFO 4499; 355 for DFO 2935; 21,170 for DFO 3372; 11,435 for DFO 2507) represent native $\approx 250\text{ m}$ MODIS raster observations ($0.00224579^\circ \times 0.00224579^\circ$) that physically intersect the geographic bounding box ($1^\circ \times 1^\circ$) of the available Copernicus DEM GLO-30 tile.
* **Non-Equivalence to Full-Event or Basin Coverage**: These counts establish spatial intersection with the single local DEM tile only. They **do NOT establish full-event coverage** (as 83.4% to 99.93% of episodic flood cells lie outside the tile), nor do they establish hydrological catchment coverage (which requires upstream watershed drainage boundaries).
* **Resolution Integrity**: These counts must **NOT be interpreted or converted to genuine 30m ground-truth labels**. While a 30m grid can sample the 250m label field, doing so replicates each satellite observation $\approx 65.4\times$ and does not increase spatial precision or resolve sub-grid topographic features.

### 11.2 Scope of CHIRPS Precipitation Verification
* **Physical File Existence Only**: The CHIRPS audit in Section 6 verifies that daily `.tif.gz` archive files exist on local disk for the listed event dates (`2017.07.25–27`, `2006.07.26–28`, `2008.08.28–30`, `2004.06.18–20`).
* **Unverified Precipitation Dimensions**: Unless separately extracted and calculated at the pixel level, this audit **does NOT claim that rainfall pixel values, valid-data coverage masks, spatial precipitation gradients, or event-peak timings have been validated**.
* **Provisional Temporal Reference**: The DFO event start date (`began`) is an administrative reporting reference derived from news and disaster records; it is **provisional and does NOT necessarily coincide with the meteorological onset, local catchment runoff peak, or maximum inundation stage**.
* **Sub-Daily Deficit**: Sub-daily (1h, 3h, 6h) precipitation remains **completely unavailable** across all historical events.

### 11.3 Reconciliation of Full-Event Flood Cell Counts with Earlier Reports
Discrepancies between the cell counts in this audit, [`docs/phase7/PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md), [`data/manifests/phase7c_multievent_acquisition_manifest.yaml`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7c_multievent_acquisition_manifest.yaml), and [`docs/phase7/PHASE_7F_3_1_EXISTING_DATA_INVENTORY.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_1_EXISTING_DATA_INVENTORY.md) originate from three distinct counting bases:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      RECONCILIATION OF CELL COUNTING BASES                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Event ID   Audit Basis A: DEM Window (250m)   Audit Basis B: Full Manifest (250m)   Inventory Report (7F.3.1)
  ────────────────────────────────────────────────────────────────────────────────────────
  DFO 4499   11,152 pure flood (185,061 valid)    67,267 pure flood (80,164 raw)        80,164 flood (72,887 perm)
  DFO 2935      355 pure flood (119,190 valid)   511,655 pure flood (611,944 raw)    1,104,291 flood (1,412,088 perm)
  DFO 3372   21,170 pure flood (117,363 valid)   302,186 pure flood (344,932 raw)      312,890 flood (451,200 perm)
  DFO 2507   11,435 pure flood (196,505 valid) 1,362,413 pure flood (1,550,173 raw)    872,014 flood (1,842,912 perm)
  ────────────────────────────────────────────────────────────────────────────────────────
```

1. **Basis A — DEM Window Pure Episodic Flood**:
   * *Definition*: Evaluated **only within the 1°×1° DEM bounding box** on the native 250m grid ($445 \times 445$ cells).
   * *Formula*: `(flooded == 1.0) & (jrc_perm_water == 0.0) & (clear_perc >= 0.70)`.
   * *Yields*: 11,152 (DFO 4499), 355 (DFO 2935), 21,170 (DFO 3372), 11,435 (DFO 2507).
   * *Role in Earlier Reports*: These are the exact available pool counts reported in Phase 7C Table 5.2 from which the 2,500 / 350 training/validation samples were drawn.
2. **Basis B — Full-Event Authoritative Manifest**:
   * *Definition*: Evaluated across the **entire regional GFD disaster raster** in [`scripts/acquire_phase7c_multievent_data.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/acquire_phase7c_multievent_data.py#L154-L165) and logged in `phase7c_multievent_acquisition_manifest.yaml`.
   * *Formula*:
     * `raw_flooded_cells`: `(flooded == 1.0)` across all valid cells.
     * `verified_episodic_flood_cells`: `(flooded == 1.0) & (jrc_perm_water == 0.0) & (clear_perc >= 0.70)`.
     * `verified_dry_cells`: `(flooded == 0.0) & (jrc_perm_water == 0.0) & (clear_perc >= 0.70)`.
   * *Yields*:
     * DFO 4499: 67,267 verified episodic flood (from 80,164 raw flooded; 72,887 permanent water).
     * DFO 2935: 511,655 verified episodic flood (from 611,944 raw flooded; 195,443 permanent water).
     * DFO 3372: 302,186 verified episodic flood (from 344,932 raw flooded; 86,009 permanent water).
     * DFO 2507: 1,362,413 verified episodic flood (from 1,550,173 raw flooded; 325,953 permanent water).
3. **Earlier Phase 7F.3.1 Inventory Table Discrepancies**:
   * For **DFO 4499**, the 7F.3.1 inventory table recorded `80,164` flooded cells, which matches **`raw_flooded_cells` exactly** (prior to permanent-water exclusion and quality masking).
   * For **DFO 2935, 3372, and 2507**, the cell counts in 7F.3.1 Table 3 (`1,104,291`, `312,890`, `872,014`) cannot be reconciled with either the raw or verified counts in the authoritative Phase 7C acquisition manifest. They represent an **unresolved alternative counting basis** (e.g., preliminary exploratory sums across different duration thresholds or unmasked regional bounding subsets). The authoritative full-event ground-truth counts are those formalized in `phase7c_multievent_acquisition_manifest.yaml` (Basis B).

### 11.4 Strict Governance & Feasibility Matrix Preservation
All governance boundaries established in Phase 7E and 7F.1–7F.3 remain in full effect:
* **DFO 2507 Inspected Holdout Quarantine**: DFO 2507 is strictly classified as an `ALREADY_INSPECTED_HOLDOUT`. It is quarantined and must never be accessed for feature selection, hyperparameter tuning, probability calibration, or decision threshold optimization.
* **DFO 3372 Balanced Validation Status**: The existing 5,000-sample Phase 7E validation set is artificially balanced (50/50) and must not be described or utilized as naturally imbalanced validation data without sampling corrections.
* **Prohibitions Maintained**:
  * No model training, threshold tuning, or probability calibration.
  * No test-set inspection or iterative parameter fitting.
  * No HAND generation from isolated tiles without regional hydro-conditioning.
  * No new dataset downloads, feature engineering, source code edits, or model artifact generation.
  * No Git commit or push.

