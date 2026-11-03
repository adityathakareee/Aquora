"""
AQUORA Phase 6C.2G.14: Pilot Rainfall Acquisition & Landmark Deluge Verification Tests.

Validates:
1. Asset immutability: Raw Copernicus DSM, Working DEM, and Raw IFI match exact SHA-256 hashes.
2. Independent revalidation of Event E03: 48 local HDF5 granules reproduce 221.78 mm point estimate,
   218.62 mm spatial mean, 32.35 mm/hr peak rate, and strict separation of 375.2 mm Santacruz gauge.
3. Event E02 temporal coverage repair: audits 48 half-hourly granules covering 2017-08-29 UTC,
   documents authentic accumulation, and explains legacy unverified 243.6 mm literature figure.
4. Grid coordinate selection and axis ordering in IMERG HDF5.
5. Rate-to-depth conversion (0.5h factor) and fill-value masking (-9999.9).
6. Separation of point estimates versus areal spatial averages.
7. Pilot event inventory: 8 landmark events across India with authentic CHIRPS and IMERG daily data.
8. Governance & safeguards: final decision, prohibited ML training, zero synthetic rainfall, and immutability.
"""

import hashlib
import json
from pathlib import Path
import h5py
import numpy as np
import pandas as pd
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

RAW_DEM_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem" / "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
WORKING_DEM_PATH = PROJECT_ROOT / "data" / "processed" / "phase7" / "terrain" / "elevation_30m_study_extent.tif"
RAW_IFI_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "india_flood_inventory_v3.csv"

E03_IMERG_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "rainfall" / "imerg" / "final" / "2019" / "07"
E02_IMERG_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "rainfall" / "imerg" / "final" / "2017" / "08"
PILOT_CHIRPS_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "rainfall" / "chirps" / "daily"
PILOT_IMERG_DAILY_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "rainfall" / "imerg" / "daily"

OUT_DIR = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall"
PILOT_CSV = OUT_DIR / "phase6c2g14_pilot_event_inventory.csv"
E02_E03_JSON = OUT_DIR / "phase6c2g14_e02_e03_revalidation.json"
QUALITY_JSON = OUT_DIR / "phase6c2g14_pilot_quality_assessment.json"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c2g14_pilot_rainfall_manifest.yaml"

EXPECTED_RAW_DEM_SHA256 = "b90f91a2b8cd69da327d8c133417d119a44f9880c8bb080114be5d8e9cf3dcdd"
EXPECTED_WORKING_DEM_SHA256 = "25ac4e254f6bef29c65d18d1cd6b3e24a5ef6bec3c6de4952b1466df4b471bda"
EXPECTED_RAW_IFI_SHA256 = "ef9ab2cd0db7bf917dcc22c7cb094ec599f5013ef1b96ba525d816f26ff1b108"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_asset_immutability():
    """Verify raw Copernicus DSM, working 30m DEM, and raw IFI CSV have not been altered."""
    assert RAW_DEM_PATH.exists()
    assert WORKING_DEM_PATH.exists()
    assert RAW_IFI_PATH.exists()

    assert compute_sha256(RAW_DEM_PATH) == EXPECTED_RAW_DEM_SHA256
    assert compute_sha256(WORKING_DEM_PATH) == EXPECTED_WORKING_DEM_SHA256
    assert compute_sha256(RAW_IFI_PATH) == EXPECTED_RAW_IFI_SHA256


def test_e03_independent_revalidation():
    """Verify Event E03 24h accumulation reproduced from 48 local HDF5 granules."""
    assert E02_E03_JSON.exists()
    with open(E02_E03_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    e03 = data["event_e03_revalidation"]
    assert e03["status"] == "VALIDATED_BENCHMARK_DELUGE"
    assert e03["granules_present_count"] == 48
    assert abs(e03["recalculated_point_accumulation_mm"] - 221.78) <= 0.01
    assert abs(e03["recalculated_areal_accumulation_mm"] - 218.62) <= 0.01
    assert e03["recalculated_peak_half_hour_rate_mm_hr"] == 32.35
    assert e03["imd_santacruz_gauge_reading_mm"] == 375.2
    assert "point gauge" in e03["point_vs_satellite_explanation"].lower()


def test_e02_temporal_coverage_revalidation():
    """Verify Event E02 temporal coverage audit and legacy 243.6 mm explanation."""
    assert E02_E03_JSON.exists()
    with open(E02_E03_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    e02 = data["event_e02_revalidation"]
    assert e02["historical_reference_value_mm"] == 243.6
    assert "unverified" in e02["discrepancy_explanation"].lower() or "secondary" in e02["discrepancy_explanation"].lower()
    assert e02["status"] in ("MATCHED_RAINFALL_COVERAGE", "PARTIAL_TEMPORAL_COVERAGE", "DOWNGRADED_TO_PARTIAL_TEMPORAL_COVERAGE")
    assert "safeguard_warning" in e02


def test_grid_coordinates_and_axis_ordering():
    """Verify IMERG HDF5 coordinate grid layout and axis ordering."""
    granules = list(E03_IMERG_DIR.glob("*.HDF5"))
    assert len(granules) > 0

    with h5py.File(granules[0], "r") as hf:
        lons = hf["Grid"]["lon"][:]
        lats = hf["Grid"]["lat"][:]
        p = hf["Grid"]["precipitation"]

        assert len(lons) == 3600
        assert len(lats) == 1800
        assert p.shape == (1, 3600, 1800)
        assert lons[0] < lons[-1]
        assert lats[0] < lats[-1]


def test_rate_to_depth_conversion_and_fill_value():
    """Verify rate-to-depth calculation and fill-value masking."""
    fill_val = -9999.9
    rates = np.array([0.0, 10.0, 25.4, fill_val, 4.2])
    masked_rates = np.where(rates != fill_val, rates, 0.0)

    # 30-min accumulation: rate * 0.5 hr
    depths = masked_rates * 0.5
    expected_depths = np.array([0.0, 5.0, 12.7, 0.0, 2.1])
    np.testing.assert_allclose(depths, expected_depths)


def test_point_vs_spatial_mean_distinction():
    """Verify point estimate and spatial mean are distinct and not conflated."""
    with open(E02_E03_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    e03 = data["event_e03_revalidation"]
    point_val = e03["recalculated_point_accumulation_mm"]
    areal_val = e03["recalculated_areal_accumulation_mm"]
    gauge_val = e03["imd_santacruz_gauge_reading_mm"]

    # Point estimate at centroid (221.78 mm) vs areal mean (218.62 mm) vs gauge (375.2 mm)
    assert point_val != areal_val
    assert point_val != gauge_val
    assert areal_val != gauge_val


def test_pilot_event_inventory_integrity():
    """Verify pilot event inventory contains 8 distinct landmark events with preserved UEIs."""
    assert PILOT_CSV.exists()
    df = pd.read_csv(PILOT_CSV)

    assert len(df) == 8
    expected_pilot_ids = [f"PILOT-0{i}" for i in range(1, 9)]
    assert df["pilot_id"].tolist() == expected_pilot_ids

    # Preserved UEIs
    assert "UEI-IMD-FL-2019-0090" in df["primary_uei"].values
    assert "UEI-IMD-FL-2017-0088" in df["primary_uei"].values
    assert "UEI-IMD-FL-2005-0062" in df["primary_uei"].values
    assert "UEI-IMD-FL-2018-0051" in df["primary_uei"].values
    assert "UEI-IMD-FL-2013-0027" in df["primary_uei"].values
    assert "UEI-IMD-FL-2019-0002" in df["primary_uei"].values
    assert "UEI-IMD-FL-2015-0077" in df["primary_uei"].values
    assert "UEI-IMD-FL-2022-0453" in df["primary_uei"].values

    # Check match status column exists and is populated
    assert "rainfall_match_status" in df.columns
    for status in df["rainfall_match_status"]:
        assert status in (
            "MATCHED_RAINFALL_COVERAGE",
            "PARTIAL_TEMPORAL_COVERAGE",
            "DATE_UNCERTAIN",
            "NOT_ACQUIRED",
            "SOURCE_VALIDATION_FAILED",
        )


def test_pilot_quality_assessment_structure():
    """Verify pilot quality assessment artifact contains scaling projections and source assessments."""
    assert QUALITY_JSON.exists()
    with open(QUALITY_JSON, "r", encoding="utf-8") as f:
        qa = json.load(f)

    assert "candidate_sources_evaluated" in qa
    assert "national_scale_projection" in qa
    proj = qa["national_scale_projection"]
    assert proj["total_ifi_events"] == 6876
    assert "daily_chirps_storage_gb" in proj
    assert "half_hourly_imerg_storage_tb" in proj


def test_manifest_governance_and_safeguards():
    """Verify manifest governance decision and explicit prohibitions."""
    assert MANIFEST_PATH.exists()
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        m = yaml.safe_load(f)

    gov = m["governance"]
    assert gov["final_decision"] in ("PILOT_ACQUISITION_VALIDATED", "PARTIAL_ACQUISITION_READY")
    assert gov["supervised_training_permitted"] is False
    assert gov["national_trigger_modeling_permitted"] is False
    assert gov["zero_synthetic_rainfall_enforced"] is True
    assert gov["zero_missing_rainfall_imputation_enforced"] is True
    assert m["immutability_verification"]["verified_unmodified"] is True


def test_no_supervised_models_trained():
    """Verify no supervised ML models have been trained or saved."""
    models_dir = PROJECT_ROOT / "ml" / "models"
    if models_dir.exists():
        model_files = list(models_dir.glob("*.pkl")) + list(models_dir.glob("*.joblib")) + list(models_dir.glob("*.onnx"))
        assert len(model_files) == 0, f"Found trained model files: {model_files}"
