# AQUORA Phase 7F Stage 4.1: Model Robustness and Scientific Review Report

**Document ID:** `PHASE_7F_STAGE4_1_ROBUSTNESS_REPORT`  
**Phase:** 7F — Model Audit and Scientific Improvement Planning  
**Subphase:** Stage 4.1 — Model Robustness, Feature Ablation, and Scientific Integrity Audit  
**Target Event:** DFO 3382 — Mahanadi River Basin / Odisha Delta, India (September 2008)  
**Administrative Disaster Record:** IMD/Disaster Inventory `UEI-IMD-FL-2008-0095`  
**Timestamp:** 2026-11-02T12:35:00Z  
**Primary Hydrodynamic Authority:** [engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py) (Phase 6 2D Hydrodynamic Physics Engine)  
**Holdout Quarantine Status:** DFO 2507 Quarantined (`ALREADY_INSPECTED_HOLDOUT_ZERO_ACCESS`)  
**Stage Decision:** **`ROBUSTNESS_AUDIT_COMPLETE`**  
**Scientific Governance Status:** **`PROTOTYPE_ONLY / NOT_CALIBRATED / NOT_FOR_PUBLIC_ALERTS`**

---

## 1. Executive Summary & Mandatory Safeguards

Under strict AQUORA project governance boundaries, **Phase 7F Stage 4.1** has executed a comprehensive scientific robustness audit of the regional machine learning exploration conducted in Stage 4 for the DFO 3382 Mahanadi event.

This audit critically examines the physical and statistical foundations of the experimental models, resolves key questions regarding feature interpretations and label coupling, evaluates spatial autocorrelation across contiguous hydrologic sub-basins, and provides independent recalculation and verification of all performance metrics.

### Mandatory Safeguards Verification:
1. **DFO 2507 Strictly Quarantined:** Zero access, reading, or sampling of `DFO_2507` ground truth.
2. **Phase 7E Assets Preserved:** Phase 7E artifacts, schemas, Kaggle packages, and evaluation metrics remain completely unaltered.
3. **Zero Rainfall Fabrication:** No precipitation data was manufactured, filled, or cross-imputed; rainfall features remain 100% NaN/excluded.
4. **Phase 6 Physics Supremacy:** The Phase 6 2D shallow water hydrodynamic solver ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py)) remains the sole operational flood authority.
5. **Stage 3 & Stage 4 Preservation:** The native-resolution Stage 3 dataset and Stage 4 baseline experiment outputs are preserved as the original benchmark.
6. **No Git Commits or Pushes:** Repository working tree changes remain uncommitted and unpushed.
7. **Regression Test Integrity:** The consolidated Phase 7 regression test suite expanded to 58 tests with a **100% pass rate (58/58 passed in 26.36s)**.

---

## 2. Land/Water Dry Fraction Ablation & Label Quality Coupling

In the Stage 4 baseline experiment, XGBoost assigned **21.08% feature importance** to `land_water_dry_fraction` (the second highest predictor after elevation). A controlled ablation was executed using identical spatial partitions (Train: 72,140; Val: 53,134; Test: 48,676), identical model hyperparameters (depth=5, lr=0.05, scale_pos_weight=balanced, random_state=42), and frozen validation-selected thresholds.

### Controlled Ablation Comparison:

| Metric | Full 13-Feature XGBoost | Without `land_water_dry_fraction` | Delta ($\Delta$) | Relative Change (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Feature Count** | 13 | 12 | -1 | -7.7% |
| **Validation Threshold** | **0.9500** | **0.9200** | -0.0300 | - |
| **Test ROC-AUC** | **0.8119** | **0.6423** | **-0.1696** | **-20.89%** |
| **Test PR-AUC** | **0.2514** | **0.0665** | **-0.1849** | **-73.55%** |
| **Test Prevalence Baseline** | 0.0490 | 0.0490 | 0.0000 | - |
| **PR-AUC / Prevalence Ratio**| **5.13x** | **1.36x** | **-3.77x** | **-73.49%** |
| **Precision** | **0.3815** | **0.0713** | **-0.3102** | **-81.31%** |
| **Recall** | **0.2336** | **0.1057** | **-0.1279** | **-54.75%** |
| **F1 Score** | **0.2898** | **0.0852** | **-0.2046** | **-70.60%** |
| **True Positives (TP)** | 557 | 252 | -305 | -54.76% |
| **False Positives (FP)** | **903** | **3,280** | **+2,377** | **+263.23%** |
| **False Negatives (FN)** | 1,827 | 2,132 | +305 | +16.69% |
| **True Negatives (TN)** | 45,389 | 43,012 | -2,377 | -5.24% |
| **False Positive Rate (FPR)** | **0.0195** | **0.0709** | **+0.0514** | **+263.59%** |

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│               IMPACT OF ABLATING `land_water_dry_fraction` ON TEST PARTITION                           │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  PR-AUC:       [█████████████████████████] 0.2514  (Full 13 Features)                                  │
│                [███████                  ] 0.0665  (Without Dry Fraction, -73.6%)                     │
│                [█████                    ] 0.0490  (Constant Prevalence Baseline)                     │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  False Alarms: [████                     ] 903 FP  (Full 13 Features)                                  │
│                [████████████████         ] 3,280 FP (Without Dry Fraction, +263.2%)                   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Investigation of Label Quality / Eligibility Coupling:
Why does removing `land_water_dry_fraction` collapse PR-AUC by 73.55% and increase false positives by 263%?

1. **Stage 3 Quality Gate Definition:** In Stage 3 dataset assembly, cells where Copernicus Water Bodies Mask (WBM) indicated $\ge 30\%$ permanent water (`dry_fraction < 0.70`) were categorized as `MIXED_WATER_MARGIN`.
2. **Extreme Flood Concentration:** Across the 173,950 Mahanadi Basin cells, `MIXED_WATER_MARGIN` constitutes only **4.24% of the geographic area** (7,378 cells). Yet **66.84% of all verified flood labels** (2,818 of 4,216 cells) fall inside this narrow margin!
3. **Empirical Flood Rate Disparity:**
   - In `MIXED_WATER_MARGIN` cells (`dry_fraction < 0.70`), the empirical flood label rate is **38.19%** (2,818 / 7,378).
   - In purely terrestrial cells (`dry_fraction >= 0.70`), the empirical flood label rate is only **0.84%** (1,398 / 166,572).
4. **Performance on High-Quality Terrestrial Cells Only:**
   When the models are evaluated strictly on the `HIGH_QUALITY` test subset (excluding riparian margin cells, $N = 41,434$, flood cells = 650, prevalence = 1.57%):
   - **Full XGBoost PR-AUC collapses from 0.2514 to 0.0192** (relative to 0.0157 prevalence).
   - **Without Dry Fraction PR-AUC is 0.0168** (ROC-AUC = 0.5679).
   - **XGBoost F1 drops to 0.0000** at the validation threshold.

> [!IMPORTANT]
> **Scientific Finding:** `land_water_dry_fraction` does not act merely as a neutral static topographic predictor. Instead, it heavily encodes the optical label eligibility and riparian boundary process. In 250m optical remote sensing (DFO/MODIS), flood detections heavily cluster along permanent water margins where sub-pixel water lowers surface reflectance. When evaluated on truly terrestrial ground away from permanent water boundaries, static terrain predictors exhibit virtually zero autonomous ranking skill.

---

## 3. Aspect Feature Mathematical & Physical Review

The mathematical definitions and Python/Numba aggregation routines for all four aspect features in [scripts/prepare_phase7f_dfo3382_dataset.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_phase7f_dfo3382_dataset.py#L85-L144) were audited.

### Formula Review & Interpretation Corrections:

1. **`aspect_mean_cos`:**
   $$\text{aspect\_mean\_cos} = \frac{1}{N_{\text{sloped}}} \sum_{k=1}^{N_{\text{sloped}}} \cos\left(\theta_k \cdot \frac{\pi}{180^\circ}\right)$$
   - **Mathematical Nature:** Mean cosine component of the 30m terrain aspect angles $\theta_k \in [0^\circ, 360^\circ)$ where $0^\circ = \text{North}$, $90^\circ = \text{East}$, $180^\circ = \text{South}$, $270^\circ = \text{West}$.
   - **True Physical Meaning:** Standard geographic **Northness** index in $[-1.0, +1.0]$. A value of $+1.0$ indicates a purely North-facing slope; $-1.0$ indicates a purely South-facing slope; $0.0$ indicates East-West or balanced slope facets.
   - **Correction of Unsupported Claim:** The Stage 4 report claimed this feature represents *"hillslope orientation relative to monsoonal atmospheric inflow"*. **This claim is REFUTED.** No atmospheric wind vector, cyclone track projection, or meteorological transformation was applied. It is purely the geometric North-South cosine projection.

2. **`aspect_mean_sin`:**
   $$\text{aspect\_mean\_sin} = \frac{1}{N_{\text{sloped}}} \sum_{k=1}^{N_{\text{sloped}}} \sin\left(\theta_k \cdot \frac{\pi}{180^\circ}\right)$$
   - **Mathematical Nature:** Mean sine component of the terrain aspect angles.
   - **True Physical Meaning:** Standard geographic **Eastness** index in $[-1.0, +1.0]$. $+1.0$ indicates East-facing; $-1.0$ indicates West-facing.
   - **Correction of Unsupported Claim:** Has no documented orographic precipitation transfer function; it is purely geometric Eastness.

3. **`aspect_circular_var`:**
   $$\bar{R} = \sqrt{(\text{aspect\_mean\_cos})^2 + (\text{aspect\_mean\_sin})^2}, \quad S_0 = 1.0 - \bar{R}$$
   - **Mathematical Nature:** **Mardia's Circular Variance** ($S_0 \in [0.0, 1.0]$) of sub-pixel slope aspects.
   - **True Physical Meaning:** Measures the **directional dispersion (angular heterogeneity)** of 30m slope facets within the ~250m cell. $S_0 = 0.0$ denotes perfectly planar / collinear facets facing the identical direction; $S_0 = 1.0$ denotes isotropic or opposing slope orientations.
   - **Correction of Unsupported Claim:** The Stage 4 report claimed circular variance indicates *"valleys or chaotic flat plains"*. **This claim is REFUTED.** Directional dispersion measures angular scatter, not topographic cross-sectional profile. A convergent valley, a divergent conical peak, an undulating dune field, and a flat terrace all exhibit high circular variance. It cannot differentiate valleys from ridges without curvature.

4. **`aspect_flat_fraction`:**
   $$\text{aspect\_flat\_fraction} = \frac{N_{\text{flat}}}{N_{\text{total}}}, \quad \text{where } \text{slope} < 0.001^\circ \implies \text{aspect} = -1$$
   - **Mathematical Nature:** Proportion of sub-cells classified as flat according to Horn (1981).
   - **True Physical Meaning:** Quantifies completely planar alluvial surfaces ($[0.0, 1.0]$). Valid physical interpretation, though strongly collinear with `slope_mean_deg`.

### Controlled Aspect Feature Ablation:
To evaluate whether aspect features provide essential predictive value, an ablation model removing all 4 aspect features was trained under identical conditions:

| Metric | Full 13-Feature XGBoost | Without Aspect Features (9 Features) | Delta ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Validation Threshold** | 0.9500 | 0.9500 | 0.0000 |
| **Test ROC-AUC** | **0.8119** | **0.7960** | -0.0159 (-1.9%) |
| **Test PR-AUC** | **0.2514** | **0.2392** | -0.0122 (-4.8%) |
| **Test Precision** | 0.3815 | 0.3617 | -0.0198 |
| **Test Recall** | 0.2336 | 0.2475 | +0.0139 |
| **Test F1 Score** | **0.2898** | **0.2939** | **+0.0041 (+1.4%)** |
| **False Positives (FP)** | 903 | 1,041 | +138 |
| **False Negatives (FN)** | 1,827 | 1,794 | -33 |

> [!TIP]
> **Audit Conclusion:** Removing all 4 aspect features leaves test PR-AUC virtually unchanged (0.2392 vs 0.2514) while test $F_1$ score slightly improves from 0.2898 to 0.2939. Because aspect features lack defensible monsoonal physical causality in this pipeline and contribute negligible incremental skill, their removal or strict geometric reinterpretation is scientifically validated.

---

## 4. Elevation Dominance & Model Robustness

A multi-model comparison was conducted across the spatial partitions to determine whether the complex multi-feature model provides meaningful physical information beyond elevation alone:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        ELEVATION DOMINANCE & MULTI-FEATURE COMPARISON (TEST SET)                       │
├─────────────────────────────────────────┬──────────┬──────────┬───────────┬─────────┬────────┬─────────┤
│ Model Experiment                        │  PR-AUC  │ ROC-AUC  │ Frozen Th │Precision│ Recall │   F1    │
├─────────────────────────────────────────┼──────────┼──────────┼───────────┼─────────┼────────┼─────────┤
│ 1. Elevation-Only Univariate Baseline   │  0.1981  │  0.8197  │   0.9500  │  0.0847 │ 0.8859 │  0.1545 │
│ 2. Full XGBoost (13 Features)           │  0.2514  │  0.8119  │   0.9500  │  0.3815 │ 0.2336 │  0.2898 │
│ 3. XGBoost Without Dry Fraction (12 f.) │  0.0665  │  0.6423  │   0.9200  │  0.0713 │ 0.1057 │  0.0852 │
│ 4. XGBoost Without Elevation (12 f.)    │  0.1658  │  0.7162  │   0.9300  │  0.3306 │ 0.2013 │  0.2503 │
│ 5. XGBoost Without Elev & Dry Frac (11) │  0.0539  │  0.4768  │   0.8600  │  0.0774 │ 0.0822 │  0.0797 │
│ 6. Constant Prevalence Baseline         │  0.0490  │  0.5000  │   0.0144  │  0.0490 │ 1.0000 │  0.0934 │
└─────────────────────────────────────────┴──────────┴──────────┴───────────┴─────────┴────────┴─────────┘
```

### Key Insights on Physical Causality:
1. **The Elevation-Only Benchmark:** Simply ranking cells inversely by mean elevation yields a test **ROC-AUC of 0.8197** and **PR-AUC of 0.1981** (4.04x prevalence), capturing **88.59% recall** (2,112 of 2,384 flood cells). However, its precision is only 8.47% with 22,837 false alarms.
2. **The Role of Non-Elevation Features:** Adding 12 additional features increases PR-AUC from 0.1981 to 0.2514 (+0.0533) and boosts precision from 8.47% to 38.15% by pruning false positives from 22,837 down to 903. This indicates that multi-feature nonlinear trees act as **spatial false-alarm suppressors** rather than independent flood discoverers.
3. **Complete Collapse Without Elevation and Riparian Margins:** When *both* `elevation_mean_m` and `land_water_dry_fraction` are ablated (`Without_elevation_and_dry_fraction`), the remaining 11 features (slope, TWI, curvatures, flow accumulation, river distance, strahler order) produce:
   - **Test ROC-AUC = 0.4768** (worse than random coin flipping of 0.50).
   - **Test PR-AUC = 0.0539** (virtually indistinguishable from the constant prevalence baseline of 0.0490).
   - **Test F1 = 0.0797** (below prevalence baseline F1 of 0.0934).
4. **Causality Limits:** Feature importance in tree models reflects split frequency and impurity reduction, not physical causality. The remaining hydrographic derivatives cannot predict inundation without gravitational minima and permanent riverbank proximity.

---

## 5. Spatial Partition Independence & Buffer Sensitivity Audit

The spatial blocking design was audited using projected Cartesian planar metrics (UTM Zone 45N / EPSG:32645):

```mermaid
graph TD
    subgraph TRAIN_PARTITION [TRAIN Partition: 15 Sub-basins]
        TR[Western Upper Approach<br>N = 72,140 | Prev = 1.44%]
    end

    subgraph VAL_PARTITION [VAL Corridor: 6 Sub-basins]
        VA[Central Valley Corridor<br>N = 53,134 | Prev = 1.50%]
    end

    subgraph TEST_PARTITION [TEST Partition: 6 Sub-basins]
        TE[Eastern Delta Inundation Corridor<br>N = 48,676 | Prev = 4.90%]
    end

    TR ===|Shared Boundary: 0.0 km| VA
    VA ===|Shared Boundary: 0.0 km| TE
    TR -.-|Natural Buffer: 24.04 km| TE

    style TR fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    style VA fill:#fff8e1,stroke:#fbc02d,stroke-width:2px
    style TE fill:#fbe9e7,stroke:#d84315,stroke-width:2px
```

### 1. Sub-Basin ID Overlap Verification:
- Train Sub-basins: `[4081030610, 4081030700, 4081032100, 4081032220, 4081032760, 4081032770, 4081033750, 4081033800, 4081035130, 4081035270, 4081035280, 4081035390, 4081037420, 4081037740, 4081037890]` ($N=15$)
- Val Sub-basins: `[4081037620, 4081038340, 4081039160, 4081039290, 4081039550, 4081039600]` ($N=6$)
- Test Sub-basins: `[4080027100, 4081037070, 4081037140, 4081038350, 4081039610, 4081039630]` ($N=6$)
- **Overlap:** Exactly **0** sub-basins overlap across any partitions. Group leakage is zero.

### 2. Physical Separation & Boundary Adjacency:
- **TRAIN to TEST Separation:** The minimum Euclidean distance between the TRAIN polygon and TEST polygon is **24.04 km** (observation point minimum is 24.16 km, median distance 88.28 km). The central VAL corridor provides an effective natural spatial buffer isolating training observations from test observations.
- **VAL to TEST Adjacency:** The VAL polygon and TEST polygon **touch directly** ($\text{distance} = 0.0\text{ km}$). Along the Naraj bifurcation and Cuttack perimeter, VAL sub-basins and TEST sub-basins share continuous geographic boundaries.
- **Boundary Cell Distribution:** In the TEST partition, **6,246 cells (12.83%)** lie within 5 km of the VAL boundary, containing 201 flood cells (8.43% of test flood labels).

### 3. Geographic Buffer Sensitivity Analysis (Held-Out Test Partition):
To evaluate whether spatial autocorrelation across the contiguous VAL-TEST border inflates performance, sensitivity evaluations were performed with geographic exclusion buffers:

| Test Evaluation Subset | Total Cells | Flood Cells | Prevalence | Full XGBoost PR-AUC | Full XGBoost ROC-AUC | Full XGBoost F1 | Without Dry Frac PR-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Unbuffered Full Test** | 48,676 | 2,384 | 4.90% | **0.2514** | **0.8119** | **0.2898** | 0.0665 |
| **Buffered: > 5 km from VAL** | 42,430 | 2,183 | 5.14% | **0.2368** | **0.7988** | **0.2560** | 0.0673 |
| **Buffered: > 10 km from VAL**| 36,498 | 2,028 | 5.56% | **0.2345** | **0.7870** | **0.2454** | 0.0677 |

> [!NOTE]
> **Spatial Independence Finding:** Applying a 5 km exclusion buffer from the VAL border causes a minor decrease in PR-AUC from 0.2514 to 0.2368 (-5.8% relative decrease), and a 10 km buffer yields 0.2345 (-6.7% relative decrease). This confirms mild spatial autocorrelation near the partition boundary, but proves that the ranking signal persists across the interior delta. However, the model without `land_water_dry_fraction` remains near random baseline across all buffer distances (0.0673 at 5 km vs 0.0514 prevalence).

---

## 6. Metrics & Threshold Verification

All metrics reported in Stage 4 were recalculated independently from raw predictions and validated against confusion matrix totals:

### Test Partition Verification Summary:
- **Total Samples:** $N = 48,676$
- **True Flood Cells:** $\text{TP} + \text{FN} = 557 + 1,827 = 2,384$ ($4.8977\%$ natural prevalence)
- **True Dry Cells:** $\text{TN} + \text{FP} = 45,389 + 903 = 46,292$ ($95.1023\%$)
- **Total Sum Check:** $557 + 903 + 1,827 + 45,389 = 48,676$ (100% accounted for)
- **Precision:** $557 / (557 + 903) = 0.3815$ (verified)
- **Recall:** $557 / (557 + 1,827) = 0.2336$ (verified)
- **F1 Score:** $2 \times (0.3815 \times 0.2336) / (0.3815 + 0.2336) = 0.2898$ (verified)
- **False Positive Rate (FPR):** $903 / (903 + 45,389) = 0.0195$ (verified)
- **Frozen Threshold Provenance:** Threshold **0.9500** was selected exclusively on the validation set ($F_1 = 0.4842$) and frozen prior to test evaluation. Zero test label tuning occurred.

### Prevalence Baseline Clarification:
The constant natural prevalence baseline ($\text{PR-AUC} = 0.0490$) represents a **ranking reference**, not an operational classifier. Operating a constant probability model yields 100% recall only by predicting every single cell as flooded ($\text{FP} = 46,292$, $\text{FPR} = 100\%$). 

A $5.13\times$ improvement in PR-AUC over prevalence demonstrates meaningful spatial sorting of risk, but **does not imply a $5.13\times$ improvement in operational warning accuracy**. At the operational threshold, the model misses 76.6% of flood cells.

---

## 7. Deliverables & Checksums

All Phase 7F Stage 4.1 audit deliverables have been generated, verified, and indexed in [data/manifests/phase7f_stage4_1_robustness_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7f_stage4_1_robustness_manifest.yaml):

| Deliverable Description | Local Artifact Path | File Size | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| **Robustness Audit Script** | [scripts/run_phase7f_stage4_1_robustness_audit.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/run_phase7f_stage4_1_robustness_audit.py) | 34,286 B | `a4974772af8a535ae06bff28e59bf4781b95e3afbfccba0629233119024140c0` |
| **Consolidated Robustness Metrics** | [data/processed/phase7/experiments/dfo3382_robustness_metrics.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/experiments/dfo3382_robustness_metrics.json) | 21,070 B | `44872db7992c4063e7138b0ca8659b8654eb627dcfb7d801d05ca7c8f2d193e7` |
| **Feature Ablation Metrics Table** | [data/processed/phase7/experiments/dfo3382_feature_ablation.csv](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/experiments/dfo3382_feature_ablation.csv) | 1,257 B | `c807f51d2b9ff12163cc8f18df2c4001c9cd617f0556a1141ad066b42901f7a8` |
| **Spatial Independence Audit** | [data/processed/phase7/experiments/dfo3382_spatial_independence_audit.json](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/experiments/dfo3382_spatial_independence_audit.json) | 2,958 B | `e953dba36d0872dd5021e100364624d80d911fed47329120b110b079191b14a1` |
| **Stage 4.1 Manifest** | [data/manifests/phase7f_stage4_1_robustness_manifest.yaml](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/manifests/phase7f_stage4_1_robustness_manifest.yaml) | 4,285 B | `e804f3ce02bdfab06117b07b34b172a1290377e7ec89fcf534b5ae2be5a37151` |
| **Stage 4.1 Pytest Suite** | [backend/tests/test_phase7f_stage4_1_robustness.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/tests/test_phase7f_stage4_1_robustness.py) | 12,605 B | `25bc20c1ca5205aa83344d57c2a472a1f81395567a216fe8d363d6bc9f0ce64d` |
| **Final Technical Report** | [docs/phase7/PHASE_7F_STAGE4_1_ROBUSTNESS_REPORT.md](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_STAGE4_1_ROBUSTNESS_REPORT.md) | Current | Active |

---

## 8. Regression Testing Summary

The consolidated Phase 7 regression test suite was executed in full:
```
backend/tests/test_phase7c_multievent_dataset.py:       6 passed
backend/tests/test_phase7_real_flood_dataset.py:       11 passed
backend/tests/test_phase7d_kaggle_preflight.py:         6 passed
backend/tests/test_phase7e_kaggle_package.py:           8 passed
backend/tests/test_phase7f_stage3_dataset.py:          10 passed
backend/tests/test_phase7f_stage4_experiments.py:       8 passed
backend/tests/test_phase7f_stage4_1_robustness.py:      9 passed
----------------------------------------------------------------
Total Consolidated Suite:                              58 passed in 26.36s (100% pass rate)
```

---

## 9. Final Decision & System Governance

### Final Decision:
**`ROBUSTNESS_AUDIT_COMPLETE`**

### System Governance Declaration:
1. **Experimental Status Reaffirmed:** All regional machine learning models developed in Phase 7F remain classified strictly as:  
   **`PROTOTYPE_ONLY / NOT_CALIBRATED / NOT_FOR_PUBLIC_ALERTS`**
2. **Operational Flood Authority:** The **Phase 6 2D hydrodynamic shallow water physics engine** ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py)) remains the sole authoritative engine for operational flood risk assessment and warning generation.
3. **Pipeline Freeze:** Execution stops immediately following this audit. No integration into operational pipelines or deployment workflows will proceed without explicit future authorization.
