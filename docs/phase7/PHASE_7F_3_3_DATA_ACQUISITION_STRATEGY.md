# AQUORA — PHASE 7F.3.3: DATA ACQUISITION STRATEGY & EVENT FEASIBILITY PLANNING
### Multi-Basin Expansion Roadmap, Physiographic Regime Analysis & Evidence-Based Event Feasibility

**Document Version:** `2.0.0-phase7f33-scientific-review-correction`  
**Phase:** Phase 7F.3.3 Data Acquisition Strategy & Event Feasibility Planning (Corrected & Validated)  
**Task Type:** READ-ONLY RESEARCH & FEASIBILITY PLANNING (Zero source-code changes, zero dataset modifications, zero data downloads, zero model training, zero Git commits/pushes)  
**Authoritative Governance Status:** `EXPERIMENTAL_EVALUATION_ONLY`  
**Operational Status:** `PROTOTYPE_ONLY` / `NOT_CALIBRATED` / `NOT_FOR_PUBLIC_ALERTS`  
**Primary Hydrodynamic Authority:** Phase 6 Deterministic Hydrodynamic Physics Engine ([engines/flood/](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/))  
**Date:** 2026-10-31  

---

## 1. Executive Summary

Following the existing data inventory in [`docs/phase7/PHASE_7F_3_1_EXISTING_DATA_INVENTORY.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_1_EXISTING_DATA_INVENTORY.md) and the pixel-level spatial compatibility audit in [`docs/phase7/PHASE_7F_3_2_EVENT_COMPATIBILITY_AUDIT.md`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7F_3_2_EVENT_COMPATIBILITY_AUDIT.md), this document establishes the **Data Acquisition Strategy and Event Feasibility Plan** for expanding AQUORA's experimental flood-event dataset.

The existing AQUORA machine learning foundation evaluated in Phase 7E relies on four historical events with severe structural constraints:
1. **DFO 2507** (North Bihar / Kosi, 2004) is strictly quarantined as an `ALREADY_INSPECTED_HOLDOUT` and cannot be accessed for model tuning, feature engineering, or threshold calibration.
2. **DFO 2935** (Upper Godavari / Maharashtra, 2006) captures only **355 flood cells** (0.069% of the regional disaster), providing insufficient sample support for independent training.
3. **DFO 3372** (Upper Brahmaputra / Assam, 2008) exists in Phase 7E only as an **artificially balanced 50/50 sample** (2,500 flood / 2,500 dry), which distorted the decision cutoff ($\tau = 0.01$) and cannot serve as natural-prevalence validation data without sampling corrections.
4. **DFO 4499** (Lower Ganga / West Bengal, 2017) captures 11,152 flood cells (16.58% of regional extent) but represents only a single physiographic regime (Gangetic deltaic plain).

### Core Methodological Revisions Adopted in this Version:
* **No Premature Readiness Labels**: No event is classified as "acquisition-ready", "training-ready", or "validation-ready". All candidates are assigned evidence-based statuses such as `PROMISING_SOURCE_PREFLIGHT`, `CANDIDATE_PENDING_VERIFICATION`, `PARTIALLY_SUPPORTED`, or `BLOCKED_BY_DATA_GAPS`.
* **Sentinel-1 SAR Ground-Truth Qualification**: Raw 10m Sentinel-1 SAR imagery is strictly distinguished from validated flood masks. Events requiring SAR (Kerala 2018, DFO 4309) are classified as **`SAR_LABEL_DEVELOPMENT_CANDIDATE`** pending the implementation of calibrated change-detection pipelines, pre-event baselines, and independent validation.
* **Event-Specific GPM IMERG Granule Verification**: General product availability on NASA GES DISC is distinguished from verified event-specific granule availability. Because individual granules have not been downloaded or inspected, sub-daily precipitation (`1h`, `3h`, `6h`) remains **STRICTLY UNAVAILABLE**.
* **Aspirational Evaluation Splitting**: Leave-One-Physiographic-Zone-Out (LOPZO) is recognized as an aspirational research design that **cannot be finalized with a small number of events**. Robust geographic generalization cannot be claimed from sparse candidate pools.
* **Refined Acceptance Gates**: The 10 acceptance gates have been updated to replace arbitrary requirements (such as requiring casualties) with scientifically defensible, provisional criteria (e.g., CWC gauge stage levels exceeding danger marks, core vs. buffer DEM coverage).

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               REVISED PHASE 7F.3.3 CANDIDATE FEASIBILITY STATUS                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
  Candidate ID  Basin / State          Physiographic Regime        Candidate Ground Truth   Evidence-Based Status
  ────────────────────────────────────────────────────────────────────────────────────────
  DFO 3382      Mahanadi Delta, OD     East Coast Deltaic / Marine GFD v1.4 (MODIS 250m)    PROMISING_SOURCE_PREFLIGHT
  DFO 3551      Krishna Basin, AP/KA   Semi-Arid Deccan Plateau    GFD v1.4 (MODIS 250m)    PROMISING_SOURCE_PREFLIGHT
  DFO 4309      Coromandel Coast, TN   Coastal Urban / NE Monsoon  GFD 250m + S-1 SAR (10m) CANDIDATE_PENDING_VERIFICATION
                                                                                            (SAR_LABEL_DEVELOPMENT)
  DFO 4179      Jhelum Valley, J&K     Himalayan Intermontane      GFD v1.4 (MODIS 250m)    PARTIALLY_SUPPORTED
  Kerala 2018   Periyar/Pamba, KL      Western Ghats Escarpment    Sentinel-1 SAR (10m)     CANDIDATE_PENDING_VERIFICATION
                                                                                            (SAR_LABEL_DEVELOPMENT)
  DFO 2049/2931 Narmada/Tapi, GJ       Western Arid Estuary        GFD v1.4 (MODIS 250m)    PARTIALLY_SUPPORTED
  DFO 4507      Middle Ganga/Terai, UP Gangetic Alluvial Aggrading GFD v1.4 (MODIS 250m)    PARTIALLY_SUPPORTED
  ────────────────────────────────────────────────────────────────────────────────────────
  DFO 2507      North Bihar / Kosi, BR Dynamic Alluvial Fan        GFD v1.4 (MODIS 250m)    ALREADY_INSPECTED_HOLDOUT
                                                                                            (PERMANENT QUARANTINE)
  ────────────────────────────────────────────────────────────────────────────────────────
```

---

## 2. Existing Data Constraints Carried Forward

Every finding from Phase 7F.3.1 and 7F.3.2 is formally integrated as a non-negotiable constraint on data acquisition and planning:

1. **Study-Box vs. Regional Flood Coverage**:
   * Isolated $1^\circ \times 1^\circ$ DEM tiles capture only **0.069% to 16.58%** of regional disaster flood pixels. Future acquisition must not assume a single DEM tile represents the entire flood event. Full-event polygons require multi-tile contiguous DEM mosaics.
2. **Native Resolution Distortion**:
   * Global Flood Database (GFD v1.4) labels have a native spatial resolution of **$\approx 250\text{ m}$**. Resampling or point-sampling 250m labels at 30m grid intervals generates $\approx 65.4$ redundant observations per pixel and creates severe sub-grid elevation contamination. Future architectures must either aggregate 30m terrain to 250m or acquire authentic high-resolution ground truth (Sentinel-1 SAR at 10m/30m).
3. **Sub-Daily Precipitation Deficit**:
   * Half-hourly GPM IMERG Final Run data is **0.0% present on disk** for the four historical events. Daily CHIRPS files cover only 3-day windows for the existing events.
4. **Isolated Tile HAND Infeasibility**:
   * Height Above Nearest Drainage (HAND) cannot be computed on isolated $1^\circ \times 1^\circ$ DEM tiles without generating severe flow-truncation artifacts at tile boundaries and sink-looping in flat alluvial fans. Conservative **NO-GO for local HAND calculation remains strictly in effect**.
5. **Validation Set Balance Distortion**:
   * The existing Phase 7E validation set (DFO 3372) is artificially balanced (50.0% flood / 50.0% dry) and must **never be described or utilized as naturally imbalanced validation data**.
6. **Strict Holdout Quarantine of DFO 2507**:
   * DFO 2507 remains designated as an `ALREADY_INSPECTED_HOLDOUT`. It is permanently quarantined from feature selection, training, hyperparameter optimization, threshold tuning, and calibration fitting.

---

## 3. Candidate Flood-Event Inventory & Evidence Traceability

From the 91 quality-checked Indian flood events cataloged in [`data/processed/phase7/ground_truth/gfd_india_events_catalog.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json) and the 6,876 historical records in [`data/raw/phase7/ground_truth/india_flood_inventory_v3.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/india_flood_inventory_v3.csv), seven candidate events have been identified.

For every candidate, evidence is strictly categorized into:
* **Locally Verified Repository Evidence**: Data physically on disk or preflight-checked with cryptographic hashes.
* **External Provider Documentation**: Published literature, portal documentation, and URLs.
* **General Product-Level Availability**: Theoretical temporal/spatial coverage of the sensor/archive.
* **Unverified Event-Specific Data**: Dimensions that have not yet been downloaded, extracted, or inspected.

---

### Detailed Event Profiles:

#### Candidate 1: DFO 3382 — Mahanadi Delta / Odisha (September 2008)
* **Administrative & Geographic Focus**: Mahanadi Delta (Cuttack, Puri, Kendrapara, Jagatsinghpur, Khordha districts, Odisha). Centroid: $20.95^\circ\text{N}, 84.41^\circ\text{E}$.
* **Physiographic Regime**: East Coast Deltaic & Alluvial Plain (Sub-humid tropical).
* **Disaster Window**: 2008-09-22 to 2008-09-29. Provisional onset: 2008-09-22. Peak stage: 2008-09-24 to 2008-09-26.
* **Physical Mechanism**: Extreme monsoonal depression over Chhattisgarh and western Odisha combined with heavy reservoir discharge from Hirakud Dam ($> 1.5\text{ million cusecs}$ peak outflow), causing widespread embankment breaches in the downstream delta network.
* **Evidence Traceability**:
  * *Locally Verified*: Documented in [`gfd_india_events_catalog.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json); GCS ZIP existence verified HTTP 200 (`DFO_3382_From_20080922_to_20080929.zip`, 39,644,622 bytes) in [Phase 7C Preflight Report](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/docs/phase7/PHASE_7C_MULTI_EVENT_ACQUISITION_REPORT.md#L45).
  * *External Documentation*: Central Water Commission (CWC) Flood Inundation Reports 2008; Odisha State Disaster Management Authority (OSDMA); Dartmouth Masterlist (`dfo_masterlist_20190418.zip`).
  * *General Product Availability*: GFD v1.4 GeoTIFF on GCS (`gs://gfd_v1_4`); daily CHIRPS 0.05° on UCSB CHC archive.
  * *Unverified Dimensions*: Copernicus DEM multi-tile mosaic coverage for the entire delta footprint; valid optical cloud-free fraction during peak discharge; sub-daily IMERG (pre-GPM launch, retro-archive uninspected); actual rainfall values and valid-pixel coverage.
* **Status**: `PROMISING_SOURCE_PREFLIGHT`

#### Candidate 2: DFO 3551 — Krishna & Tungabhadra Basins / Andhra Pradesh & Karnataka (October 2009)
* **Administrative & Geographic Focus**: Krishna & Tungabhadra confluence (Kurnool, Mahabubnagar, Guntur, Krishna districts, Andhra Pradesh/Telangana). Centroid: $15.71^\circ\text{N}, 78.23^\circ\text{E}$.
* **Physiographic Regime**: Semi-Arid Deccan Plateau (Hard-rock basaltic and granitic incised valleys).
* **Disaster Window**: 2009-09-25 to 2009-10-12. Provisional onset: 2009-09-25. Peak deluge: 2009-10-02 to 2009-10-04.
* **Physical Mechanism**: Historical 100-year cloudburst in upper catchments ($> 400\text{ mm}$ in 48h) generating $2.55\text{ million cusecs}$ peak inflow into Srisailam Dam (design capacity $1.36\text{ million cusecs}$), inundating Kurnool municipal corporation and riparian lowlands.
* **Evidence Traceability**:
  * *Locally Verified*: Documented in [`gfd_india_events_catalog.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json); GCS ZIP verified HTTP 200 (`DFO_3551_From_20090925_to_20091012.zip`, 27,086,981 bytes); peak day daily CHIRPS file exists locally: [`chirps-v2.0.2009.10.02.tif.gz`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/rainfall/chirps/daily/chirps-v2.0.2009.10.02.tif.gz) (2,785,152 bytes).
  * *External Documentation*: Government of Andhra Pradesh Disaster Management Department White Paper (2009); CWC Srisailam Hydrological Records; UEI-IMD-FL-2009-0012 in [`india_flood_inventory_v3.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/india_flood_inventory_v3.csv).
  * *General Product Availability*: GFD v1.4 GeoTIFF on GCS; CHIRPS daily archive; Copernicus DEM GLO-30 AWS Open Data.
  * *Unverified Dimensions*: Antecedent CHIRPS daily files for $t_{-1}$ (`2009.10.01`) and $t_{-2}$ (`2009.09.30`) are absent from local disk; IMERG sub-daily retro-archive uninspected; full raster episodic flood cell counts uncalculated.
* **Status**: `PROMISING_SOURCE_PREFLIGHT`

#### Candidate 3: DFO 4309 — Coromandel Coast / Chennai Deluge / Tamil Nadu (November–December 2015)
* **Administrative & Geographic Focus**: Adyar, Cooum, and Palar River basins (Chennai, Kanchipuram, Tiruvallur, Cuddalore districts, Tamil Nadu). Centroid: $11.83^\circ\text{N}, 78.86^\circ\text{E}$.
* **Physiographic Regime**: Southeastern Coastal Plain / Urban & Peri-Urban Coastal Lowlands (Northeast Monsoon regime).
* **Disaster Window**: 2015-11-10 to 2015-12-04. Provisional onset: 2015-11-10. Peak deluge: 2015-12-01 to 2015-12-02.
* **Physical Mechanism**: Extreme Northeast Monsoon depression with coastal convergence during an intense El Niño year. Chembarambakkam reservoir catchment received $494\text{ mm}$ in 24 hours, forcing emergency gate releases into the Adyar River that breached embankments across metropolitan Chennai.
* **Evidence Traceability**:
  * *Locally Verified*: Documented in [`gfd_india_events_catalog.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json); peak day daily CHIRPS exists locally: [`chirps-v2.0.2015.12.01.tif.gz`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/rainfall/chirps/daily/chirps-v2.0.2015.12.01.tif.gz) (2,752,949 bytes).
  * *External Documentation*: Narasimhan et al. (2016, *Nature Climate Change*); IMD Special Report on Chennai Deluge 2015; CWC Gauge Reports; International Charter Space and Major Disasters records.
  * *General Product Availability*: GFD v1.4 GeoTIFF (`DFO_4309_From_20151110_to_20151204.zip`, 93,202 km²); NASA GPM IMERG Final Run V07B half-hourly data on NASA GES DISC ([GPM_3IMERGHH](https://disc.gsfc.nasa.gov/)); Copernicus Sentinel-1A C-SAR GRD imagery on Copernicus Open Access Hub / Alaska Satellite Facility.
  * *Unverified Dimensions*: Raw Sentinel-1 SAR imagery exists in public archives but has **NOT been converted to a validated flood mask**; MODIS optical imagery suffered severe cloud obscuration during peak rainfall; antecedent CHIRPS dates (`2015.11.29`, `2015.11.30`) missing from local disk; event-specific IMERG granules uninspected.
* **Status**: `CANDIDATE_PENDING_VERIFICATION` (Designated as **`SAR_LABEL_DEVELOPMENT_CANDIDATE`**)

#### Candidate 4: DFO 4179 — Jhelum Valley / Kashmir Deluge (September 2014)
* **Administrative & Geographic Focus**: Jhelum River Valley (Srinagar, Anantnag, Pulwama, Baramulla, Jammu & Kashmir). Centroid: $33.94^\circ\text{N}, 75.34^\circ\text{E}$.
* **Physiographic Regime**: High-Altitude Himalayan Intermontane Valley (1,580 m valley floor to 4,000 m mountain walls).
* **Disaster Window**: 2014-09-01 to 2014-10-11. Provisional onset: 2014-09-01. Peak stage: 2014-09-04 to 2014-09-07.
* **Physical Mechanism**: Interaction between a late-season monsoonal low-pressure system and a mid-latitude Western Disturbance, yielding $> 300\text{ mm}$ in 72h over steep glaciated catchments. Jhelum discharge exceeded carrying capacity ($70,000\text{ cusecs}$ vs. $35,000\text{ cusecs}$ channel capacity), causing massive dike breaches and inundating Srinagar under 1–4 meters of water for $> 10\text{ days}$.
* **Evidence Traceability**:
  * *Locally Verified*: Documented in [`gfd_india_events_catalog.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json); peak day daily CHIRPS exists locally: [`chirps-v2.0.2014.09.04.tif.gz`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/rainfall/chirps/daily/chirps-v2.0.2014.09.04.tif.gz) (2,779,833 bytes).
  * *External Documentation*: J&K State Disaster Management Authority Official Report (2014); CWC Gauge Records at Ram Munshi Bagh; Romshoo et al. (2015, *Geocarto International*).
  * *General Product Availability*: GFD v1.4 GeoTIFF on GCS (`DFO_4179_From_20140901_to_20141011.zip`, 253,687 km²); Copernicus DEM GLO-30 AWS Open Data; GPM IMERG V07B daily/half-hourly on NASA GES DISC (post-Feb 2014 launch).
  * *Unverified Dimensions*: High mountain terrain causes severe radar shadow/layover and optical cloud shadows; antecedent CHIRPS dates (`2014.09.02`, `2014.09.03`) missing on local disk; IMERG half-hourly granules uninspected.
* **Status**: `PARTIALLY_SUPPORTED`

#### Candidate 5: DFO 2049 / DFO 2931 — Lower Narmada & Tapi / Gujarat (September 2002 / August 2006)
* **Administrative & Geographic Focus**: Lower Tapi and Narmada estuaries (Surat, Bharuch, Narmada, Navsari districts, Gujarat). Centroid: $21.54^\circ\text{N}, 73.22^\circ\text{E}$.
* **Physiographic Regime**: Western Arid / Semi-Arid Alluvial Coastal Plain & Tidal Estuary.
* **Disaster Window**: 
  * DFO 2049: 2002-09-03 to 2002-09-06. Provisional onset: 2002-09-03.
  * DFO 2931: 2006-07-24 to 2006-08-22. Peak: 2006-08-07 to 2006-08-10.
* **Physical Mechanism**: Intense catchment-wide rainfall over Madhya Pradesh and Maharashtra draining into the Tapi River; Ukai Dam reached critical capacity, requiring emergency release of $900,000\text{ cusecs}$ into a channel capacity of $300,000\text{ cusecs}$, submerging 80% of Surat city under 2 to 4 meters of water.
* **Evidence Traceability**:
  * *Locally Verified*: Documented in [`gfd_india_events_catalog.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json); daily CHIRPS exists locally for 2006 peak: [`chirps-v2.0.2006.08.07.tif.gz`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/rainfall/chirps/daily/chirps-v2.0.2006.08.07.tif.gz) (3,046,750 bytes).
  * *External Documentation*: Surat Municipal Corporation Flood Report (2006); CWC Tapi Basin Hydrology Records; Gujarat SDMA; UEI-IMD-FL-2006-0044.
  * *General Product Availability*: GFD v1.4 GeoTIFFs on GCS; CHIRPS daily archive.
  * *Unverified Dimensions*: High optical cloud cover during the 2006 peak; complex estuarine and tidal water interactions; Copernicus DEM tiles unverified for full estuarine floodplain.
* **Status**: `PARTIALLY_SUPPORTED`

#### Candidate 6: DFO 4507 — Middle Ganga & Eastern Alluvial Plains (August 2017)
* **Administrative & Geographic Focus**: Terai foothills and Middle Ganga tributaries (Araria, Kishanganj, Purnia, Katihar, Madhepura, Pashchim Champaran, Bihar & Eastern UP). Centroid: $28.17^\circ\text{N}, 79.08^\circ\text{E}$.
* **Physiographic Regime**: Sub-Himalayan Piedmont & Alluvial Aggradational Plain (Terai zone).
* **Disaster Window**: 2017-08-10 to 2017-08-26. Provisional onset: 2017-08-10. Peak stage: 2017-08-14 to 2017-08-18.
* **Physical Mechanism**: Monsoon trough shifted to Himalayan foothills, causing catastrophic rainfall over southern Nepal catchments that drained into Mahananda, Kankai, and Gandak rivers, triggering rapid flash floods across the flat Terai plain.
* **Evidence Traceability**:
  * *Locally Verified*: Documented in [`gfd_india_events_catalog.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json); 26 matching records in [`india_flood_inventory_v3.csv`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/ground_truth/india_flood_inventory_v3.csv).
  * *External Documentation*: Bihar SDMA Official Report (2017); CWC Flood Bulletins.
  * *General Product Availability*: GFD v1.4 GeoTIFF on GCS (`DFO_4507_From_20170810_to_20170826.zip`, 421,575 km²); NASA GPM IMERG V07B daily/half-hourly on NASA GES DISC.
  * *Unverified Dimensions*: Daily CHIRPS files for August 2017 missing on local disk (only July 2017 exists for DFO 4499); extreme optical cloud cover during monsoon peak in Terai; IMERG half-hourly granules uninspected.
* **Status**: `PARTIALLY_SUPPORTED`

#### Candidate 7: Great Kerala Floods (August 2018) — Multi-Sensor SAR Candidate
* **Administrative & Geographic Focus**: Periyar, Pamba, Chalakudy, and Bharathapuzha river basins (Ernakulam, Idukki, Thrissur, Alappuzha, Pathanamthitta districts, Kerala). Centroid: $10.15^\circ\text{N}, 76.50^\circ\text{E}$.
* **Physiographic Regime**: Steep Western Ghats Escarpment to Tropical Coastal Plain/Backwater Lagoons.
* **Disaster Window**: 2018-08-08 to 2018-08-20. Provisional onset: 2018-08-08. Peak deluge: 2018-08-15 to 2018-08-17.
* **Physical Mechanism**: Extreme Southwest Monsoon cloudburst (Kerala received $2,347\text{ mm}$ from June 1 to August 19, 42% above normal; 800 mm in 72h over high ranges). 35 major dams opened simultaneously, routing flash discharge down narrow bedrock gorges into densely populated coastal floodplains.
* **Evidence Traceability**:
  * *Locally Verified*: Documented in [`gfd_india_events_catalog.json`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/processed/phase7/ground_truth/gfd_india_events_catalog.json) (entry DFO 4665); peak day daily CHIRPS exists locally: [`chirps-v2.0.2018.08.16.tif.gz`](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/data/raw/phase7/rainfall/chirps/daily/chirps-v2.0.2018.08.16.tif.gz) (2,683,169 bytes).
  * *External Documentation*: Central Water Commission Study on Kerala Floods 2018; International Charter: Space and Major Disasters Activation (Call ID: 671 / Activation 584 on August 16, 2018); ISRO National Remote Sensing Centre (NRSC) Bhuvan flood maps.
  * *General Product Availability*: Sentinel-1 C-SAR GRD (10m) multi-temporal imagery on Copernicus Open Access Hub / ASF; NASA GPM IMERG Final Run V07B half-hourly on NASA GES DISC; Copernicus DEM GLO-30 AWS Open Data.
  * *Unverified Dimensions*: Raw Sentinel-1 SAR imagery is **NOT a validated flood mask**; requires complete backscatter change-detection processing, pre-event dry baseline coregistration, and permanent-water masking; antecedent CHIRPS dates (`2018.08.14`, `2018.08.15`) missing on local disk; IMERG 30-min granules uninspected.
* **Status**: `CANDIDATE_PENDING_VERIFICATION` (Designated as **`SAR_LABEL_DEVELOPMENT_CANDIDATE`**)

---

## 4. Candidate Event Compatibility Matrix

| Evaluation Dimension | Candidate 1: DFO 3382 (Mahanadi 2008) | Candidate 2: DFO 3551 (Krishna 2009) | Candidate 3: DFO 4309 (Chennai 2015) | Candidate 4: DFO 4179 (Kashmir 2014) | Candidate 5: DFO 2931 (Surat 2006) | Candidate 6: DFO 4507 (Terai/Bihar 2017) | Candidate 7: Kerala Floods (2018 SAR) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A. Basin & State** | Mahanadi, Odisha | Krishna/Tungabhadra, AP/KA | Adyar/Cooum, Tamil Nadu | Jhelum, Jammu & Kashmir | Tapi, Gujarat | Middle Ganga, Bihar/UP | Periyar/Pamba, Kerala |
| **A. Primary Dates** | 2008-09-22 to 2008-09-29 | 2009-09-25 to 2009-10-12 | 2015-11-10 to 2015-12-04 | 2014-09-01 to 2014-10-11 | 2006-07-24 to 2006-08-22 | 2017-08-10 to 2017-08-26 | 2018-08-08 to 2018-08-20 |
| **A. Provisional Peak**| 2008-09-24 to 2008-09-26 | 2009-10-02 to 2009-10-04 | 2015-12-01 to 2015-12-02 | 2014-09-04 to 2014-09-07 | 2006-08-07 to 2006-08-10 | 2017-08-14 to 2017-08-18 | 2018-08-15 to 2018-08-17 |
| **A. Corroboration** | CWC, OSDMA, 2400 dead | CWC, AP SDMA, 303 dead | IMD, CWC, 180 dead | J&K SDMA, 300 dead | CWC, Surat MC, 248 dead | Bihar SDMA, 253 dead | CWC, Charter 584, 483 dead |
| **B. Ground Truth Source**| GFD v1.4 MODIS (250m) | GFD v1.4 MODIS (250m) | GFD 250m + Raw S-1 SAR | GFD v1.4 MODIS (250m) | GFD v1.4 MODIS (250m) | GFD v1.4 MODIS (250m) | Raw Sentinel-1 SAR (10m) |
| **B. Native Resolution**| $\approx 250\text{ m}$ ($0.002246^\circ$)| $\approx 250\text{ m}$ ($0.002246^\circ$)| 250m (MODIS) / 10m (SAR) | $\approx 250\text{ m}$ ($0.002246^\circ$)| $\approx 250\text{ m}$ ($0.002246^\circ$)| $\approx 250\text{ m}$ ($0.002246^\circ$)| $10\text{ m} \times 10\text{ m}$ (SAR) |
| **B. SAR Flood Mask?**  | Not Applicable (Pre-2014)| Not Applicable (Pre-2014)| **UNPROCESSED / PENDING**| Not Applicable (Pre-2014)| Not Applicable (Pre-2014)| Not Applicable | **UNPROCESSED / PENDING**|
| **B. Cloud Occlusion**  | High cloud during peak  | Moderate optical clarity| Optical blocked; SAR clean| Cloud/shadow in mountains| High cloud during peak  | Extreme cloud during peak| Zero cloud impact in SAR |
| **C. DEM Source & Res** | Copernicus GLO-30 (30m)  | Copernicus GLO-30 (30m)  | Copernicus GLO-30 (30m)  | Copernicus GLO-30 (30m)  | Copernicus GLO-30 (30m)  | Copernicus GLO-30 (30m)  | Copernicus GLO-30 (30m)  |
| **C. Topographic Relief**| Deltaic plain ($< 50\text{ m}$)| Plateau valley ($250–500\text{ m}$)| Coastal plain ($< 30\text{ m}$)| Intermontane ($1500–4000\text{ m}$)| Estuarine lowland ($< 25\text{ m}$)| Alluvial plain ($40–100\text{ m}$)| Steep escarpment ($0–2600\text{ m}$)|
| **D. CHIRPS Daily Window**| Unacquired (UCSB server)| Peak on disk; $t_{-1,-2}$ gap| Peak on disk; $t_{-1,-2}$ gap| Peak on disk; $t_{-1,-2}$ gap| Peak on disk; $t_{-1,-2}$ gap| Unacquired (UCSB server)| Peak on disk; $t_{-1,-2}$ gap|
| **D. GPM IMERG Sub-Daily**| Pre-GPM (Uninspected)   | Pre-GPM (Uninspected)   | Granules Uninspected    | Granules Uninspected    | Pre-GPM (Uninspected)   | Granules Uninspected    | Granules Uninspected    |
| **E. Drainage / HAND**  | Flat delta looping (NO-GO)| Hard-rock incised (Feasible)| Urban barriers (NO-GO)  | Mountain valley (Feasible)| Tidal estuary (NO-GO)   | Flat Terai looping (NO-GO)| Steep bedrock (Feasible) |
| **F. Land-Cover Match** | MODIS 2008 / ESA 2021 gap| MODIS 2009 / ESA 2021 gap| MODIS 2015 / ESA 2020 match| MODIS 2014 / ESA 2020 match| MODIS 2006 / ESA 2021 gap| MODIS 2017 / ESA 2021 match| MODIS 2018 / ESA 2020 match|
| **G. Physiographic Regime**| East Coast Deltaic     | Deccan Hard-Rock Valley | SE Coastal Urban Plain  | Himalayan Intermontane  | Western Arid Estuary    | Gangetic Aggrading Plain| Western Ghats Escarpment |
| **Revised Status**      | `PROMISING_SOURCE_PREFLIGHT`| `PROMISING_SOURCE_PREFLIGHT`| `CANDIDATE_PENDING_VERIFICATION`| `PARTIALLY_SUPPORTED` | `PARTIALLY_SUPPORTED` | `PARTIALLY_SUPPORTED` | `CANDIDATE_PENDING_VERIFICATION`|

---

## 5. Sentinel-1 SAR Ground-Truth Qualification Framework

For events where Sentinel-1 SAR data is proposed (Candidate 3: DFO 4309 Chennai 2015, Candidate 7: Great Kerala Floods 2018), **raw SAR imagery must never be conflated with validated ground-truth labels**.

### 5.1 Why 10m Raw SAR Imagery is Not Ground Truth:
1. **Surface Roughness & Wind**: Wind-induced capillary waves roughen open water surfaces, increasing backscatter and causing false-negative omissions (water appearing like land).
2. **Urban Corner Reflections**: Dense building geometries create double-bounce corner reflections, masking standing water on inundated city streets.
3. **Radar Shadow & Layover**: In steep terrain (Kerala Western Ghats) or high-rise urban clusters (Chennai), radar shadow casts dark patches identical to specular water reflection, causing false-positive commissions.

### 5.2 Mandatory Five-Stage SAR Label-Development Pipeline:
Before any SAR acquisition can be admitted as ground truth, the following workflow must be executed, documented, and independently validated:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   MANDATORY FIVE-STAGE SAR LABEL-DEVELOPMENT PIPELINE                  │
└────────────────────────────────────────────────────────────────────────────────────────┘

  STAGE 1: PRE-EVENT & EVENT DUAL-ACQUISITION MATCHING
  ├── Event Image: Acquired during peak inundation window (e.g. Kerala Aug 16, 2018).
  └── Baseline Image: Acquired during identical dry season orbital pass (same relative
      orbit track, same looking angle, same polarization mode: VV + VH).

  STAGE 2: RADIOMETRIC CALIBRATION & TERRAIN FLATTENING
  ├── Radiometric calibration to sigma-nought (σ°) or gamma-nought (γ°).
  ├── Range-Doppler terrain correction using Copernicus DEM GLO-30.
  └── Speckle filtering using Refined Lee or Multitemporal Box filter (5×5 window).

  STAGE 3: CHANGE DETECTION & RATIO THRESHOLDING
  ├── Compute backscatter difference ratio: Δσ° = σ°_event - σ°_baseline (in dB).
  └── Determine optimal inundation threshold (e.g. Δσ° ≤ -3.0 dB) using Kittler-Illingworth
      or Otsu bimodal histogram thresholding on cross-polarized VH channel.

  STAGE 4: GEOMORPHIC & WATER MASKING GATES
  ├── Mask terrain slopes > 5° using Copernicus DEM to eliminate shadow artifacts.
  └── Mask permanent water bodies using JRC Global Surface Water (jrc_perm_water == 0).

  STAGE 5: INDEPENDENT ACCURACY ASSESSMENT
  ├── Quantitatively validate flood mask against high-resolution cloud-free optical patches
  │   (Sentinel-2 MSI or PlanetScope) or CWC ground telemetry.
  └── Require Overall Accuracy ≥ 85% and Cohen's Kappa ≥ 0.70 before label acceptance.
```

Until this pipeline is executed and validated, both Chennai 2015 and Kerala 2018 are classified strictly as **`CANDIDATE_PENDING_VERIFICATION` (SAR_LABEL_DEVELOPMENT)**.

---

## 6. Event-Specific GPM IMERG Verification Protocol

General product availability on the NASA GES DISC portal does **NOT** equal verified event-specific granule availability. 

### 6.1 Status of Sub-Daily Rainfall:
* **Current Physical Reality**: Across all historical events evaluated in AQUORA, **zero half-hourly IMERG granules exist on local disk**.
* **Governance Invariant**: Sub-daily precipitation features (`rainfall_1h_mm`, `rainfall_3h_mm`, `rainfall_6h_mm`) remain **STRICTLY UNAVAILABLE** and will not be populated by heuristics or uninspected files.

### 6.2 Event-Specific Verification Windows:

| Event ID | Event Region | Critical Inundation Window | Target IMERG Half-Hourly Window | Pre-GPM Launch Era? | Verification Status on Disk |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **DFO 3382** | Mahanadi Delta, Odisha | 2008-09-22 to 2008-09-29 | 2008-09-20 00:00 to 2008-09-29 23:30 | **YES** (TRMM Era Retro-archive) | **0.0% Present (Uninspected)** |
| **DFO 3551** | Krishna Basin, AP/KA | 2009-09-25 to 2009-10-12 | 2009-09-23 00:00 to 2009-10-06 23:30 | **YES** (TRMM Era Retro-archive) | **0.0% Present (Uninspected)** |
| **DFO 4309** | Chennai / Coromandel, TN | 2015-11-10 to 2015-12-04 | 2015-11-28 00:00 to 2015-12-03 23:30 | NO (GPM Operational Era) | **0.0% Present (Uninspected)** |
| **DFO 4179** | Jhelum Valley, J&K | 2014-09-01 to 2014-10-11 | 2014-09-01 00:00 to 2014-09-08 23:30 | NO (GPM Operational Era) | **0.0% Present (Uninspected)** |
| **Kerala 2018** | Western Ghats, Kerala | 2018-08-08 to 2018-08-20 | 2018-08-12 00:00 to 2018-08-19 23:30 | NO (GPM Operational Era) | **0.0% Present (Uninspected)** |
| **DFO 2049** | Narmada/Tapi, Gujarat | 2002-09-03 to 2002-09-06 | 2002-09-01 00:00 to 2002-09-07 23:30 | **YES** (TRMM Era Retro-archive) | **0.0% Present (Uninspected)** |
| **DFO 2931** | Tapi / Surat, Gujarat | 2006-07-24 to 2006-08-22 | 2006-08-05 00:00 to 2006-08-11 23:30 | **YES** (TRMM Era Retro-archive) | **0.0% Present (Uninspected)** |
| **DFO 4507** | Middle Ganga, Bihar/UP | 2017-08-10 to 2017-08-26 | 2017-08-10 00:00 to 2017-08-19 23:30 | NO (GPM Operational Era) | **0.0% Present (Uninspected)** |

### 6.3 Mandatory IMERG Granule Verification Criteria:
Before any IMERG dataset is accepted into future pre-flight staging, the following dimensions must be confirmed:
1. **Exact Timestamp Synchronization**: Half-hourly timestamps (`UTC`) must bracket the documented meteorological cloudburst prior to river cresting.
2. **Spatial Pixel Validity**: Valid precipitation rate ($\text{mm/hr}$) must cover 100% of the candidate basin's bounding box without missing data or sensor-blind swathes.
3. **NoData / Sensor Flag Verification**: The `precipitationQualityIndex` and `HQprecipitation` fields must be verified to ensure observations are derived from calibrated passive microwave radiometers rather than infrared morphing interpolation.

---

## 7. Data-Source Priority Matrix

| Data Source | Data Type | Spatial Resolution | Temporal Resolution | Historical Archive Scope | Access Portal & License | Role in AQUORA | Known Limitations | Local Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Global Flood Database (GFD v1.4)** | Satellite Inundation GeoTIFF | $\approx 250\text{ m}$ ($0.002246^\circ$) | Event composite (3-day standard) | 2000–2018 (913 global events) | Google Cloud Storage (`gs://gfd_v1_4`), CC-BY-NC-4.0 | Primary macroscopic ground truth for pre-2015 historical events. | 250m resolution; cannot resolve small channels; optical cloud gaps. | Verified locally: 4 events on disk; 87 cataloged. |
| **Copernicus Sentinel-1 SAR** | C-Band SAR Microwave GRD | $10\text{ m} \times 10\text{ m}$ | 6 to 12 day revisit | October 2014 to present | Copernicus Open Access / Earthdata, CC-BY-4.0 | Authentic high-resolution ground truth; cloud-penetrating. | Post-2014 only; requires multi-stage change detection and filtering. | Verified available in public archive; unacquired for candidates. |
| **Copernicus DEM GLO-30** | Digital Elevation Model (DSM) | $30\text{ m}$ ($0.000278^\circ$) | Static (2011–2015 radar baseline) | Current release | AWS Open Data (`copernicus-dem-30m`), Public Domain | Authoritative terrain elevation, slope, aspect, curvature. | Isolated $1^\circ$ tiles produce boundary clipping for hydrology. | Verified locally: 4 tiles on disk ($3600 \times 3600$, 100% valid). |
| **MERIT Hydro & HAND** | Hydrography & Normalized Height | $90\text{ m}$ ($0.000833^\circ$) | Static | Current release | Yamazaki Lab / GEE, Research Open | Continental precomputed HAND without tile-edge truncation. | Coarser than 30m DEM; small urban ditches omitted. | Publicly documented; unacquired. |
| **HydroRIVERS v1.0** | Vector Stream Network | Polylines ($> 10\text{ km}^2$ basin) | Static | Current release | HydroSHEDS portal, CC-BY-4.0 | River centerlines, flow distance, stream order, upstream area. | Omits small streams $< 10\text{ km}^2$; rural distributary channels absent. | Absent locally: `data/raw/` empty; pilot snippets only. |
| **CHIRPS v2.0 Daily** | Gridded Gauge-Satellite Rain | $0.05^\circ$ ($\approx 5.5\text{ km}$) | Daily (24h accumulation) | 1981 to present | UC Santa Barbara CHC, Public Domain | Continuous antecedent rainfall ($24\text{h}$, $72\text{h}$) across all years. | Daily only (sub-daily absent); 5.5 km grid smooths cloudbursts. | Verified locally: 35 daily files on disk. |
| **NASA GPM IMERG Final Run** | Satellite Microwave-Infrared | $0.1^\circ$ ($\approx 10\text{ km}$) | Half-hourly (30 min) | June 2000 to present (V07B) | NASA GES DISC (`GPM_3IMERGHH`), NASA Open Data | Research-quality sub-daily rainfall intensity (`1h`, `3h`, `6h`). | 10 km grid is much coarser than floodplains; 3.5-month latency. | Documented; 0 sub-daily files on disk for candidates. |
| **ESA WorldCover 10m** | Multispectral Land Cover | $10\text{ m}$ | Annual (2020, 2021) | 2020, 2021 | ESA / VITO, CC-BY-4.0 | High-resolution land-cover classes for modern events (2015+). | Significant temporal gap for events before 2015 ($> 10\text{ years}$). | Verified locally: 4 tiles on disk ($36000 \times 36000$). |
| **MODIS Land Cover (MCD12Q1)**| Annual Multispectral Land Cover | $500\text{ m}$ | Annual (2001–present) | 2001 to present | NASA LP DAAC, Public Domain | Contemporaneous annual land cover for historical events (2001–2014). | $500\text{ m}$ resolution is coarser than $10\text{ m}$ WorldCover. | Publicly documented; unacquired. |

---

## 8. Strengthened Event-Level Validation Design

### 8.1 Event-Level and Basin-Level Isolation as Primary Principle:
To prevent severe spatial autocorrelation leakage, **event-level and basin-level separation is the non-negotiable primary evaluation objective**:
* Random pixel-level splitting is formally prohibited.
* Models must never be evaluated on pixels drawn from the same flood event or contiguous catchment used for training.

### 8.2 LOPZO as an Aspirational Roadmap:
* **Scientific Qualification**: Leave-One-Physiographic-Zone-Out (LOPZO) cross-validation is an **aspirational research concept**.
* **Constraint**: LOPZO **cannot be finalized with only 4 to 7 candidate events**. If a physiographic regime (e.g. Himalayan Intermontane or Western Ghats Escarpment) contains only a single historical event, holding it out tests extreme out-of-distribution transferability, not statistical variance within that regime.
* **Prerequisite**: True LOPZO validation requires at least 2 to 3 independent flood events per physiographic zone before generalizable claims can be supported.

### 8.3 Preservation of Existing Validation & Holdout Truths:
1. **DFO 3372 Balanced Status**:
   The existing Phase 7E validation sample of DFO 3372 is artificially balanced (2,500 flood / 2,500 dry, 50.0% balance). Describing it as naturally imbalanced validation data is **empirically false**.
   * Probability calibration (Platt scaling, Isotonic regression) and operational threshold tuning ($\tau$) must **NOT** be executed on this balanced sample.
   * Calibration requires a representative natural-prevalence evaluation population (e.g., preserving the authentic $18.04\%$ natural prevalence of the native DEM footprint or applying inverse sampling weights).
2. **DFO 2507 Strict Quarantine**:
   DFO 2507 remains permanently classified as an `ALREADY_INSPECTED_HOLDOUT`. It is strictly barred from model selection, feature engineering, and calibration fitting.

---

## 9. Refined Ten Minimum Acceptance Gates

Before any candidate flood event can be admitted into an AQUORA supervised dataset, it must satisfy all 10 explicit pass/fail gates. All numerical thresholds are formally designated as **PROVISIONAL SCREENING THRESHOLDS** until validated against production data:

| Gate | Assessment Dimension | Refined Minimum Acceptance Criterion | Scientific Rationale |
| :---: | :--- | :--- | :--- |
| **Gate 1** | **Event Identity & Provenance** | Documented DFO ID, begin/end dates, state, basin, and centroid coordinates verified against authoritative catalogs. | Eliminates synthetic, ambiguous, or uncorroborated event records. |
| **Gate 2** | **Physical Corroboration** | Documented in CWC gauge hydrographs (water levels exceeding danger marks), official State Disaster Management Authority bulletins, or IMD reports. *Casualties or displacement are NOT required*. | Validates that a genuine physical inundation event occurred regardless of human population exposure or successful evacuations. |
| **Gate 3** | **Native Ground-Truth Quality** | Verified multi-band satellite raster (GFD v1.4 GeoTIFF) or raw Sentinel-1 SAR GRD with documented acquisition timestamps. | Enforces authentic remote sensing observation as the sole target authority. |
| **Gate 4** | **Optical Quality & Cloud Gate** | *Optical*: Clear view percentage $\text{clear\_perc} \ge 0.70$ (*provisional threshold*). Pixels below threshold quarantined as `UNOBSERVED_CLOUD`.<br>*SAR*: Validated backscatter change detection ($\Delta \sigma^0$) with slope shadow masking. | Prevents inferring dry labels from unobserved cloud-covered terrain while ensuring SAR labels are fully processed. |
| **Gate 5** | **Permanent Water Exclusion** | JRC Global Surface Water mask applied; permanent water pixels quarantined ($\text{jrc\_perm\_water} == 0$, Pekel et al. 2016). | Prevents classifiers from confusing perennial rivers, lakes, and reservoirs with episodic floods. |
| **Gate 6** | **Natural Prevalence Tracking** | Authentic event-level natural flood prevalence logged in metadata. Balanced subsampling prohibited for evaluation splits. | Prevents false-alarm collapse caused by tuning decision cutoffs on balanced data. |
| **Gate 7** | **Measurable DEM Coverage** | Copernicus DEM GLO-30 must cover **$\ge 95\%$ of the core contiguous flood polygon** (*provisional threshold*) **PLUS a minimum $5\text{ km}$ topographic buffer** (or extending to local ridge divides). | Distinguishes core inundation coverage from valley-wall containment, preventing artificial edge gradient spikes. |
| **Gate 8** | **Rainfall Window & Spatial Validity** | Continuous 3-day antecedent rainfall sequence ($t_{-2}, t_{-1}, t_0$) present on local disk with **0% missing data over the catchment bounding box**. File existence alone is insufficient. | Ensures valid calculation of $24\text{h}$ and $72\text{h}$ cumulative precipitation forcing with verified spatial coverage. |
| **Gate 9** | **Land-Cover Temporal Relevance** | Land cover observed within 5 years of event date (*provisional screening threshold*), OR geomorphic and land-cover stability physically verified. | Prevents geomorphic invalidation caused by multi-decade river avulsions while permitting stable bedrock basins. |
| **Gate 10** | **Cryptographic Provenance & Manifest** | SHA-256 checksums, byte sizes, source URLs, and band specifications logged in versioned acquisition manifests. | Guarantees complete reproducibility and immutable data provenance across all phases. |

---

## 10. Drainage and HAND Feasibility Requirements

The proposal to compute Height Above Nearest Drainage (HAND) directly from isolated DEM tiles remains a **STRICT CONSERVATIVE NO-GO**.

### 10.1 Preconditions for HAND Feasibility:
HAND computation will only become feasible when all three hydrological engineering criteria are met simultaneously:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                   MANDATORY THREE-PILLAR HAND FEASIBILITY GATE                         │
└────────────────────────────────────────────────────────────────────────────────────────┘

  PILLAR 1: WATERSHED-SCALE DEM EXTENT
  ├── Elevation raster must cover the entire upstream contributing watershed.
  └── External river inflows (e.g., Kosi from Nepal, Godavari from Western Ghats)
      must have non-zero accumulated drainage area at the domain boundary.

  PILLAR 2: HYDRO-ENFORCED RIVER VECTOR NETWORK
  ├── Seamless vector stream networks (HydroRIVERS v1.0 or Survey of India hydrography)
  │   must be burned into the digital elevation model.
  └── Flat alluvial plains (slopes < 0.1°) must have enforced downstream flow direction
      to prevent priority-flood algorithm looping and artificial sink creation.

  PILLAR 3: CONTINENTAL PRECOMPUTED BENCHMARK
  ├── Alternatively, precomputed continental HAND products (such as MERIT-Hydro 90m HAND,
  │   Yamazaki et al. 2019) must be acquired directly.
  └── Precomputed HAND eliminates local boundary truncation and guarantees continental
      hydrological consistency without local GIS conditioning errors.
```

Until either Pillar 1+2 or Pillar 3 is physically acquired and verified, **AQUORA must not compute or deploy HAND features**.

---

## 11. Recommended Next Phase & Prerequisites

### Proposed Next Phase: Phase 7F.3.4 — Data Acquisition Pre-Flight & Staging Protocol
Phase 7F.3.4 will prepare the exact, reproducible pre-flight scripts, checksum manifests, and storage quotas required for candidate data acquisition **without executing any downloads**.

### Prerequisites Before Acquisition Can Begin:
1. **Executive Review & Sign-Off**: The corrected Phase 7F.3.3 Data Acquisition Strategy report must be reviewed and accepted.
2. **Storage Allocation Verification**: Ensure adequate disk storage is confirmed for candidate DEM mosaics and multi-event GFD rasters.
3. **NASA Earthdata Credentials**: Verify access credentials for NASA GES DISC to enable retrieval of GPM IMERG Final Run V07B half-hourly granules.
4. **Acquisition Manifest Staging**: Formalize all target URLs, candidate IDs, bounding boxes, and expected SHA-256 hashes in `data/manifests/phase7f_candidate_acquisition_manifest.yaml`.
5. **Preservation of Existing Pipelines**: Ensure that Phase 7A–7E datasets, models, manifests, and test suites remain untouched and uncommitted.

---

## 12. Governance, Limitations, and Outstanding Uncertainties

### 12.1 Authoritative Governance Invariants:
1. **Deterministic Hydrodynamic Supremacy**:
   The Phase 6 deterministic hydrodynamic physics engine ([engines/flood/solver.py](file:///c:/Users/thaka/OneDrive/Desktop/Hackathon/AQUORA/Aquoraa/engines/flood/solver.py#L33-L60)) remains the **sole authorized operational authority** for physical flood depths, velocities, hazard classifications, and emergency routing. Machine learning models remain strictly categorized as `EXPERIMENTAL_EVALUATION_ONLY`.
2. **Deep Zone Invariant**:
   Mumbai / Mithi (`deep_mumbai_mithi`) remains the ONLY active Deep Intelligence Zone. National and regional screening models must never overwrite or replace hydrodynamic physics simulations.
3. **Permanent Quarantine of DFO 2507**:
   DFO 2507 (North Bihar / Kosi, 2004) is an `ALREADY_INSPECTED_HOLDOUT`. It is strictly forbidden to use DFO 2507 for training, feature extraction, threshold tuning, or calibration. It will serve solely as an immutable, unadjusted historical benchmark once future architectures are finalized.

### 12.2 Outstanding Uncertainties:
1. **Monsoon Optical Cloud Gaps in GFD**:
   In high-intensity monsoon events (e.g. DFO 3382 Odisha, DFO 4507 Bihar), heavy cloud cover frequently obscures peak flood stages from MODIS optical sensors.
2. **GPM IMERG Spatial Resolution Mismatch**:
   While IMERG Final Run V07B provides 30-minute temporal resolution, its $0.1^\circ$ ($\approx 10\text{ km}$) spatial grid cannot capture micro-scale convective cells over complex terrain.
3. **Streamline Network Detail in Rural Basins**:
   HydroRIVERS v1.0 captures only river reaches with upstream contributing areas $> 10\text{ km}^2$. In flat deltaic plains and irrigation-dense agricultural landscapes, smaller distributary channels and flood canals are omitted.
