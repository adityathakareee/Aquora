"""
AQUORA Phase 6C.2G.9: Authentic Flood Ground-Truth Acquisition Tests.

Validates:
1. Source DEM immutability (Raw Copernicus DSM and Working DEM match exact hashes).
2. Acquired ground-truth file presence, readability, and SHA-256 checksums:
   - India Flood Inventory v3 (Zenodo / IIT Delhi / IMD).
   - Dartmouth Flood Observatory (DFO) Global Masterlist.
3. Event correspondence and temporal alignment:
   - Event E03 (July 1-2, 2019 Mumbai Deluge): UEI-IMD-FL-2019-0090, UEI-IMD-FL-2019-0091.
   - Event E02 (August 29-30, 2017 Mumbai Deluge): UEI-IMD-FL-2017-0088, UEI-IMD-FL-2017-0089.
4. Epistemological and label-provenance invariants:
   - Absence of reported flood != verified non-flood negative sample.
   - Candidate SAR backscatter drop != verified flood ground truth.
   - Simulated physical depths != supervised training ground truth.
   - Resolution mismatch: District/sub-district scale inventory != 30m street inundation vector.
5. Governance decision:
   - Final decision strictly PARTIAL_DATA_ACQUIRED.
   - Supervised training strictly prohibited (supervised_training_permitted == False).
   - No models trained in ml/models/.
"""

import hashlib
import json
from pathlib import Path
import zipfile
import pytest
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"

IFI_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "india_flood_inventory_v3.csv"
DFO_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "dfo_masterlist_20190418.zip"

INVENTORY_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g9_ground_truth_inventory.json"
PROVENANCE_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g9_label_provenance.json"
ALIGNMENT_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g9_alignment_validation.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g9_ground_truth_manifest.yaml"
SCHEMA_PATH = PROJECT_ROOT / "ml" / "aquora_ml_feature_schema_v1.json"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"

EXPECTED_IFI_SHA256 = "ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108"
EXPECTED_DFO_SHA256 = "976f0904c603ba31e8aa62f6d1b55cec4c153be783495593ed247d01629ffe09"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_source_dem_immutability():
    """Verify raw Copernicus DSM and working study-extent DEM remain strictly unmodified."""
    assert RAW_DEM_PATH.exists(), f"Raw DEM missing at {RAW_DEM_PATH}"
    assert WORKING_DEM_PATH.exists(), f"Working DEM missing at {WORKING_DEM_PATH}"
    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256


def test_acquired_ground_truth_checksums_and_readability():
    """Verify authentic acquired ground-truth files exist, match exact checksums, and are readable."""
    assert IFI_PATH.exists(), f"India Flood Inventory missing at {IFI_PATH}"
    assert compute_sha256(IFI_PATH) == EXPECTED_IFI_SHA256
    assert IFI_PATH.stat().st_size == 1801579

    # Verify CSV readability and columns
    df_ifi = pd.read_csv(IFI_PATH)
    assert len(df_ifi) == 6876, f"Expected 6,876 records, got {len(df_ifi)}"
    assert "UEI" in df_ifi.columns
    assert "Districts" in df_ifi.columns
    assert "Start Date" in df_ifi.columns

    # Verify Maharashtra and Mumbai coverage
    mh_mask = df_ifi["Districts"].str.contains("Maharashtra|Mumbai|Pune|Thane|Nashik", case=False, na=False) | (
        df_ifi["State"].str.contains("Maharashtra", case=False, na=False)
    )
    assert mh_mask.sum() >= 1000, f"Expected >= 1000 Maharashtra records, got {mh_mask.sum()}"

    mumbai_mask = df_ifi["Districts"].str.contains("Mumbai", case=False, na=False)
    assert mumbai_mask.sum() == 182, f"Expected 182 Mumbai records, got {mumbai_mask.sum()}"

    # Verify DFO zip package
    assert DFO_PATH.exists(), f"DFO shapefile zip missing at {DFO_PATH}"
    assert compute_sha256(DFO_PATH) == EXPECTED_DFO_SHA256
    assert DFO_PATH.stat().st_size == 610578

    with zipfile.ZipFile(DFO_PATH, "r") as zf:
        namelist = zf.namelist()
        assert any(n.endswith(".shp") for n in namelist)
        assert any(n.endswith(".dbf") for n in namelist)
        assert any(n.endswith(".shx") for n in namelist)


def test_target_event_temporal_and_spatial_alignment():
    """Verify Event E03 (July 2019) and Event E02 (August 2017) are verified by authentic primary records."""
    df_ifi = pd.read_csv(IFI_PATH)

    # Event E03: 1-2 July 2019
    e03_ids = ["UEI-IMD-FL-2019-0090", "UEI-IMD-FL-2019-0091"]
    e03_records = df_ifi[df_ifi["UEI"].isin(e03_ids)]
    assert len(e03_records) == 2, f"Expected 2 records for E03, got {len(e03_records)}"

    rec90 = e03_records[e03_records["UEI"] == "UEI-IMD-FL-2019-0090"].iloc[0]
    rec91 = e03_records[e03_records["UEI"] == "UEI-IMD-FL-2019-0091"].iloc[0]

    assert "07-01-2019" in str(rec90["Start Date"])
    assert "Mumbai" in str(rec90["Districts"])
    assert "Heavy rains" in str(rec90["Main Cause"])

    assert "07-02-2019" in str(rec91["Start Date"])
    assert "Mumbai" in str(rec91["Districts"])
    assert "flood" in str(rec91["Main Cause"]).lower()

    # Event E02: 29-30 August 2017
    e02_ids = ["UEI-IMD-FL-2017-0088", "UEI-IMD-FL-2017-0089"]
    e02_records = df_ifi[df_ifi["UEI"].isin(e02_ids)]
    assert len(e02_records) == 2, f"Expected 2 records for E02, got {len(e02_records)}"

    rec88 = e02_records[e02_records["UEI"] == "UEI-IMD-FL-2017-0088"].iloc[0]
    rec89 = e02_records[e02_records["UEI"] == "UEI-IMD-FL-2017-0089"].iloc[0]

    assert "29-08-2017" in str(rec88["Start Date"])
    assert "Thane" in str(rec88["Districts"])
    assert "30-08-2017" in str(rec89["Start Date"])
    assert "Mumbai" in str(rec89["Districts"])


def test_epistemological_and_provenance_invariants():
    """Verify label provenance correctly records the negative sampling gap and resolution limitations."""
    assert PROVENANCE_JSON.exists(), f"Provenance JSON missing at {PROVENANCE_JSON}"
    with open(PROVENANCE_JSON, "r", encoding="utf-8") as f:
        prov = json.load(f)

    # Negative sampling gap
    neg_audit = prov["negative_sampling_analysis"]
    assert neg_audit["current_negative_samples_count"] == 0
    assert "never systematically record locations that remained dry" in neg_audit["the_incident_reporting_bias_problem"].lower()
    assert neg_audit["status"] == "DEFENSIBLE_NEGATIVE_GROUND_TRUTH_CURRENTLY_UNAVAILABLE"

    # Taxonomy audit
    tax = prov["taxonomy_evaluation"]
    assert "VERIFIED" in tax
    assert "PARTIALLY_VERIFIED" in tax
    assert "UNVERIFIED" in tax
    assert "UNLABELED" in tax

    # Alignment validation artifact
    assert ALIGNMENT_JSON.exists(), f"Alignment JSON missing at {ALIGNMENT_JSON}"
    with open(ALIGNMENT_JSON, "r", encoding="utf-8") as f:
        align = json.load(f)
    assert align["event_e03_verification"]["temporal_alignment_status"] == "EXACT_DATE_AND_LOCATION_MATCH"
    assert align["event_e02_verification"]["temporal_alignment_status"] == "EXACT_DATE_AND_LOCATION_MATCH"


def test_manifest_integrity_and_governance_decision():
    """Verify manifest governance decision is strictly PARTIAL_DATA_ACQUIRED and prohibits training."""
    assert MANIFEST_PATH.exists(), f"Manifest missing at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["final_decision"] == "PARTIAL_DATA_ACQUIRED"
    assert gov["supervised_training_permitted"] is False
    assert gov["zero_label_fabrication_enforced"] is True
    assert gov["zero_synthetic_interpolation_enforced"] is True

    # Check that acquired datasets are registered with correct hashes
    acq = manifest["acquired_datasets"]
    assert acq["india_flood_inventory"]["sha256"] == EXPECTED_IFI_SHA256
    assert acq["india_flood_inventory"]["records_count"] == 6876
    assert acq["dfo_masterlist_shapefile"]["sha256"] == EXPECTED_DFO_SHA256


def test_no_model_training_occurred():
    """Verify safety rule: no model training was executed in this phase."""
    models_dir = PROJECT_ROOT / "ml" / "models"
    if models_dir.exists():
        model_files = list(models_dir.glob("*.joblib")) + list(models_dir.glob("*.onnx")) + list(models_dir.glob("*.pt"))
        assert len(model_files) == 0, f"Found unexpected model files: {model_files}"


def test_feature_schema_preserved():
    """Verify ml/aquora_ml_feature_schema_v1.json was not modified or corrupted."""
    assert SCHEMA_PATH.exists()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["schema_version"] == "1.0.0"
    assert len(schema["tiers"]["CORE_NATIONAL"]["features"]) == 11
    assert len(schema["tiers"]["REGIONAL_EXPANSION"]["features"]) == 3
    assert len(schema["tiers"]["DEEP_ZONE_EXCLUSIVE"]["features"]) == 6
