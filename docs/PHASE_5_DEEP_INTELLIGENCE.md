# AQUORA Phase 5: Deep Intelligence Integration & Physical Engine Federation (Level 3)

## 1. Executive Summary

AQUORA Track B Phase 5 delivers **Level 3: Deep Intelligence Integration & Physical Engine Federation**, establishing the highest-resolution tier of flood intelligence in the AQUORA multi-tier architecture. Phase 5 operates strictly within the operational **Mumbai Mithi River Basin Deep Intelligence Zone** (`deep_mumbai_mithi`).

Phase 5 federates:
1. **30m High-Resolution Terrain Rasters:** Sub-catchment sampling of elevation, slope, aspect, flow accumulation, and surface drainage proxy in projected metric space (`EPSG:32643`).
2. **Phase 6 Deterministic Hydrodynamic Solver:** Mass-conserving 2D hydrodynamic surface routing driven by real-time Open-Meteo ECMWF Numerical Weather Prediction (NWP) precipitation forcing.
3. **Verified Critical Facilities Impact Assessment:** High-precision raster-grid intersection for all 366 verified facilities (359 OSM + 7 MCGM verified) enforcing a strict **Zero-Proximity-Inference** policy.
4. **Multiscale Data Contracts & Governance:** Federation of `DeepDataContract`, `IndiaFeaturePipelineService`, `IndiaSARService`, and `FloodModelRegistry`, strictly preserving uningested physical attributes as `None`.

---

## 2. Architecture & Reuse

Phase 5 reuses existing AQUORA services and contracts without duplicating code or inventing synthetic interfaces:

```
                  POST /api/v1/intelligence/deep (Point Inspection)
                 POST /api/v1/intelligence/deep/simulate (Simulation)
                                       │
                                       ▼
                         DeepIntelligenceService
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
IndiaSpatialService        IndiaFeaturePipelineService     FloodProcessingService
(EPSG:32643 Rasters)        (Multiscale Features)           (Phase 6 2D Hydro Solver)
        │                              │                              │
        ├─ elevation_30m.tif           ├─ 11 Core National            ├─ Real Copernicus DEM
        ├─ slope_30m.tif               ├─ 3 Regional Expansion        ├─ Real ECMWF NWP
        ├─ aspect_30m.tif              └─ Multiscale Provenance       └─ Mass Conservation
        ├─ flow_acc_30m.tif                                                  │
        └─ drainage_proxy_30m.tif                                            ▼
                                                                  FacilityImpactSummary
                                                                  (366 Facilities Grid Match)
```

### Component Integration Matrix:
- **`app.schemas.intelligence_contracts.DeepDataContract`:** Underlying schema standard defining high-resolution deep zone fields.
- **`app.services.india_feature_pipeline.IndiaFeaturePipelineService`:** Reused for macro-scale precipitation accumulations and antecedent moisture indices.
- **`app.services.india_sar_service.IndiaSARService`:** Reused for Sentinel-1 backscatter corroboration query (truthfully returning `UNAVAILABLE`).
- **`app.services.flood_service.FloodProcessingService`:** Reused as the deterministic 2D hydrodynamic simulation engine.
- **`app.services.ml_model_registry.FloodModelRegistry`:** Reused for Level 3 prototype XGBoost model metadata and supplementary ML susceptibility scores.

---

## 3. High-Resolution Raster Engineering & CRS Transformation

### Native Raster Geometry
All physical rasters for the Mumbai / Mithi Deep Intelligence Zone reside in `data/processed/phase7/terrain/` and are natively projected in **UTM Zone 43N (`EPSG:32643`)**:

| Raster Layer | Native Dimensions | Resolution | Data Type | NoData Value | Range | Valid Pixels |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `elevation_30m.tif` | $476 \times 392$ | $(30.0, 30.0)\,\text{m}$ | `float32` | `-9999.0` | $[0.10, 115.89]\,\text{m}$ | 186,592 (100%) |
| `slope_30m.tif` | $476 \times 392$ | $(30.0, 30.0)\,\text{m}$ | `float32` | `-9999.0` | $[0.00, 0.98]^\circ$ | 186,592 (100%) |
| `aspect_30m.tif` | $476 \times 392$ | $(30.0, 30.0)\,\text{m}$ | `float32` | `-9999.0` | $[0.00, 360.00]^\circ$ | 186,592 (100%) |
| `flow_accumulation_30m.tif` | $476 \times 392$ | $(30.0, 30.0)\,\text{m}$ | `float32` | `-9999.0` | $[1.00, 183.96]$ | 186,592 (100%) |
| `drainage_proxy_30m.tif` | $476 \times 392$ | $(30.0, 30.0)\,\text{m}$ | `float32` | `-9999.0` | $[3.49, 14.37]$ | 186,592 (100%) |

### Coordinate Transformation
Input coordinates are supplied in standard geographic WGS84 (`EPSG:4326`). Coordinate-to-pixel sampling transforms coordinates to UTM Zone 43N before indexing:
```python
transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
x, y = transformer.transform(longitude, latitude)
row, col = src.index(x, y)
```
Points falling outside $0 \le \text{row} < 476$ or $0 \le \text{col} < 392$ are rejected with `OUTSIDE_DEEP_ZONE_COVERAGE`.

---

## 4. Scientific Justification for Integer Flow Accumulation Rounding

In digital terrain analysis and hydrological routing theory (O'Callaghan & Mark, 1984; Tarboton, 1997), D8 flow accumulation represents the **discrete count of upstream contributing grid cells** whose overland drainage path traverses a given cell:
$$A_i = 1 + \sum_{j \in \text{upstream}(i)} A_j \in \mathbb{Z}_{\ge 1}$$

### Why the Raster Stores Floating Point:
Geospatial processing libraries (GDAL, TauDEM, RichDEM) and GIS software often write flow accumulation layers as 32-bit floating point (`float32`) to:
1. Prevent integer overflow on continental-scale river basins.
2. Accommodate bilinear interpolation and smoothing filters.

### Scientific Rationale for Rounding:
In AQUORA's versioned `DeepDataContract`, the attribute is specified as `flow_accumulation_cells: Optional[int] = Field(None, ge=0)`. Rounding continuous values via `int(round(float(val)))`:
- Accurately restores the discrete cell count intended by the D8 hydrologic definition.
- Avoids truncation bias that would occur with standard integer floor casting (`int(val)`).
- Ensures non-negative compliance (`ge=0`).

---

## 5. Zero-Fabrication Invariants & Missing Data Preservation

In strict alignment with AQUORA scientific ethics, missing or uningested physical layers are never approximated, synthesized, or filled with heuristic defaults:

| Deep Data Field | Status on Disk | Contract Output | Scientific Provenance |
| :--- | :--- | :--- | :--- |
| `built_up_fraction` | Absent for Mumbai | `None` | `UNAVAILABLE_NOT_ON_DISK` |
| `distance_to_road_m` | Absent for Mumbai | `None` | `UNAVAILABLE_NOT_ON_DISK` |
| `distance_to_waterway_m` | Absent for Mumbai | `None` | `UNAVAILABLE_NOT_ON_DISK` |
| `tide_level_m` | Tide gauge CSV uningested | `None` | `UNAVAILABLE_NOT_ON_DISK` |
| `sar_delta_vv_db` | Raw SAFE granules absent | `None` | `REGISTERED_TARGET_AWAITING_DOWNLOAD` |

---

## 6. Physical Engine Federation vs. ML Susceptibility

A fundamental architectural boundary in AQUORA is the clear separation between **physically modeled hydraulic depth** and **ML susceptibility scores**:

1. **Deterministic Hydraulic Depth (`modeled_water_depth_m`):**
   - Derived from the Phase 6 mass-conserving 2D hydrodynamic solver.
   - Represents physical water ponding depth in meters $[0.0, \infty)$.
   - Evaluated under strict mass-conservation invariants ($\Delta M \le 10^{-4}\,\text{m}^3$).
   - Governs the physical severity scale: `DRY` (< 0.05 m), `LOW` (0.05–0.15 m), `MODERATE` (0.15–0.30 m), `HIGH` (0.30–0.60 m), `SEVERE` ($\ge$ 0.60 m).
2. **ML Susceptibility Score (`ml_susceptibility_score`):**
   - Derived from the Kaggle-trained XGBoost prototype (`aquora_xgboost_prototype.joblib`).
   - Dimensionless probability $[0.0, 1.0]$.
   - Explicitly labeled as `PROTOTYPE_ONLY` / uncalibrated heuristic, strictly separate from physical depth.

### Opt-In Simulation Invariant
A standard point inspection (`POST /api/v1/intelligence/deep`) **never** automatically launches a hydrodynamic simulation. Simulation is strictly opt-in via `run_simulation=True` or via `POST /api/v1/intelligence/deep/simulate`.

---

## 7. Critical Facility Impact Assessment

AQUORA ingests 366 verified critical facilities for the Mumbai Mithi catchment:
- **359 facilities** from OpenStreetMap (`data/raw/facilities/osm_critical_facilities.json`).
- **7 facilities** from MCGM Government Open Data (`data/raw/facilities/mithi_critical_facilities.json`).

### Grid Intersection Findings:
- **365 facilities** fall strictly inside the $476 \times 392$ raster grid geometry and are assigned direct cell-level depth impacts.
- **Exactly 1 facility** (`Bandra Bus Station (W)` at $19.05404^\circ\text{N}, 72.83968^\circ\text{E}$) lies at `col=-1` just outside the western edge of the DEM bounding box.

### Zero Proximity Inference Policy:
Rather than inferring flood depth from nearby cells, the out-of-bounds facility is strictly marked:
- `raster_covered: False`
- `modeled_water_depth_m: None`
- `flood_severity: UNCOVERED`
- `impact_status: OUT_OF_RASTER_BOUNDS`

---

## 8. API Reference

### 1. Point Inspection (`POST /api/v1/intelligence/deep`)
```bash
curl -X POST http://localhost:8000/api/v1/intelligence/deep \
  -H "Content-Type: application/json" \
  -d '{"latitude": 19.065, "longitude": 72.879}'
```

**Response Example:**
```json
{
  "status": "POINT_INSPECTED",
  "intelligence_level": "DEEP",
  "zone_id": "deep_mumbai_mithi",
  "zone_name": "Mumbai Mithi River Basin Deep Zone",
  "coordinates": {"latitude": 19.065, "longitude": 72.879},
  "point_in_zone": true,
  "raster_sampled": true,
  "elevation_m": 48.173,
  "slope_degrees": 0.167,
  "aspect_degrees": 155.887,
  "flow_accumulation_cells": 1,
  "drainage_proxy_score": 9.478,
  "built_up_fraction": null,
  "distance_to_road_m": null,
  "distance_to_waterway_m": null,
  "tide_level_m": null,
  "modeled_water_depth_m": null,
  "physical_severity": null,
  "ml_susceptibility_score": 0.3362,
  "calibration_status": "PHYSICAL_HYDRODYNAMIC_SOLVER_PRIMARY",
  "sar_corroboration": {
    "sar_available": false,
    "evidence_classification": "UNAVAILABLE"
  },
  "critical_facilities_count": 366,
  "simulation": null,
  "facility_impacts": null
}
```

### 2. Physical Flood Simulation (`POST /api/v1/intelligence/deep/simulate`)
```bash
curl -X POST http://localhost:8000/api/v1/intelligence/deep/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 19.065,
    "longitude": 72.879,
    "horizon_minutes": 30,
    "timestep_minutes": 10,
    "evaluate_facility_impacts": true
  }'
```

---

## 9. Test Suite Verification

The Phase 5 test suite (`backend/tests/test_phase5_deep_intelligence.py`) validates 19 targeted integration tests:
1. `test_deep_inspection_valid_kurla_coordinate`: Valid point inspection in Mithi Deep Zone.
2. `test_deep_inspection_bkc_coordinate`: Valid BKC inspection.
3. `test_deep_inspection_outside_deep_zone_patna`: Strict rejection of out-of-zone coordinates.
4. `test_deep_inspection_outside_deep_zone_delhi`: Strict rejection of macro-national coordinates.
5. `test_deep_inspection_colaba_outside_mithi_dem`: Strict rejection of South Mumbai out-of-DEM coordinates.
6. `test_deep_inspection_invalid_latitude`: HTTP 422 on latitude $> 90^\circ$.
7. `test_deep_inspection_invalid_longitude`: HTTP 422 on longitude $< -180^\circ$.
8. `test_deep_inspection_zero_fabrication_missing_features`: Uningested physical fields remain `None`.
9. `test_deep_inspection_sar_unavailable`: Honest UNAVAILABLE SAR status reporting.
10. `test_raster_nodata_handling`: Correct mapping of NoData ($-9999.0$) to `None`.
11. `test_flow_accumulation_integer_rounding`: D8 integer cell count rounding verification.
12. `test_normal_inspection_does_not_launch_simulation`: Opt-in simulation invariant.
13. `test_explicit_simulation_request_via_deep_endpoint`: On-demand solver triggering via `run_simulation=True`.
14. `test_standalone_deep_simulate_endpoint`: Complete physical simulation and mass-balance accounting.
15. `test_standalone_deep_simulate_outside_zone`: Rejection of out-of-zone simulation requests.
16. `test_simulation_failure_handled_truthfully`: Truthful error reporting on solver exceptions.
17. `test_facility_impacts_zero_proximity_inference`: Verified 365 covered vs 1 uncovered facility.
18. `test_facility_depth_impact_thresholds`: Depth-to-severity threshold mapping verification.
19. `test_distinction_between_physical_depth_and_ml_susceptibility`: Strict physical vs ML separation.
