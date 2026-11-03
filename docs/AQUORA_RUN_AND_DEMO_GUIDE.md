# AQUORA 2.0 — Run & Demonstration Guide
**Urban & Regional Flood Intelligence Platform**  
**Version:** 0.6.0-phase7f  
**Status:** `SYSTEM_INTEGRATION_COMPLETE`

---

## 1. Overview & System Architecture

AQUORA is a multiscale flood intelligence platform for India bridging three graduated tiers of capability:

1. **Level 1: National Macro Screening** — Broad 11-feature macro susceptibility screening across the Indian subcontinent.
2. **Level 2: Regional Watershed Intelligence** — HydroBASINS Level 5/6 watershed exposure index using 14 authorized features, and regional research study extents (Mahanadi Basin DFO 3382).
3. **Level 3: Deep Catchment Digital Twin** — Verified high-resolution 2D hydrodynamic simulation, urban drainage proxy, and routing for 366 critical facilities in Mumbai Mithi.

> [!IMPORTANT]
> **Primary Authority Invariant:** The Phase 6 2D Hydrodynamic Physics Solver ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py)) is the primary operational flood authority. Regional ML exploration models serve diagnostic research purposes and are strictly barred from triggering emergency alerts.

---

## 2. Prerequisites & Installation

### Backend Setup (FastAPI / Python 3.11+)

```powershell
# 1. From workspace root, install backend requirements
pip install -r backend/requirements.txt

# 2. Start FastAPI development server
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

The backend server starts at `http://localhost:8000`. Swagger API documentation is available at `http://localhost:8000/docs`.

### Frontend Setup (Vite / React / TypeScript)

```powershell
# 1. Navigate to frontend directory and install dependencies
cd frontend
npm install

# 2. Start Vite development server
npm run dev
```

The frontend application opens at `http://localhost:5173`.

---

## 3. Step-by-Step Demonstration Script

### Walkthrough Step 1: Foundational Deep Zone (Mumbai Mithi)
1. Open `http://localhost:5173/` in your browser.
2. **Hero Section:** Displays the Mumbai skyline banner ("Safer Mumbai Together").
3. **4 KPI Cards:** Real-time metrics from the latest digital twin simulation:
   - Next significant change (+60 min peak)
   - Area at risk (1.84 km², max depth 0.42 m)
   - Essential access at risk (Sion Hospital primary route affected)
   - Suggested action (Intervention recommendation: CST Road alternate route)
4. **Flood Situation Map:** Click **Play** on the timeline strip to watch the 0–180 min simulation progression. The 2D mass-conserving water surface dynamically rises to peak (+60m) and recedes (+180m).
5. **Critical Facility Inspection:** Navigate to the **Facility Access** tab to inspect reachability and flood thresholds across 366 verified Mumbai hospitals, fire stations, and emergency shelters.

---

### Walkthrough Step 2: Geographic Tier & Screening Navigator
1. On the Overview page, click **"Explore Geographic Tiers & Screening"** on the navigator bar.
2. The modal presents four tabs:
   - **Tiers Overview:** Shows the hierarchy of National, Regional, and Deep zones with active indicators.
   - **National Screening Demo:** Interactive tool testing the 11 Core National Features.
   - **Regional Watershed Demo:** Evaluates 14 features across HydroBASINS river basins.
   - **Deep Intelligence:** Verifies 30m Copernicus DEM and local drainage loss proxy.
3. Test the **Presets** in the National tab:
   - Click **Patna (Ganga)**: Successfully extracts 11 features.
   - Click **Test Out of Bounds (London)**: Returns `OUTSIDE_COVERAGE` without silent fallback.

---

### Walkthrough Step 3: Regional Research Exploration (Mahanadi River Basin)
1. In the **Geographic Tiers** modal, click the button:  
   `Mahanadi Basin · Phase 7F Research (PROTOTYPE)`
2. The application dynamically switches scope to `Mahanadi Basin · Odisha (DFO 3382 Study)`.
3. **Regional Research Overview Page:**
   - **Research Header:** Displays `PROTOTYPE_ONLY` and `NOT_FOR_PUBLIC_ALERTS` badges.
   - **Prominent Warning Box:** Explains that the Phase 6 physics engine remains the primary operational flood authority, and ML scores are diagnostic spatial rankings only.
   - **4 Regional Story KPIs:**
     - Basin Drainage Extent: `141,589 km²`
     - Spatial Partitions: `27 Sub-basins (15 Train / 6 Val / 6 Test)`
     - Optical Margin Coupling: `66.8%` of labels located in mixed water margins (`dry_fraction < 0.70`)
     - Rainfall Feed: `100% NaN` (honest missingness, zero synthetic imputation)
   - **Stage 4.1 Scientific Robustness Review:** Compares the 13-feature full model vs 12-feature ablated model, demonstrating the terrestrial margin collapse (PR-AUC 0.0192 on dry cells).
4. Click **"Explore Basin Map Layers"** (or switch to the **Flood Map** tab):
   - Map automatically centers at Mahanadi Delta `[20.45, 85.85]`, Zoom 8.
   - **Interactive Layer Toggles:**
     - `[x]` **Sub-basins (27 Lev08):** Color-coded by partition (15 Train [Blue], 6 Val [Amber], 6 Test [Emerald]).
     - `[x]` **HydroRIVERS Network:** Displays main stem and distributaries (Devi, Daya, Bhargavi).
     - `[x]` **DFO 3382 Inundation (MODIS):** Displays satellite-observed optical flood surfaces.
     - `[ ]` **Water Margin Uncertainty:** Toggles mixed water boundary interface zones.
     - `[ ]` **ML Ranking Scores:** Toggles diagnostic relative rankings.
   - **Floating Legend & Diagnostics Panels:** Summarizes zero-leakage spatial blocking and quarantine of holdout DFO 2507.
5. Click **"Return to Mumbai Deep Zone"** to seamlessly return to the Mumbai operational digital twin.

---

## 4. Key API Endpoints & cURL Examples

### 1. Geographic Capabilities Lookup
```bash
# Query Mahanadi River Basin capability
curl -X GET "http://localhost:8000/api/v1/intelligence/capabilities?location_code=BASIN-MAHANADI"

# Query Odisha State capability
curl -X GET "http://localhost:8000/api/v1/intelligence/capabilities?location_code=IN-OD"

# Query Mumbai Deep Zone capability
curl -X GET "http://localhost:8000/api/v1/intelligence/capabilities?location_code=IN-MH-MUMBAI"
```

### 2. Mahanadi Regional Research Endpoints
```bash
# Get experimental results, ablation metrics, and spatial independence audit
curl -X GET "http://localhost:8000/api/v1/intelligence/regional/mahanadi/experiments"

# Get 27 Level 8 HydroBASINS sub-basins with TRAIN/VAL/TEST partition tags
curl -X GET "http://localhost:8000/api/v1/intelligence/regional/mahanadi/subbasins"

# Get regional layer catalog and governance manifest
curl -X GET "http://localhost:8000/api/v1/intelligence/regional/mahanadi/layers"
```

### 3. Basin Hydrographic Summary
```bash
# Get HydroBASINS canonical summary for Mahanadi
curl -X GET "http://localhost:8000/api/v1/intelligence/regional/basins/BASIN-MAHANADI"
```

### 4. Regional Point Evaluation (14 Features)
```bash
# Evaluate point in Cuttack delta (honest None for facilities, zero synthetic rainfall)
curl -X POST "http://localhost:8000/api/v1/intelligence/regional" \
  -H "Content-Type: application/json" \
  -d '{"latitude": 20.46, "longitude": 85.88, "allow_benchmark_rainfall": false}'
```

---

## 5. Automated Verification & Testing

To run the complete automated test suite verifying all 63 regression tests:

```powershell
# Run consolidated test suite
& "C:\Program Files\Python312\python.exe" -m pytest `
  backend/tests/test_phase4_regional_intelligence.py `
  backend/tests/test_phase7f_stage4_experiments.py `
  backend/tests/test_phase7f_stage4_1_robustness.py `
  backend/tests/test_phase7f_stage5_integration.py `
  backend/tests/test_phase7f_stage3_dataset.py
```

Expected output: `63 passed in ~12s (100%)`.

To verify frontend TypeScript type safety and build:

```powershell
cd frontend
npx tsc
npx vite build
```

Expected output: `✓ built in ~12s` with zero errors.
