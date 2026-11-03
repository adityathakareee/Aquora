# AQUORA — Urban Flood Intelligence & Emergency Response Platform

> **See the flood before it becomes a crisis.**

Aquora is an end-to-end urban flood intelligence platform engineered for high-resolution hydraulic forecasting, flood-aware critical access routing, satellite evidence corroboration, and real-time emergency responder decision support.

---

## 🌊 What Aquora Does

Aquora integrates physical hydrology, remote sensing, spatial analytics, and machine learning to give municipal response teams early visibility into urban flood dynamics. It converts raw satellite imagery, elevation models, meteorological feeds, and terrain topography into actionable exposure timelines, route safety windows, and prioritized asset protection strategies.

---

## 🎯 Core Capabilities (Eight User-Facing Views)

1. **Overview (`/`)**: Executive situational dashboard displaying city-wide flood risk index, active alerts, operational facility status, live rainfall telemetry, and key performance indicators.
2. **Future Flood Map (`/flood-map`)**: 0 to +180 minute dynamic inundation forecast powered by the Phase 6 deterministic physical flood engine with time-step playback controls (+30m, +60m, +90m, +120m, +150m, +180m).
3. **Travel Window (`/travel-window`)**: Safe departure and arrival time window analysis for emergency transport corridors based on cell-level flood arrival timing and water depth thresholds.
4. **Critical Access (`/critical-access`)**: Monitoring status for 366 verified Mumbai hospitals, fire stations, and substations, identifying primary access road submergence and routing to alternate functional facilities.
5. **Protect the City (`/protect-city`)**: Priority intervention site optimization tool recommending structural drainage interventions, mobile pump deployments, and barrier placements.
6. **Ground Truth (`/ground-truth`)**: Community and field responder evidence submission portal matching photo/field observations against Digital Twin spatial slices with automated corroboration logic.
7. **Simulator (`/simulator`)**: Scenario planning engine for stress-testing urban catchments under synthetic or historical extreme rainfall hydrographs and tide level combinations.
8. **Alert Center (`/alerts`)**: Multi-tiered operational alert management hub tracking physical simulation warnings, statistical risk signals, and SAR evidence corroboration.

---

## 🔬 Scientific Architecture & Authority Hierarchy

Aquora enforces a strict multi-tier authority hierarchy for scientific computations:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    AUTHORITATIVE PHYSICAL SOURCE                        │
│             Phase 6 Deterministic Physical Flow & Drainage Engine       │
│       (Copernicus DEM 30m + D8 Routing + Drainage Coupling Solver)      │
│     *Mass conservation error <= 1e-4 m³; not a 2D Saint-Venant solver*  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SECONDARY STATISTICAL SIGNAL                         │
│                    XGBoost Risk Classifier                              │
│         (PROTOTYPE_ONLY | NOT_CALIBRATED — Evaluated on E07)            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CORROBORATING SATELLITE EVIDENCE                      │
│                  Sentinel-1 GRD VV+VH SAR Bitemporal Pair               │
│                (Historical Flood Event Evidence E02–E07)                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Multiscale Geographic Intelligence Hierarchy

AQUORA structures flood intelligence into three strictly governed operational tiers:

1. **Level 1: NATIONAL (India Subcontinent — Macro Screening)**:
   - Evaluates the 11 Core National Predictors (`rainfall_1h_mm` to `rainfall_72h_mm`, `rainfall_anomaly_index`, `elevation_m`, `slope_deg`, `distance_to_river_m`, `historical_flood_frequency`, `landcover_class`).
   - Macro screening returns `MODEL_NOT_TRAINED` with `calibration_status: UNCALIBRATED_MACRO_SCREENING`.
   - Out-of-bounds rejection: coordinates outside India are rejected with `OUTSIDE_COVERAGE`.

2. **Level 2: REGIONAL (Major River Basins — Meso Intelligence & Research)**:
   - Operates across HydroBASINS Level 5/6 river basins: **Ganga Basin**, **Brahmaputra Basin**, **Godavari Basin**, and **Narmada Basin**.
   - **Mahanadi River Basin (DFO 3382 Research Study — Phase 7F Stage 5)**:
     - Integrated experimental regional research zone covering 27 Level 8 HydroBASINS sub-basins within the DFO 3382 flood extent (15 Train, 6 Validation, 6 Test).
     - Provides 5 interactive research layers: Sub-basin Partitions, HydroSHEDS River Network, Sentinel/WorldCover Land/Water Mask, DFO 3382 Remote-Sensing Observations, and Experimental Diagnostic Ranking Scores.
     - **Scientific Robustness Finding**: Stage 4.1 audit proved optical margin coupling—66.8% of DFO 3382 positive flood points lie within permanent water body transition zones (`dry_fraction < 0.70`). On clean terrestrial terrain away from permanent water, PR-AUC drops to 0.0192 (baseline prevalence 0.0157). Surfaced across UI as relative diagnostic ranking only.
     - **Alert Decoupling**: Strictly governed as `PROTOTYPE_ONLY / NOT_CALIBRATED / NOT_FOR_PUBLIC_ALERTS`. Experimental ML rankings never emit or trigger municipal emergency alerts.
   - Evaluates 14 hydrologic and terrain features; calculates the Watershed Exposure Index (WEI).
   - **Zero-Fabrication Invariant**: Uningested regional attributes (e.g., population density, critical facilities count outside pilot zones) strictly return `None (uningested)` rather than synthetic numbers.
   - Non-basin points (e.g. marine coordinates) are rejected with `OUTSIDE_REGIONAL_COVERAGE`.

3. **Level 3: DEEP ZONE (Mumbai · Mithi Catchment — Micro Physics)**:
   - Active strictly in **Mumbai / Mithi River Catchment** (`EPSG:32643`).
   - Samples 30m Copernicus DEM rasters (elevation, slope, aspect, flow accumulation, drainage proxy) and cross-references 366 verified Mumbai critical infrastructure facilities.
   - **Strict Deep-Zone Isolation**: Requests outside Mumbai (e.g., Patna or Delhi) strictly return `OUTSIDE_DEEP_ZONE_COVERAGE` with `point_in_zone: false` and **zero silent fallback to Mumbai**.

---

## 🤖 Kaggle Readiness & ML Training Decision

- **Governance Gate Decision**: `BLOCKED_BY_GROUND_TRUTH` (Zero-synthetic-labels policy strictly enforced).
- **Audit Findings**:
  - The 6,876 records in the India Flood Inventory (IFI v3) are administrative disaster incident summaries (fatalities, affected districts, dates).
  - They lack 30-meter continuous empirical inundation boundaries and verified non-flood dry-negative background pixels.
  - Converting district incident records into binary labels causes catastrophic false-positive inflation.
  - Sentinel-1 SAR contains radar shadow, corner reflection, and 6–12 day revisit gaps.
  - Deterministic physics outputs are synthetic simulation predictions, not empirical ground truth.
- **Supervised Model Training**: **Zero supervised models trained or evaluated**.
- **Kaggle Deliverables**:
  - Reusable Kaggle-Ready Notebook: [`notebooks/aquora_national_screening_kaggle.ipynb`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/notebooks/aquora_national_screening_kaggle.ipynb) (v4 schema, spatial `GroupKFold` by basin, automated Ground Truth Gate).
  - Kaggle Dataset Manifest: [`data/processed/phase7/ml/phase7_kaggle_dataset_manifest.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ml/phase7_kaggle_dataset_manifest.json).
  - Preparation CLI: [`scripts/prepare_kaggle_dataset.py`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/scripts/prepare_kaggle_dataset.py).
- **Existing Model Status**: `PROTOTYPE_ONLY` & `NOT_CALIBRATED` (`aquora_xgboost_prototype.joblib`). Provides relative risk rankings only; never overrides physical hydraulic depth.

---

## 🛰️ Real Data Sources & Provenance

Aquora is built exclusively on real acquired global and regional datasets:

- **Copernicus DEM GLO-30**: 30 m resolution digital elevation model (`Copernicus_DSM_COG_10_N19_00_E072_00.tif`).
- **NASA GPM IMERG Final V07B**: 30-minute half-hourly precipitation records for historical Mumbai flood events (E01–E07).
- **ESA WorldCover 2021 v200**: 10 m resolution global land cover classification map (`N18E072`).
- **OpenStreetMap & MCGM Facilities**: 359 verified OSM critical infrastructure facilities + 7 Municipal Corporation of Greater Mumbai (MCGM) healthcare nodes.
- **Sentinel-1 SAR Evidence**: Official Sentinel-1 GRD dual-polarization VV+VH bitemporal radar acquisitions for historical events E02–E07.
- **UHSLC Tide Gauge Observations**: High-resolution sea level observations from Mumbai Port (Station h846a).

---

## 📁 Repository Structure

```text
Aquora/
├── backend/                  # FastAPI async monolith API service & test suite
│   ├── app/                  # Router, controllers, services, providers, models, schemas
│   ├── data/models/          # Trained XGBoost model artifact (.joblib) & metadata (.json)
│   └── tests/                # 476 pytest unit, integration, and E2E test suites
├── frontend/                 # React 18 + TypeScript + Vite + Leaflet web application
│   ├── src/                  # App components, layout, features, map overlays, stores
│   └── public/               # Static web assets & icons
├── engines/                  # Pure hydrologic, physical solver, and drainage computation modules
├── geospatial/               # Spatial reference system & raster handling utilities
├── ml/                       # Machine learning feature pipelines and calibration modules
├── data/                     # Data documentation, manifests, and verified facility datasets
│   ├── manifests/            # Data provenance manifests and dataset specifications
│   └── raw/facilities/       # 366 verified Mumbai critical infrastructure facilities
├── scripts/                  # Data acquisition, dataset building, training & audit scripts
├── docs/                     # Comprehensive architecture and scientific phase documentation
├── .env.example              # Safe environment variable configuration template
├── .gitignore                # Production-hardened Git ignore rules
├── .dockerignore              # Container image build exclusion rules
├── docker-compose.yml        # Docker orchestration setup (PostGIS, Redis, Backend, Frontend)
└── README.md                 # Project root documentation
```

---

## 💻 Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ / npm 9+
- PostgreSQL 15+ with PostGIS 3.4+ extension
- Redis 7+

### 2. Backend Installation
```bash
# Navigate to backend directory
cd backend

# Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend development server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend Installation
```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

App runs at: [http://127.0.0.1:5175](http://127.0.0.1:5175)

---

## 🧪 Testing & Verification

Run the automated test suites to verify system integrity across all tiers:

```powershell
# 1. Run Phase 7F Stage 5 System-Wide Integration Suite (10 tests, ~4s)
# Validates health, geographic hierarchy, Mahanadi experiments, sub-basins, layer manifest, physics authority & quarantine
& backend\.venv\Scripts\pytest.exe backend\tests\test_phase7f_stage5_integration.py -v

# 2. Run Consolidated Regression Suite Across All Phases (63 tests, ~12s)
& backend\.venv\Scripts\pytest.exe backend\tests\test_phase7f_stage5_integration.py backend\tests\test_consolidation2_e2e_integration.py backend\tests\test_phase3_national_screening_model.py backend\tests\test_phase4_regional_intelligence.py backend\tests\test_phase5_deep_intelligence.py -q

# 3. Run Focused End-to-End Integration Suite (7 tests, ~10s)
# Validates tiers, capabilities, out-of-bounds rejection, and Kaggle artifacts
& backend\.venv\Scripts\pytest.exe backend\tests\test_consolidation2_e2e_integration.py -v

# 4. Run Multiscale Intelligence Suites (59 tests, ~16s)
# National Screening (9 tests), Regional Intelligence (26 tests), Deep Intelligence (24 tests)
& backend\.venv\Scripts\pytest.exe backend\tests\test_phase3_national_screening_model.py backend\tests\test_phase4_regional_intelligence.py backend\tests\test_phase5_deep_intelligence.py -q

# 5. Run National Rainfall Archive & Provenance Suites (52 tests, ~4s)
& backend\.venv\Scripts\pytest.exe backend\tests\test_phase6c2g21_national_rainfall.py backend\tests\test_phase6c2g20_national_rainfall.py backend\tests\test_phase6c2g18_extraction_integrity.py backend\tests\test_phase6c2g9_ground_truth.py backend\tests\test_phase6c2g8_ml_readiness.py backend\tests\test_phase6c2g1_reconciliation.py -q

# 6. Run Core 8-Page Full Application E2E Suite (7 tests, ~60s)
& backend\.venv\Scripts\pytest.exe backend\tests\test_phase9_step9_end_to_end.py -v

# 7. Run Kaggle ML Readiness Audit & Manifest Generator
& backend\.venv\Scripts\python.exe scripts\prepare_kaggle_dataset.py

# 8. Run Frontend Production Type-Check and Bundle Build
cd frontend
npm run build
```

---

## 📚 Key Documentation & Audit Reports

- **Final System Integration Report**: [`docs/FINAL_SYSTEM_INTEGRATION_REPORT.md`](docs/FINAL_SYSTEM_INTEGRATION_REPORT.md) — Comprehensive architecture, route registry, test matrices, and scientific governance summary.
- **Application Run & Demo Guide**: [`docs/AQUORA_RUN_AND_DEMO_GUIDE.md`](docs/AQUORA_RUN_AND_DEMO_GUIDE.md) — Step-by-step local startup commands, multi-tier navigation walkthrough, and verification endpoints.
- **Phase 7F Stage 5 Manifest**: [`data/manifests/phase7f_stage5_integration_manifest.yaml`](data/manifests/phase7f_stage5_integration_manifest.yaml) — Cryptographic hashes, artifact inventory, and scientific compliance audit.
- **Stage 4.1 Ablation & Scientific Review**: [`docs/phase7/PHASE_7F_STAGE4_1_SCIENTIFIC_REVIEW.md`](docs/phase7/PHASE_7F_STAGE4_1_SCIENTIFIC_REVIEW.md) — Land/water margin coupling audit and spatial generalization evaluation.

---

## 🐳 Docker Quickstart

To build and run the complete Aquora platform in containers:

```bash
# Copy example environment configuration
cp .env.example .env

# Build and start all services (PostGIS, Redis, Backend, Frontend)
docker compose up --build -d
```

Service Endpoints:
- **Frontend SPA**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **API Liveness**: [http://localhost:8000/api/v1/health/live](http://localhost:8000/api/v1/health/live)
- **API Readiness**: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)
- **OpenAPI Interactive Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ⚠️ Known Limitations & Scope

1. **Hydraulic Solver Formulations**: The Phase 6 physical solver uses a deterministic 2D cellular surface routing model with rainfall-runoff excess, depression storage, D8 terrain-constrained routing, and municipal drainage loss coupling (mass conservation error &le; 1e-4 m³). It is a simplified physical model and **not a full 2D Saint-Venant shallow-water hydrodynamic solver**.
2. **Model Calibration & Kaggle Training Gate**: The prototype XGBoost model is explicitly uncalibrated (`NOT_CALIBRATED` | `PROTOTYPE_ONLY`). Scores represent relative risk rankings, not frequentist flood probabilities, and must never supersede physical hydraulic depths. Supervised national screening model training is strictly `BLOCKED_BY_GROUND_TRUTH` until authentic empirical inundation masks become available.
3. **Missing Data Semantics**: Missing rainfall observations, unacquired SAR satellite passes, null feature values, or zero model output **never imply that no flood exists**. Unextracted features outside ingested pilot areas strictly return `None (uningested)` rather than synthetic zeroes.
4. **Geographic Hierarchy Boundaries**: Mumbai / Mithi River Catchment is the **only operational Deep Intelligence Zone**. Requests outside Mumbai (e.g. Patna or Delhi) are strictly rejected with `OUTSIDE_DEEP_ZONE_COVERAGE` with zero silent fallback to Mumbai. Macro and meso screening cover India and major river basins (Ganga, Brahmaputra, Godavari, Narmada) respectively.
