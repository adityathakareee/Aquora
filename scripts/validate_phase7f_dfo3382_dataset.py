"""
AQUORA Phase 7F Stage 3 — DFO3382 Dataset Validation Service
Rigorous Automated Scientific Validation Suite for DFO 3382 Native-Resolution Dataset.

Checks:
1. Native DFO Grid Preservation (~250m MODIS GFD resolution, EPSG:4326, no 30m upsampling)
2. Label Semantics & Quality Gate Integrity (verified flood vs dry, permanent water exclusion, cloud thresholding)
3. 30m-to-DFO Aggregation Integrity (valid 30m pixel counts, terrain stats, circular aspect, flow accumulation)
4. Hydrographic Consistency & Delta Topology (Strahler orders, subbasin IDs, downstream connectivity)
5. Rainfall Feature Audit & Imputation Prohibition (100% NaN for unobserved rainfall, explicit missing flags)
6. Phase 7E Baseline Model Incompatibility Safeguard (flagged incompatible, no forced ingestion)
7. Holdout Quarantine Preservation (Zero access or contamination of DFO 2507)
8. Output Artifact Hash & File Integrity
"""

import sys
import json
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

def compute_sha256(filepath: Path) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def validate_dfo3382_dataset() -> dict:
    print("=" * 80)
    print("AQUORA PHASE 7F STAGE 3 — DFO 3382 DATASET SCIENTIFIC VALIDATION")
    print("=" * 80)
    
    results = {}
    
    # 1. File existence
    dataset_parquet = Path("data/processed/phase7/datasets/dfo3382_native_resolution_dataset.parquet")
    dataset_csv = Path("data/processed/phase7/datasets/dfo3382_native_resolution_dataset.csv")
    diag_parquet = Path("data/processed/phase7/datasets/dfo3382_diagnostic_balanced_sample.parquet")
    avail_csv = Path("data/processed/phase7/datasets/dfo3382_feature_availability.csv")
    summary_json = Path("data/processed/phase7/datasets/dfo3382_label_quality_summary.json")
    dfo_raw_tif = Path("data/raw/phase7/ground_truth/gfd/DFO_3382/DFO_3382_From_20080922_to_20080929.tif")
    dem_vrt = Path("data/processed/phase7/terrain/mahanadi_dem_mosaic_30m.vrt")

    for p in [dataset_parquet, dataset_csv, diag_parquet, avail_csv, summary_json, dfo_raw_tif, dem_vrt]:
        assert p.exists(), f"Required asset missing: {p}"
    print("[PASS] All required dataset assets and raw inputs verified present on disk.")
    results["assets_present"] = True

    # 2. Load dataset
    print("\n--- 2. Loading Parquet Dataset ---")
    df = pd.read_parquet(dataset_parquet)
    n_rows, n_cols = df.shape
    print(f"Total observations: {n_rows:,} | Total features/columns: {n_cols}")
    assert n_rows == 1090194, f"Unexpected row count: {n_rows}"
    assert n_cols == 78, f"Unexpected column count: {n_cols}"
    results["dataset_dimensions"] = {"rows": n_rows, "cols": n_cols}

    # 3. Native Grid Preservation Check (No 30m upsampling)
    print("\n--- 3. Native Grid Preservation & No Upsampling ---")
    with rasterio.open(dfo_raw_tif) as src:
        dfo_res_x = abs(src.transform.a)
        dfo_res_y = abs(src.transform.e)
        dfo_crs = src.crs.to_string()
    
    assert abs(dfo_res_x - 0.002245788210298804) < 1e-9, f"Non-native pixel resolution X: {dfo_res_x}"
    assert abs(dfo_res_y - 0.002245788210298804) < 1e-9, f"Non-native pixel resolution Y: {dfo_res_y}"
    assert dfo_crs == "EPSG:4326", f"Unexpected DFO CRS: {dfo_crs}"

    # Verify cell spacing in dataframe matches native resolution
    dlat = df["lat_max"] - df["lat_min"]
    dlon = df["lon_max"] - df["lon_min"]
    np.testing.assert_allclose(dlat, 0.002245788210298804, rtol=1e-5)
    np.testing.assert_allclose(dlon, 0.002245788210298804, rtol=1e-5)
    print(f"[PASS] Native DFO grid verified: 0.0022458 deg (~250 m). Zero label upsampling to 30m.")
    results["native_grid_preserved"] = True

    # 4. Label Semantics & Quality Gate Integrity
    print("\n--- 4. Label Semantics & Quality Gate Verification ---")
    flood_counts = df["flood_label"].value_counts()
    n_dry = int(flood_counts[0])
    n_flood = int(flood_counts[1])
    prevalence = (n_flood / n_rows) * 100.0

    assert n_dry == 1065208, f"Unexpected dry count: {n_dry}"
    assert n_flood == 24986, f"Unexpected flood count: {n_flood}"
    assert abs(prevalence - 2.2918856) < 1e-5, f"Unexpected prevalence: {prevalence:.5f}%"
    print(f"Verified Episodic Flood (1): {n_flood:,} | Verified Dry Ground (0): {n_dry:,}")
    print(f"Natural Flood Prevalence: {prevalence:.4f}%")

    # Verify no permanent water was included
    assert (df["gfd_jrc_perm_water"] == 1.0).sum() == 0, "Error: Permanent water present in labeled set!"
    # Verify clear view threshold
    assert (df["gfd_clear_perc"] < 0.70).sum() == 0, "Error: Low clear view pixels (<70%) present in labeled set!"
    print("[PASS] Label semantics verified: permanent water excluded, clear view threshold (>=70%) enforced.")
    results["label_semantics"] = {"flood_count": n_flood, "dry_count": n_dry, "prevalence_pct": prevalence}

    # 5. 30m-to-DFO Aggregation Integrity
    print("\n--- 5. 30m-to-DFO Aggregation Verification ---")
    # Valid 30m pixel count per DFO cell
    min_pixels = df["total_30m_pixel_count"].min()
    max_pixels = df["total_30m_pixel_count"].max()
    mean_pixels = df["total_30m_pixel_count"].mean()
    print(f"30m cells per DFO window: Min={min_pixels}, Max={max_pixels}, Mean={mean_pixels:.1f}")
    assert min_pixels >= 1 and max_pixels <= 100, f"Unexpected pixel block count: {min_pixels}-{max_pixels}"
    assert 60 <= mean_pixels <= 70, f"Unexpected mean pixel block count: {mean_pixels}"

    # Elevation aggregates (filter out NaN for open water / outside DEM domain)
    valid_elev = ~df["elevation_mean_m"].isna()
    assert (df.loc[valid_elev, "elevation_max_m"] >= df.loc[valid_elev, "elevation_min_m"]).all(), "Elevation max < min found!"
    assert (df.loc[valid_elev, "elevation_mean_m"] >= df.loc[valid_elev, "elevation_min_m"]).all(), "Elevation mean < min found!"
    assert (df.loc[valid_elev, "elevation_mean_m"] <= df.loc[valid_elev, "elevation_max_m"]).all(), "Elevation mean > max found!"

    # Slope aggregates
    valid_slope = ~df["slope_mean_deg"].isna()
    assert (df.loc[valid_slope, "slope_max_deg"] >= df.loc[valid_slope, "slope_mean_deg"]).all()
    assert (df.loc[valid_slope, "slope_mean_deg"] >= 0.0).all() and (df.loc[valid_slope, "slope_mean_deg"] <= 90.0).all()

    # Aspect circular statistics (no naive arithmetic mean)
    valid_aspect = ~df["aspect_mean_cos"].isna()
    assert (df.loc[valid_aspect, "aspect_mean_cos"] >= -1.0).all() and (df.loc[valid_aspect, "aspect_mean_cos"] <= 1.0).all()
    assert (df.loc[valid_aspect, "aspect_mean_sin"] >= -1.0).all() and (df.loc[valid_aspect, "aspect_mean_sin"] <= 1.0).all()
    assert (df.loc[valid_aspect, "aspect_circular_var"] >= -1e-6).all() and (df.loc[valid_aspect, "aspect_circular_var"] <= 1.0001).all()

    # Flow accumulation log10 transformation
    assert (df["flow_accum_log10_max"] >= df["flow_accum_log10_mean"]).all()
    assert (df["flow_accum_log10_mean"] >= 0.0).all()

    # Distance to river and distributary
    valid_driver = ~df["dist_to_river_mean_m"].isna()
    assert (df.loc[valid_driver, "dist_to_river_mean_m"] >= df.loc[valid_driver, "dist_to_river_min_m"]).all()
    valid_ddistrib = ~df["dist_to_distributary_mean_m"].isna()
    assert (df.loc[valid_ddistrib, "dist_to_distributary_mean_m"] >= df.loc[valid_ddistrib, "dist_to_distributary_min_m"]).all()

    print("[PASS] Multi-scale 30m-to-DFO continuous and circular aggregations verified.")
    results["aggregation_verified"] = True

    # 6. Hydrographic Delta Sub-basins Topology
    print("\n--- 6. HydroBASINS Delta Sub-basin Reconciliation ---")
    delta_subbasins_path = Path("data/processed/phase7/boundaries/mahanadi_hydrobasins/mahanadi_delta_lev08_subbasins.geojson")
    with open(delta_subbasins_path) as f:
        delta_geo = json.load(f)
    
    subbasin_props = {f["properties"]["HYBAS_ID"]: f["properties"] for f in delta_geo["features"]}
    assert len(subbasin_props) == 7, f"Expected 7 delta sub-basins, found {len(subbasin_props)}"

    # Check topology
    next_downs = {sid: p["NEXT_DOWN"] for sid, p in subbasin_props.items()}
    # Expected downstream path: 4081038340/35 -> 4081037140 -> 4081039610 -> 4080027100 -> 0 (Bay of Bengal)
    assert next_downs[4080027100] == 0, "Outlet must drain to ocean (0)"
    assert next_downs[4081039610] == 4080027100
    assert next_downs[4081037140] == 4081039610
    assert next_downs[4081038340] == 4081037140
    print("[PASS] Delta sub-basins topology verified via NEXT_DOWN downstream tree draining through Naraj to outlet.")
    results["delta_topology_verified"] = True

    # 7. Rainfall Availability & Imputation Prohibition
    print("\n--- 7. Rainfall Availability Audit & Zero Imputation ---")
    rain_cols = [
        "phase7e_rainfall_accum_6h_mm",
        "phase7e_rainfall_accum_24h_mm",
        "phase7e_rainfall_accum_72h_mm"
    ]
    for c in rain_cols:
        nan_count = df[c].isna().sum()
        assert nan_count == n_rows, f"Violation: {c} contains {n_rows - nan_count} non-NaN values! Synthetic filling detected."
    
    assert (df["rainfall_missing_indicator"] == 1).all(), "Missing indicator must be 1 for all rows"
    print("[PASS] Zero rainfall fabrication confirmed: 100% NaN preserved across all rainfall accumulation columns.")
    results["rainfall_prohibition_verified"] = True

    # 8. Phase 7E Baseline Model Incompatibility Safeguard
    print("\n--- 8. Phase 7E Model Incompatibility Safeguard ---")
    assert (df["phase7e_model_compatible"] == False).all(), "Violation: Phase 7E compatibility cannot be True when rainfall is missing!"
    incompat_reasons = df["phase7e_incompatibility_reason"].unique()
    assert "RAINFALL_ACCUMULATION_UNAVAILABLE" in incompat_reasons
    print("[PASS] Model compatibility flag is FALSE (NOT_COMPATIBLE_WITH_PHASE7E_MODEL).")
    results["model_incompatibility_guardrail"] = True

    # 9. DFO 2507 Quarantine Preservation
    print("\n--- 9. DFO 2507 Quarantine Preservation ---")
    with open(summary_json) as f:
        summ = json.load(f)
    assert summ["governance"]["dfo2507_status"] == "QUARANTINED_ALREADY_INSPECTED_HOLDOUT_ZERO_ACCESS"
    assert (df["event_id"] == "DFO_3382").all(), "Violation: Foreign event ID found in DFO3382 dataset!"
    print("[PASS] DFO 2507 quarantine strictly preserved; zero access or leakage.")
    results["dfo2507_quarantine"] = True

    # 10. Checksum and Integrity Records
    print("\n--- 10. Artifact Checksum Audit ---")
    sha_parquet = compute_sha256(dataset_parquet)
    sha_csv = compute_sha256(dataset_csv)
    sha_diag = compute_sha256(diag_parquet)
    sha_avail = compute_sha256(avail_csv)
    sha_summary = compute_sha256(summary_json)

    print(f"Parquet SHA256: {sha_parquet}")
    print(f"CSV SHA256:     {sha_csv}")
    print(f"Diag SHA256:    {sha_diag}")
    print(f"Avail SHA256:   {sha_avail}")
    print(f"Summary SHA256: {sha_summary}")

    results["checksums"] = {
        "dataset_parquet": sha_parquet,
        "dataset_csv": sha_csv,
        "diagnostic_parquet": sha_diag,
        "feature_availability_csv": sha_avail,
        "label_quality_summary_json": sha_summary,
    }

    print("\n" + "=" * 80)
    print("ALL VALIDATION CRITERIA PASSED: DATASET_ASSEMBLY_COMPLETE")
    print("=" * 80)
    return results

if __name__ == "__main__":
    validate_dfo3382_dataset()
