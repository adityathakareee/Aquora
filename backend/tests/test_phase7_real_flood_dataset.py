"""
AQUORA Phase 7: Real Flood Dataset Verification Test Suite.

Comprehensive automated test suite validating:
1. Source Provenance & Immutability: GFD raster, Copernicus DEM, CHIRPS daily precipitation files.
2. Dataset Artifacts & Schema Conformance: Exactly the 11 CORE_NATIONAL features from
   ml/aquora_ml_feature_schema_v1.json in governed order.
3. Spatial CRS & Bounding Box Alignment: EPSG:4326 coordinate fidelity within study domain.
4. Physical Predictor Units & Value Ranges: Rainfall (mm), elevation (m), slope (deg [0, 90]), distance (m >= 0).
5. Ground Truth Label Fidelity & Rejection Gate:
   - Asserts zero floodwater in permanent water bodies ((flooded==1) & (perm==1) => label == -1).
   - Asserts zero cloudy unobserved false negatives (all dry samples have clear_perc >= 0.70).
   - Asserts distinct classification of flood (1), verified dry (0), and excluded (-1).
6. Spatial Cross-Validation Zero-Leakage:
   - Spatially disjoint sub-basins strictly partitioned between train, validation, and test.
   - Asserts zero overlapping basins across folds (train ∩ val == ∅, train ∩ test == ∅, val ∩ test == ∅).
7. Manifest & Hash Verification: Asserts manifest SHA-256 checksums exactly match serialized files.
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

# Source Asset Paths
RAW_GFD_DIR = REPO_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "gfd"
DFO_4499_TIF = RAW_GFD_DIR / "DFO_4499" / "DFO_4499_From_20170727_to_20170810.tif"
RAW_DEM_PATH = REPO_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N22_00_E088_00_DEM.tif"
CHIRPS_DIR = REPO_ROOT / "data" / "raw" / "phase7" / "rainfall" / "chirps" / "daily"

# Output Deliverable Paths
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "phase7" / "ml"
PARQUET_PATH = OUTPUT_DIR / "phase7_gfd_pilot_dataset.parquet"
CSV_PATH = OUTPUT_DIR / "phase7_gfd_pilot_dataset.csv"
MANIFEST_PATH = REPO_ROOT / "data" / "manifests" / "phase7_real_flood_dataset_manifest.yaml"
SCHEMA_PATH = REPO_ROOT / "ml" / "aquora_ml_feature_schema_v1.json"
GFD_CATALOG_CSV = REPO_ROOT / "data" / "processed" / "phase7" / "ground_truth" / "gfd_india_events_catalog.csv"

# Expected Provenance Hashes
EXPECTED_GFD_TIF_SHA256 = "9fab987aa7cb9becaf607c0960799b1e72b217ddd9bb7940e08e902349c1f4eb"
EXPECTED_DEM_SHA256 = "018d3e47ae82f12f08e22681ebbf553f3dd0ebd0a33aff248d5dd717bf9a61ed"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------------------------------------------------------
# 1. Source Provenance & Immutability Tests
# -----------------------------------------------------------------------------
def test_source_provenance_and_immutability():
    """Verify authentic raw ground truth and predictor assets are present with verified checksums."""
    assert DFO_4499_TIF.exists(), f"Missing GFD GeoTIFF: {DFO_4499_TIF}"
    assert compute_sha256(DFO_4499_TIF) == EXPECTED_GFD_TIF_SHA256, "GFD GeoTIFF SHA-256 checksum mismatch"

    assert RAW_DEM_PATH.exists(), f"Missing Copernicus DEM tile: {RAW_DEM_PATH}"
    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_DEM_SHA256, "Copernicus DEM SHA-256 checksum mismatch"

    # CHIRPS daily files
    for d in ["2017.07.25", "2017.07.26", "2017.07.27"]:
        f = CHIRPS_DIR / f"chirps-v2.0.{d}.tif.gz"
        assert f.exists(), f"Missing CHIRPS daily file: {f}"
        assert f.stat().st_size > 2_000_000, f"CHIRPS daily file abnormally small: {f.stat().st_size} bytes"

    # GFD India catalog
    assert GFD_CATALOG_CSV.exists(), "Missing GFD India catalog CSV"
    df_cat = pd.read_csv(GFD_CATALOG_CSV)
    assert len(df_cat) == 91, f"Expected 91 GFD India flood events, found {len(df_cat)}"


# -----------------------------------------------------------------------------
# 2. Dataset Artifacts & Schema Conformance Tests
# -----------------------------------------------------------------------------
def test_dataset_artifacts_and_schema():
    """Verify generated dataset files exist, contain exact row counts, and follow feature schema."""
    assert PARQUET_PATH.exists(), "Parquet dataset file missing"
    assert CSV_PATH.exists(), "CSV dataset file missing"

    df_parquet = pd.read_parquet(PARQUET_PATH)
    df_csv = pd.read_csv(CSV_PATH)

    assert len(df_parquet) == 5500, f"Expected exactly 5,500 samples in Parquet, got {len(df_parquet)}"
    assert len(df_csv) == 5500, f"Expected exactly 5,500 samples in CSV, got {len(df_csv)}"

    # Load official schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    expected_core_features = schema["tiers"]["CORE_NATIONAL"]["features"]
    assert len(expected_core_features) == 11

    # Verify all 11 core features are in DataFrame
    for feat in expected_core_features:
        assert feat in df_parquet.columns, f"Mandatory feature missing: {feat}"

    # Verify forbidden leakage fields are not present in predictors
    forbidden_in_predictors = [
        "sar_delta_vv_db",
        "sar_scene_id",
        "water_depth_m",
        "flow_velocity_ms",
        "modeled_depth_m",
    ]
    for forbidden in forbidden_in_predictors:
        assert forbidden not in df_parquet.columns, f"Leakage column found: {forbidden}"


# -----------------------------------------------------------------------------
# 3. Spatial CRS & Coordinate Alignment Tests
# -----------------------------------------------------------------------------
def test_spatial_crs_and_coordinate_alignment():
    """Verify coordinate bounds fall strictly inside Lower Ganga study extent in EPSG:4326."""
    df = pd.read_parquet(PARQUET_PATH)

    assert df["longitude"].min() >= 87.99, f"Longitude below min bound: {df['longitude'].min()}"
    assert df["longitude"].max() <= 89.01, f"Longitude above max bound: {df['longitude'].max()}"
    assert df["latitude"].min() >= 21.99, f"Latitude below min bound: {df['latitude'].min()}"
    assert df["latitude"].max() <= 23.01, f"Latitude above max bound: {df['latitude'].max()}"

    # Zero duplicate points
    assert df[["longitude", "latitude"]].duplicated().sum() == 0, "Duplicate coordinate pairs detected"


# -----------------------------------------------------------------------------
# 4. Predictor Units & Value Ranges Tests
# -----------------------------------------------------------------------------
def test_predictor_units_and_ranges():
    """Verify physical predictor columns adhere to rigorous unit definitions and realistic bounds."""
    df = pd.read_parquet(PARQUET_PATH)

    # 1. 24h & 72h Rainfall (mm)
    assert df["rainfall_24h_mm"].min() >= 0.0, "Negative 24h rainfall detected"
    assert df["rainfall_24h_mm"].max() <= 1000.0, "Unrealistic 24h rainfall (>1000mm)"
    assert df["rainfall_72h_mm"].min() >= 0.0, "Negative 72h rainfall detected"
    assert (df["rainfall_72h_mm"] >= df["rainfall_24h_mm"]).all(), "72h rainfall must be >= 24h rainfall"

    # Null preservation: 1h, 3h, 6h rainfall must be explicit nulls under Zero-Fabrication
    assert df["rainfall_1h_mm"].isnull().all(), "Unobserved 1h rainfall must remain NaN"
    assert df["rainfall_3h_mm"].isnull().all(), "Unobserved 3h rainfall must remain NaN"
    assert df["rainfall_6h_mm"].isnull().all(), "Unobserved 6h rainfall must remain NaN"

    # 2. Elevation (meters MSL)
    assert df["elevation_m"].min() >= -10.0, "Elevation physically unrealistic (< -10m)"
    assert df["elevation_m"].max() <= 100.0, "Elevation unrealistic for Bengal delta (> 100m)"

    # 3. Slope (degrees [0, 90])
    assert df["slope_deg"].min() >= 0.0, "Negative slope detected"
    assert df["slope_deg"].max() <= 90.0, "Slope exceeds 90 degrees"
    assert df["slope_deg"].mean() < 10.0, "Bengal floodplain mean slope should be low (< 10 deg)"

    # 4. Distance to River (meters, >= 0)
    assert df["distance_to_river_m"].min() >= 0.0, "Negative river distance detected"
    assert df["distance_to_river_m"].max() < 100_000.0, "River distance abnormally large (>100km)"

    # 5. Historical flood frequency (events/decade)
    assert (df["historical_flood_frequency"] > 0.0).all(), "Flood frequency must be positive"

    # 6. Landcover class (ESA WorldCover codes: 40, 50, 80, 90)
    valid_lc_codes = {40, 50, 80, 90}
    actual_lc_codes = set(df["landcover_class"].unique())
    assert actual_lc_codes.issubset(valid_lc_codes), f"Unexpected landcover codes: {actual_lc_codes}"


# -----------------------------------------------------------------------------
# 5. Ground Truth Label Fidelity & Rejection Gate Tests
# -----------------------------------------------------------------------------
def test_label_fidelity_and_rejection_gate():
    """Verify scientific classification of flood, dry ground, and permanent water."""
    df = pd.read_parquet(PARQUET_PATH)

    # Class counts
    counts = df["flood_label"].value_counts().to_dict()
    assert counts.get(1) == 2500, f"Expected 2,500 verified flood samples, got {counts.get(1)}"
    assert counts.get(0) == 2500, f"Expected 2,500 verified dry samples, got {counts.get(0)}"
    assert counts.get(-1) == 500, f"Expected 500 permanent water / excluded samples, got {counts.get(-1)}"

    # Permanent Water Rejection Gate:
    # Any cell with jrc_perm_water == 1.0 MUST NOT have flood_label == 1
    perm_flooded_leak = df[(df["gfd_jrc_perm_water"] == 1.0) & (df["flood_label"] == 1)]
    assert len(perm_flooded_leak) == 0, "Permanent water cell falsely labeled as episodic flood (flood_label=1)"

    # Dry Sample Visibility Gate:
    # All verified dry cells (flood_label == 0) must have clear_perc >= 0.70
    cloudy_dry_leak = df[(df["flood_label"] == 0) & (df["gfd_clear_perc"] < 0.70)]
    assert len(cloudy_dry_leak) == 0, "Cloudy observation falsely labeled as verified dry ground"

    # Label quality flags must match labels exactly
    assert (df[df["flood_label"] == 1]["label_quality_flag"] == "VERIFIED_EPISODIC_FLOOD").all()
    assert (df[df["flood_label"] == 0]["label_quality_flag"] == "VERIFIED_DRY_GROUND").all()
    assert (df[df["flood_label"] == -1]["label_quality_flag"] == "EXCLUDED_PERMANENT_WATER").all()


# -----------------------------------------------------------------------------
# 6. Spatial Cross-Validation Zero-Leakage Tests
# -----------------------------------------------------------------------------
def test_spatial_cross_validation_zero_leakage():
    """Verify that spatial sub-basins are strictly partitioned across train/val/test splits."""
    df = pd.read_parquet(PARQUET_PATH)

    assert "basin_id" in df.columns
    assert "split" in df.columns

    train_basins = set(df[df["split"] == "train"]["basin_id"].unique())
    val_basins = set(df[df["split"] == "validation"]["basin_id"].unique())
    test_basins = set(df[df["split"] == "test"]["basin_id"].unique())

    # Sub-basin disjointness
    assert len(train_basins.intersection(val_basins)) == 0, (
        f"Spatial Leakage between Train and Validation: {train_basins.intersection(val_basins)}"
    )
    assert len(train_basins.intersection(test_basins)) == 0, (
        f"Spatial Leakage between Train and Test: {train_basins.intersection(test_basins)}"
    )
    assert len(val_basins.intersection(test_basins)) == 0, (
        f"Spatial Leakage between Validation and Test: {val_basins.intersection(test_basins)}"
    )

    # Minimum representation per split
    assert len(df[df["split"] == "train"]) >= 2000, "Train split contains too few samples"
    assert len(df[df["split"] == "validation"]) >= 500, "Validation split contains too few samples"
    assert len(df[df["split"] == "test"]) >= 500, "Test split contains too few samples"


# -----------------------------------------------------------------------------
# 7. Manifest & Hash Verification Tests
# -----------------------------------------------------------------------------
def test_manifest_consistency_and_hashes():
    """Verify the Phase 7 manifest exists and its recorded checksums match on-disk files."""
    assert MANIFEST_PATH.exists(), "Manifest file missing"

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["phase"] == "PHASE_7_REAL_FLOOD_DATASET_BUILD"
    assert manifest["governance_status"] == "APPROVED_REAL_SATELLITE_GROUND_TRUTH"

    # Master files
    master_parquet_meta = manifest["dataset_files"]["master_dataset"]["parquet"]
    master_csv_meta = manifest["dataset_files"]["master_dataset"]["csv"]
    assert compute_sha256(PARQUET_PATH) == master_parquet_meta["sha256"], "Master Parquet SHA-256 does not match manifest"
    assert compute_sha256(CSV_PATH) == master_csv_meta["sha256"], "Master CSV SHA-256 does not match manifest"

    # Binary training files
    bin_parquet_path = OUTPUT_DIR / "phase7_gfd_pilot_binary_dataset.parquet"
    bin_csv_path = OUTPUT_DIR / "phase7_gfd_pilot_binary_dataset.csv"
    bin_parquet_meta = manifest["dataset_files"]["binary_training_dataset"]["parquet"]
    bin_csv_meta = manifest["dataset_files"]["binary_training_dataset"]["csv"]
    assert compute_sha256(bin_parquet_path) == bin_parquet_meta["sha256"], "Binary Parquet SHA-256 does not match manifest"
    assert compute_sha256(bin_csv_path) == bin_csv_meta["sha256"], "Binary CSV SHA-256 does not match manifest"


# -----------------------------------------------------------------------------
# 8. Independent Raw Pixel Extraction & Numerical Tolerance Tests
# -----------------------------------------------------------------------------
def test_independent_raw_pixel_extraction_tolerance():
    """Verify point values match independent raw GeoTIFF queries within numerical precision."""
    import gzip
    import rasterio

    df = pd.read_parquet(PARQUET_PATH)
    sample_pts = df.sample(20, random_state=123)

    # 1. Independent CHIRPS rainfall verification
    chirps_f = CHIRPS_DIR / "chirps-v2.0.2017.07.27.tif.gz"
    with gzip.open(chirps_f, "rb") as gz:
        with rasterio.open(gz) as src:
            for _, row in sample_pts.iterrows():
                r, c = src.index(row["longitude"], row["latitude"])
                val = float(src.read(1, window=((r, r + 1), (c, c + 1)))[0, 0])
                assert abs(val - row["rainfall_24h_mm"]) < 0.01, (
                    f"CHIRPS rainfall extraction mismatch at {row['point_id']}: dataset={row['rainfall_24h_mm']}, raw={val}"
                )

    # 2. Independent Copernicus DEM elevation verification
    with rasterio.open(RAW_DEM_PATH) as src:
        for _, row in sample_pts.iterrows():
            r, c = src.index(row["longitude"], row["latitude"])
            val = float(src.read(1, window=((r, r + 1), (c, c + 1)))[0, 0])
            assert abs(val - row["elevation_m"]) < 0.01, (
                f"DEM elevation extraction mismatch at {row['point_id']}: dataset={row['elevation_m']}, raw={val}"
            )


# -----------------------------------------------------------------------------
# 9. Binary Training Dataset Isolation Tests
# -----------------------------------------------------------------------------
def test_binary_training_dataset_isolation():
    """Verify binary training package strictly excludes label=-1 permanent water controls."""
    bin_parquet_path = OUTPUT_DIR / "phase7_gfd_pilot_binary_dataset.parquet"
    bin_csv_path = OUTPUT_DIR / "phase7_gfd_pilot_binary_dataset.csv"

    assert bin_parquet_path.exists()
    assert bin_csv_path.exists()

    df_bin = pd.read_parquet(bin_parquet_path)
    assert len(df_bin) == 5000, f"Expected exactly 5,000 binary samples, got {len(df_bin)}"

    # Strictly 0 and 1
    labels = df_bin["flood_label"].unique()
    assert set(labels) == {0, 1}, f"Unexpected labels in binary dataset: {labels}"
    assert (df_bin["flood_label"] == -1).sum() == 0, "Permanent water controls (label=-1) leaked into binary training set"

    # Perfect class balance in master binary pool
    assert (df_bin["flood_label"] == 1).sum() == 2500
    assert (df_bin["flood_label"] == 0).sum() == 2500


# -----------------------------------------------------------------------------
# 10. Optical Confidence & Permanent Water Accounting Audit
# -----------------------------------------------------------------------------
def test_optical_confidence_and_cloud_accounting():
    """Verify that cloud-affected cells (<70%) are exactly 0, and permanent water is exactly 72,887."""
    import rasterio

    with rasterio.open(DFO_4499_TIF) as src:
        flooded = src.read(1)
        clear_perc = src.read(4)
        jrc_perm = src.read(5)

        valid = ~np.isnan(flooded)

        # Clear percentage range on valid cells
        min_clear = float(np.nanmin(clear_perc[valid]))
        max_clear = float(np.nanmax(clear_perc[valid]))
        assert min_clear >= 0.82, f"Expected clear_perc >= 82%, found {min_clear}"
        assert max_clear <= 1.0

        # Assert zero cells with clear_perc < 0.70 within the mapped footprint
        cloudy_cells = int(((clear_perc < 0.70) & valid).sum())
        assert cloudy_cells == 0, f"Found {cloudy_cells} cloud-affected cells"

        # Assert exact permanent water cells count
        perm_cells = int(((jrc_perm == 1.0) & valid).sum())
        assert perm_cells == 72887, f"Expected 72,887 permanent water cells, found {perm_cells}"


# -----------------------------------------------------------------------------
# 11. Event-Level Isolation & Within-Event Scope Tests
# -----------------------------------------------------------------------------
def test_event_isolation_and_within_event_limitation():
    """Assert single-event limitation: spatial cross-validation is a within-event spatial holdout."""
    df = pd.read_parquet(PARQUET_PATH)

    # Asserts all samples originate from DFO 4499
    assert df["event_id"].nunique() == 1
    assert df["event_id"].iloc[0] == "DFO_4499"

    # Single observation date
    assert df["observation_date"].nunique() == 1
    assert df["observation_date"].iloc[0] == "2017-07-27"

    # Audit notice: zero-variance historical flood frequency in single-event pilot
    assert df["historical_flood_frequency"].nunique() == 1, (
        "Historical flood frequency must have 1 regional value in single-event pilot"
    )

    # Documented notice: model calibration is BLOCKED until multi-event ingestion
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
    assert "PILOT_PIPELINE_VALIDATION_ONLY" in manifest.get("pilot_scope_notice", "")

