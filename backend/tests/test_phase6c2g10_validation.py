"""
AQUORA Phase 6C.2G.10: Ground-Truth Validation and Training Dataset Feasibility Tests.

Validates:
1. Source DEM immutability (Raw Copernicus DSM and Working DEM match exact hashes).
2. File existence, size, and SHA-256 hash consistency with Phase 6C.2G.9 and Phase 6C.2G.10 manifests.
3. IFI schema inspection, coordinate gap (Latitude/Longitude 100% NaN), and clean date parsing.
4. DFO schema inspection, point geometry enforcement (0 polygons), and temporal cutoff at August 2010 (no 2017/2019).
5. Target event records validation (E02 and E03), source homogeneity (100% IMD), and non-independence/overlap safeguard.
6. Geographic applicability rules: prohibition of district-to-pixel label broadcasting and prohibition of centroid-to-polygon conversion.
7. Training feasibility decision: EVENT_LEVEL_ANALYSIS_FEASIBLE for macro analysis, while pixel-level supervised training is strictly prohibited.
8. Model training prohibition: no model artifacts created in ml/models/.
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import zipfile
import geopandas as gpd
import pandas as pd
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"

IFI_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "india_flood_inventory_v3.csv"
DFO_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "dfo_masterlist_20190418.zip"

PHASE6C2G9_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase6c2g9_ground_truth_manifest.yaml"
PHASE6C2G10_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase6c2g10_validation_manifest.yaml"
VALIDATION_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g10_validation_assessment.json"
PROVENANCE_JSON = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g10_label_provenance.json"
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
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()
    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256


def test_file_integrity_and_manifest_hash_match():
    """Verify both datasets exist on disk and match hashes in both Phase 6C.2G.9 and 6C.2G.10 manifests."""
    assert IFI_PATH.exists()
    assert DFO_PATH.exists()
    assert PHASE6C2G9_MANIFEST.exists()
    assert PHASE6C2G10_MANIFEST.exists()

    ifi_hash = compute_sha256(IFI_PATH)
    dfo_hash = compute_sha256(DFO_PATH)

    assert ifi_hash == EXPECTED_IFI_SHA256
    assert dfo_hash == EXPECTED_DFO_SHA256

    with open(PHASE6C2G9_MANIFEST, "r", encoding="utf-8") as f:
        m9 = yaml.safe_load(f)
    assert m9["acquired_datasets"]["india_flood_inventory"]["sha256"] == ifi_hash
    assert m9["acquired_datasets"]["dfo_masterlist_shapefile"]["sha256"] == dfo_hash

    with open(PHASE6C2G10_MANIFEST, "r", encoding="utf-8") as f:
        m10 = yaml.safe_load(f)
    assert m10["verified_datasets"]["india_flood_inventory"]["sha256"] == ifi_hash
    assert m10["verified_datasets"]["dfo_masterlist"]["sha256"] == dfo_hash


def test_ifi_schema_and_coordinate_gap():
    """Verify IFI schema, complete absence of coordinates, and date format consistency."""
    df = pd.read_csv(IFI_PATH)
    assert len(df) == 6876
    assert len(df.columns) == 23

    # Critical coordinate gap: 100% missing
    assert df["Latitude"].isna().sum() == 6876
    assert df["Longitude"].isna().sum() == 6876
    assert df["Location"].isna().sum() == 6876
    assert df["Severity"].isna().sum() == 6876
    assert df["Area Affected"].isna().sum() == 6876

    # Clean date parsing for non-null dates
    non_null_dates = df["Start Date"].dropna()
    assert len(non_null_dates) == 6856
    assert df["Start Date"].isna().sum() == 20

    parsed_dates = pd.to_datetime(non_null_dates, format="%d-%m-%Y %H:%M", errors="coerce")
    assert parsed_dates.isna().sum() == 0, "All non-null start dates must follow %d-%m-%Y %H:%M"

    # Source homogeneity: 100% IMD DWE
    assert (df["Event Source"] == "IMD").all()


def test_dfo_schema_and_temporal_cutoff():
    """Verify DFO geometries are strictly points and historical coverage cuts off in 2010."""
    gdf = gpd.read_file(f"zip://{DFO_PATH.as_posix()}")
    assert len(gdf) == 4029
    assert str(gdf.crs) == "EPSG:4326"

    # Must be 100% points, no polygons
    assert set(gdf.geometry.geom_type.unique()) == {"Point"}

    # Temporal cutoff verification
    began_dates = pd.to_datetime(gdf["Began"], errors="coerce").dropna()
    max_date = began_dates.max()
    assert max_date.year == 2010
    assert max_date.month == 8

    # Zero events in 2017 or 2019
    assert len(gdf[gdf["Began"].astype(str).str.contains("2017")]) == 0
    assert len(gdf[gdf["Began"].astype(str).str.contains("2019")]) == 0


def test_event_records_validation_and_overlap_safeguards():
    """Verify Mumbai events E02 and E03 records and enforce non-independence / grouping safeguards."""
    df = pd.read_csv(IFI_PATH)

    # Event E03: 1-2 July 2019
    e03 = df[df["UEI"].isin(["UEI-IMD-FL-2019-0090", "UEI-IMD-FL-2019-0091"])]
    assert len(e03) == 2
    rec90 = e03[e03["UEI"] == "UEI-IMD-FL-2019-0090"].iloc[0]
    rec91 = e03[e03["UEI"] == "UEI-IMD-FL-2019-0091"].iloc[0]
    assert rec90["Start Date"] == "07-01-2019 00:00"
    assert rec91["Start Date"] == "07-02-2019 00:00"
    assert rec91["Human fatality"] == 45.0
    assert "Malad East" in str(rec91["Extent of damage "])

    # Event E02: 29-30 August 2017
    e02 = df[df["UEI"].isin(["UEI-IMD-FL-2017-0088", "UEI-IMD-FL-2017-0089"])]
    assert len(e02) == 2
    rec88 = e02[e02["UEI"] == "UEI-IMD-FL-2017-0088"].iloc[0]
    rec89 = e02[e02["UEI"] == "UEI-IMD-FL-2017-0089"].iloc[0]
    assert "29-08-2017" in rec88["Start Date"]
    assert "30-08-2017" in rec89["Start Date"]

    # Verify both pairs share identical IMD source and constitute consecutive slices of single storms
    assert rec90["Event Source"] == "IMD" and rec91["Event Source"] == "IMD"
    assert rec88["Event Source"] == "IMD" and rec89["Event Source"] == "IMD"


def test_geographic_applicability_safeguards():
    """Verify tier applicability and critical negative/broadcasting safeguards."""
    assert VALIDATION_JSON.exists()
    with open(VALIDATION_JSON, "r", encoding="utf-8") as f:
        val = json.load(f)

    tiers = val["geographic_applicability"]["tier_evaluations"]
    assert tiers["NATIONAL"]["applicability"] == "USABLE_FOR_MACRO_ANALYSIS"
    assert tiers["LOCAL_MITHI_DEEP_ZONE"]["applicability"] == "COMPLETELY_UNUSABLE"
    assert tiers["LOCAL_MITHI_DEEP_ZONE"]["pixel_training_supported"] is False

    safeguards = val["geographic_applicability"]["critical_safeguards"]
    assert any("Do NOT broadcast district-level event labels to 30m raster grid cells" in s for s in safeguards)
    assert any("Do NOT convert DFO point centroids into synthetic flood inundation polygons" in s for s in safeguards)
    assert any("Do NOT treat absence of an event record as evidence of dry ground" in s for s in safeguards)


def test_training_feasibility_decision_and_governance():
    """Verify governance decision is EVENT_LEVEL_ANALYSIS_FEASIBLE and supervised pixel training is prohibited."""
    with open(PHASE6C2G10_MANIFEST, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["final_decision"] == "EVENT_LEVEL_ANALYSIS_FEASIBLE"
    assert gov["event_level_national_analysis_permitted"] is True
    assert gov["pixel_level_supervised_training_permitted"] is False
    assert gov["zero_synthetic_labels_enforced"] is True
    assert gov["zero_district_to_pixel_broadcasting_enforced"] is True

    # Check validation assessment JSON consistency
    with open(VALIDATION_JSON, "r", encoding="utf-8") as f:
        val = json.load(f)
    assert val["final_decision"] == "EVENT_LEVEL_ANALYSIS_FEASIBLE"
    target_labels = val["training_feasibility"]["feature_status"]["target_labels"]
    assert target_labels["flood_positive_labels_30m"]["count"] == 0
    assert target_labels["flood_negative_labels_30m"]["count"] == 0


def test_safety_and_schema_preservation():
    """Verify feature schema preserved and zero models trained."""
    # Zero trained models
    models_dir = PROJECT_ROOT / "ml" / "models"
    if models_dir.exists():
        model_files = list(models_dir.glob("*.joblib")) + list(models_dir.glob("*.onnx")) + list(models_dir.glob("*.pt"))
        assert len(model_files) == 0

    # Schema integrity
    assert SCHEMA_PATH.exists()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    assert schema["schema_version"] == "1.0.0"
    assert len(schema["tiers"]["CORE_NATIONAL"]["features"]) == 11
    assert len(schema["tiers"]["REGIONAL_EXPANSION"]["features"]) == 3
    assert len(schema["tiers"]["DEEP_ZONE_EXCLUSIVE"]["features"]) == 6
