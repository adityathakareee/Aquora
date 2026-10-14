# AQUORA Phase 2E — National Flood Feature Pipeline & Multiscale Feature Generation

## 1. Overview & Objective
Phase 2E establishes the national multiscale flood feature extraction pipeline, bridging Phase 2B (India Geographic Foundation), Phase 2C (Rainfall Ingestion), and Phase 2D (SAR Evidence Ingestion) with downstream ML screening and Kaggle dataset preparation (Phase 3/7).

All feature extraction operations strictly adhere to [`ml/aquora_ml_feature_schema_v1.json`](../ml/aquora_ml_feature_schema_v1.json) (Version 1.0.0).

---

## 2. Invariant Rules & Zero Leakage

1. **Exact 20 Features & Tier Gating**:
   - **`CORE_NATIONAL` (11 features)**: `rainfall_1h_mm`, `rainfall_3h_mm`, `rainfall_6h_mm`, `rainfall_24h_mm`, `rainfall_72h_mm`, `rainfall_anomaly_index`, `elevation_m`, `slope_deg`, `distance_to_river_m`, `historical_flood_frequency`, `landcover_class`. Structurally guaranteed for all extraction queries.
   - **`REGIONAL_EXPANSION` (3 features)**: `basin_drainage_area_km2`, `soil_saturation_index`, `population_density_per_km2`. Gated to Regional Corridors and Deep Zones; evaluates to `None` for generic National queries.
   - **`DEEP_ZONE_EXCLUSIVE` (6 features)**: `flow_accumulation_cells`, `drainage_proxy_score`, `built_up_fraction`, `distance_to_road_m`, `distance_to_waterway_m`, `tide_level_m`. Strictly isolated to verified Deep Intelligence Zones (e.g. Mumbai/Mithi). Must never be required for National models.

2. **Zero-Leakage Target Label Separation**:
   - Predictor features contain strictly environmental and terrain signals.
   - Target flood labels (`flood_label ∈ {-1, 0, 1}`), Sentinel-1 SAR scene IDs, and backscatter deltas ($\Delta \gamma^0$) are isolated into separate `candidate_target` metadata.

3. **Physics Solver Isolation**:
   - Phase 6 hydrodynamic 2D solver outputs (`water_depth_m`, `flow_velocity_ms`, `modeled_depth_m`) are strictly barred from predictor feature vectors.

4. **Missing Data vs Zero Rainfall**:
   - Unavailable observations remain explicitly `None` (JSON) or `NaN` (Parquet).
   - Authentic measured zero rainfall is preserved as `0.0` with verified provenance.

---

## 3. Architecture & Service Components

- **`backend/app/services/india_feature_pipeline.py`**:
  - Class `IndiaFeaturePipelineService`: Orchestrates spatial resolution, terrain sampling via `IndiaSpatialService`, rainfall accumulation sampling via `IndiaRainfallService`, schema validation, DataFrame nullable conversions, and Parquet streaming.
- **`backend/app/schemas/features.py`**:
  - Request and response Pydantic models for single-point and bounded grid extractions.
- **`backend/app/api/v1/features.py`**:
  - `GET /api/v1/features/schema`: Metadata and tier structure.
  - `POST /api/v1/features/extract/point`: Single-point extraction.
  - `POST /api/v1/features/extract/batch`: Bounded batch grid extraction.

---

## 4. Verification & Regression Matrix

- All 10 acceptance criteria (P2E-ACC-01 through P2E-ACC-10) pass 100% in `backend/tests/test_phase2e_feature_pipeline.py`.
- Regression suites across Phase 2B, 2C, 2D, 10, 12, and 15 pass with 0 regressions.
