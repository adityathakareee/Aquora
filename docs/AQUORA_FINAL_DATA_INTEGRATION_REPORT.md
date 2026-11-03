# AQUORA — Final Integrated Data Infrastructure Report

**Document ID:** `DOC-AQUORA-FINAL-DATA-INTEGRATION-2026-V1`  
**Classification:** Scientific Infrastructure & Data Governance Report  
**Date:** November 3, 2026  
**Status:** Approved & Validated Operational Baseline  
**Scope:** Pan-India Geospatial, Hydrographic, Hydrometeorological, and Physical Datasets  

---

## 1. Executive Summary

This report establishes the complete, authoritative data infrastructure of **AQUORA 2.0**, an operational flood intelligence system structured across three nested geographic and analytical tiers:
1. **Tier 1 (National Macro Screening):** Pan-India flood susceptibility ranking using the frozen 7-feature Kaggle XGBoost classifier trained on authentic global and national disaster records.
2. **Tier 2 (Regional Watershed Intelligence):** Basin-scale hydrological governance using genuine **HydroBASINS Level 04** polygon containment and **HydroRIVERS Asia** hydrographic stream networks.
3. **Tier 3 (Deep Intelligence Zone):** Physics-first urban flood hydraulics powered by the **Phase 6 deterministic 2D shallow-water numerical solver**, operational exclusively within the **Mumbai / Mithi River catchment**.

### Core Scientific & Data Invariants
- **Zero Fabrication Invariant:** No missing feature or predictor is ever synthesized, imputed with global or regional averages, or replaced with default placeholders. Missing operational observations strictly trigger `INSUFFICIENT_INPUT_DATA` inference suppression.
- **Physics Solver Primacy:** In the Mumbai Deep Intelligence Zone, deterministic shallow-water equations maintain absolute operational supremacy over statistical proxies.
- **Operational vs. Benchmark Isolation:** Historical disaster benchmark fixtures (e.g., NASA IMERG 2008 Kosi deluge, June 2022 Assam flood, August 2020 Mumbai cloudburst) are strictly tagged as `LITERATURE_DERIVED_BENCHMARK` / `NON_OPERATIONAL_TEST_FIXTURE` and can never be claimed as live operational observations.
- **Validation Holdout Quarantine:** DFO 2507 remains strictly quarantined as an untouched blind holdout for third-party auditing; it has never been accessed for training, threshold tuning, or feature engineering.

---

## 2. Comprehensive Inventory of Integrated Authentic Datasets

| Dataset Asset | Originating Provider | Format & Storage Path | Spatial Resolution | Temporal Coverage | Role & Application in AQUORA |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Copernicus GLO-30 DEM** | European Space Agency (ESA) / Airbus | Cloud-Optimized GeoTIFF (COG), `data/processed/dem/` | 1 arc-second (~30 m at equator) | Static (2020 baseline, EGM2008 geoid) | Authoritative surface elevation (`elevation_m`) and source for slope derivation |
| **Horn Topographic Slope** | AQUORA Mathematical Engine | 32-bit Float GeoTIFF, `data/processed/terrain/` | 30 m grid alignment | Derived from Copernicus DEM | Planar terrain gradient (`slope_deg`) derived via Horn (1981) 3x3 finite-difference algorithm |
| **HydroBASINS Asia (Lev01–Lev12)** | HydroSHEDS / WWF (Lehner & Grill 2013) | ESRI Shapefile, `data/raw/phase7/hydrography/hydrobasins/` | Seamless vector watersheds | Static hydrographic topology | Level 04 genuine polygon containment resolving regional macro-watersheds across India |
| **HydroRIVERS Asia v1.0** | HydroSHEDS / WWF | ESRI Shapefile, `data/raw/phase7/hydrography/hydrorivers/` | Vector lines (Reach network, Strahler order, $Q_{\text{avg}}$) | Static topological drainage | Geodetic distance to perennial drainage channels (`distance_to_river_m`, $ORD\_STRA \ge 4$) |
| **ESA WorldCover 2021 v200** | European Space Agency (ESA) | 10m GeoTIFF, `data/raw/phase7/landcover/` & `data/processed/landcover/` | 10 m (resampled to 30 m grid) | Annual baseline (2021) | Discrete 11-class surface cover (`landcover_class`) and local impervious built-up fraction |
| **NASA GPM IMERG Final V07B** | NASA GSFC / PMM Science Team | NetCDF4 / HDF5, `data/raw/phase7/rainfall/imerg/` | 0.1° (~10 km) | 13 Major Monsoon Flood Events (2006–2023) | Gauge-calibrated historical disaster benchmark scenarios and model validation |
| **CHIRPS Daily v2.0** | UCSB Climate Hazards Center | GeoTIFF (0.05°), `data/raw/phase7/rainfall/chirps/` | 0.05° (~5.5 km) | 35 Historical Storm Episodes (1981–2024) | Long-term 30-year climatological normals ($\mu, \sigma$) and historical rainfall validation |
| **JRC Global Surface Water** | European Commission JRC (Pekel et al.) | 30m GeoTIFF, `data/raw/phase7/water/jrc_gsw/` | 30 m raster | Multi-decadal (1984–2021) | Permanent water body anchor and water occurrence masking |
| **Global Flood Database (GFD)** | Cloud to Street / Dartmouth Flood Observatory | GeoTIFF / Vector, `data/raw/phase7/ground_truth/gfd/` | 250 m MODIS inundation | DFO 2935, 3372, 3382, 4499 | Ground-truth empirical inundation validation (DFO 2507 held in quarantine) |

---

## 3. Physical Feature Derivation Algorithms

### 3.1 Topographic Slope: Horn (1981) Algorithm
Topographic slope is derived directly from the unprojected 30m Copernicus DEM grid using Horn's weighted 3x3 finite-difference convolution kernels:
$$\frac{\partial z}{\partial x} = \frac{(z_{tr} + 2z_{r} + z_{br}) - (z_{tl} + 2z_{l} + z_{bl})}{8 \cdot \Delta x}$$
$$\frac{\partial z}{\partial y} = \frac{(z_{bl} + 2z_{b} + z_{br}) - (z_{tl} + 2z_{t} + z_{tr})}{8 \cdot \Delta y}$$
$$\text{Slope}_{\text{deg}} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) \cdot \frac{180}{\pi}$$
Where $\Delta y = \Delta \phi \cdot 111,320\,\text{m}$ and $\Delta x = \Delta \lambda \cdot 111,320\,\text{m} \cdot \cos(\phi_{\text{mean}})$. Output slope is clipped to the physical domain $[0.0^\circ, 90.0^\circ]$.

### 3.2 River Reach Distance: Padded Euclidean Distance Transform (EDT)
To prevent edge distortion when major river reaches run adjacent to domain boundaries, HydroRIVERS lines ($\text{Strahler Order} \ge 4$) are queried within a $0.25^\circ$ padded spatial envelope, rasterized onto a padded binary grid, and subjected to exact metric Euclidean Distance Transformation (`scipy.ndimage.distance_transform_edt` with anisotropic sampling $[dy, dx]$). The result is cropped to the exact domain extent, yielding sub-meter distance precision ($0.0\,\text{m}$ inside river channels, expanding continuously across valley floodplains).

### 3.3 Land Cover & Built-Up Fraction Resampling
ESA WorldCover 10m pixels are resampled to the 30m Copernicus grid using zero-order nearest-neighbor / modal assignment to preserve discrete integer class codes (e.g., `10`: Trees, `40`: Cropland, `50`: Built-up, `80`: Water). Built-up fraction is computed via uniform 2D filtering over the 10m binary built-up mask ($class == 50$) and resampled with bilinear interpolation into a smooth continuous metric $[0.0, 1.0]$.

### 3.4 Precipitation Accumulation & Climatological Anomaly $Z$-Score
Antecedent rainfall accumulations are derived from sliding 24-hour and 72-hour sums:
$$R_{24h}(t_0) = \int_{t_0 - 24h}^{t_0} P(t) \, dt, \quad R_{72h}(t_0) = \int_{t_0 - 72h}^{t_0} P(t) \, dt$$
The dimensionless climatological anomaly index is defined as:
$$Z_{72h}(x, y, d) = \frac{R_{72h}(x, y, d) - \mu_{72h}(x, y, d)}{\sigma_{72h}(x, y, d)}$$
Where $\mu_{72h}$ and $\sigma_{72h}$ represent the 30-year daily climatological normal mean and standard deviation for the respective calendar day. In hyper-arid or non-rainy conditions where $\sigma < 0.1\,\text{mm}$, $Z \equiv 0.0$ if $R = 0.0$.

---

## 4. Operational Ingestion vs. Benchmark Status across the 6 Priority Cities

| Priority City | Canonical River Basin | Terrain Ingestion Status | WorldCover Ingestion Status | HydroRIVERS Distance Grid | Operational Screening Status | Benchmark Screening Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Patna** | `BASIN-GANGA` | Verified (GLO-30 30m) | Verified (10m $\to$ 30m) | Verified ($0 - 15\,\text{km}$) | `INSUFFICIENT_INPUT_DATA` (Gate 3) | `READY` (Score: 0.0477) |
| **Guwahati** | `BASIN-BRAHMAPUTRA` | Verified (GLO-30 30m) | Verified (10m $\to$ 30m) | Verified ($0 - 14\,\text{km}$) | `INSUFFICIENT_INPUT_DATA` (Gate 3) | `READY` (Score: 0.0330) |
| **Mumbai** | `BASIN-MITHI` (Deep Zone) | Verified (GLO-30 30m) | Verified (10m $\to$ 30m) | Verified ($0 - 10\,\text{km}$) | `INSUFFICIENT_INPUT_DATA` (Gate 3) | `READY` (Score: 0.5304) |
| **Vijayawada** | `BASIN-KRISHNA` | Verified (GLO-30 30m) | Verified (10m $\to$ 30m) | Verified ($0 - 15\,\text{km}$) | `INSUFFICIENT_INPUT_DATA` (Gate 3) | `READY` (Score: 0.0423) |
| **Nagpur** | `BASIN-GODAVARI` | Verified (GLO-30 30m) | Verified (10m $\to$ 30m) | Verified ($1.2 - 24.4\,\text{km}$) | `INSUFFICIENT_INPUT_DATA` (Gate 3) | `READY` (Score: 0.0098) |
| **Ahmedabad** | `BASIN-SABARMATI` | Verified (GLO-30 30m) | Verified (10m $\to$ 30m) | Verified ($0 - 11.3\,\text{km}$) | `INSUFFICIENT_INPUT_DATA` (Gate 3) | `READY` (Score: 0.3047) |

---

## 5. Verification & Audit Trail

All raster transformations, geodetic reach computations, and data contract extractions have been validated through automated test suites:
- Backend test suites: **104 passed / 0 failed** across polygon containment, feature pipelines, national models, and regional intelligence.
- Frontend production build: **100% clean Vite build (`built in 10.77s`)** with strict TypeScript type-checking (`npx tsc --noEmit` passed).
- Playwright Browser QA: **0 defects / 0 failed network requests** across 4 responsive viewports.

