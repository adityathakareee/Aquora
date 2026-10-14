# AQUORA Phase 4 — Regional Flood Intelligence & Watershed Risk Modeling (Level 2)

## 1. Executive Summary & Objective

Phase 4 operationalizes **Level 2 (Regional) Flood Intelligence** for AQUORA across verified Indian river basins (Ganga, Brahmaputra, Godavari, Narmada, and Mithi), continuing directly from Phase 3 (commit `a080923`).

### Intelligence Hierarchy Placement
```text
               INDIA-WIDE FLOOD INTELLIGENCE
                            │
                            ▼
                    NATIONAL SCREENING (Level 1)
           Phase 2E (Features) & Phase 3 (ML Architecture)
                            │
                            ▼
              ►►► REGIONAL INTELLIGENCE (Level 2) ◄◄◄
           Phase 4: Basin Watershed & Corridor Intelligence
                            │
                            ▼
                    DEEP INTELLIGENCE (Level 3)
     Phase 6 Deterministic Physics Engine & High-Res Sensors
```

---

## 2. Invariants & Scientific Governance

1. **Exact 14 Predictors Evaluated**:
   - Strictly limited to the 11 `CORE_NATIONAL` features plus the 3 `REGIONAL_EXPANSION` features governed by `ml/aquora_ml_feature_schema_v1.json` (v1.0.0):
     `rainfall_1h_mm`, `rainfall_3h_mm`, `rainfall_6h_mm`, `rainfall_24h_mm`, `rainfall_72h_mm`, `rainfall_anomaly_index`, `elevation_m`, `slope_deg`, `distance_to_river_m`, `historical_flood_frequency`, `landcover_class`, `basin_drainage_area_km2`, `soil_saturation_index`, `population_density_per_km2`.
2. **Deep-Zone Feature Isolation**:
   - Deep-zone exclusive predictors (`flow_accumulation_cells`, `drainage_proxy_score`, `built_up_fraction`, `distance_to_road_m`, `distance_to_waterway_m`, `tide_level_m`) are strictly prohibited from regional predictors and rejected with validation errors if injected.
3. **Physical Hydraulic Solver Primacy**:
   - The Phase 6 deterministic physical simulation engine (`MithiPhysicsEngine`, `HydrodynamicEngine`) remains the primary authority for urban hydraulics.
   - Regional intelligence never invokes or imitates the physical hydraulic solver as a shortcut or side effect.
4. **Zero Fabrication**:
   - **Population Density**: Since high-resolution gridded WorldPop/Census GeoTIFFs are not yet ingested locally, `IndiaPopulationService` returns `None` with explicit `UNAVAILABLE` provenance. No synthetic population densities are invented.
   - **Critical Facilities**: 366 authentic facilities are reported in Mumbai/Mithi; other basins report `None` with explicit `CRITICAL_FACILITIES_UNINGESTED` provenance.
   - **Out of Coverage**: Points outside verified river basin boundaries return explicit `OUTSIDE_REGIONAL_COVERAGE` status; no synthetic fallback or defaulting to Mumbai occurs.
5. **Uncalibrated Screening Index**:
   - When ML model artifacts are not yet trained on authentic coincident flood events, the regional service computes a dimensionless watershed screening index based on rainfall, river proximity, and terrain slope.
   - This index is explicitly labeled as `calibration_status = "UNCALIBRATED_REGIONAL_SCREENING"`. It is strictly **never described as a calibrated probability or flood forecast**.

---

## 3. Architecture & Implemented Components

### 3.1. Regional Schemas (`backend/app/schemas/regional.py`)
- `RegionalIntelligenceRequest`: Validates WGS84 coordinates, observation timestamp, optional basin identifier hint, and benchmark rainfall permission.
- `RegionalIntelligenceResponse`: Formats the 14 feature values, watershed exposure index, exposure grade (`LOW`, `MEDIUM`, `HIGH`, `UNCALIBRATED`), critical facilities count, and complete traceable provenance.
- `RegionalBatchRequest` / `RegionalBatchResponse`: Enforces bounded batch processing strictly capped at 250 points.
- `BasinSummaryResponse`: Exposes Pfafstetter hydrologic hierarchy metadata, drainage area, state intersections, bounding box, and operational capabilities for Indian basins.

### 3.2. Honest Population Service (`backend/app/services/india_population_service.py`)
- Checks for local presence of authentic gridded demographic GeoTIFFs.
- When uningested, returns `(None, provenance)` stating `UNINGESTED_WORLDPOP_CENSUS` under Zero-Fabrication principles.
- Wired directly into `IndiaFeaturePipelineService`.

### 3.3. Regional Watershed Intelligence Service (`backend/app/services/regional_intelligence_service.py`)
- Resolves actual river basin geometry via `IndiaSpatialService.get_river_basin()`.
- Extracts the 14 authorized features via `IndiaFeaturePipelineService`.
- Resolves authentic critical facility counts (366 for Mumbai/Mithi, explicit None elsewhere).
- Dispatches inference to `FloodModelRegistry.get_model(IntelligenceLevel.REGIONAL)`.
- Bounded batch processor rejecting requests exceeding 250 points.
- Basin summary retriever querying `hydrobasins_india.json`.

### 3.4. Regional Model Registry Integration (`backend/app/services/ml_model_registry.py`)
- Implements `RegionalBasinModel` conforming to `BaseFloodModel` protocol.
- Supported zones: `regional_ganga_basin`, `regional_brahmaputra_basin`, `regional_godavari_basin`, `regional_narmada_basin`, `regional_maharashtra`, and major HydroBASINS codes.
- Distinguishes:
  - `OPERATIONAL`: When a certified trained ML artifact is present on disk.
  - `PLANNED` / `NOT_TRAINED`: When untrained, returning `is_ready = False`, `predicted_probability = None`, and an uncalibrated watershed exposure screening index if inputs exist, or `UNCALIBRATED` if rainfall is missing.
- Rejects forbidden columns (Phase 6 hydraulic variables and Deep-zone exclusive features).

### 3.5. REST API Endpoints (`backend/app/api/v1/intelligence.py`)
- `POST /api/v1/intelligence/regional`: Single-point regional flood intelligence.
- `POST /api/v1/intelligence/regional/batch`: Bounded batch regional intelligence (max 250 points).
- `GET /api/v1/intelligence/regional/basins/{basin_id}`: Basin hydrographic summary and capabilities.

---

## 4. Verification & Testing Evidence

Dedicated test battery: `backend/tests/test_phase4_regional_intelligence.py`
- Schema compliance and contract adherence.
- 14-feature governance: Core National + Regional Expansion only.
- Strict rejection of Deep-zone feature leakage.
- Zero-fabrication: uningested population returns None, facilities return None outside Mumbai.
- Spatial boundary: points outside verified basins return `OUTSIDE_REGIONAL_COVERAGE`.
- Batch size limit: 250 accepted, 251 rejected with HTTP 400.
- Registry behavior: untrained model reports `is_ready = False`, `predicted_probability = None`.
- Phase 6 physical engine remains completely uninvoked.
