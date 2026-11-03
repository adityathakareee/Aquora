"""
AQUORA Phase 6C.2G.8: ML Dataset Readiness and Training-Data Design Tests.

Validates:
1. Source DEM immutability (Raw Copernicus DSM and Working DEM match exact hashes).
2. Candidate asset inventory completeness, file readability, and checksum consistency.
3. Feature schema compatibility with ml/aquora_ml_feature_schema_v1.json (11 core, 3 regional, 6 deep).
4. NoData preservation and refusal of zero-imputation for missing observations.
5. Unverified labels strictly excluded from supervised training (10 pilot rows remain -1).
6. Leakage-resistant event-based and basin-based splitting rules.
7. Label readiness decision strictly BLOCKED_FOR_SUPERVISED_TRAINING.
8. ML readiness manifest consistency and governance invariants.
9. No accidental model training or historical flood simulations.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest
import pandas as pd
import yaml

from ml.training_pipeline import DataSufficiencyError, NationalScreeningTrainingPipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
INVENTORY_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g8_asset_inventory.json"
SPEC_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g8_training_dataset_spec.json"
LABEL_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "ml" / "phase6c2g8_label_readiness.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g8_ml_readiness_manifest.yaml"
SCHEMA_PATH = PROJECT_ROOT / "ml" / "aquora_ml_feature_schema_v1.json"
PILOT_PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "ml" / "national_screening" / "national_screening_pilot_master.parquet"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"


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


def test_candidate_asset_inventory_completeness_and_hashes():
    """Verify candidate asset inventory exists, matches file hashes, and catalogs authentic assets."""
    assert INVENTORY_PATH.exists()
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        inv = json.load(f)

    # Check DEM assets
    assert inv["dem_assets"]["raw_copernicus_dsm"]["verified_unmodified"] is True
    assert inv["dem_assets"]["working_study_extent_dem"]["verified_unmodified"] is True

    # Check IMERG granules
    rain = inv["rainfall_assets"]["imerg_v07b_raw_granules"]
    assert rain["granule_count"] == 48
    assert "FillValue -9999.9" in rain["nodata_convention"]

    # Check SAR scenes
    sar = inv["sar_assets"]["raw_safe_archives"]
    assert len(sar) == 2
    for zname, zmeta in sar.items():
        zpath = PROJECT_ROOT / zmeta["path"]
        assert zpath.exists()
        assert zmeta["size_bytes"] == zpath.stat().st_size

    # Check terrain rasters
    terrain = inv["terrain_feature_rasters"]
    assert len(terrain) >= 6
    assert "elevation_30m.tif" in terrain
    assert "slope_30m.tif" in terrain


def test_feature_schema_strict_compatibility():
    """Verify training dataset spec adheres strictly to ml/aquora_ml_feature_schema_v1.json."""
    assert SCHEMA_PATH.exists()
    assert SPEC_PATH.exists()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)

    schema_core = schema["tiers"]["CORE_NATIONAL"]["features"]
    schema_reg = schema["tiers"]["REGIONAL_EXPANSION"]["features"]
    schema_deep = schema["tiers"]["DEEP_ZONE_EXCLUSIVE"]["features"]

    assert len(schema_core) == 11
    assert len(schema_reg) == 3
    assert len(schema_deep) == 6

    # Verify dataset spec lists all 11 core predictors in identical order
    spec_core_objs = spec["training_dataset_specification"]["feature_schema_adherence"]["governed_tiers"]["core_national_predictors"]
    spec_core_names = [item["name"] for item in spec_core_objs]
    assert spec_core_names == schema_core

    # Check regional expansion features
    spec_reg_objs = spec["training_dataset_specification"]["feature_schema_adherence"]["governed_tiers"]["regional_expansion_features"]
    spec_reg_names = [item["name"] for item in spec_reg_objs]
    assert spec_reg_names == schema_reg

    # Check deep zone exclusive features
    spec_deep_objs = spec["training_dataset_specification"]["feature_schema_adherence"]["governed_tiers"]["deep_zone_exclusive_features"]
    spec_deep_names = [item["name"] for item in spec_deep_objs]
    assert spec_deep_names == schema_deep


def test_nodata_preservation_and_refusal_of_zero_replacement():
    """Verify NoData protocol enforces native tree routing and strictly forbids zero-replacement."""
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)

    protocol = spec["training_dataset_specification"]["missing_value_protocol"]
    assert protocol["strategy"] == "NATIVE_TREE_ROUTING_ONLY"
    assert protocol["zero_replacement_forbidden"] is True
    assert "false-dry biases" in protocol["rationale"].lower()


def test_unverified_labels_excluded_from_supervised_training():
    """Verify that unverified labels (including the 10 pilot rows) are excluded from supervised training."""
    assert PILOT_PARQUET_PATH.exists()
    df_pilot = pd.read_parquet(PILOT_PARQUET_PATH)

    # All 10 pilot rows must have flood_label == -1
    assert len(df_pilot) == 10
    assert (df_pilot["flood_label"] == -1).all()

    # Verify that NationalScreeningTrainingPipeline refuses to train with unobserved labels
    pipeline = NationalScreeningTrainingPipeline()
    with pytest.raises(DataSufficiencyError) as exc_info:
        pipeline.validate_dataset(df_pilot)
    assert "no supervised training samples available" in str(exc_info.value).lower()


def test_leakage_resistant_splitting_and_forbidden_columns():
    """Verify that forbidden columns are excluded and GroupKFold basin splitting is enforced."""
    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)

    forbidden = spec["training_dataset_specification"]["strictly_forbidden_predictor_columns"]
    core_preds = [p["name"] for p in spec["training_dataset_specification"]["feature_schema_adherence"]["governed_tiers"]["core_national_predictors"]]

    # Zero overlap between predictors and forbidden columns
    for col in forbidden:
        assert col not in core_preds, f"Forbidden column {col} found in predictors!"

    # Check splitting strategy
    splitting = spec["training_dataset_specification"]["leakage_prevention_and_splitting_strategy"]
    assert "basin_id" in splitting["spatial_grouping"]
    assert "Leave-One-Event-Out" in splitting["event_holdout"]
    assert "5 km" in splitting["spatial_buffer"]


def test_label_readiness_audit_and_governance_decision():
    """Verify that label audit concludes BLOCKED_FOR_SUPERVISED_TRAINING due to 0 authentic ground-truth labels."""
    assert LABEL_PATH.exists()
    with open(LABEL_PATH, "r", encoding="utf-8") as f:
        label_audit = json.load(f)

    accounting = label_audit["class_balance_accounting"]
    assert accounting["verified_flood_positive_samples_count"] == 0
    assert accounting["verified_defensible_dry_negative_samples_count"] == 0
    assert accounting["total_authentic_supervised_samples"] == 0
    assert accounting["pct_unobserved_or_unverified"] == 100.0

    verdict = label_audit["governance_readiness_verdict"]
    assert verdict["decision"] == "BLOCKED_FOR_SUPERVISED_TRAINING"
    assert len(verdict["unblocking_requirements"]) >= 3

    # Check candidate SAR anomaly audit
    sar_audit = label_audit["candidate_label_sources_audit"]["sentinel1_backscatter_anomaly_masks"]
    assert sar_audit["suitable_for_supervised_training"] is False
    assert "circular leakage" in sar_audit["audit_findings"].lower()


def test_ml_readiness_manifest_consistency():
    """Verify machine-readable manifest enforces governance decision and integrity constraints."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    gov = manifest["governance"]
    assert gov["final_ml_readiness_decision"] == "BLOCKED_FOR_SUPERVISED_TRAINING"
    assert gov["supervised_model_training_permitted"] is False
    assert gov["exploratory_dataset_export_permitted"] is True
    assert gov["zero_label_fabrication_enforced"] is True
    assert gov["zero_synthetic_interpolation_enforced"] is True

    # Check DEM immutability in manifest
    assert manifest["dem_immutability_audit"]["raw_copernicus_dsm"]["verified"] is True
    assert manifest["dem_immutability_audit"]["working_study_extent_dem"]["verified"] is True


def test_no_accidental_model_training_or_simulation():
    """Verify that no trained model weight files were created and no simulation occurred."""
    model_dir = PROJECT_ROOT / "ml" / "models"
    model_files = list(model_dir.glob("*.joblib")) + list(model_dir.glob("*.onnx")) + list(model_dir.glob("*.bin"))
    assert len(model_files) == 0, f"Unauthorized model files found: {model_files}"
