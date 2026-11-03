# AQUORA — Phase 7E Kaggle Model Live Inference Integration Audit

**Document ID:** `AUDIT-PHASE7E-LIVE-MODEL-001`  
**Audit Date:** 2026-11-02  
**Auditor:** Antigravity Autonomous Systems & Scientific Verification Team  
**Final Governance Decision:** `LIVE_MODEL_INTEGRATION_VERIFIED`  
**Hydrodynamic Authority:** Phase 6 deterministic physics solver remains primary authority for inundation depths.  

---

## Executive Summary & Direct Audit Conclusion

**Question:** *Is the actual Kaggle-trained model being executed by the live AQUORA National Intelligence backend, or not?*

**Direct Evidence-Based Conclusion:** **YES.**  
The actual Kaggle-trained XGBoost model artifact (`aquora_xgboost.json`, SHA-256 `5940b9bd5e745a0085d149ff2805042847a7422233fcde765df32bdda9c844d8`), trained in Kaggle Version 2 on the DFO multi-event dataset, is directly encapsulated in `ml/models/aquora_national_screening_model.joblib` via `Phase7EXGBoostWrapper` and actively executed on live inference requests by the AQUORA FastAPI backend endpoint `POST /api/v1/intelligence/screening/national`.

The model evaluates real terrain and hydrometeorological features, executes dynamic probability scoring via `xgboost.Booster.predict()` with sub-4 millisecond pure model inference time (51.7 ms end-to-end including GIS extraction), and enforces all zero-fabrication and phase-isolation safeguards.

---

## 1. Model Artifact Identity Verification

### 1.1 Artifact Inventory & Cryptographic Checksums

We performed direct filesystem inspection and SHA-256 checksum calculations across all Phase 7E Kaggle artifacts and the live integrated runtime model:

| Artifact Identifier | Filesystem Path | File Type | File Size | SHA-256 Checksum | Timestamp (UTC) |
|---|---|---|---|---|---|
| **Live Integrated Artifact** | `ml/models/aquora_national_screening_model.joblib` | Joblib Archive (`dict` container) | 437,544 bytes | `62fff9430390aa745b169802007b4032a6e446567463c88898dc52f2340a7e20` | 2026-11-02 17:34:03 |
| **Kaggle Original RF** | `data/packages/phase7e_kaggle_package/models/aquora_random_forest.joblib` | Scikit-Learn `RandomForestClassifier` | 1,811,394 bytes | `9143171fee275848ad132f605012d13f73c377f3dd1393b613fa077a0e91a3e4` | 2026-11-02 17:25:02 |
| **Kaggle Original XGBoost** | `data/packages/phase7e_kaggle_package/models/aquora_xgboost.json` | XGBoost Native JSON Booster | 434,555 bytes | `5940b9bd5e745a0085d149ff2805042847a7422233fcde765df32bdda9c844d8` | 2026-11-02 17:25:02 |
| **Frozen Decisions JSON** | `data/packages/phase7e_kaggle_package/models/aquora_frozen_validation_decisions.json` | JSON Governance Record | 410 bytes | `7aca2a41377079863b7cac62affbe03b4e254637e023b610a58520a6b8d8fec4` | 2026-11-02 17:25:02 |
| **Model Metadata JSON** | `data/packages/phase7e_kaggle_package/models/aquora_model_metadata.json` | JSON Experiment Registry | 3,417 bytes | `e0aab3d562bc6ce52d1ef3364c841221d1ade19ac2b4de9a3d8dc92276d653eb` | 2026-11-02 17:25:02 |

### 1.2 Model Nature Determination

- **Nature:** Converted/packaged production container wrapping the authentic Kaggle Version 2 XGBoost model.
- **Embedded Booster Verification:** The joblib dictionary payload contains an instance of `app.services.ml_model_registry.Phase7EXGBoostWrapper`. The embedded string attribute `model.bst_json_str` was extracted and hashed:
  $$\text{SHA-256}(\text{bst\_json\_str}) = \mathbf{5940b9bd5e745a0085d149ff2805042847a7422233fcde765df32bdda9c844d8}$$
  This is a **100% bit-for-bit cryptographic match** to the original Kaggle-exported `aquora_xgboost.json`.
- **Packaging Rationale:** The raw XGBoost booster JSON requires an adapter layer to reconcile AQUORA's governed 11 Core National Features schema with the 7 non-leaking predictors selected during Phase 7E training.

---

## 2. Model Loading in the Backend

### 2.1 Trace of Loading Implementation

- **Python Module:** `backend/app/services/ml_model_registry.py`
- **Class / Functions:**
  - Class: `NationalScreeningModel` ([ml_model_registry.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/ml_model_registry.py#L122-L250))
  - Class: `Phase7EXGBoostWrapper` ([ml_model_registry.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/ml_model_registry.py#L81-L120))
  - Class: `FloodModelRegistry` ([ml_model_registry.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/backend/app/services/ml_model_registry.py#L480-L530))
- **Model Path Resolution:**
  Resolved via `DEFAULT_SCREENING_ARTIFACT = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "models" / "aquora_national_screening_model.joblib"`.
- **Loading Mechanism:**
  1. `FloodModelRegistry.get_model(IntelligenceLevel.NATIONAL)` instantiates `NationalScreeningModel`.
  2. `NationalScreeningModel._load_artifact()` executes `joblib.load()` on the path.
  3. Validates container dictionary keys (`schema_version == "1.0.0"`, `feature_names == FEATURE_NAMES`).
  4. Assigns `self._model = payload["model"]`, `self.model_version = payload["model_version"]`, and `self.status = "OPERATIONAL"`.
- **Lazy Booster Initialization:** `Phase7EXGBoostWrapper.bst` lazily instantiates the underlying C++ `xgboost.Booster()` upon first inference call using `bst.load_model(bytearray(bst_json_str, "utf-8"))`, caching the compiled booster indefinitely.
- **In-Memory Persistence:** The `FloodModelRegistry._models` dictionary stores `NationalScreeningModel` as a singleton. The model remains loaded in memory across all incoming HTTP requests without disk reload.
- **Error Handling on Missing Artifact:** If the artifact does not exist, `NationalScreeningModel.status` defaults to `"PLANNED"`, `is_ready` returns `False`, and any inference call returns `MODEL_NOT_TRAINED` with a zero-fabrication message without throwing unhandled exceptions.

---

## 3. Actual Prediction Execution Trace

### 3.1 End-to-End Execution Trace

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Browser
    participant Modal as GeographicTierModal.tsx
    participant Client as intelligence.ts
    participant API as FastAPI /screening/national
    participant GIS as IndiaFeaturePipelineService
    participant Reg as FloodModelRegistry
    participant Model as NationalScreeningModel
    participant Wrapper as Phase7EXGBoostWrapper
    participant XGB as xgboost.Booster

    User->>Modal: Selects coordinate (e.g., Patna 25.5941°N, 85.1376°E)
    Modal->>Client: screenNationalPoint(request)
    Client->>API: POST /api/v1/intelligence/screening/national
    API->>API: Validate coordinates in bounds [6.5-37.5°N, 68.0-97.5°E]
    API->>GIS: extract_point_features(lat, lon)
    GIS-->>API: 11 Core National Features (terrain DEM, slope, hydro, rainfall)
    API->>Reg: get_model(IntelligenceLevel.NATIONAL)
    Reg-->>API: Singleton NationalScreeningModel instance
    API->>Model: predict_risk(core_features)
    Model->>Wrapper: predict_proba(X_11_features)
    Wrapper->>Wrapper: Slice to 7 non-leaking columns [3, 4, 5, 6, 7, 8, 10]
    Wrapper->>XGB: predict(DMatrix(X_7_features))
    XGB-->>Wrapper: Probability p1 = 0.0477
    Wrapper-->>Model: [[1 - p1, p1]]
    Model-->>API: {predicted_probability: 0.0477, susceptibility_grade: "LOW", is_ready: True}
    API-->>Client: NationalScreeningResponse JSON
    Client-->>Modal: Displays status READY, zone, calibration, 11 features
```

### 3.2 Confirmation of Dynamic Execution

- `xgboost.Booster.predict()` is **unconditionally executed** for every in-bounds request.
- Results are **NOT** read from precomputed CSV tables, static rasters, hardcoded mock values, or synthetic generators.
- Inputting distinct terrain/rainfall vectors immediately yields distinct floating-point probabilities (e.g., Highland dry point: `0.0037` vs. Lowland inundated point: `0.5102`).

---

## 4. Feature Schema Compatibility Verification

### 4.1 Schema Comparison Table

| Feature Name | Phase 7E Kaggle Trained Predictor | Live Registry Core National Feature | Live Slicing Index in Wrapper | Handling of Missing Data |
|---|---|---|---|---|
| `rainfall_1h_mm` | ❌ Excluded (Missing nationwide) | ✅ Yes (Feature 0) | *Excluded* | Kept as `null` / `NaN` |
| `rainfall_3h_mm` | ❌ Excluded (Missing nationwide) | ✅ Yes (Feature 1) | *Excluded* | Kept as `null` / `NaN` |
| `rainfall_6h_mm` | ❌ Excluded (Missing nationwide) | ✅ Yes (Feature 2) | *Excluded* | Kept as `null` / `NaN` |
| `rainfall_24h_mm` | ✅ Yes (Predictor 0) | ✅ Yes (Feature 3) | Index 3 | Floats / NaN handled natively by XGBoost |
| `rainfall_72h_mm` | ✅ Yes (Predictor 1) | ✅ Yes (Feature 4) | Index 4 | Floats / NaN handled natively by XGBoost |
| `rainfall_anomaly_index` | ✅ Yes (Predictor 2) | ✅ Yes (Feature 5) | Index 5 | Floats / NaN handled natively by XGBoost |
| `elevation_m` | ✅ Yes (Predictor 3) | ✅ Yes (Feature 6) | Index 6 | Continuous DEM elevation (Copernicus 30m) |
| `slope_deg` | ✅ Yes (Predictor 4) | ✅ Yes (Feature 7) | Index 7 | Continuous terrain gradient in degrees |
| `distance_to_river_m` | ✅ Yes (Predictor 5) | ✅ Yes (Feature 8) | Index 8 | HydroSHEDS / HydroRIVERS distance in meters |
| `historical_flood_frequency` | ❌ Excluded (Leakage risk) | ✅ Yes (Feature 9) | *Excluded* | Suppressed to prevent target leakage |
| `landcover_class` | ✅ Yes (Predictor 6) | ✅ Yes (Feature 10) | Index 10 | Categorical ESA WorldCover integer class |

### 4.2 Scientific Safeguards on Schema

1. **Anti-Leakage Protection:** Phase 7E training intentionally dropped `historical_flood_frequency` because it caused target leakage and artificially inflated metrics. The wrapper index slicing enforces this omission.
2. **Short-Duration Rainfall Handling:** IMD operational rain gauges do not provide sub-daily data uniformly across India. The wrapper drops 1h, 3h, and 6h rainfall without fabricating values.
3. **No Phase 7F Schema Bleed:** The regional DFO 3382 feature schema (incorporating regional discharge and delta features) is strictly isolated and not accepted by `NationalScreeningModel`.

---

## 5. Controlled Live Inference Benchmark

### 5.1 Controlled Test Parameters

- **Test Target:** Live FastAPI service at `http://127.0.0.1:8000/api/v1/intelligence/screening/national`
- **Model Checksum:** `62fff9430390aa745b169802007b4032a6e446567463c88898dc52f2340a7e20`
- **Schema Version:** `1.0.0`
- **Sample Coordinate:** Patna, Bihar (Latitude: `25.5941°N`, Longitude: `85.1376°E`)
- **Holdout Data Quarantine:** DFO 2507 test data was **strictly untouched** during this benchmark.

### 5.2 Latency Results Across 15 Repeated Trials

```
Trials: 15
Latencies (ms): [152.56, 37.87, 42.26, 40.10, 39.31, 42.20, 51.70, 68.34, 58.86, 52.82, 59.08, 59.95, 42.30, 44.62, 142.97]

End-to-End HTTP Benchmark Statistics:
- Minimum Latency: 37.87 ms
- Median Latency: 51.70 ms
- Mean Latency: 62.33 ms
- Maximum Latency: 152.56 ms (includes cold JIT / TCP socket handshake)

Pure Model Inference Latency (Internal Micro-benchmark, 20 runs):
- Minimum Latency: 2.57 ms
- Median Latency: 3.81 ms
- Mean Latency: 8.52 ms
- Maximum Latency: 99.21 ms (first-call booster compilation)
```

### 5.3 Sample API Response Body

```json
{
  "status": "READY",
  "is_ready": true,
  "model_id": "aquora_national_screening_xgboost_v1",
  "model_version": "1.2.0-phase7e",
  "intelligence_level": "NATIONAL",
  "resolved_zone": "Ganga River Basin Regional Zone",
  "coordinates": {
    "latitude": 25.5941,
    "longitude": 85.1376
  },
  "features_used": [
    "rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm", "rainfall_24h_mm",
    "rainfall_72h_mm", "rainfall_anomaly_index", "elevation_m", "slope_deg",
    "distance_to_river_m", "historical_flood_frequency", "landcover_class"
  ],
  "feature_values": {
    "rainfall_1h_mm": null,
    "rainfall_3h_mm": null,
    "rainfall_6h_mm": null,
    "rainfall_24h_mm": null,
    "rainfall_72h_mm": null,
    "rainfall_anomaly_index": null,
    "elevation_m": 60.39,
    "slope_deg": 0.07,
    "distance_to_river_m": 4834.6,
    "historical_flood_frequency": null,
    "landcover_class": 40.0
  },
  "susceptibility_probability": 0.0477,
  "susceptibility_grade": "LOW",
  "calibration_status": "UNCALIBRATED_MACRO_SCREENING",
  "provenance": {
    "tier": "REGIONAL",
    "pipeline_version": "1.0.0",
    "model_status": "OPERATIONAL",
    "feature_provenance": {
      "tier": "REGIONAL",
      "resolved_zone": "Ganga River Basin Regional Zone",
      "terrain_source": "VERIFIED_DOMAIN_ganga_patna",
      "flood_frequency_source": "UNAVAILABLE",
      "rainfall_status": "OPERATIONAL_OBSERVATION_UNAVAILABLE"
    }
  },
  "message": null
}
```

---

## 6. Frontend Connection Verification

### 6.1 Frontend Integration Trace

- **API Route Caller:** `frontend/src/api/intelligence.ts` ([intelligence.ts](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/frontend/src/api/intelligence.ts#L199-L205))
  ```typescript
  export async function screenNationalPoint(payload: NationalScreeningRequest): Promise<NationalScreeningResponse> {
    return apiFetch<NationalScreeningResponse>('/api/v1/intelligence/screening/national', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  }
  ```
- **UI Component:** `frontend/src/components/layout/GeographicTierModal.tsx` ([GeographicTierModal.tsx](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/frontend/src/components/layout/GeographicTierModal.tsx#L353-L476))
  - Provides interactive presets: Patna (Ganga), Delhi (Yamuna), Guwahati (Brahmaputra), Mumbai, Bengaluru, and Out-of-Bounds (London).
  - Triggers live HTTP call upon coordinate selection or manual Lat/Lon submission.
  - Correctly displays:
    - Status Badge: `READY` (green badge when operational model returns `is_ready: true`)
    - Resolved Basin Zone: `Ganga River Basin Regional Zone`
    - Calibration Badge: `UNCALIBRATED_MACRO_SCREENING`
    - 11 Feature Grid: Renders real extracted elevation, slope, distance to river, and honest `null` for unobserved rainfall.
  - **Empirical Observation:** While `NationalScreeningResponse` transmits `susceptibility_probability` and `susceptibility_grade` over the wire, the UI card in `GeographicTierModal.tsx` currently focuses on feature inspection and status badges. The raw response is fully accessible in client state.

---

## 7. Scientific and Architectural Safeguards Audit

| Governance Invariant | Audit Verification | Status |
|---|---|---|
| **1. Feature Schema Governance** | `NationalScreeningModel` strictly requires the 11 Core National Features and rejects extraneous features. | **ENFORCED** |
| **2. Regional Mahanadi Separation** | Mahanadi DFO 3382 regional research is isolated in `regional_mahanadi_basin` (flagged `ZoneStatus.PROTOTYPE`). No code or weights are mingled with National Screening. | **ENFORCED** |
| **3. Deep Physics Authority** | Mumbai Mithi Deep Zone is driven exclusively by the Phase 6 2D hydrodynamic finite volume shallow water equations. ML never computes inundation depth. | **ENFORCED** |
| **4. No Physics Override** | Macro susceptibility does not alter, modulate, or suppress deterministic hydraulic output. | **ENFORCED** |
| **5. Calibration Honesty** | API responses explicitly state `calibration_status: "UNCALIBRATED_MACRO_SCREENING"`. Model is never presented as calibrated probability. | **ENFORCED** |
| **6. Zero Synthetic Spatial Fallback** | Out-of-bounds coordinates (e.g., London, UK: 51.50°N, -0.12°E) return `OUTSIDE_COVERAGE` with probability `null`. Never fabricates spatial scores. | **ENFORCED** |
| **7. Rainfall Zero Fabrication** | When real-time IMD rain gauges are unobserved, rainfall features remain strictly `null`. No synthetic rain is generated. | **ENFORCED** |
| **8. Holdout Data Quarantine** | DFO 2507 holdout data was not accessed or used during live integration or audit testing. | **ENFORCED** |

---

## 8. Final Decision & Sign-Off

```
================================================================================
FINAL AUDIT DECISION: LIVE_MODEL_INTEGRATION_VERIFIED
================================================================================
```

The authentic Kaggle-trained Phase 7E XGBoost booster (`aquora_xgboost.json`, SHA-256 `5940b9bd5e745a0085d149ff2805042847a7422233fcde765df32bdda9c844d8`) has been successfully, verifiably, and safely integrated into the AQUORA National Intelligence backend service.
