"""
Unit and Integration Tests for AQUORA Phase 7F Stage 3 — DFO3382 Dataset Assembly.

Validates:
1. Native DFO Grid Preservation (~250m, EPSG:4326, no 30m upsampling)
2. Correct flood/dry/permanent-water/cloud/NoData handling & exclusion criteria
3. No 30m label upsampling (labels are on ~250m DFO cells)
4. Correct 30m-to-DFO feature aggregation & circular aspect statistics
5. CRS and affine alignment
6. Missing rainfall preservation (100% NaN, explicit missing indicator)
7. Feature compatibility checks (flagged NOT_COMPATIBLE_WITH_PHASE7E_MODEL)
8. No DFO2507 access or leakage
9. No modification of existing Phase 7E artifacts
10. Manifest and output hash integrity
11. Delta sub-basin topological reconciliation
"""

import json
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import rasterio
import yaml


@pytest.fixture(scope="module")
def dataset_df():
    path = Path("data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet")
    assert path.exists(), f"Dataset not found at {path}"
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def manifest_data():
    path = Path("data/manifests/phase7f_stage3_dataset_manifest.yaml")
    assert path.exists(), f"Manifest not found at {path}"
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def summary_data():
    path = Path("data/processed/phase7/datasets/dfo3382_label_quality_summary.json")
    assert path.exists(), f"Summary JSON not found at {path}"
    with open(path) as f:
        return json.load(f)


def test_native_dfo_grid_preservation_and_no_upsampling(dataset_df):
    """Test that DFO labels remain at native ~250m resolution and are NOT upsampled to 30m."""
    dfo_raw_path = Path("data/raw/phase7/ground_truth/gfd/DFO_3382/DFO_3382_From_20080922_to_20080929.tif")
    with rasterio.open(dfo_raw_path) as src:
        expected_res = abs(src.transform.a)
        expected_crs = src.crs.to_string()

    # Check resolution (~0.002245788 deg)
    assert abs(expected_res - 0.002245788210298804) < 1e-9
    assert expected_crs == "EPSG:4326"

    # Verify cell dimensions in dataset match native DFO cell spacing
    dlat = dataset_df["lat_max"] - dataset_df["lat_min"]
    dlon = dataset_df["lon_max"] - dataset_df["lon_min"]
    np.testing.assert_allclose(dlat, expected_res, rtol=1e-5)
    np.testing.assert_allclose(dlon, expected_res, rtol=1e-5)

    # Confirm dataset row count is ~1.09 million (native DFO cells), NOT ~155 million (30m cells)
    assert len(dataset_df) == 1090194
    assert len(dataset_df) < 2000000


def test_label_semantics_and_exclusion_criteria(dataset_df, summary_data):
    """Test clean flood/dry target labels, permanent water exclusion, and clear view threshold."""
    labels = dataset_df["flood_label"].value_counts()
    n_flood = int(labels[1])
    n_dry = int(labels[0])

    assert n_flood == 24986
    assert n_dry == 1065208
    prevalence = (n_flood / len(dataset_df)) * 100.0
    assert abs(prevalence - 2.2918856) < 1e-4

    # Permanent water exclusion: no eligible sample has JRC permanent water = 1.0
    assert (dataset_df["gfd_jrc_perm_water"] == 1.0).sum() == 0

    # Clear observation threshold: all eligible samples must have clear_perc >= 0.70
    assert (dataset_df["gfd_clear_perc"] < 0.70).sum() == 0

    # Label quality rubric verified
    assert "label_quality" in dataset_df.columns
    quality_counts = dataset_df["label_quality"].value_counts()
    assert quality_counts["HIGH_QUALITY"] == 777437
    assert quality_counts["MIXED_WATER_MARGIN"] == 262365
    assert quality_counts["MEDIUM_QUALITY"] == 50392


def test_30m_to_dfo_feature_aggregation_integrity(dataset_df):
    """Test multi-scale spatial aggregation of 30m terrain and hydrographic layers."""
    # 30m pixel count per DFO cell
    min_pixels = dataset_df["total_30m_pixel_count"].min()
    max_pixels = dataset_df["total_30m_pixel_count"].max()
    mean_pixels = dataset_df["total_30m_pixel_count"].mean()
    assert min_pixels >= 1
    assert max_pixels <= 100
    assert 60 <= mean_pixels <= 70

    # Elevation aggregates (filter out NaNs over open water / off-domain)
    valid_elev = ~dataset_df["elevation_mean_m"].isna()
    assert (dataset_df.loc[valid_elev, "elevation_max_m"] >= dataset_df.loc[valid_elev, "elevation_min_m"]).all()
    assert (dataset_df.loc[valid_elev, "elevation_mean_m"] >= dataset_df.loc[valid_elev, "elevation_min_m"]).all()
    assert (dataset_df.loc[valid_elev, "elevation_mean_m"] <= dataset_df.loc[valid_elev, "elevation_max_m"]).all()

    # Slope aggregates
    valid_slope = ~dataset_df["slope_mean_deg"].isna()
    assert (dataset_df.loc[valid_slope, "slope_max_deg"] >= dataset_df.loc[valid_slope, "slope_mean_deg"]).all()

    # Circular aspect statistics (no naive arithmetic mean)
    valid_aspect = ~dataset_df["aspect_mean_cos"].isna()
    assert (dataset_df.loc[valid_aspect, "aspect_mean_cos"] >= -1.0).all()
    assert (dataset_df.loc[valid_aspect, "aspect_mean_cos"] <= 1.0).all()
    assert (dataset_df.loc[valid_aspect, "aspect_circular_var"] >= -1e-6).all()
    assert (dataset_df.loc[valid_aspect, "aspect_circular_var"] <= 1.0001).all()

    # Hydrographic distances
    valid_driver = ~dataset_df["dist_to_river_mean_m"].isna()
    assert (dataset_df.loc[valid_driver, "dist_to_river_mean_m"] >= dataset_df.loc[valid_driver, "dist_to_river_min_m"]).all()


def test_crs_affine_alignment_and_bounds(dataset_df):
    """Test CRS consistency and bounding box alignment."""
    # Bounds within domain with 1-pixel buffer for discrete cell centers
    pixel_tol = 0.003 # ~1 pixel width buffer (0.002246 deg)
    assert (dataset_df["longitude"] >= 84.0 - pixel_tol).all()
    assert (dataset_df["longitude"] <= 88.0 + pixel_tol).all()
    assert (dataset_df["latitude"] >= 19.0 - pixel_tol).all()
    assert (dataset_df["latitude"] <= 22.0 + pixel_tol).all()

    # Center is midpoint of bounds
    mid_lon = (dataset_df["lon_min"] + dataset_df["lon_max"]) / 2.0
    mid_lat = (dataset_df["lat_min"] + dataset_df["lat_max"]) / 2.0
    np.testing.assert_allclose(dataset_df["longitude"], mid_lon, rtol=1e-5)
    np.testing.assert_allclose(dataset_df["latitude"], mid_lat, rtol=1e-5)


def test_rainfall_availability_and_zero_imputation(dataset_df):
    """Test that missing rainfall is 100% preserved as NaN with zero synthetic imputation."""
    rain_cols = [
        "phase7e_rainfall_accum_6h_mm",
        "phase7e_rainfall_accum_24h_mm",
        "phase7e_rainfall_accum_72h_mm"
    ]
    for c in rain_cols:
        assert dataset_df[c].isna().sum() == len(dataset_df), f"Violation: {c} contains fabricated values!"

    assert (dataset_df["rainfall_missing_indicator"] == 1).all()


def test_phase7e_model_incompatibility_safeguards(dataset_df):
    """Test that dataset is explicitly marked NOT_COMPATIBLE_WITH_PHASE7E_MODEL."""
    assert (dataset_df["phase7e_model_compatible"] == False).all()
    assert (dataset_df["phase7e_incompatibility_reason"] == "RAINFALL_ACCUMULATION_UNAVAILABLE").all()


def test_dfo2507_quarantine_and_isolation(dataset_df):
    """Test strict isolation of DFO 2507 holdout."""
    assert (dataset_df["event_id"] == "DFO_3382").all()
    assert "2507" not in str(dataset_df["event_id"].unique())


def test_phase7e_artifacts_immutability():
    """Test that Phase 7E artifacts and schema have not been altered."""
    schema_path = Path("ml/aquora_ml_feature_schema_v1.json")
    with open(schema_path) as f:
        schema = json.load(f)
    assert schema["schema_name"] == "aquora_ml_feature_schema_v1"
    assert len(schema["tiers"]["CORE_NATIONAL"]["features"]) == 11
    assert "rainfall_6h_mm" in schema["tiers"]["CORE_NATIONAL"]["features"]


def test_manifest_and_output_hash_integrity(manifest_data):
    """Test manifest completeness and cryptographic hashes of generated assets."""
    assert manifest_data["manifest_metadata"]["decision"] == "DATASET_ASSEMBLY_COMPLETE"
    assert manifest_data["manifest_metadata"]["benchmark_event"] == "DFO_3382_MAHANADI_2008"

    # Verify Parquet checksum matches manifest
    parquet_path = Path("data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet")
    with open(parquet_path, "rb") as f:
        computed_hash = hashlib.sha256(f.read()).hexdigest()
    
    assert computed_hash == manifest_data["dataset_outputs"]["authoritative_master_parquet"]["sha256"]


def test_delta_subbasin_topology_reconciliation():
    """Test topological reconciliation of the 7 delta sub-basins draining to Bay of Bengal."""
    delta_subbasins_path = Path("data/processed/phase7/boundaries/mahanadi_hydrobasins/mahanadi_delta_lev08_subbasins.geojson")
    with open(delta_subbasins_path) as f:
        geo = json.load(f)
    
    subbasin_props = {f["properties"]["HYBAS_ID"]: f["properties"] for f in geo["features"]}
    assert len(subbasin_props) == 7

    # Upstream to downstream tree
    next_downs = {sid: p["NEXT_DOWN"] for sid, p in subbasin_props.items()}
    assert next_downs[4080027100] == 0 # Coastal outlet into Bay of Bengal
    assert next_downs[4081039610] == 4080027100
    assert next_downs[4081037140] == 4081039610
    assert next_downs[4081038340] == 4081037140
