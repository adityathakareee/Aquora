# AQUORA Phase 6C.2G.20: Consolidated National Rainfall Expansion, Spatial Provenance & ML-Readiness Audit Report

**Phase Identifier:** `PHASE_6C_2G_20_CONSOLIDATED_NATIONAL_RAINFALL_EXPANSION`  
**Timestamp:** `2026-10-28T15:20:00Z`  
**Final Governance Decision:** `NATIONAL_BATCH_AND_READINESS_VALIDATED`  
**ML-Readiness Decision:** `BLOCKED_BY_GROUND_TRUTH`  
**Primary Objective:** Expand authentic national historical rainfall in bounded Mode B batches, independently recompute prior extractions and landmarks, audit administrative location enrichment against authoritative boundaries, reconcile the 6,876-row national inventory, and conduct a preliminary ML data-readiness audit under strict zero-fabrication and zero-leakage safeguards.

---

## 1. Executive Summary & Governance Decisions

In AQUORA Phase 6C.2G.20, national historical rainfall ingestion and data governance were consolidated across multiple interrelated tasks without bypassing validation gates or altering core system architecture.

### Key Accomplishments:
1. **Preflight Audit & Extraction Recomputation:**
   - Re-verified foundational asset immutability (Copernicus DSM, working 30m DEM, raw IFI v3 CSV).
   - Re-verified the three canonical landmarks: **E01** (July 2005, `193.8802 mm`), **E02** (August 2017, `154.3250 mm` daily & 48 HHR), and **E03** (July 2019, `243.1200 mm` daily / `221.7750 mm` IMD cycle).
   - Independently recomputed the four zero-rainfall extractions from Phase 19 (`UEI-IMD-FL-1981-0046`, `0077`, `0086`, `0009`) from raw UCSB CHIRPS rasters, confirming authentic `0.00 mm` values and documenting $5 \times 5$ neighborhood diagnostics.
2. **Bounded National Acquisition (Mode B Batch of 10 Dates):**
   - Successfully acquired 10 eligible unique dates across 1981, 1982, and 1983 (`1981-07-27`, `1981-08-01`, `1981-08-22`, `1981-09-15`, `1982-04-15`, `1982-04-22`, `1982-08-08`, `1982-08-22`, `1983-06-15`, `1983-06-24`).
   - Covered **27 historical IFI events**:
     - **11 newly verified extractions** at administrative proxies (e.g., `107.94 mm` in Mumbai on 1983-06-24, `53.88 mm` in Mumbai on 1981-09-15, `34.65 mm` in Chamoli/Kedarnath on 1982-08-08, `31.52 mm` in Idukki/Kerala on 1981-07-27).
     - **16 events with unspecified locations** strictly preserved with `NULL` (`NaN`) rainfall.
   - Total data transfer: **`29.94 MB decimal`**, with temporary scratch files cleaned up immediately following SHA-256 and Affine extraction logging.
3. **Location Enrichment Audit:**
   - Audited Datameet / Survey of India authoritative administrative boundary hierarchy (version 2024.1, ODbL license, EPSG:4326, 36 states, 8 pilot districts).
   - Evaluated conservative single-district matching: identified 75 unambiguous single-district matches across the inventory.
   - Enforced strict safeguard: multi-district regional events remain `LOCATION_UNSPECIFIED`. Original IFI `state` and `districts` fields remain 100% unaltered.
4. **Authoritative National Inventory Reconciliation:**
   - Maintained exact, closed accounting across all **6,876 IFI v3 event records**:
     - `MATCHED_RAINFALL_COVERAGE`: **26** ($15 + 11$)
     - `DATE_ACQUIRED_UNEXTRACTED_LOCATION`: **41** ($25 + 16$)
     - `NOT_ACQUIRED`: **6,468** ($6,495 - 27$)
     - `UNAVAILABLE_ERA` (Pre-1981): **321**
     - `DATE_UNCERTAIN` / Invalid Bounds: **20**
     - **Total:** $\mathbf{6,876}$ rows.
   - Zero silent zero-filling verified: all 41 unextracted locations have verified `NaN` values.
5. **Preliminary ML-Readiness Audit:**
   - Audited predictor features against `ml/aquora_ml_feature_schema_v1.json` and `PHASE_7_FEATURE_POLICY.yaml`. Core predictors (Copernicus 30m DEM, slope, aspect, HydroRIVERS distance-to-river, CHIRPS/IMERG rainfall, HydroBASINS Level 5/6) are structurally sound.
   - Evaluated label availability: tabular administrative disaster reports do **not** provide continuous 30m pixel-level inundation masks or defensible dry-negative background labels.
   - Supervised spatial training is strictly **`BLOCKED_BY_GROUND_TRUTH`**.
   - Zero supervised models trained or evaluated.
6. **Testing & Governance:**
   - Focused Phase 20 suite: **10/10 tests passed in 0.55s**.
   - Full Phase 6C regression suite: **218/218 tests passed in 31.92s**.
   - Final status: **`NATIONAL_BATCH_AND_READINESS_VALIDATED`**.

---

## 2. Preflight Audit & Independent Recomputations

### 2.1 Core Asset Immutability

| Foundational Asset | Local Relative Path | Immutable SHA-256 | Immutability Status |
|---|---|---|---|
| **Copernicus GLO-30 DSM** | `data/raw/phase7/dem/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif` | `b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd` | `VERIFIED_IMMUTABLE` |
| **Working 30m Terrain DEM** | `data/processed/phase7/terrain/elevation_30m_study_extent.tif` | `25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda` | `VERIFIED_IMMUTABLE` |
| **Raw IFI v3 CSV (6,876 rows)** | `data/raw/phase7/ground_truth/india_flood_inventory_v3.csv` | `ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108` | `VERIFIED_IMMUTABLE` |

### 2.2 Canonical Landmarks Recomputation

Re-computed directly from local NetCDF4, HDF5, and GeoTIFF assets at target coordinate `(72.85°E, 19.05°N)`:

```
+===================================================================================================================+
| Landmark | Event Date   | Product Type      | Source Granules / Datasets     | Value (mm) | Residual | Status     |
+===================================================================================================================+
| E01      | 2005-07-26   | CHIRPS Daily      | chirps-v2.0.2005.07.26.tif.gz   | 193.8802   | 0.000000 | PASS       |
| E02      | 2017-08-29   | IMERG 3B-DAY      | 3B-DAY...20170829...nc4         | 154.3250   | 0.000000 | PASS       |
| E02      | 2017-08-29   | IMERG 3B-HHR (48) | 48 granules (00:00 - 24:00 UTC) | 154.3250   | 0.000000 | PASS       |
| E03      | 2019-07-01   | IMERG 3B-DAY      | 3B-DAY...20190701...nc4         | 243.1200   | 0.000000 | PASS       |
| E03      | 2019-07-01/2 | IMERG 3B-HHR (48) | 48 granules (IMD 24h cycle)     | 221.7750   | 0.000000 | PASS       |
+===================================================================================================================+
```

### 2.3 Independent Recomputation of Phase 19 Zero-Rainfall Extractions

The 4 zero-rainfall extractions reported in Phase 19 were re-streamed from UCSB CHIRPS canonical GeoTIFFs, and their pixel index, raw values, and $5 \times 5$ spatial neighborhood metrics were analyzed:

| Event UEI | Date | Target / Coordinate | Pixel (Row, Col) | Raw Value | 5x5 Neighborhood [Min, Max, Mean] | Audit Outcome |
|---|---|---|---|---|---|---|
| `UEI-IMD-FL-1981-0046` | 1981-06-22 | Mumbai Centroid (`72.85°E, 19.05°N`) | `(618, 5056)` | `0.00 mm` | `[-9999.0, 0.0, -3599.64]` | `VERIFIED_AUTHENTIC_ZERO` |
| `UEI-IMD-FL-1981-0077` | 1981-07-01 | Kedarnath Valley (`79.07°E, 30.73°N`) | `(385, 5181)` | `0.00 mm` | `[0.00, 0.00, 0.00]` | `VERIFIED_AUTHENTIC_ZERO` |
| `UEI-IMD-FL-1981-0086` | 1981-07-01 | Jalpaiguri Centroid (`88.72°E, 26.52°N`) | `(469, 5374)` | `0.00 mm` | `[0.00, 0.00, 0.00]` | `VERIFIED_AUTHENTIC_ZERO` |
| `UEI-IMD-FL-1981-0009` | 1981-07-08 | Bihar Kosi Basin (`86.60°E, 26.12°N`) | `(477, 5331)` | `0.00 mm` | `[0.00, 0.00, 0.00]` | `VERIFIED_AUTHENTIC_ZERO` |

*Diagnostic Note:* In `UEI-IMD-FL-1981-0046`, the $5 \times 5$ neighborhood min of `-9999.0` represents ocean nodata cells to the west (Arabian Sea), confirming that the cell is on the coastal boundary, while the land pixels in the cell and immediately east record authentic `0.00 mm`.

---

## 3. Bounded National Rainfall Acquisition (Phase 20 Batch)

### 3.1 Batch Selection & Pre-Download Analysis
- **Operating Mode:** Mode B (Storage-Constrained In-Memory Extraction with Automated Provenance Logging).
- **Candidate Dates Selected:** 10 earliest eligible post-1981 dates in `NOT_ACQUIRED` having events with proxy coordinates:
  `['1981-07-27', '1981-08-01', '1981-08-22', '1981-09-15', '1982-04-15', '1982-04-22', '1982-08-08', '1982-08-22', '1983-06-15', '1983-06-24']`.
- **Pre-Download Statistics:**
  - Total events in batch: **27**.
  - Events with administrative proxy coordinates: **11**.
  - Events with unspecified locations: **16**.
  - Expected file count: **10 GeoTIFFs**.
  - Total transferred bytes: **`29,944,228 bytes` (~29.94 MB decimal)**.
  - Disk headroom: Available free disk space is **`66.1 GB`** decimal, well above the **`10.0 GB`** disk safety reserve.

### 3.2 Mode B Execution & Extraction Evidence
All 10 dates were streamed, validated via SHA-256, extracted, and cleaned up:

```
+======================================================================================================================+
| Event Date | Canonical File & SHA-256 Hash                          | Size (Bytes)| Events | Extracted Observables   |
+======================================================================================================================+
| 1981-07-27 | chirps-v2.0.1981.07.27.tif.gz (d2f44bad3013e996...)    | 3,547,629   | 1      | Idukki (31.52 mm)       |
| 1981-08-01 | chirps-v2.0.1981.08.01.tif.gz (a1a9e15db62a3ec9...)    | 2,929,337   | 5      | Punjab (0.00 mm), 4 Unsp|
| 1981-08-22 | chirps-v2.0.1981.08.22.tif.gz (9b3c95023e5f5c82...)    | 2,726,338   | 2      | Mumbai (0.00 mm), 1 Unsp|
| 1981-09-15 | chirps-v2.0.1981.09.15.tif.gz (04c391cb3b040156...)    | 2,756,994   | 4      | Mumbai (53.88 mm), 3 Unsp|
| 1982-04-15 | chirps-v2.0.1982.04.15.tif.gz (52d14574e1ad54b2...)    | 3,593,701   | 4      | Srinagar (29.25 mm),    |
|            |                                                        |             |        | Ludhiana (19.86 mm)     |
| 1982-04-22 | chirps-v2.0.1982.04.22.tif.gz (947a726254e67379...)    | 3,210,781   | 1      | Punjab (0.00 mm)        |
| 1982-08-08 | chirps-v2.0.1982.08.08.tif.gz (cae98bf3ce529f41...)    | 3,227,323   | 1      | Chamoli (34.65 mm)      |
| 1982-08-22 | chirps-v2.0.1982.08.22.tif.gz (56d8c931a3258cd5...)    | 2,513,660   | 7      | Cuttack (27.18 mm), 6 Unsp|
| 1983-06-15 | chirps-v2.0.1983.06.15.tif.gz (ad19315af17d4956...)    | 3,039,862   | 1      | Bengaluru (12.77 mm)    |
| 1983-06-24 | chirps-v2.0.1983.06.24.tif.gz (9e665d2b73a82c36...)    | 2,390,545   | 1      | Mumbai (107.94 mm)      |
+----------------------------------------------------------------------+-------------+--------+-------------------------+
| Cumulative Batch Totals: 10 unique dates acquired                    | 29,944,228  | 27     | 11 Matched, 16 Unspec   |
+======================================================================================================================+
```

All scratch files were cleaned up after persisting full cryptographic provenance in `phase6c2g20_acquisition_checkpoint.json`.

---

## 4. Location Enrichment Audit

### 4.1 Authoritative Administrative Hierarchy
The repository contains authoritative administrative vector boundaries in `data/processed/boundaries/`:
- **Source:** Survey of India / Datameet GIS
- **Version:** 2024.1
- **License:** Open Database License (ODbL) / Open Government Data
- **Canonical CRS:** `EPSG:4326`
- **Coverage:** 36 states and union territories, 8 regional pilot districts (`Patna`, `Varanasi`, `Kamrup Metropolitan`, `Nashik`, `East Godavari`, `Bharuch`, `Jabalpur`, `Mumbai Suburban`).

### 4.2 Conservative Location Enrichment Rules
1. **Unambiguous Single-District Matching:**  
   When an event with `LOCATION_UNSPECIFIED` has a clean state matching an authoritative state and the district string contains exactly one token corresponding to a verified district entity, an `ADMIN_DISTRICT_PROXY` centroid point is generated:
   - **75 events** across the IFI v3 inventory match this criterion.
   - Example: `UEI-IMD-FL-1983-0002` (Andhra Pradesh, `districts = "East Godavari"`) unambiguously matches `DIST-AP-EG`, yielding proxy coordinate `(81.8040°E, 17.0005°N)` with `spatial_confidence = "PROXY_CENTROID"`.
2. **Multi-District Region Ambiguity:**  
   When an event record lists multiple districts (e.g., `Adilabad, East Godavari, Karimnagar, Khammam...`), assigning a single district's centroid introduces severe spatial bias. Such events **strictly remain `LOCATION_UNSPECIFIED`** (`spatial_confidence = "NO_LOCATION"`).
3. **Data Integrity:**  
   The original IFI v3 `state` and `districts` columns remain 100% unaltered. Centroids are never mistaken for precise flood footprints.

---

## 5. Authoritative National Inventory Reconciliation

Row-level lineage was updated in `data/processed/phase7/rainfall/phase6c2g20_acquisition_inventory.csv`, preserving all 6,876 IFI v3 records:

```
+===================================================================================================+
| Inventory Classification Category    | Phase 19 Count | Phase 20 Change    | Phase 20 Final Count |
+===================================================================================================+
| MATCHED_RAINFALL_COVERAGE            | 15             | +11                | 26                   |
| DATE_ACQUIRED_UNEXTRACTED_LOCATION   | 25             | +16                | 41                   |
| NOT_ACQUIRED                         | 6,495          | -27                | 6,468                |
| UNAVAILABLE_ERA (Pre-1981)           | 321            | 0                  | 321                  |
| DATE_UNCERTAIN (Invalid/Out of Bounds)| 20            | 0                  | 20                   |
+--------------------------------------+----------------+--------------------+----------------------+
| Total India Flood Inventory Records  | 6,876          | 0                  | 6,876                |
+===================================================================================================+
```

### Strict Zero-Filling Prevention:
- All 41 `DATE_ACQUIRED_UNEXTRACTED_LOCATION` records have verified `NaN` rainfall depths.
- Zero silent zero-filling: 0.00 mm is never assigned to missing locations or nodata pixels.
- All 26 `MATCHED_RAINFALL_COVERAGE` records carry explicit `spatial_confidence = "PROXY_CENTROID"` and cryptographic SHA-256 evidence links.

---

## 6. Preliminary ML-Readiness Audit

Adhering strictly to `ml/aquora_ml_feature_schema_v1.json` and `PHASE_7_FEATURE_POLICY.yaml`:

### 6.1 Predictor Feature Pipeline Evaluation
- **Rainfall Features:** Historical CHIRPS/IMERG daily accumulations are mathematically sound and expanding in bounded batches.
- **Terrain Features:** Copernicus GLO-30 DSM provides authentic 30m elevation across India; slope, aspect, and flow accumulation are deterministically derived.
- **Hydrographic Features:** HydroRIVERS vectors provide authentic river centerline distance transforms across major Indian basins (Ganga, Brahmaputra, Godavari, Narmada).
- **Basin Grouping:** HydroBASINS Level 5/6 provides non-overlapping hydrologic units for GroupKFold cross-validation, preventing spatial leakage between training and validation folds.

### 6.2 Ground-Truth & Target Label Integrity Audit
The audit assessed candidate label sources for supervised spatial machine learning:
1. **India Flood Inventory v3 Records:** Tabular disaster summaries (state, district, date, fatalities, houses destroyed). **Cannot serve as spatial flood labels.** A district-level record does not identify which 30m pixels were inundated and contains no dry-negative background pixels.
2. **Sentinel-1 SAR Radar Masks:** Observational radar anomalies with known physical limitations (urban corner-reflector occlusion, radar shadow, wind-roughened open water false positives, 6–12 day revisit gaps). Limited to targeted pilot deluges; absent at national historical scale.
3. **Physics Simulation Outputs:** Synthetic model outputs from deterministic 2D hydrodynamic solvers. Training ML on physics models introduces severe inductive bias and violates the zero-synthetic-labels policy.

### 6.3 Governance Decision
```
================================================================================
FINAL ML-READINESS DECISION: BLOCKED_BY_GROUND_TRUTH
================================================================================
Rationale: Supervised spatial machine learning training is strictly prohibited
until independent, spatially continuous, empirical ground-truth inundation masks
and verified dry-negative background pixels are established.
Zero supervised models have been trained or evaluated in this phase.
================================================================================
```

---

## 7. Storage Safety & Resource Headroom

- **Workspace Free Space:** **`66.1 GB`** decimal.
- **Enforced Safety Reserve:** **`10.0 GB`** decimal.
- **Storage Mode B Performance:** Cleaned up all scratch files immediately after observation extraction. Net disk growth for the 10-date batch was under 3 MB (limited to CSV and JSON metadata updates).
- **Reserve Status:** **`SAFE`** ($66.1\text{ GB} \gg 10.0\text{ GB}$).

---

## 8. Test Suite Verification & Outputs

### 8.1 Focused Phase 6C.2G.20 Tests (10/10 Passed in 0.55s)
Command: `backend\.venv\Scripts\pytest.exe backend/tests/test_phase6c2g20_national_rainfall.py -v`
```text
backend\tests\test_phase6c2g20_national_rainfall.py::test_asset_immutability PASSED [ 10%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_landmarks_e01_e02_e03_recomputation PASSED [ 20%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_phase19_extractions_recomputation_and_diagnostics PASSED [ 30%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_mode_b_staged_acquisition_provenance PASSED [ 40%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_location_enrichment_rules_and_preservation PASSED [ 50%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_inventory_reconciliation_exact_accounting PASSED [ 60%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_strict_null_preservation_zero_filling_prohibition PASSED [ 70%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_disk_safety_reserve_enforcement PASSED [ 80%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_ml_readiness_audit_blocked_by_ground_truth PASSED [ 90%]
backend\tests\test_phase6c2g20_national_rainfall.py::test_manifest_governance_and_zero_supervised_models PASSED [100%]

============================= 10 passed in 0.55s ==============================
```

### 8.2 Full Phase 6C Regression Suite (218/218 Passed in 31.92s)
Command: `powershell -Command "& backend\.venv\Scripts\pytest.exe (Get-ChildItem backend\tests\test_phase6c*.py) -q"`
```text
........................................................................ [ 33%]
........................................................................ [ 66%]
........................................................................ [ 99%]
..                                                                       [100%]
218 passed in 31.92s
```

---

## 9. Deliverable Artifact Register

| Deliverable Artifact | File Path | Status | Cryptographic Hash (SHA-256) |
|---|---|---|---|
| **National Acquisition Script** | `scripts/acquire_phase6c2g20_national_rainfall.py` | `CREATED` | `fc2a578a159937a0...` |
| **Validation Engine Script** | `scripts/validate_phase6c2g20_national_rainfall.py` | `CREATED` | `b99e7104beaf7f16...` |
| **ML-Readiness Audit Script** | `scripts/audit_phase6c2g20_ml_readiness.py` | `CREATED` | `bceb4c52f6d0fca7...` |
| **Focused Test Suite** | `backend/tests/test_phase6c2g20_national_rainfall.py` | `CREATED` | `75dbcb8a10b42fbb...` |
| **Acquisition Checkpoint** | `data/processed/phase7/rainfall/phase6c2g20_acquisition_checkpoint.json` | `GENERATED` | `ad7535bc87b07da7...` |
| **Authoritative Inventory** | `data/processed/phase7/rainfall/phase6c2g20_acquisition_inventory.csv` | `GENERATED` | `f63b0a7c4f693240...` |
| **Quality Assessment JSON** | `data/processed/phase7/rainfall/phase6c2g20_quality_assessment.json` | `GENERATED` | `e97148bf5b273b4e...` |
| **ML-Readiness Audit JSON** | `data/processed/phase7/ml/phase6c2g20_ml_readiness.json` | `GENERATED` | `a147fc2b1890cd12...` |
| **Manifest YAML** | `data/manifests/phase6c2g20_national_rainfall_manifest.yaml` | `GENERATED` | `d7249be88a20ca88...` |
| **Consolidated Report** | `docs/phase7/PHASE_6C2G20_CONSOLIDATED_DATA_READINESS_REPORT.md` | `DOCUMENTED` | Present document |

---

## 10. Next Consolidated Milestone (Phase 6C.2G.21)

With national rainfall scaling established under Mode B, location enrichment rules audited, and ML readiness formally gated:
1. **Scaled Multi-Decade Batch Scaling:** Ingest 20–50 unique dates per batch across remaining post-1981 monsoon seasons while maintaining the 10.0 GB disk safety reserve.
2. **Conservative Pilot Centroid Integration:** For the 75 unambiguous single-district events identified in Section 4, enable selective proxy point extraction upon source acquisition with explicit `PROXY_CENTROID` provenance.
3. **Observational Benchmark Delineation:** Focus empirical flood benchmarking on high-confidence landmark deluges (e.g., Mumbai Mithi E02 and E03) where multi-sensor radar and gauge data converge.
