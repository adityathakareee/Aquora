# AQUORA — PHASE 7F.2: SCIENTIFIC IMPROVEMENT STRATEGY REPORT
### Physics-Guided Hydrological Feature Engineering, Cross-Basin Generalization & Operational Evaluation Architecture

**Document Version:** `1.0.0-phase7f2-strategy`  
**Phase:** Phase 7F.2 Scientific Improvement Planning & Feature Engineering Design  
**Task Type:** RESEARCH AND ARCHITECTURAL DESIGN ONLY (Zero code/data edits, zero retrained models, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine (`engines/flood/`)  
**Date:** 2026-10-31  

---

## 1. Executive Summary

Phase 7F.1 completed an exhaustive read-only audit of the AQUORA repository and the Phase 7E Kaggle Version 2 training artifacts ([artifacts/phase7e/AQUORA_Phase_7E_Final_Artifacts.zip](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/artifacts/phase7e/AQUORA_Phase_7E_Final_Artifacts.zip)). That audit revealed critical scientific deficiencies:
1. **The 98% False Alarm Collapse**: Both Random Forest and XGBoost classifiers, tuned on balanced 50/50 validation data, selected an extreme decision cutoff of $\tau = 0.01$, resulting in a **70% to 98% False Positive Rate (FPR)** and collapsing Precision to **5.8%** on the natural test landscape ([DFO 2507](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/gfd/DFO_2507), 196,505 rows, 5.82% flood prevalence).
2. **Physical Inverted Elevation Superiority**: An unsupervised, zero-parameter physical elevation ranking heuristic inside the test basin achieved **ROC-AUC of 0.8038**, soundly outperforming the trained cross-basin machine learning models (Random Forest ROC-AUC = **0.6215**; XGBoost ROC-AUC = **0.5899**).
3. **Core Root Cause — Absolute Elevation Shift**: Decision trees trained on raw absolute elevation meters (`elevation_m`) cannot transfer across river basins with differing baseline altitudes (coastal Bengal at 0–25m, Deccan upland at 500–1000m, and Gangetic Bihar at 38–75m).
4. **Feature Degradation & Missingness**: Only 7 active features were usable in Phase 7E. Sub-daily rainfall was 100% missing (`NaN`), `rainfall_anomaly_index` was perfectly collinear ($r = 1.0000$) with `rainfall_72h_mm`, `historical_flood_frequency` introduced future catalog leakage, and `distance_to_river_m` was derived from standing water rather than river channels.

This document establishes the **scientific improvement strategy for AQUORA Phase 8 and beyond**. It formulates the transition from unconstrained, purely statistical decision trees to a **Physics-Guided Machine Learning (PGML)** architecture that works alongside the Phase 6 deterministic hydrodynamic physics engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)).

---

## 2. Root-Cause Investigation of Documented Limitations

The empirical failures observed in Phase 7E stem from five interrelated methodological and physical flaws:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE 5 ROOT CAUSES OF ML MODEL COLLAPSE                          │
└────────────────────────────────────────────────────────────────────────────────────────┘
  1. ABSOLUTE ELEVATION SHIFT       ──► Trees learn regional altitudes, not flood physics.
  2. 50/50 THRESHOLD TRAP          ──► Tuning F1 on balanced data guarantees false alarm explosion.
  3. SATELLITE MISSING RAINFALL     ──► Daily CHIRPS leaves 1h/3h/6h rain as 100% explicit NaNs.
  4. COLLINEARITY & LEAKAGE ATTRITION ─► 4 of 11 features eliminated (leakage, NaN, collinearity).
  5. PROXIMITY SEMANTIC ERROR      ──► Distance to permanent water ≠ distance to river channel.
```

### A. Absolute Elevation Feature Limitations Across Distinct River Basins
In [scripts/prepare_phase7c_multievent_dataset.py:L338-L342](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_phase7c_multievent_dataset.py#L338-L342), terrain elevation is extracted as raw meters above mean sea level (`elevation_m`).
* **The Physical Reality**: Inundation risk is governed by **relative hydrologic relief** (elevation above the local drainage channel, $z - z_{\text{stream}}$), NOT absolute altitude above global sea level ($z$).
* **The Failure Mechanism**:
  * In the Lower Ganga delta (DFO 4499), floodplains sit at $2\text{ m} - 12\text{ m}$.
  * In the Upper Godavari plateau (DFO 2935), floodplains sit at $520\text{ m} - 580\text{ m}$.
  * In the North Bihar Kosi fan (DFO 2507), the entire landscape lies uniformly between $38\text{ m}$ and $75\text{ m}$.
  * Decision trees partition feature space with orthogonal hyperplanes (e.g., `elevation_m <= 15.4m`). When transferred to Bihar, the model evaluates pixels at $45\text{ m}$ elevation. Because $45\text{ m}$ is higher than the Bengal flood threshold ($15\text{ m}$) but lower than the Maharashtra flood threshold ($550\text{ m}$), the tree's split rules have zero physical meaning.
  * In contrast, the unsupervised inverted elevation ranking within DFO 2507 ($1 - \frac{z - z_{\min}}{z_{\max} - z_{\min}}$) evaluates relative local relief across the basin, achieving **ROC-AUC of 0.8038**.

### B. The Balanced Training vs. Naturally Imbalanced Evaluation Trap
In Phase 7C and 7D, the training and validation splits were artificially subsampled to an exact 50.0% flood / 50.0% dry balance ([manifest lines 51, 61](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7e_kaggle_package_manifest.yaml#L51)).
* **The Optimization Distortion**:
  When tuning the decision threshold $\tau$ on a 50/50 balanced validation set (DFO 3372, Assam) to maximize the $F_1$-score:
  $$F_1 = \frac{2 \cdot \text{TP}}{2 \cdot \text{TP} + \text{FP} + \text{FN}}$$
  Because false positives and false negatives carry identical numerical weight under equal class prevalence, lowering $\tau$ down to $0.01$ captures almost all true positives ($\text{Recall} = 99.15\%$) while the false positive penalty remains small relative to the 2,500 true dry points.
* **The Real-World Landscape Reality**:
  On the natural landscape of DFO 2507, there are **11,435 flood pixels (5.82%)** and **185,070 dry pixels (94.18%)**.
  When a model with an FPR of $70\%$ is applied to 185,070 dry pixels:
  $$\text{False Positives} = 0.7075 \times 185,070 \approx 130,944$$
  Even with $\text{Recall} = 70.72\%$ ($\text{TP} = 8,087$), the resulting Precision is:
  $$\text{Precision} = \frac{8,087}{8,087 + 130,944} = \mathbf{0.0582} \approx 5.82\%$$
  The model's precision completely collapses to the random baseline prevalence of the basin.

### C. Missing Sub-Daily Rainfall Observations
The Phase 7 pipeline sourced precipitation exclusively from daily **CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data)** at 0.05° resolution ([prepare_phase7c_multievent_dataset.py:L343-L355](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_phase7c_multievent_dataset.py#L343-L355)).
* Daily CHIRPS provides only 24-hour daily sums.
* Consequently, `rainfall_1h_mm`, `rainfall_3h_mm`, and `rainfall_6h_mm` were **100% unobserved (`NaN`)**.
* In Kaggle Version 2, these 3 features were completely dropped from model training.
* **The Physical Deficit**: Flood generation in monsoon India is driven by intense convective bursts (e.g., 80 mm in 2 hours), which overwhelm drainage conveyance long before 24-hour totals accumulate. Without sub-daily precipitation, models cannot distinguish flash cloudbursts from light, steady drizzles.

### D. Redundancy of `rainfall_anomaly_index`
In [prepare_phase7c_multievent_dataset.py:L352-L354](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_phase7c_multievent_dataset.py#L352-L354), `rainfall_anomaly_index` was calculated as:
$$\text{rain\_anomaly} = \frac{\text{rainfall\_72h\_mm} - \mu_{72h,\text{event}}}{\sigma_{72h,\text{event}}}$$
Because $\mu$ and $\sigma$ were scalar constants for each event footprint, `rainfall_anomaly_index` is an exact linear affine transformation ($r = 1.0000$) of `rainfall_72h_mm`. For decision trees, which are invariant to monotonic transformations, this feature added zero new split information.

### E. Misleading Semantics of `distance_to_river_m`
In [prepare_phase7c_multievent_dataset.py:L323-L336](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_phase7c_multievent_dataset.py#L323-L336), `dists_to_river_m` was computed by querying a KDTree against raster pixels where `jrc_perm == 1.0` (Global Surface Water permanent standing water).
* **Flaws**:
  1. Permanent water bodies include isolated farm ponds, oxbow lakes, and reservoirs, which are not river channels.
  2. Seasonal or braided alluvial channels that run dry during pre-monsoon overpasses are not classified as permanent water, meaning distance to the actual flood-carrying riverbed was completely ignored.
  3. It does not measure distance along the downhill flow path, but planar line-of-sight distance across ridges.

### F. Temporal Mismatch in ESA WorldCover 2021
ESA WorldCover provides a 10m global land cover baseline for calendar year 2021.
* The historical flood ground truth dates back to:
  * DFO 2507: June 2004 (**17-year temporal offset**)
  * DFO 2935: July 2006 (**15-year temporal offset**)
  * DFO 3372: August 2008 (**13-year temporal offset**)
  * DFO 4499: July 2017 (**4-year temporal offset**)
* Significant agricultural land conversion, urban sprawl, and river channel avulsions occurred across North Bihar and West Bengal between 2004 and 2021, introducing label-feature misalignment.

---

## 3. Candidate Feature Engineering Research & Evaluation

We evaluate five candidate feature classes across six objective scientific criteria: problem solved, required data, Indian applicability, resolution/limitations, leakage risk, and implementation verdict.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CANDIDATE FEATURE EVALUATION MATRIX                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Candidate A: HAND (Height Above Nearest Drainage)       ──► [ACCEPTED - TIER 1 PRIORITY]
  Candidate B: GPM IMERG (Sub-Daily Satellite Rain)       ──► [ACCEPTED - TIER 1 PRIORITY]
  Candidate C: HydroRIVERS (Vector River Network)         ──► [ACCEPTED - TIER 1 PRIORITY]
  Candidate D: Temporal Land-Cover (MODIS / ESA CCI)      ──► [ACCEPTED - TIER 2 HISTORICAL]
  Candidate E: Terrain Derivatives (TWI, Slope, Curvature)──► [ACCEPTED - TIER 1 PRIORITY]
```

### A. HAND — Height Above Nearest Drainage

| Evaluation Dimension | Scientific Specification |
| :--- | :--- |
| **Problem Solved** | **Eliminates the absolute elevation cross-basin domain shift.** Normalizes local topography into vertical height above the hydraulically connected stream channel along flow paths ($z - z_{\text{drainage}}$). A HAND of 1.5m represents identical flood inundation potential whether in Assam, Bihar, or Maharashtra. |
| **Data Required** | 30m Copernicus DEM GLO-30 (or MERIT-DEM 90m), D8 hydrologically conditioned flow direction grid, and HydroSHEDS flow accumulation channel threshold ($\ge 10\text{ km}^2$ contributing area). |
| **Applicability to India** | **Excellent.** 100% of the Indian landmass is covered by Copernicus DEM 30m, MERIT Hydro, and HydroSHEDS. Global 30m/90m HAND layers (Donchyts et al. 2016, Yamazaki et al. 2019) are open-access. |
| **Spatial & Temporal Resolution** | **Spatial:** 30m (Copernicus DEM) or 90m (MERIT Hydro). **Temporal:** Static geomorphology. |
| **Limitations** | In extremely flat alluvial fans (e.g. Kosi mega-fan), raw DEM sinks can cause flow direction looping. Requires hydro-enforced depression filling (e.g., Wang & Liu priority-flood algorithm). |
| **Leakage & Causality Risk** | **Zero leakage.** Static physical terrain variable derived from baseline topography. |
| **Scientific Verdict** | **ACCEPTED (TOP PRIORITY)**. This is the single most critical feature required to resolve cross-basin generalization failure. |

### B. GPM IMERG — Sub-Daily Satellite Precipitation Observations

| Evaluation Dimension | Scientific Specification |
| :--- | :--- |
| **Problem Solved** | **Resolves the 100% missing data void for sub-daily precipitation.** Captures intense convective storm bursts (`rainfall_1h_mm`, `3h_mm`, `6h_mm`), providing the temporal dynamic signal needed to predict flash flooding. |
| **Data Required** | NASA GPM (Global Precipitation Measurement) IMERG V06 / V07 product. Specifically: IMERG Final Run for historical training; IMERG Early / Late Run for operational preflight screening. |
| **Applicability to India** | **Excellent.** Complete coverage across India (quasi-global 60°N–60°S). IMERG explicitly integrates Indian Meteorological Department (IMD) rain gauges and dual-frequency radar calibration. |
| **Spatial & Temporal Resolution** | **Spatial:** 0.1° × 0.1° (~10 km × 10 km). **Temporal:** 30-minute intervals, June 2000 to present (covers all historical flood disasters from 2004 onward). |
| **Limitations** | Spatial grid (10 km) is coarser than 30m DEM; requires spatial bilinear or conservative area-weighted interpolation to sample at pixel centroids. High mountain terrain (Himalayas) can exhibit radar beam blockage. |
| **Leakage & Causality Risk** | **Strict causality required**: Accumulations must be computed strictly prior to the satellite overpass timestamp ($t \le t_{\text{obs}}$). Operational models must evaluate IMERG Early (4h latency) or Late (14h latency). |
| **Scientific Verdict** | **ACCEPTED (TOP PRIORITY)**. Eliminates explicit NaNs and provides authentic sub-daily convective rainfall. |

### C. HydroRIVERS — Vector River Network Geometry & Streamline Distance

| Evaluation Dimension | Scientific Specification |
| :--- | :--- |
| **Problem Solved** | **Replaces the flawed standing-water distance feature with true river centerline hydrography.** Distinguishes high-order trunk rivers (Ganga, Brahmaputra) from minor tributaries using Strahler stream order, upstream catchment area (`Upa_km2`), and naturalized discharge (`Dis_av_cms`). |
| **Data Required** | WWF / HydroSHEDS HydroRIVERS South Asia v1.0 vector polyline dataset. |
| **Applicability to India** | **Validated.** HydroRIVERS South Asia v1.0 covers the entire Indian subcontinent and was previously audited in Phase 2B ([docs/PHASE_2B_DATA_MANIFEST.csv:L6](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/PHASE_2B_DATA_MANIFEST.csv#L6)). |
| **Spatial & Temporal Resolution** | **Spatial:** Vector polylines derived from 90m SRTM/HydroSHEDS DEM. **Temporal:** Static hydrographic network. |
| **Limitations** | Ephemeral urban nullahs or highly altered irrigation canals (< 10 km² catchment) are omitted. Channel migration in active alluvial fans (e.g. Kosi) can cause minor positional offsets. |
| **Leakage & Causality Risk** | **Zero leakage.** Static pre-existing hydrography. |
| **Scientific Verdict** | **ACCEPTED (TOP PRIORITY)**. Directly fixes the semantic misinterpretation of `distance_to_river_m`. |

### D. Temporal Land-Cover Datasets — Historical Event Matching

| Evaluation Dimension | Scientific Specification |
| :--- | :--- |
| **Problem Solved** | **Addresses the 4-to-17 year temporal gap of ESA WorldCover 2021.** Provides contemporaneous land cover classifications for the exact year each historical disaster occurred. |
| **Data Required** | **MODIS MCD12Q1** (Annual, 2001–present, 500m resolution, IGBP 17-class) or **ESA Climate Change Initiative (CCI) Land Cover** (Annual, 1992–2020, 300m resolution). |
| **Applicability to India** | **Excellent.** Continuous annual historical records spanning 2004, 2006, 2008, and 2017 across India. |
| **Spatial & Temporal Resolution** | **Spatial:** 300m (ESA CCI) or 500m (MODIS MCD12Q1). **Temporal:** Annual time steps. |
| **Limitations** | Coarser spatial resolution (300m–500m) than 10m ESA WorldCover. However, for 250m GFD MODIS flood pixels, 300m resolution is well-matched to sensor footprint geometry. |
| **Leakage & Causality Risk** | **Zero leakage** if the annual land cover layer from the preceding calendar year ($t = \text{event\_year} - 1$) is ingested. |
| **Scientific Verdict** | **ACCEPTED (TIER 2 HISTORICAL)**. Ingest annual ESA CCI / MODIS land cover for historical event training; maintain ESA WorldCover 2021 for operational contemporary screening. |

### E. Geomorphic Terrain Derivatives — TWI, Slope, Curvature & Catchment Area

| Evaluation Dimension | Scientific Specification |
| :--- | :--- |
| **Problem Solved** | **Provides scale-invariant physical runoff accumulation metrics.** Raw slope only captures local gravity acceleration. The **Topographic Wetness Index (TWI)**:  $$\text{TWI} = \ln\left(\frac{a}{\tan \beta + 10^{-5}}\right)$$  quantifies the tendency of an upslope area $a$ to accumulate surface runoff relative to local drainage capacity $\tan \beta$. Planform and profile curvature capture convergent hollows vs. divergent ridges. |
| **Data Required** | Copernicus DEM GLO-30 30m tiles (already present in repository). D8/D-infinity flow accumulation algorithms. |
| **Applicability to India** | **Validated.** Fully supported by existing Copernicus DEM tiles and the Phase 6 terrain engine ([engines/flood/surface_routing.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/surface_routing.py)). |
| **Spatial & Temporal Resolution** | **Spatial:** 30m raster grid. **Temporal:** Static geomorphology. |
| **Limitations** | Requires robust sink filling in flat Gangetic floodplains to avoid artificially truncated flow accumulation pathways. |
| **Leakage & Causality Risk** | **Zero leakage.** Derived strictly from baseline digital topography. |
| **Scientific Verdict** | **ACCEPTED (TOP PRIORITY)**. Standard hydrological indicators that transfer across basins. |

---

## 4. Recommended Feature Engineering Strategy (Phase 8 Specification)

Based on our empirical and physical evaluation, we specify a **12-Predictor National Hydrological Feature Schema** for the next development phase:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   RECOMMENDED PHASE 8 NATIONAL PREDICTOR SCHEMA                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
  1. hand_m                    (Height Above Nearest Drainage - Copernicus DEM 30m)
  2. twi_score                 (Topographic Wetness Index - ln(a / tan(beta)))
  3. slope_deg                 (30m Copernicus DEM Horn gradient)
  4. plan_curvature_m_inv      (Planform curvature - flow convergence)
  5. distance_to_hydrorivers_m (Euclidean distance to HydroRIVERS vector network)
  6. strahler_stream_order     (Stream order of nearest HydroRIVERS channel, 1-10)
  7. rainfall_1h_mm            (GPM IMERG Early/Final 1h precipitation)
  8. rainfall_3h_mm            (GPM IMERG Early/Final 3h precipitation)
  9. rainfall_6h_mm            (GPM IMERG Early/Final 6h precipitation)
 10. rainfall_24h_mm           (GPM IMERG / CHIRPS daily precipitation)
 11. rainfall_72h_mm           (GPM IMERG / CHIRPS 3-day antecedent precipitation)
 12. landcover_class           (ESA CCI historical / ESA WorldCover operational)

  EXCLUDED FEATURES (LEAKAGE / REDUNDANCY):
  - historical_flood_frequency ──► EXCLUDED (Future catalog leakage, zero spatial variance)
  - rainfall_anomaly_index     ──► EXCLUDED (Collinear affine clone of rainfall_72h_mm)
  - raw elevation_m            ──► REPLACED BY hand_m (Non-transferable across basins)
```

---

## 5. Geographic Generalization & Validation Methodology

To prevent overfitting to individual regional altitudes, the validation methodology must separate data geographically, physiographically, and temporally.

```
                    INDIAN PHYSIOGRAPHIC MACRO-ZONES
 ┌────────────────────────────────────────────────────────────────────┐
 │  ZONE 1: Gangetic Alluvial Plains (Bihar, Bengal, UP)              │
 │  ZONE 2: Brahmaputra Valley (Assam, Eastern Sub-Himalaya)          │
 │  ZONE 3: Peninsular Deccan Plateau (Maharashtra, Telangana, MP)    │
 │  ZONE 4: Coastal Deltaic & Littoral Plains (Mahanadi, Krishna)     │
 └────────────────────────────────────────────────────────────────────┘
```

### A. Leave-One-Physiographic-Zone-Out (LOPZO) Cross-Validation
Rather than randomly holding out arbitrary events, cross-validation must evaluate transferability across distinct geomorphic regimes:
1. **Fold 1 (Plateau Transfer)**: Train on Gangetic Plain + Brahmaputra; Validate on Peninsular Deccan Plateau (DFO 2935).
2. **Fold 2 (Valley Transfer)**: Train on Gangetic Plain + Deccan Plateau; Validate on Brahmaputra Valley (DFO 3372).
3. **Fold 3 (Delta Transfer)**: Train on Deccan Plateau + Brahmaputra; Validate on Lower Bengal Delta (DFO 4499).

### B. Anti-Leakage Rules for Event-Based Construction
1. **Zero Spatial Autocorrelation**: Pixels from the same satellite overpass or continuous catchment must NEVER be split between training and validation. Spatial cross-validation must be partitioned by HydroBASINS Level 5/6 polygons.
2. **Strict Temporal Causality**: Antecedent precipitation must be computed strictly over timestamps $t \le t_{\text{obs}}$. No post-event catalog statistics may be used as static predictors.
3. **Natural Prevalence Preserved in Validation**:
   - Training sets may utilize class-weighted loss functions or moderate downsampling ($1:2$ or $1:3$ ratio) for computational efficiency.
   - **Validation and test sets must retain their 100% natural unskewed class distribution** (typically 3% to 8% flood prevalence). Threshold tuning must NEVER occur on artificially balanced 50/50 data.

### C. Mandatory Status of DFO 2507: `ALREADY_INSPECTED_HOLDOUT`
- DFO 2507 (North Bihar / Kosi Basin, June 2004) has been thoroughly audited in Phase 7D, 7E, and 7F.1.
- **It is an already-inspected benchmark dataset.**
- **Governance Mandate**: DFO 2507 must remain strictly frozen. It must NEVER be used to choose features, tune hyperparameters, or select decision thresholds.
- When Phase 8 models are finalized, DFO 2507 will be evaluated once as a comparative historical benchmark, clearly disclosed as an inspected holdout.
- For true blind operational evaluation, a newly acquired uninspected event (e.g. 2019 Mahanadi or 2020 Godavari flood) must be introduced.

---

## 6. Evaluation and Calibration Methodology

### A. The Flaw of F1 Tuning on Balanced Validation Sets
The mathematical proof below demonstrates why optimizing F1 on balanced validation data causes operational collapse:

Let positive prevalence be $p = P(Y=1)$. Precision is given by Bayes' Theorem:
$$\text{Precision} = \frac{p \cdot \text{TPR}}{p \cdot \text{TPR} + (1 - p) \cdot \text{FPR}}$$
* Under **balanced validation** ($p = 0.50$):
  $$\text{Precision}_{\text{bal}} = \frac{\text{TPR}}{\text{TPR} + \text{FPR}}$$
  If a threshold yields $\text{TPR} = 0.99$ and $\text{FPR} = 0.70$, $\text{Precision}_{\text{bal}} = \frac{0.99}{1.69} \approx \mathbf{58.6\%}$.
  Validation $F_1 = \frac{2 \times 0.586 \times 0.99}{0.586 + 0.99} \approx \mathbf{0.736}$ (appears strong!).
* Under **natural landscape** ($p = 0.0582$):
  $$\text{Precision}_{\text{nat}} = \frac{0.0582 \times 0.99}{(0.0582 \times 0.99) + (0.9418 \times 0.70)} = \frac{0.0576}{0.0576 + 0.6593} = \frac{0.0576}{0.7169} \approx \mathbf{8.03\%}$$
  The identical model and threshold produce **92% false alarms** in real operational deployment!

### B. Recommended Operational Metric Suite
1. **Precision-Recall AUC (PR-AUC)**: Primary threshold-independent metric for imbalanced domains. The random baseline is $p$ (e.g., $0.058$), not $0.50$.
2. **Prevalence-Aware Cost Utility ($U_{\text{cost}}$)**:
   Define an explicit operational loss function where a false alarm carries cost $C_{\text{FP}}$ and a missed flood carries cost $C_{\text{FN}}$:
   $$\mathcal{L} = C_{\text{FN}} \cdot \text{FN} + C_{\text{FP}} \cdot \text{FP}$$
   Thresholds must be selected to minimize $\mathcal{L}$ on a **naturally imbalanced validation fold**.
3. **Precision at Fixed Recall (e.g., Precision @ Recall = 80%)**: Evaluates false alarm volume at an operationally acceptable flood detection rate.
4. **Probability Calibration Diagnostics**:
   - **Brier Score**: Mean squared error of calibrated posterior probabilities.
   - **Reliability Diagrams (Calibration Curves)**: Bin predicted probabilities into deciles and verify that points predicted with $P=0.20$ experience flooding exactly 20% of the time.
   - **Post-Hoc Calibration**: Apply **Platt Scaling** (logistic sigmoid) or **Isotonic Regression** fit strictly on an independent, naturally imbalanced validation split.

---

## 7. Proposed Future Architecture: Physics-Guided Machine Learning (PGML)

Machine learning in AQUORA must work **alongside, rather than replace**, the Phase 6 deterministic physics engine.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               AQUORA 3-TIER OPERATIONAL INTEGRATION ARCHITECTURE                       │
└────────────────────────────────────────────────────────────────────────────────────────┘

 [TIER 1: NATIONAL SCREENING]
 ┌──────────────────────────────────────────────────────────────────────────────────────┐
 │ Atmospheric Forcing (GPM IMERG) + Terrain (Copernicus DEM / HAND / HydroRIVERS)      │
 │                                       │                                              │
 │                                       ▼                                              │
 │               Physics-Guided ML National Screening Model                             │
 │               (Calibrated Posterior Flood Probability: P(flood | x))                 │
 └───────────────────────────────────┬──────────────────────────────────────────────────┘
                                     │ Regional Alert Screening (> 10 km²)
                                     ▼
 [TIER 2: REGIONAL BASIN CORRIDORS]
 ┌──────────────────────────────────────────────────────────────────────────────────────┐
 │ HydroBASINS Catchment Water Balance & CWC River Stage Gauge Cross-Referencing        │
 └───────────────────────────────────┬──────────────────────────────────────────────────┘
                                     │ High-Risk Catchment Trigger
                                     ▼
 [TIER 3: DEEP INTELLIGENCE ZONE - MUMBAI/MITHI]
 ┌──────────────────────────────────────────────────────────────────────────────────────┐
 │ PHASE 6 DETERMINISTIC HYDRODYNAMIC PHYSICS ENGINE (engines/flood/)                    │
 │ • 2D Surface Routing & Shallow Water Overland Solver (solver.py)                     │
 │ • High-Resolution Terrain Sink Storage (surface_storage.py)                          │
 │ • Stormwater Drainage Network Coupling & Throttle (drainage_coupling.py)             │
 │ • Conservation of Mass Balance Diagnostics (diagnostics.py)                          │
 │                                       │                                              │
 │                                       ▼                                              │
 │ Authoritative Physical Depths (m), Flow Velocities (m/s) & Evacuation Route Routing   │
 └──────────────────────────────────────────────────────────────────────────────────────┘
```

### End-to-End Workflow & Governance Gates

```
  Step 1: Data Acquisition          ──► Sentinel-1 SAR + GPM IMERG + Copernicus DEM + HydroRIVERS
  Step 2: Ground-Truth Gating       ──► GFD v1.4 quality gate (clear_perc >= 0.70; exclude perm water)
  Step 3: Feature Engineering       ──► Compute HAND, TWI, stream order, sub-daily IMERG sums
  Step 4: LOPZO Dataset Assembly    ──► Leave-One-Physiographic-Zone-Out holdout partitioning
  Step 5: Physics-Guided ML Fit     ──► Tree ensembles fit with monotonicity constraints on HAND
  Step 6: Natural Split Calibration ──► Platt scaling / Isotonic regression on unskewed validation
  Step 7: Independent Evaluation    ──► PR-AUC, cost-utility curve, spatial error profiling
  Step 8: Governance Gate Review    ──► Requires FPR <= 0.05 and Precision >= 0.40 before deployment
```

### Architectural Safeguards Preserved
1. **Deterministic Authority**: The Phase 6 physics engine remains the sole authority for physical flood depths, velocities, and evacuation routing.
2. **Deep Zone Invariant**: Mumbai/Mithi (`deep_mumbai_mithi`) remains the ONLY active Deep Zone. National ML outputs must NEVER be passed as simulated depths.
3. **No Synthetic Labels**: All supervised targets must originate from verified satellite ground truth.
4. **Safety Disclaimer**: All ML outputs remain tagged: `PROTOTYPE_ONLY`, `NOT_CALIBRATED`, `NOT_FOR_PUBLIC_ALERTS`.

---

## 8. Data Acquisition Priorities for Phase 8

| Priority Level | Dataset Candidate | Product / Source | Purpose | Estimated Size / Acquisition Path |
| :---: | :--- | :--- | :--- | :--- |
| **PRIORITY 1** | **HAND (Height Above Nearest Drainage)** | MERIT-Hydro / Derived Copernicus 30m | Replaces absolute elevation; provides cross-basin transferable relief | ~2.5 GB for target Indian basins (OpenAccess HTTPS) |
| **PRIORITY 1** | **GPM IMERG V07** | NASA GES DISC (30-min, 0.1°) | Populates sub-daily rainfall (`1h`, `3h`, `6h`), eliminating NaNs | NASA Earthdata API (Open access, script-based download) |
| **PRIORITY 1** | **HydroRIVERS South Asia v1.0** | WWF HydroSHEDS | Replaces permanent standing water distance with stream centerlines | ~250 MB Shapefile/GeoPackage (Already cataloged in Phase 2B) |
| **PRIORITY 2** | **New GFD Indian Flood Events** | Global Flood Database v1.4 | Expands training events to Peninsular/Central basins (Godavari, Mahanadi) | ~500 MB GeoTIFF tiles from Cloud-to-Street / GFD portal |
| **PRIORITY 2** | **ESA CCI Land Cover** | ESA Climate Change Initiative (300m) | Provides contemporaneous land cover for historical events (2004–2017) | ~800 MB GeoTIFF (Open access via ESA CCI portal) |

---

## 9. Risks and Unresolved Scientific Questions

1. **Hydrological Flatness in Alluvial Plains**:
   In extremely flat low-relief floodplains (like North Bihar's Kosi mega-fan, slope $< 0.1^\circ$), flow accumulation and HAND derivations are sensitive to DEM elevation noise ($\pm 1\text{m}$). Stream burning using HydroRIVERS polylines will be necessary to prevent artificial flow looping.
2. **Optical Sensor Cloud-Penetration Void**:
   MODIS optical ground-truth cannot observe the peak flood stage beneath deep monsoonal storm clouds. Integrating **Sentinel-1 SAR backscatter ground truth** (as demonstrated in Phase 6B) will be essential for modern events (2015–present).
3. **Precipitation Spatial Mismatch**:
   GPM IMERG at 0.1° (~10 km) is coarser than 30m terrain features. Highly localized cloudbursts over urban terrain may be smoothed over the 10 km grid cell.
4. **Embankment and Levee Breaches**:
   Catastrophic flood events in Bihar (such as the 2008 Kosi embankment breach) are caused by human infrastructure failures rather than simple natural terrain runoff. Topographic models without hydraulic structural data cannot predict levee failures.

---

## 10. Explicit GO / NO-GO Recommendations

$$\mathbf{OPERATIONAL\ AUTOMATED\ WARNINGS:\ CRITICAL\ NO-GO}$$
$$\mathbf{PHASE\ 6\ SIMULATOR\ CODE\ CHANGES:\ STRICT\ NO-GO}$$
$$\mathbf{PHASE\ 8\ FEATURE\ PROTOTYPING:\ FUTURE\ PROPOSAL\ ONLY\ (NOT\ APPROVED)}$$

### Concrete Governance Decisions:
1. **Civil Defense Alerting: CRITICAL NO-GO**  
   Current ML models must NEVER be connected to alerting or public safety infrastructure.
2. **Phase 6 Physics Engine Modification: STRICT NO-GO**  
   Do not modify `engines/flood/` or replace the deterministic mass-balance solver with statistical ML models.
3. **Phase 8 Feature Prototyping: FUTURE PROPOSAL ONLY**  
   The proposed acquisition and feature prototyping for Phase 8 represents a future scientific roadmap subject to peer review. No implementation work is authorized or started.

---

## 11. Scientific Review Amendments — Phase 7F.2

This section records formal scientific review qualifications adopted following the Phase 7F.2 evaluation:

### 1. HAND Methodological Dependencies and Leakage Constraints
Height Above Nearest Drainage (HAND) is a strong candidate for resolving cross-basin domain shift, but its validity depends strictly on DEM conditioning, drainage-network quality, spatial resolution, and hydrological connectivity. It must **not be described as automatically leakage-free**:
- **DEM Conditioning**: Quality of sink filling, breach routing, and stream burning to prevent artificial drainage pooling across flat alluvial plains.
- **Drainage-Network Quality & Thresholding**: Channel initiation area threshold (e.g., 10 km² vs 1 km²) dictates stream density and HAND base level.
- **Spatial Resolution**: DEM spatial resolution (30m Copernicus vs 90m MERIT) and channel discretization determine whether local micro-topographic barriers are resolved.
- **Hydrological Connectivity**: HAND assumes static gravity drainage to the nearest stream; it does not capture backwater effects, tidal surges, or structural levee impoundments.
- **Anti-Leakage Qualification**: If drainage networks or flow directions incorporate post-event water extent, or if conditioning parameters are tuned against flood labels, feature leakage can occur.

### 2. GPM IMERG Spatial Resolution Mismatch & Data Stream Distinction
- **Resolution Mismatch**: GPM IMERG's approximately 0.1-degree (~10 km × 10 km) rainfall resolution is substantially coarser than the 30m flood-label grid (>300 times coarser in linear dimension, ~100,000 times coarser in area). Sub-grid convective rainfall spatial variability (cloudburst cells < 3 km) remains unresolved at 10 km scales.
- **Operational vs. Retrospective Data Distinction**:
  * **IMERG Final Run**: Retrospective research product incorporating monthly GPCC rain gauge adjustments with a 3.5-month latency. Suitable only for retrospective benchmark studies.
  * **IMERG Early Run** (4-hour latency) / **Late Run** (14-hour latency): Forward operational products without monthly ground gauge calibration. Model architectures must be evaluated against Early/Late Run characteristics if intended for operational screening workflows.

### 3. HydroRIVERS Verification & Scale Boundaries
- HydroRIVERS coverage must be verified independently for each selected catchment before ingestion.
- **Scale Limitations**: Derived from 90m SRTM/HydroSHEDS DEM, HydroRIVERS may omit small streams (< 10 km² catchment), ephemeral gullies, agricultural drainage channels, and urban drainage channels. In deltaic plains, distributary bifurcation networks are often generalized.

### 4. Leave-One-Physiographic-Zone-Out (LOPZO) Validation Requirements
- Leave-One-Physiographic-Zone-Out validation requires sufficient independent events in every geographic regime before adopting this design.
- **Minimum Requirements for Adoption**:
  * Minimum of **3 to 5 independent disaster events** per physiographic zone across multiple monsoon seasons.
  * Minimum of **10 to 15 distinct catchments** across India.
  * Evaluating LOPZO on single-event zones (e.g., only one event in Maharashtra or Assam) conflates regional physiography with event-specific meteorological anomalies.

### 5. Precision vs. Prevalence & Ranking vs. Threshold-Based Operational Usefulness
- **Threshold-Level Precision Advantage**: Phase 7E precision approximately matching test prevalence (~5.82% at threshold $\tau = 0.01$) indicates **poor threshold-level precision advantage** (the decision cutoff provides zero operational discrimination advantage, behaving no better than assigning the positive class randomly based on the prior).
- **Ranking vs. Operational Usefulness**: However, PR-AUC (0.1906 for RF, 0.1890 for XGBoost) remains substantially above the 0.0582 prevalence baseline, confirming retained ordinal ranking capacity across the full curve. Ranking performance must be clearly distinguished from threshold-based operational usefulness.

### 6. Probability Calibration Governance
- Probability calibration must use an independent, naturally imbalanced calibration/validation design (e.g., Platt scaling or Isotonic regression).
- **DFO 2507 Quarantine**: Calibration methods must **not access DFO 2507** for fitting, calibration parameter estimation, or model selection. DFO 2507 remains quarantined strictly as an unadjusted historical benchmark.

### 7. Conceptual Status of Physics-Guided ML (PGML)
- The proposed Physics-Guided ML architecture remains **strictly conceptual**.
- Phase 6 deterministic hydrodynamic physics engine (`engines/flood/`) remains the **primary physical authority** for flood depths, flow velocities, and critical access routing.
- No ML-to-Phase-6 coupling, solver overrides, or automated public warnings are authorized.

### 8. Phase 8 Status: Future Proposal Only
- Phase 8 feature prototyping is a **future proposal, not an approved implementation task**.
- No implementation work, code modifications, dataset downloads, or model training tasks are authorized or performed.

