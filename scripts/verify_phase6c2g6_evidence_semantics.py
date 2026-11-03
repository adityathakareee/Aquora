"""
AQUORA Phase 6C.2G.6: Evidence Status Correction and Acquisition Request Readiness Script.

Executes:
1. DEM source immutability audit (Raw DEM and Working DEM hashes).
2. Construction of the Phase 6C.2G.6 Evidence Register with strictly corrected semantics:
   - VERIFIED_PRIMARY_SOURCE, PARTIALLY_VERIFIED, BIBLIOGRAPHICALLY_VERIFIED,
     UNVERIFIED, NOT_FOUND_IN_SEARCH, ACCESS_NOT_ESTABLISHED, NOT_ACQUIRED,
     CUSTODIAN_CONFIRMED_RESTRICTED.
   - Strictly enforces that failed URLs or empty searches do NOT justify claims of custodian restriction.
   - Crossref bibliographic metadata verifies only publication metadata, NOT article technical claims.
   - Arithmetic checks are explicitly labeled as mathematical identities, NOT source verification.
3. Creation of the Review-Ready Formal Acquisition Request Package:
   - 5 prioritized requests (MCGM, MIAL, Survey of India, MMRDA, Railways).
   - Includes lower-sensitivity alternatives and recipient verification status.
   - Strictly marked DRAFT_ONLY_NOT_SUBMITTED with zero external contact.
4. Definition of the Safe Parallel-Work Plan:
   - Validating existing rainfall and SAR artifacts.
   - Documenting terrain limitations.
   - Expanding contract and provenance unit tests.
   - Non-authoritative study area mapping without implying official boundaries.
   - Strict ban on historical flood-depth/inundation simulations.
5. Generation of machine-readable data/manifests/phase6c2g6_evidence_manifest.yaml.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
EVIDENCE_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "evidence"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g6_evidence_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"

VALID_STATUSES = {
    "VERIFIED_PRIMARY_SOURCE",
    "PARTIALLY_VERIFIED",
    "BIBLIOGRAPHICALLY_VERIFIED",
    "UNVERIFIED",
    "NOT_FOUND_IN_SEARCH",
    "ACCESS_NOT_ESTABLISHED",
    "NOT_ACQUIRED",
    "CUSTODIAN_CONFIRMED_RESTRICTED"
}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def generate_evidence_register():
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    claims = [
        {
            "claim_id": "CLM-01-CHITALE-REPORT-PHYSICAL-DOCUMENT",
            "exact_claim": "The Chitale Committee Report (March 2006, 359 pp.) is possessed locally on disk as an authoritative primary source document.",
            "topic": "Physical Document Possession",
            "source_title": "Report of the Fact-Finding Committee on Mumbai Floods of 26th July 2005",
            "publisher_or_custodian": "Government of Maharashtra",
            "canonical_identifier_or_url": "Govt Resolution No. FFC-2005/CR-146/DMR / Question of Cities public URL",
            "original_source_retrieved_and_inspected": False,
            "supporting_location_in_source": "Whole Volume (pp. 1-359)",
            "retrieval_timestamp_utc": "2026-10-17T09:23:26Z",
            "retrieval_outcome": "HTTP_404_NOT_FOUND (Direct download endpoint returned 404; document hosted on Scribd but not retrieved to disk)",
            "local_file_path": None,
            "local_sha256": None,
            "evidence_status": "NOT_ACQUIRED",
            "unresolved_limitations": "The 359-page government report volume is not present locally on disk in AQUORA repository."
        },
        {
            "claim_id": "CLM-02-CHITALE-CATCHMENT-METRICS",
            "exact_claim": "Mithi River watershed spans 72.95 sq km, comprising Vihar Lake (18.96 sq km), Powai Lake (6.61 sq km), and direct river reach below lakes (47.38 sq km).",
            "topic": "Catchment Area Benchmark",
            "source_title": "Report of the Fact-Finding Committee on Mumbai Floods of 26th July 2005",
            "publisher_or_custodian": "Government of Maharashtra (Chitale Committee)",
            "canonical_identifier_or_url": "Govt Resolution No. FFC-2005/CR-146/DMR; cited in Maharashtra WRD documents",
            "original_source_retrieved_and_inspected": False,
            "supporting_location_in_source": "Chapter 4 ('Lakes and Reservoirs') & Chapter 5 ('Mithi River and Its Catchment'), Table 5.1, p. 64",
            "retrieval_timestamp_utc": "2026-10-17T09:50:00Z",
            "retrieval_outcome": "DOCUMENTED_IN_SECONDARY_ADMINISTRATIVE_CITATIONS",
            "local_file_path": "data/raw/phase7/evidence/chitale_committee_2006_benchmark_record.json",
            "local_sha256": compute_sha256(EVIDENCE_DIR / "chitale_committee_2006_benchmark_record.json"),
            "evidence_status": "PARTIALLY_VERIFIED",
            "unresolved_limitations": (
                "The scalar numbers are consistently cited in administrative consensus, and the arithmetic check (18.96 + 6.61 + 47.38 = 72.95) "
                "is mathematically exact. However, arithmetic checks do NOT constitute primary-source verification. The original government PDF "
                "was not inspected on disk, and the report demarcated the catchment on legacy 1:50,000 paper toposheets without digital GIS coordinates."
            )
        },
        {
            "claim_id": "CLM-03-ZOPE-BIBLIOGRAPHIC-METADATA",
            "exact_claim": "P. E. Zope, T. I. Eldho, and V. Jothiprakash published 'Impacts of urbanization on flooding of a coastal urban catchment: a case study of Mumbai City, India' in Natural Hazards (2015), 75(1), 887-908, DOI: 10.1007/s11069-014-1356-4.",
            "topic": "Hydrodynamic Literature Bibliographic Identity",
            "source_title": "Natural Hazards (Springer Netherlands)",
            "publisher_or_custodian": "Springer Netherlands / CrossRef",
            "canonical_identifier_or_url": "https://doi.org/10.1007/s11069-014-1356-4",
            "original_source_retrieved_and_inspected": True,
            "supporting_location_in_source": "CrossRef REST API Work Object / Journal Table of Contents",
            "retrieval_timestamp_utc": "2026-10-17T09:54:15Z",
            "retrieval_outcome": "HTTP_200_OK (Authoritative metadata retrieved from CrossRef REST API)",
            "local_file_path": "data/raw/phase7/evidence/zope_et_al_2015_hydrodynamic_literature_record.json",
            "local_sha256": compute_sha256(EVIDENCE_DIR / "zope_et_al_2015_hydrodynamic_literature_record.json"),
            "evidence_status": "BIBLIOGRAPHICALLY_VERIFIED",
            "unresolved_limitations": "Bibliographic metadata is verified, but does not independently establish or verify technical modeling claims from inaccessible full text."
        },
        {
            "claim_id": "CLM-04-ZOPE-TECHNICAL-MODELING-CLAIMS",
            "exact_claim": "Zope et al. reports a 70.57 sq km Mithi catchment and explicitly documents that unconditioned satellite DEMs treat the airport runway and railway bridges as dams, requiring HEC-RAS cross-sections.",
            "topic": "Hydrodynamic Modeling Findings",
            "source_title": "Natural Hazards, Vol. 75, Issue 1, pp. 887-908",
            "publisher_or_custodian": "Springer Netherlands",
            "canonical_identifier_or_url": "https://doi.org/10.1007/s11069-014-1356-4",
            "original_source_retrieved_and_inspected": False,
            "supporting_location_in_source": "Article Text & Abstract (Section 2: Study Area and Methodology)",
            "retrieval_timestamp_utc": "2026-10-17T09:54:15Z",
            "retrieval_outcome": "FULL_TEXT_NOT_LOCALLY_ACQUIRED (Abstract and secondary literature excerpts only)",
            "local_file_path": None,
            "local_sha256": None,
            "evidence_status": "UNVERIFIED",
            "unresolved_limitations": (
                "Article full text is not locally possessed on disk. CrossRef bibliographic metadata must not be presented as verification "
                "of article-specific technical findings. The article provides no open supplementary GIS files or public geometry repositories."
            )
        },
        {
            "claim_id": "CLM-05-CSMIA-RUNWAY-CULVERT-DIMENSIONS-INVERTS",
            "exact_claim": "The CSMIA Runway 09/27 crossing is a triple-barrel box culvert (3 x 20m spans = 60m width, height 4.0-5.0m), upstream invert +2.50m MSL, downstream +2.10m MSL.",
            "topic": "Runway Crossing Hydraulic Geometry",
            "source_title": "CWPRS Technical Report 4321 / MIAL Airport Expansion Project Proposals",
            "publisher_or_custodian": "MIAL / CWPRS / AAI",
            "canonical_identifier_or_url": "CWPRS Report 4321; cited in secondary flood mitigation briefs",
            "original_source_retrieved_and_inspected": False,
            "supporting_location_in_source": "CWPRS Report 4321 hydraulic design section",
            "retrieval_timestamp_utc": "2026-10-17T09:54:50Z",
            "retrieval_outcome": "NOT_FOUND_IN_SEARCH (Signed as-built drawings not located in open web searches)",
            "local_file_path": None,
            "local_sha256": None,
            "evidence_status": "UNVERIFIED",
            "unresolved_limitations": (
                "Dimensions originate from planning/widening recommendations (pre-2005 span was ~27m). Signed as-built drawings and surveyed invert sheets "
                "have not been acquired. Access restrictions have not been confirmed by MIAL/AAI custodians (ACCESS_NOT_ESTABLISHED). Local file status is NOT_ACQUIRED."
            )
        },
        {
            "claim_id": "CLM-06-CSMIA-RUNWAY-CULVERT-GEOREFERENCED-ALIGNMENT",
            "exact_claim": "A georeferenced 3D CAD centerline vector and inlet/outlet coordinate pair exists for the CSMIA Runway 09/27 culvert crossing.",
            "topic": "Runway Crossing Spatial Vector",
            "source_title": "MIAL As-Built Engineering Drawings",
            "publisher_or_custodian": "Mumbai International Airport Limited (MIAL)",
            "canonical_identifier_or_url": "MIAL Infrastructure Engineering Archives",
            "original_source_retrieved_and_inspected": False,
            "supporting_location_in_source": "Civil Engineering As-Built Alignment Plan",
            "retrieval_timestamp_utc": "2026-10-17T09:54:50Z",
            "retrieval_outcome": "NOT_FOUND_IN_SEARCH",
            "local_file_path": None,
            "local_sha256": None,
            "evidence_status": "UNVERIFIED",
            "unresolved_limitations": "Centerline coordinates not found in public searches. Dataset is NOT_ACQUIRED. Custodian access restrictions are ACCESS_NOT_ESTABLISHED."
        },
        {
            "claim_id": "CLM-07-RAILWAY-HIGHWAY-BRIDGE-OPENINGS",
            "exact_claim": "Surveyed bridge opening hydraulic cross-sections, bed invert levels, and pier scour depths exist for Central Railway Bridge 12, Western Railway Bridge 24, and WEH Kalanagar Bridge.",
            "topic": "Railway & Highway Crossings",
            "source_title": "Central Railway / Western Railway / MSRDC Bridge Inspection Registers",
            "publisher_or_custodian": "Indian Railways / MSRDC",
            "canonical_identifier_or_url": "Indian Railways Bridge Inspection Records",
            "original_source_retrieved_and_inspected": False,
            "supporting_location_in_source": "Bridge Inspection Forms BR-1/BR-2",
            "retrieval_timestamp_utc": "2026-10-17T09:54:50Z",
            "retrieval_outcome": "NOT_FOUND_IN_SEARCH (Bridge existence known from OSM, but structural opening registers not found in search)",
            "local_file_path": None,
            "local_sha256": None,
            "evidence_status": "UNVERIFIED",
            "unresolved_limitations": "Bridge registers not present locally (NOT_ACQUIRED). Empty search results do not establish custodian restriction (ACCESS_NOT_ESTABLISHED)."
        },
        {
            "claim_id": "CLM-08-MBPA-TIDAL-DATUM-CONSTANT",
            "exact_claim": "Mean Sea Level (MSL) is +2.51 m above Chart Datum (CD) for Mumbai Harbour at Apollo Bandar (reduction formula: z_local_msl = z_chart_datum - 2.51m).",
            "topic": "Hydrographic Vertical Datum Relationship",
            "source_title": "Mumbai Port Authority Navigation & Tidal Parameters",
            "publisher_or_custodian": "Mumbai Port Authority (MbPA)",
            "canonical_identifier_or_url": "https://mumbaiport.gov.in/ (Navigation & Hydrographic Parameters)",
            "original_source_retrieved_and_inspected": True,
            "supporting_location_in_source": "Tidal Range Table (Navigation Section, Apollo Bandar station particulars)",
            "retrieval_timestamp_utc": "2026-10-17T09:55:38Z",
            "retrieval_outcome": "DOCUMENTED_IN_OFFICIAL_PORT_NAVIGATION_TABLES",
            "local_file_path": "data/raw/phase7/evidence/mumbai_port_authority_tidal_datum_record.json",
            "local_sha256": compute_sha256(EVIDENCE_DIR / "mumbai_port_authority_tidal_datum_record.json"),
            "evidence_status": "PARTIALLY_VERIFIED",
            "unresolved_limitations": (
                "Local datum relationship (MSL = CD + 2.51m) is verified. However, this is a local relative relationship only; "
                "it does NOT independently establish the required geodetic tie to the Copernicus DEM global EGM96 Geoid."
            )
        },
        {
            "claim_id": "CLM-09-EVENT-E03-HIGH-TIDE-PEAK",
            "exact_claim": "During Event E03, high tide peaked at 4.59 m CD (+2.08 m local MSL) on 2019-07-02 at 11:52 IST (06:22 UTC).",
            "topic": "Historical Tide Peak Stage",
            "source_title": "Disaster Management Control Room Daily Bulletin (2 July 2019)",
            "publisher_or_custodian": "Brihanmumbai Municipal Corporation (BMC / MCGM)",
            "canonical_identifier_or_url": "BMC Disaster Management Department Press Release / Municipal News Archives",
            "original_source_retrieved_and_inspected": True,
            "supporting_location_in_source": "Daily Monsoon Weather & Tide Bulletin, 2 July 2019",
            "retrieval_timestamp_utc": "2026-10-17T09:55:00Z",
            "retrieval_outcome": "VERIFIED_FROM_MUNICIPAL_DISASTER_BULLETIN",
            "local_file_path": "data/raw/phase7/evidence/mumbai_port_authority_tidal_datum_record.json",
            "local_sha256": compute_sha256(EVIDENCE_DIR / "mumbai_port_authority_tidal_datum_record.json"),
            "evidence_status": "PARTIALLY_VERIFIED",
            "unresolved_limitations": "Isolated peak stage is verified, but an isolated peak does not constitute an observed continuous 24-hour time series."
        },
        {
            "claim_id": "CLM-10-EVENT-E03-CONTINUOUS-TIDE-SERIES",
            "exact_claim": "A continuous observed half-hourly or hourly water-level series for 1-2 July 2019 has been acquired.",
            "topic": "Continuous Marine Boundary Time Series",
            "source_title": "Apollo Bandar Tide Gauge Continuous Observations (Station 43 / 846A)",
            "publisher_or_custodian": "Survey of India (G&RB) / Mumbai Port Authority",
            "canonical_identifier_or_url": "Survey of India Geodetic Tide Archives",
            "original_source_retrieved_and_inspected": False,
            "supporting_location_in_source": "Hourly Tide Record (2019-07-01 to 2019-07-03)",
            "retrieval_timestamp_utc": "2026-10-17T09:55:00Z",
            "retrieval_outcome": "NOT_FOUND_IN_SEARCH (PSMSL hosts only monthly/annual means; UHSLC hourly feed does not host July 2019 Mumbai series)",
            "local_file_path": None,
            "local_sha256": None,
            "evidence_status": "UNVERIFIED",
            "unresolved_limitations": "Dataset is NOT_ACQUIRED. Custodian access restrictions are ACCESS_NOT_ESTABLISHED."
        },
        {
            "claim_id": "CLM-11-SURVEY-OF-INDIA-EGM96-GEOID-TIE",
            "exact_claim": "An official Survey of India leveling tie sheet links Apollo Bandar Benchmark 846A (BM 5/88) to the global EGM96 Geoid.",
            "topic": "Vertical Datum Geodetic Tie",
            "source_title": "Survey of India Benchmark Leveling Record (Apollo Bandar BM 846A)",
            "publisher_or_custodian": "Survey of India (Geodetic and Research Branch, Dehradun)",
            "canonical_identifier_or_url": "Survey of India Geodetic Levelling Computations",
            "original_source_retrieved_and_inspected": False,
            "supporting_location_in_source": "Benchmark Tie Sheet BM 846A / BM 5/88",
            "retrieval_timestamp_utc": "2026-10-17T09:55:00Z",
            "retrieval_outcome": "NOT_FOUND_IN_SEARCH",
            "local_file_path": None,
            "local_sha256": None,
            "evidence_status": "UNVERIFIED",
            "unresolved_limitations": "Tie sheet not found in open searches. Dataset is NOT_ACQUIRED. Custodian access restriction is ACCESS_NOT_ESTABLISHED. Local geoid undulation uncertainty is ±0.3m to ±0.5m."
        }
    ]

    for c in claims:
        assert c["evidence_status"] in VALID_STATUSES, f"Invalid status: {c['evidence_status']}"

    out_file = EVIDENCE_DIR / "phase6c2g6_evidence_register.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "register_id": "REG-PHASE6C2G6-CORRECTED-EVIDENCE-SEMANTICS",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "claims_count": len(claims),
            "claims": claims
        }, f, indent=2)

    print(f"Evidence register written to: {out_file}")
    return out_file


def generate_acquisition_request_package():
    requests = [
        {
            "request_id": "REQ-01-MCGM-BRIMSTOWAD-GIS",
            "agency_name": "Municipal Corporation of Greater Mumbai (MCGM / BMC) - Storm Water Drains Department",
            "recipient_office": "The Chief Engineer (Storm Water Drains), MCGM, Engineering Hub Building, Dr. E. Moses Road, Worli Naka, Worli, Mumbai 400018",
            "recipient_verified": True,
            "verification_note": "Office address verified via official MCGM portal (portal.mcgm.gov.in); specific officer designation verified, individual name unverified.",
            "dataset_requested": "Official GIS boundary polygon of Mithi River drainage catchment and sub-catchments (Vihar, Powai, Kurla, Kalina, Marol, Saki Naka), plus vector polyline of primary/secondary storm water nallahs.",
            "coverage": "Mithi River Catchment, Greater Mumbai (approx. 72.95 sq km, 19.00°N - 19.16°N, 72.82°E - 72.93°E)",
            "acceptable_formats": "ESRI Shapefile or GeoJSON with valid .prj projection file (EPSG:32643 / WGS84 UTM 43N) and vertical datum documentation.",
            "intended_research_use": "Authoritative spatial ground-truth validation of Mithi River watershed boundary for open non-commercial flood intelligence evaluation.",
            "lower_sensitivity_alternative": "A single dissolved outer boundary polygon without internal nallah topology, or a downsampled boundary (50m vertex spacing) with certified area and perimeter.",
            "aquora_blocker_resolved": "Blocker B1: Unverified exploratory watershed boundary; unblocks authoritative spatial delineation.",
            "status": "DRAFT_ONLY_NOT_SUBMITTED"
        },
        {
            "request_id": "REQ-02-MIAL-CULVERT-ASBUILT",
            "agency_name": "Mumbai International Airport Limited (MIAL / Adani Airports) / Airports Authority of India (AAI)",
            "recipient_office": "Head of Civil Engineering & Infrastructure, MIAL, Chhatrapati Shivaji Maharaj International Airport, Terminal 1B, Santacruz (E), Mumbai 400099",
            "recipient_verified": True,
            "verification_note": "Corporate airport terminal address verified; civil engineering departmental division verified; specific personnel unverified.",
            "dataset_requested": "As-built engineering drawings and surveyed 3D coordinates for the Mithi River box culvert crossing beneath Runway 09/27 and associated taxiways.",
            "coverage": "CSMIA Runway 09/27 Corridor (~19.090°N, 72.875°E), between Marol nallah outfall and Kalina nallah confluence.",
            "acceptable_formats": "AutoCAD DWG/DXF drawings or stamped PDF engineering plans with surveyed 3D coordinates (Easting, Northing, GTS/MSL Elevation) of upstream inlet headwall and downstream outlet wingwalls.",
            "intended_research_use": "Defensible hydrodynamic conveyance parameterization through the airport runway barrier without unverified DEM alterations or artificial trench burning.",
            "lower_sensitivity_alternative": "A single non-confidential tabular specification sheet listing 3D inlet and outlet centerline coordinates, barrel count, clear opening dimensions, and bed slope, without full structural CAD drawings.",
            "aquora_blocker_resolved": "Blocker B2: Lack of georeferenced culvert alignment; unblocks physical hydrodynamic routing through runway barrier.",
            "status": "DRAFT_ONLY_NOT_SUBMITTED"
        },
        {
            "request_id": "REQ-03-SOI-TIDE-SERIES-EGM96-TIE",
            "agency_name": "Survey of India (Geodetic and Research Branch) / Mumbai Port Authority (MbPA)",
            "recipient_office": "The Director, Geodetic and Research Branch (G&RB), Survey of India, 17 E.C. Road, Dehradun, Uttarakhand 248001",
            "recipient_verified": True,
            "verification_note": "Survey of India national geodetic headquarters verified via surveyofindia.gov.in; specific geodetic officer unverified.",
            "dataset_requested": "Observed continuous water-level observations (15-minute or hourly) from Apollo Bandar Tide Gauge (Station 43) covering 2019-07-01 00:00 UTC through 2019-07-03 00:00 UTC, plus leveling tie sheet connecting Benchmark 846A (BM 5/88) to GTS datum and global EGM96 Geoid.",
            "coverage": "Apollo Bandar Tide Gauge, Mumbai Harbour (18.927°N, 72.833°E), 1-2 July 2019.",
            "acceptable_formats": "ISO-8601 formatted CSV/ASCII table with UTC timestamps, heights in meters, datum reference, quality flags; signed geodetic leveling computation sheet.",
            "intended_research_use": "Rigorous geodetic datum reduction of marine boundary water levels to match the Copernicus 30m DEM vertical reference frame (EGM96).",
            "lower_sensitivity_alternative": "Hourly water level observations relative to local MSL and a certified single scalar geoid undulation value (N) for Apollo Bandar BM 846A.",
            "aquora_blocker_resolved": "Blocker B3: Unverified marine stage boundary condition and missing vertical datum tie.",
            "status": "DRAFT_ONLY_NOT_SUBMITTED"
        },
        {
            "request_id": "REQ-04-MMRDA-MITHI-CROSSSECTIONS",
            "agency_name": "Mumbai Metropolitan Region Development Authority (MMRDA) - Mithi River Development Project",
            "recipient_office": "Chief Engineer, Mithi River Development Project, MMRDA, Bandra-Kurla Complex, Bandra (E), Mumbai 400051",
            "recipient_verified": True,
            "verification_note": "MMRDA BKC headquarters verified via mmrda.maharashtra.gov.in; Mithi Project cell verified; individual officer unverified.",
            "dataset_requested": "DGPS surveyed riverbed cross-sections (chainage, offset, GTS elevation) along the 17.8 km reach from Vihar/Powai to Mahim Causeway, surveyed post-2005 widening.",
            "coverage": "Mithi River channel from Powai overflow (19.127°N, 72.905°E) to Mahim Causeway outfall (19.040°N, 72.840°E).",
            "acceptable_formats": "Tab-delimited ASCII / CSV tables of cross-section station and elevation, or CAD cross-section profiles.",
            "intended_research_use": "1D/2D sub-grid river channel bathymetric calibration in the deterministic hydraulic solver.",
            "lower_sensitivity_alternative": "Average bankfull width, bankfull depth, and representative trapezoidal cross-sections at 500m intervals along the 17.8 km reach.",
            "aquora_blocker_resolved": "Blocker B4: Absence of sub-grid channel bathymetry in Copernicus surface DSM.",
            "status": "DRAFT_ONLY_NOT_SUBMITTED"
        },
        {
            "request_id": "REQ-05-RAILWAY-BRIDGE-REGISTERS",
            "agency_name": "Central Railway & Western Railway, Civil Engineering / Bridge Branch",
            "recipient_office": "Principal Chief Engineer, Central Railway (Headquarters, CSMT, Mumbai 400001); Principal Chief Engineer, Western Railway (Headquarters, Churchgate, Mumbai 400020)",
            "recipient_verified": True,
            "verification_note": "Railway zonal headquarters verified via indianrailways.gov.in; divisional bridge engineer unverified.",
            "dataset_requested": "Certified Bridge Inspection Register excerpts (Form BR-1/BR-2) or general arrangement drawings for Western Railway Bridge No. 24 (Mahim outfall) and Central Railway Bridge No. 12 (Sion-Kurla).",
            "coverage": "Western Railway Bridge 24 (~19.042°N, 72.844°E) and Central Railway Bridge 12 (~19.062°N, 72.868°E).",
            "acceptable_formats": "PDF scan of signed Bridge Inspection Register pages or structural engineering drawings.",
            "intended_research_use": "Parameterization of bridge pier flow obstruction and opening conveyance to prevent artificial damming in 2D hydrodynamic flow routing.",
            "lower_sensitivity_alternative": "A single tabular summary providing total clear opening width, number of piers, pier thickness, and lowest soffit elevation for each bridge.",
            "aquora_blocker_resolved": "Blocker B5: Railway embankment barrier obstruction in 30m DSM.",
            "status": "DRAFT_ONLY_NOT_SUBMITTED"
        }
    ]

    out_file = EVIDENCE_DIR / "phase6c2g6_acquisition_request_package.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "package_id": "REQ-PKG-PHASE6C2G6-MITHI-WATERSHED",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "governance_notice": "STRICTLY DRAFT / NOT SUBMITTED. Under Master Engineering Instructions, no email, form, or inquiry has been sent to any authority without explicit human authorization.",
            "requests_count": len(requests),
            "requests": requests
        }, f, indent=2)

    print(f"Acquisition request package written to: {out_file}")
    return out_file


def generate_parallel_work_plan():
    plan = {
        "plan_id": "PLAN-PHASE6C2G6-SAFE-PARALLEL-WORK",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "objective": "Safe parallel research and engineering activities that can proceed without fabricating missing evidence",
        "governance_rule": "STRICT BAN on generating historical flood-depth rasters, overland inundation extents, or calibrated coastal boundary results while required authoritative inputs remain unavailable.",
        "authorized_work_packages": [
            {
                "package_id": "WORK-PKG-01-RAINFALL-SAR-VALIDATION",
                "title": "Rainfall & Sentinel-1 SAR Artifact Temporal Coincidence Audit",
                "scope": "Systematic verification of time stamps, bounding boxes, and observation overlaps between NASA IMERG precipitation granules and ESA Sentinel-1 SAR scenes for Events E01 through E07.",
                "safe_outputs": "Temporal alignment matrices, SAR backscatter dynamic range audits, and rainfall intensity summary statistics.",
                "dependencies_on_missing_evidence": None
            },
            {
                "package_id": "WORK-PKG-02-TERRAIN-LIMITATIONS-DOCUMENTATION",
                "title": "Copernicus 30m DEM Surface Limitations Technical Documentation",
                "scope": "Documenting specific spatial failure modes of the surface DSM: road bridge deck elevations (+9.95m MSL at Mahim Causeway), airport runway embankment damming, and mangrove canopy elevation bias (+2m to +4m).",
                "safe_outputs": "Technical report on surface DSM limitations and physical necessity of subsurface hydraulic structures.",
                "dependencies_on_missing_evidence": None
            },
            {
                "package_id": "WORK-PKG-03-DATA-CONTRACTS-AND-PROVENANCE-TESTS",
                "title": "Backend Data Contract, Nodata Masking, and Reprojection Unit Tests",
                "scope": "Expanding automated test suites covering DeepDataContract schemas, Pydantic v2 validation, GeoTIFF nodata masking, array orientation conventions, and pyproj EPSG:32643 transformations.",
                "safe_outputs": "Passing pytest suites ensuring robust software infrastructure and schema compliance.",
                "dependencies_on_missing_evidence": None
            },
            {
                "package_id": "WORK-PKG-04-NON-AUTHORITATIVE-STUDY-AREA-VISUALIZATION",
                "title": "Non-Authoritative Study Area Visual Context Map",
                "scope": "Preparing cartographic context visuals displaying landmark coordinates, weather station locations, and the study bounding box.",
                "safe_outputs": "A clearly stamped graphic labeled: 'NON-AUTHORITATIVE EXPLORATORY STUDY AREA — NOT AN OFFICIAL WATERSHED BOUNDARY'.",
                "dependencies_on_missing_evidence": None
            }
        ],
        "strict_prohibitions": [
            "DO NOT produce historical flood-depth raster grids.",
            "DO NOT simulate 2D overland flood inundation for validation events.",
            "DO NOT calibrate coastal boundary tide-surge interaction curves without continuous observed water levels.",
            "DO NOT train machine learning models on unverified or synthetic flood labels.",
            "DO NOT burn guessed culvert alignments or trenches into the DEM.",
            "DO NOT modify protected Copernicus DEM or working terrain rasters."
        ]
    }

    out_file = EVIDENCE_DIR / "phase6c2g6_parallel_work_plan.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    print(f"Parallel work plan written to: {out_file}")
    return out_file


def generate_manifest(reg_file, req_file, plan_file):
    all_evidence_files = [
        EVIDENCE_DIR / "chitale_committee_2006_benchmark_record.json",
        EVIDENCE_DIR / "zope_et_al_2015_hydrodynamic_literature_record.json",
        EVIDENCE_DIR / "municipal_engineering_datasets_investigation.json",
        EVIDENCE_DIR / "mumbai_port_authority_tidal_datum_record.json",
        EVIDENCE_DIR / "formal_data_request_letters.json",
        EVIDENCE_DIR / "prioritized_dataset_acquisition_plan.json",
        reg_file,
        req_file,
        plan_file
    ]

    manifest_entries = []
    for ef in all_evidence_files:
        manifest_entries.append({
            "local_path": str(ef.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "file_size_bytes": ef.stat().st_size,
            "sha256": compute_sha256(ef),
            "filename": ef.name
        })

    manifest = {
        "manifest_version": "1.0.0",
        "phase": "PHASE_6C_2G_6_EVIDENCE_STATUS_CORRECTION_AND_ACQUISITION_REQUEST_READINESS",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "governance": {
            "status": "EVIDENCE_SEMANTICS_CORRECTED_ACQUISITION_PACKAGE_READY",
            "watershed_status": "EXPLORATORY_ONLY",
            "final_governance_decision": "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE",
            "historical_simulation_permitted": False,
            "zero_culvert_fabrication_enforced": True,
            "zero_synthetic_interpolation_enforced": True,
            "working_dem_immutable": True,
            "human_authorization_enforced": True
        },
        "dem_immutability_audit": {
            "raw_dem_sha256": compute_sha256(RAW_DEM_PATH),
            "working_dem_sha256": compute_sha256(WORKING_DEM_PATH),
            "expected_raw_dem_sha256": EXPECTED_RAW_DEM_SHA256,
            "expected_working_dem_sha256": EXPECTED_WORKING_DEM_SHA256,
            "immutability_verified": (
                compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256 and
                compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256
            )
        },
        "evidence_status_semantic_rules": {
            "allowed_statuses": list(VALID_STATUSES),
            "restriction_confirmation_rule": "Failed URLs or empty search results MUST NOT be labeled CUSTODIAN_CONFIRMED_RESTRICTED. Access restrictions without custodian written response must remain ACCESS_NOT_ESTABLISHED.",
            "crossref_limitation_rule": "Crossref bibliographic metadata proves publication identity only, NOT article technical findings.",
            "arithmetic_rule": "Mathematical sum checks (18.96 + 6.61 + 47.38 = 72.95) are arithmetic checks only, NOT source verification.",
            "local_possession_rule": "Missing local source files must be labeled NOT_ACQUIRED."
        },
        "acquisition_evidence_package": {
            "package_directory": str(EVIDENCE_DIR.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "entries_count": len(manifest_entries),
            "entries": manifest_entries
        },
        "go_no_go_decision": {
            "decision": "BLOCKED — AUTHORITATIVE EVIDENCE UNAVAILABLE",
            "justification": (
                "Authoritative watershed delineation and coastal flood simulation remain STRICTLY BLOCKED because: "
                "(1) No authoritative digital GIS watershed boundary polygon is available on disk or in open public records. "
                "(2) CSMIA runway culvert as-built CAD drawings and invert survey coordinates are unretrieved (NOT_ACQUIRED, ACCESS_NOT_ESTABLISHED). "
                "(3) Marine continuous water levels for Event E03 and the Survey of India EGM96 geodetic tie sheet are missing (NOT_ACQUIRED). "
                "In accordance with Master Governance rules, synthesizing data, guessing culverts, or forcing benchmarks is prohibited."
            )
        }
    }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False, indent=2)

    print(f"Manifest written to: {MANIFEST_PATH}")


def main():
    print("=== AQUORA Phase 6C.2G.6: Evidence Status Correction & Readiness ===")

    print("Auditing source DEM immutability...")
    raw_hash = compute_sha256(RAW_DEM_PATH)
    working_hash = compute_sha256(WORKING_DEM_PATH)
    assert raw_hash == EXPECTED_RAW_DEM_SHA256, f"Raw DEM corrupted: {raw_hash}"
    assert working_hash == EXPECTED_WORKING_DEM_SHA256, f"Working DEM corrupted: {working_hash}"
    print(f"Raw DEM SHA-256 verified: {raw_hash}")
    print(f"Working DEM SHA-256 verified: {working_hash}")

    reg_file = generate_evidence_register()
    req_file = generate_acquisition_request_package()
    plan_file = generate_parallel_work_plan()

    generate_manifest(reg_file, req_file, plan_file)
    print("Phase 6C.2G.6 script execution complete.")


if __name__ == "__main__":
    main()
