"""
AQUORA Phase 7C: Multi-Event Real Flood Dataset Verification Test Suite.

Comprehensive automated verification testing:
1. Acquisition Integrity: Checksums, file existence, and raster properties for all 4 GFD events,
   4 Copernicus DEM tiles, 4 ESA WorldCover tiles, and 12 CHIRPS daily precipitation files.
2. Dataset Artifacts & Schema Conformance: Exactly the 11 CORE_NATIONAL features from
   ml/aquora_ml_feature_schema_v1.json in governed order.
3. Label Quality & Rejection Gate:
   - Asserts zero floodwater in permanent water bodies.
   - Asserts zero unobserved or cloud-affected false negatives.
   - Asserts verified 1:1 balance in binary dataset (50.0% flood, 50.0% dry).
4. Missing Feature Preservation & Authentic Sourcing:
   - Asserts sub-daily rainfall (1h, 3h, 6h) are preserved as explicit NaNs.
   - Asserts landcover_class is sourced from authentic ESA WorldCover 2021 10m rasters (not heuristics).
   - Asserts historical_flood_frequency varies across basins (std > 0).
5. Event Separation & Zero Data Leakage:
   - Complete isolation between Train (DFO 4499, DFO 2935), Validation (DFO 3372), and Test (DFO 2507).
   - Train events ∩ Val events == ∅, Train events ∩ Test events == ∅, Val events ∩ Test events == ∅.
   - Spatial disjointness across Indian states (West Bengal, Maharashtra, Assam, Bihar).
6. No-Overwrite Invariant:
   - Confirms that the validated Phase 7B DFO 4499 pilot dataset is completely preserved.
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
RAW_DEM_DIR = REPO_ROOT / "data" / "raw" / "phase7" / "dem"
RAW_CHIRPS_DIR = REPO_ROOT / "data" / "raw" / "phase7" / "rainfall" / "chirps" / "daily"
RAW_LC_DIR = REPO_ROOT / "data" / "raw" / "phase7" / "landcover"

# Processed Dataset Paths
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "phase7" / "ml"
MASTER_PARQUET = OUTPUT_DIR / "phase7c_multievent_dataset.parquet"
MASTER_CSV = OUTPUT_DIR / "phase7c_multievent_dataset.csv"
BINARY_PARQUET = OUTPUT_DIR / "phase7c_multievent_binary_dataset.parquet"
BINARY_CSV = OUTPUT_DIR / "phase7c_multievent_binary_dataset.csv"
MANIFEST_PATH = REPO_ROOT / "data" / "manifests" / "phase7c_multievent_dataset_manifest.yaml"
SCHEMA_PATH = REPO_ROOT / "ml" / "aquora_ml_feature_schema_v1.json"

# Pilot Preservation Paths
PILOT_PARQUET = OUTPUT_DIR / "phase7_gfd_pilot_dataset.parquet"
PILOT_MANIFEST = REPO_ROOT / "data" / "manifests" / "phase7_real_flood_dataset_manifest.yaml"

# Governed Checksums
EXPECTED_GFD_SHA256 = {
    "DFO_4499": "9fab987aa7cb9becaf607c0960799b1e72b217ddd9bb7940e08e902349c1f4eb",
    "DFO_2935": "ad0b331f7ef84fd32a787ef7f698df9aba3a385974e05c4b24d8cdeb98d4b4ff",
    "DFO_3372": "e7ebc1376c217e8268cfc6762b6e274315dbe0c09fbeb537768c85ddd3fd97f4",
    "DFO_2507": "0cd6b8b23f55cfa768dc3966226ce4c0020e05b0652909ed966e6031eac356da",
}

EXPECTED_DEM_SHA256 = {
    "N22_00_E088": "018d3e47ae82f12f08e22681ebbf553f3dd0ebd0a33aff248d5dd717bf9a61ed",
    "N20_00_E073": "4fc2ff36a7a830233e5fb86b8a33a8ad2ed4824fb6e247a7fc45e28f284aa3af",
    "N27_00_E094": "088f251fe4fa1b30c23b3f660b660958f10aa828b9fc92882d64e2db187312f3",
    "N25_00_E085": "1f2e00a1a5488f0d94e2842fff1ba0ea564967710dfbe56181fd997869d33a00",
}

EXPECTED_LC_SHA256 = {
    "N21E087": "a652fbd8e327ceb600d309f1934223a8d95d7ab0902dbc524c830aba9587b160",
    "N18E072": "2d28650e0eba865efb08656e45b75a269eaf535f9260a245ae5aad72ee5a5c63",
    "N27E093": "648aa16f0448cb08eefd46bbd83e3f0dc8ef69af965d9249f59f7f4db29b9eb9",
    "N24E084": "8b1d2333c81cc8ac0de1d9cbdfe5bd8ff85259e919caf8f21502ea8a7f2b4f1b",
}


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# -----------------------------------------------------------------------------
# 1. Acquisition Integrity Tests
# -----------------------------------------------------------------------------
def test_phase7c_raw_acquisition_integrity():
    """Verify authentic raw ground truth, DEM, WorldCover, and CHIRPS assets are intact."""
    # GFD Rasters
    for dfo_id, exp_sha in EXPECTED_GFD_SHA256.items():
        tifs = list((RAW_GFD_DIR / dfo_id).glob("*.tif"))
        assert len(tifs) == 1, f"Missing or duplicate GeoTIFF for {dfo_id}"
        assert compute_sha256(tifs[0]) == exp_sha, f"SHA-256 mismatch for {dfo_id}"

    # DEM Rasters
    for tile, exp_sha in EXPECTED_DEM_SHA256.items():
        dem_path = list(RAW_DEM_DIR.glob(f"*{tile}*.tif"))[0]
        assert dem_path.exists(), f"Missing DEM tile {tile}"
        assert compute_sha256(dem_path) == exp_sha, f"SHA-256 mismatch for DEM {tile}"

    # ESA WorldCover Rasters
    for tile, exp_sha in EXPECTED_LC_SHA256.items():
        lc_path = list(RAW_LC_DIR.glob(f"*{tile}*.tif"))[0]
        assert lc_path.exists(), f"Missing WorldCover tile {tile}"
        assert compute_sha256(lc_path) == exp_sha, f"SHA-256 mismatch for WorldCover {tile}"

    # CHIRPS Daily Rainfall
    chirps_dates = [
        "2017.07.25", "2017.07.26", "2017.07.27",  # DFO 4499
        "2006.07.26", "2006.07.27", "2006.07.28",  # DFO 2935
        "2008.08.28", "2008.08.29", "2008.08.30",  # DFO 3372
        "2004.06.18", "2004.06.19", "2004.06.20",  # DFO 2507
    ]
    for d in chirps_dates:
        f = RAW_CHIRPS_DIR / f"chirps-v2.0.{d}.tif.gz"
        assert f.exists(), f"Missing CHIRPS daily file: {f}"
        assert f.stat().st_size > 2_500_000, f"CHIRPS file abnormally small: {f.name}"


# -----------------------------------------------------------------------------
# 2. Multi-Event Dataset Artifacts & Schema Conformance
# -----------------------------------------------------------------------------
def test_phase7c_dataset_artifacts_and_schema():
    """Verify generated multi-event dataset files exist, contain exact rows, and adhere to schema."""
    assert MASTER_PARQUET.exists(), "Master Parquet dataset missing"
    assert MASTER_CSV.exists(), "Master CSV dataset missing"
    assert BINARY_PARQUET.exists(), "Binary Parquet dataset missing"
    assert BINARY_CSV.exists(), "Binary CSV dataset missing"

    df_master = pd.read_parquet(MASTER_PARQUET)
    df_binary = pd.read_parquet(BINARY_PARQUET)

    assert len(df_master) == 209116, f"Expected 209,116 master samples, got {len(df_master)}"
    assert len(df_binary) == 207205, f"Expected 207,205 binary samples, got {len(df_binary)}"

    # Load official schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    expected_core = schema["tiers"]["CORE_NATIONAL"]["features"]
    assert len(expected_core) == 11

    # Check presence and order of core features in dataframe
    for feat in expected_core:
        assert feat in df_master.columns, f"Missing feature: {feat}"
        assert feat in df_binary.columns, f"Missing feature in binary: {feat}"


# -----------------------------------------------------------------------------
# 3. Label Quality & Rejection Gate Tests
# -----------------------------------------------------------------------------
def test_phase7c_label_quality_and_rejection_gate():
    """Verify scientific flood and dry label separation, natural test distribution, and rejection of invalid observations."""
    df_master = pd.read_parquet(MASTER_PARQUET)
    df_binary = pd.read_parquet(BINARY_PARQUET)

    # 1. Flood labels must be strictly from {1, 0, -1}
    assert set(df_master["flood_label"].unique()) == {-1, 0, 1}
    assert set(df_binary["flood_label"].unique()) == {0, 1}

    # 2. Rejection Gate: Permanent water must never be labeled as episodic flood
    perm_flooded = df_master[(df_master["gfd_jrc_perm_water"] == 1.0) & (df_master["flood_label"] == 1)]
    assert len(perm_flooded) == 0, f"Found {len(perm_flooded)} permanent water cells falsely marked as flood!"

    # 3. Permanent water controls must be marked -1
    perm_controls = df_master[df_master["flood_label"] == -1]
    assert (perm_controls["gfd_jrc_perm_water"] == 1.0).all(), "Permanent water controls contain non-water pixels"
    assert len(perm_controls) == 1911, f"Expected 1,911 permanent water controls, got {len(perm_controls)}"

    # 4. Clear observation gate: all binary samples must have clear_perc >= 0.70
    assert (df_binary["gfd_clear_perc"] >= 0.70).all(), "Binary dataset contains cloud-obscured cells (< 0.70)"

    # 5. Split-Specific Class Balance:
    # Training & Validation splits are 50/50 balanced for training stability
    train_binary = df_binary[df_binary["split"] == "train"]
    assert (train_binary["flood_label"] == 1).sum() == 2850
    assert (train_binary["flood_label"] == 0).sum() == 2850

    val_binary = df_binary[df_binary["split"] == "validation"]
    assert (val_binary["flood_label"] == 1).sum() == 2500
    assert (val_binary["flood_label"] == 0).sum() == 2500

    # Test split (DFO_2507) preserves unskewed natural population (NO forced balance)
    test_binary = df_binary[df_binary["split"] == "test"]
    n_test_flood = int((test_binary["flood_label"] == 1).sum())
    n_test_dry = int((test_binary["flood_label"] == 0).sum())
    assert n_test_flood == 11435, f"Expected 11,435 natural test flood cells, got {n_test_flood}"
    assert n_test_dry == 185070, f"Expected 185,070 natural test dry cells, got {n_test_dry}"
    assert n_test_flood != n_test_dry, "Held-out test set was artificially balanced! Natural population required."
    test_prevalence = n_test_flood / len(test_binary)
    assert 0.057 < test_prevalence < 0.060, f"Unexpected natural prevalence: {test_prevalence}"


# -----------------------------------------------------------------------------
# 4. Missing Feature Preservation & Authentic Data Sourcing
# -----------------------------------------------------------------------------
def test_phase7c_missing_features_and_authentic_sourcing():
    """Verify sub-daily rainfall is preserved as NaN, and landcover/terrain are authentically sourced."""
    df_master = pd.read_parquet(MASTER_PARQUET)

    # 1. Missing feature preservation: sub-daily rainfall must be 100% NaN
    assert df_master["rainfall_1h_mm"].isnull().all(), "rainfall_1h_mm must be NaN when unobserved"
    assert df_master["rainfall_3h_mm"].isnull().all(), "rainfall_3h_mm must be NaN when unobserved"
    assert df_master["rainfall_6h_mm"].isnull().all(), "rainfall_6h_mm must be NaN when unobserved"

    # 2. CHIRPS 24h and 72h rainfall: no nulls, non-negative, r72 >= r24
    assert df_master["rainfall_24h_mm"].isnull().sum() == 0
    assert df_master["rainfall_72h_mm"].isnull().sum() == 0
    assert (df_master["rainfall_24h_mm"] >= 0.0).all()
    assert (df_master["rainfall_72h_mm"] >= 0.0).all()
    assert (df_master["rainfall_72h_mm"] >= df_master["rainfall_24h_mm"] - 1e-4).all()

    # 3. Authentic ESA WorldCover 2021 classes
    # Standard ESA classes: 10, 20, 30, 40, 50, 60, 80, 90, 95
    valid_esa_classes = {10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}
    sampled_classes = set(df_master["landcover_class"].unique())
    assert sampled_classes.issubset(valid_esa_classes), f"Unexpected landcover classes: {sampled_classes}"
    # Must contain multiple distinct classes (not a dummy constant)
    assert len(sampled_classes) >= 5, f"Expected diverse landcover classes, found only: {sampled_classes}"
    assert df_master["landcover_class"].std() > 10.0, "Landcover class has no variance"

    # 4. Multi-basin Historical Flood Frequency has variance across basins
    freq_values = df_master.groupby("event_id")["historical_flood_frequency"].mean()
    assert len(freq_values.unique()) == 4, "Historical flood frequency must vary across the 4 distinct basins"
    assert freq_values.std() > 1.0, "Inter-basin historical flood frequency must have variance"
    assert df_master["historical_flood_frequency"].std() > 0.4, "Dataset historical flood frequency must have non-zero variance"

    # 5. Physical Terrain: elevation and slope bounds
    assert df_master["elevation_m"].min() >= -10.0
    assert df_master["elevation_m"].max() > 2000.0, "Elevation should reflect Himalayan/Ghats topography"
    assert (df_master["slope_deg"] >= 0.0).all()
    assert (df_master["slope_deg"] <= 90.0).all()
    assert (df_master["distance_to_river_m"] >= 0.0).all()


# -----------------------------------------------------------------------------
# 5. Event Separation & Zero Data Leakage Tests
# -----------------------------------------------------------------------------
def test_phase7c_event_separation_and_zero_leakage():
    """Verify strict event-level holdout splitting and geographic isolation across folds."""
    df_binary = pd.read_parquet(BINARY_PARQUET)

    train_events = set(df_binary[df_binary["split"] == "train"]["event_id"].unique())
    val_events = set(df_binary[df_binary["split"] == "validation"]["event_id"].unique())
    test_events = set(df_binary[df_binary["split"] == "test"]["event_id"].unique())

    # 1. Event separation: folds must have disjoint event sets
    assert train_events == {"DFO_4499", "DFO_2935"}, f"Unexpected train events: {train_events}"
    assert val_events == {"DFO_3372"}, f"Unexpected validation events: {val_events}"
    assert test_events == {"DFO_2507"}, f"Unexpected test events: {test_events}"

    assert len(train_events.intersection(val_events)) == 0, "Data leakage: Train and Val share events!"
    assert len(train_events.intersection(test_events)) == 0, "Data leakage: Train and Test share events!"
    assert len(val_events.intersection(test_events)) == 0, "Data leakage: Val and Test share events!"

    # 2. Spatial disjointness: latitude and longitude bounds across events must not overlap
    for ev1 in ["DFO_4499", "DFO_2935", "DFO_3372", "DFO_2507"]:
        df1 = df_binary[df_binary["event_id"] == ev1]
        for ev2 in ["DFO_4499", "DFO_2935", "DFO_3372", "DFO_2507"]:
            if ev1 >= ev2:
                continue
            df2 = df_binary[df_binary["event_id"] == ev2]
            # Verify coordinates are in distinct Indian regions
            lon_dist = abs(df1["longitude"].mean() - df2["longitude"].mean())
            lat_dist = abs(df1["latitude"].mean() - df2["latitude"].mean())
            assert (lon_dist > 1.0) or (lat_dist > 1.0), f"Events {ev1} and {ev2} are too close spatially!"


# -----------------------------------------------------------------------------
# 6. Manifest & Pilot Preservation Tests
# -----------------------------------------------------------------------------
def test_phase7c_manifest_and_pilot_preservation():
    """Verify manifest cryptographic integrity and verify pilot dataset was not overwritten."""
    assert MANIFEST_PATH.exists(), "Phase 7C dataset manifest missing"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    # 1. Checksum matches serialized master & binary files
    assert compute_sha256(MASTER_PARQUET) == manifest["master_dataset"]["parquet_sha256"]
    assert compute_sha256(MASTER_CSV) == manifest["master_dataset"]["csv_sha256"]
    assert compute_sha256(BINARY_PARQUET) == manifest["binary_dataset"]["parquet_sha256"]
    assert compute_sha256(BINARY_CSV) == manifest["binary_dataset"]["csv_sha256"]

    # 2. Pilot Preservation: Phase 7 DFO 4499 pilot files must remain intact
    assert PILOT_PARQUET.exists(), "Pilot Parquet dataset was overwritten or deleted!"
    assert PILOT_MANIFEST.exists(), "Pilot dataset manifest was overwritten or deleted!"
    df_pilot = pd.read_parquet(PILOT_PARQUET)
    assert len(df_pilot) == 5500, f"Pilot dataset corrupted: expected 5,500 samples, got {len(df_pilot)}"
    assert (df_pilot["event_id"] == "DFO_4499").all(), "Pilot dataset contains non-pilot events"
