"""
AQUORA Phase 7F Stage 3 — DFO3382 Native-Resolution Dataset Preparation Pipeline
Authoritative Dataset Assembly Script for DFO 3382 (Mahanadi Basin & Odisha Coastal Corridor).

Scientific Governance:
- Native DFO resolution preserved (~250m nominal MODIS GFD grid, EPSG:4326).
- High-resolution (30m) terrain and hydrographic rasters aggregated to native DFO cells.
- Natural flood prevalence strictly preserved in primary dataset.
- Separate diagnostic balanced sample provided for diagnostic baselines.
- Zero rainfall fabrication: missing rainfall explicitly flagged and marked NaN.
- Phase 7E baseline model compatibility explicitly flagged as NOT_COMPATIBLE_WITH_PHASE7E_MODEL.
- DFO 2507 holdout quarantine strictly preserved (zero access).
- Phase 6 hydrodynamic physics engine remains the primary operational flood authority.
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
import rasterio.features
import geopandas as gpd
import numba

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prepare_phase7f_dfo3382_dataset")

# -----------------------------------------------------------------------------
# NUMBA PARALLEL AGGREGATION KERNELS
# -----------------------------------------------------------------------------

@numba.njit(parallel=True)
def aggregate_continuous_stats(arr, r0s, r1s, c0s, c1s, out_mean, out_std, out_min, out_max, out_median, nodata_val):
    """Computes mean, std, min, max, median for continuous 30m raster blocks."""
    n = len(r0s)
    for i in numba.prange(n):
        r0 = r0s[i]
        r1 = r1s[i]
        c0 = c0s[i]
        c1 = c1s[i]
        
        buf = np.empty(128, dtype=np.float32)
        cnt = 0
        s = 0.0
        
        for r in range(r0, r1):
            for c in range(c0, c1):
                v = arr[r, c]
                if not np.isnan(v) and v != nodata_val and v > -999000:
                    buf[cnt] = v
                    cnt += 1
                    s += v
        
        if cnt > 0:
            mean = s / cnt
            out_mean[i] = mean
            
            var_s = 0.0
            for k in range(cnt):
                diff = buf[k] - mean
                var_s += diff * diff
            out_std[i] = np.sqrt(var_s / cnt)
            
            vals = buf[:cnt]
            vals.sort()
            out_min[i] = vals[0]
            out_max[i] = vals[cnt - 1]
            if cnt % 2 == 1:
                out_median[i] = vals[cnt // 2]
            else:
                out_median[i] = 0.5 * (vals[cnt // 2 - 1] + vals[cnt // 2])
        else:
            out_mean[i] = np.nan
            out_std[i] = np.nan
            out_min[i] = np.nan
            out_max[i] = np.nan
            out_median[i] = np.nan

@numba.njit(parallel=True)
def aggregate_aspect_circular(arr, r0s, r1s, c0s, c1s, out_cos, out_sin, out_deg, out_cvar, out_flat_frac, nodata_val):
    """Computes circular statistics on aspect (in degrees [0, 360), -1 is flat)."""
    n = len(r0s)
    pi = np.pi
    deg2rad = pi / 180.0
    rad2deg = 180.0 / pi
    
    for i in numba.prange(n):
        r0 = r0s[i]
        r1 = r1s[i]
        c0 = c0s[i]
        c1 = c1s[i]
        
        sum_cos = 0.0
        sum_sin = 0.0
        non_flat_cnt = 0
        flat_cnt = 0
        total_valid = 0
        
        for r in range(r0, r1):
            for c in range(c0, c1):
                v = arr[r, c]
                if not np.isnan(v) and v != nodata_val and v > -999000:
                    total_valid += 1
                    if v < 0:
                        flat_cnt += 1
                    else:
                        rad = v * deg2rad
                        sum_cos += np.cos(rad)
                        sum_sin += np.sin(rad)
                        non_flat_cnt += 1
        
        if total_valid > 0:
            out_flat_frac[i] = flat_cnt / total_valid
            if non_flat_cnt > 0:
                mean_cos = sum_cos / non_flat_cnt
                mean_sin = sum_sin / non_flat_cnt
                r_len = np.sqrt(mean_cos * mean_cos + mean_sin * mean_sin)
                
                out_cos[i] = mean_cos
                out_sin[i] = mean_sin
                out_cvar[i] = 1.0 - r_len
                
                angle = np.arctan2(mean_sin, mean_cos) * rad2deg
                if angle < 0.0:
                    angle += 360.0
                out_deg[i] = angle
            else:
                out_cos[i] = 0.0
                out_sin[i] = 0.0
                out_deg[i] = np.nan
                out_cvar[i] = 1.0
        else:
            out_flat_frac[i] = np.nan
            out_cos[i] = np.nan
            out_sin[i] = np.nan
            out_deg[i] = np.nan
            out_cvar[i] = np.nan

@numba.njit(parallel=True)
def aggregate_flow_accum(arr, r0s, r1s, c0s, c1s, out_mean, out_max, out_log_mean, out_log_max):
    """Computes raw and log10-transformed flow accumulation statistics."""
    n = len(r0s)
    for i in numba.prange(n):
        r0 = r0s[i]
        r1 = r1s[i]
        c0 = c0s[i]
        c1 = c1s[i]
        
        s = 0.0
        s_log = 0.0
        cnt = 0
        vmax = 0.0
        
        for r in range(r0, r1):
            for c in range(c0, c1):
                v = arr[r, c]
                cnt += 1
                s += v
                l = np.log10(1.0 + v)
                s_log += l
                if v > vmax:
                    vmax = v
        
        if cnt > 0:
            out_mean[i] = s / cnt
            out_max[i] = vmax
            out_log_mean[i] = s_log / cnt
            out_log_max[i] = np.log10(1.0 + vmax)
        else:
            out_mean[i] = 0.0
            out_max[i] = 0.0
            out_log_mean[i] = 0.0
            out_log_max[i] = 0.0

@numba.njit(parallel=True)
def aggregate_strahler_order(arr, r0s, r1s, c0s, c1s, out_max, out_rep):
    """Computes maximum and representative non-zero Strahler stream order (0..7)."""
    n = len(r0s)
    for i in numba.prange(n):
        r0 = r0s[i]
        r1 = r1s[i]
        c0 = c0s[i]
        c1 = c1s[i]
        
        vmax = 0
        buf = np.empty(128, dtype=np.uint8)
        non_zero_cnt = 0
        
        for r in range(r0, r1):
            for c in range(c0, c1):
                v = arr[r, c]
                if v > 0:
                    buf[non_zero_cnt] = v
                    non_zero_cnt += 1
                    if v > vmax:
                        vmax = v
        
        out_max[i] = vmax
        if non_zero_cnt > 0:
            vals = buf[:non_zero_cnt]
            vals.sort()
            out_rep[i] = vals[non_zero_cnt // 2]
        else:
            out_rep[i] = 0

@numba.njit(parallel=True)
def aggregate_water_mask_proportions(arr, r0s, r1s, c0s, c1s, out_dry, out_ocean, out_lake, out_river, out_valid_cnt, out_total_cnt):
    """Computes land/water proportions from 8-class validated mask:
    1: Open ocean
    2: Permanent inland water
    3: River channels
    4: Seasonal water
    5: Intertidal or tidal flats
    6: Mangrove
    7: Terrestrial land
    8: Uncertain or unclassified
    """
    n = len(r0s)
    for i in numba.prange(n):
        r0 = r0s[i]
        r1 = r1s[i]
        c0 = c0s[i]
        c1 = c1s[i]
        
        dry_cnt = 0
        ocean_cnt = 0
        lake_cnt = 0
        river_cnt = 0
        valid_cnt = 0
        total_cnt = 0
        
        for r in range(r0, r1):
            for c in range(c0, c1):
                v = arr[r, c]
                total_cnt += 1
                if 1 <= v <= 7:
                    valid_cnt += 1
                    if v == 7: # Terrestrial land
                        dry_cnt += 1
                    elif v == 1: # Open ocean
                        ocean_cnt += 1
                    elif v == 2: # Permanent inland water
                        lake_cnt += 1
                    elif v == 3: # River channels
                        river_cnt += 1
        
        out_valid_cnt[i] = valid_cnt
        out_total_cnt[i] = total_cnt
        if valid_cnt > 0:
            out_dry[i] = dry_cnt / valid_cnt
            out_ocean[i] = ocean_cnt / valid_cnt
            out_lake[i] = lake_cnt / valid_cnt
            out_river[i] = river_cnt / valid_cnt
        else:
            out_dry[i] = 0.0
            out_ocean[i] = 0.0
            out_lake[i] = 0.0
            out_river[i] = 0.0

@numba.njit(parallel=True)
def aggregate_majority_id(arr, r0s, r1s, c0s, c1s, out_majority, nodata_val):
    """Computes majority ID (e.g. HYBAS_ID) in block."""
    n = len(r0s)
    for i in numba.prange(n):
        r0 = r0s[i]
        r1 = r1s[i]
        c0 = c0s[i]
        c1 = c1s[i]
        
        # Collect values
        buf = np.empty(128, dtype=np.float64)
        cnt = 0
        for r in range(r0, r1):
            for c in range(c0, c1):
                v = arr[r, c]
                if not np.isnan(v) and v != nodata_val and v > 0:
                    buf[cnt] = v
                    cnt += 1
        
        if cnt > 0:
            vals = buf[:cnt]
            vals.sort()
            
            # Find mode
            best_val = vals[0]
            best_count = 1
            curr_val = vals[0]
            curr_count = 1
            
            for k in range(1, cnt):
                if vals[k] == curr_val:
                    curr_count += 1
                else:
                    if curr_count > best_count:
                        best_count = curr_count
                        best_val = curr_val
                    curr_val = vals[k]
                    curr_count = 1
            if curr_count > best_count:
                best_val = curr_val
            
            out_majority[i] = best_val
        else:
            out_majority[i] = 0.0

# -----------------------------------------------------------------------------
# MAIN PIPELINE
# -----------------------------------------------------------------------------

def build_dfo3382_dataset():
    t_start = time.time()
    logger.info("Starting AQUORA Phase 7F Stage 3 DFO3382 Native-Resolution Dataset Assembly...")

    # Paths
    dfo_path = Path("data/raw/phase7/ground_truth/gfd/DFO_3382/DFO_3382_From_20080922_to_20080929.tif")
    dem_vrt = Path("data/processed/phase7/terrain/mahanadi_dem_mosaic_30m.vrt")
    basin_geojson = Path("data/processed/phase7/boundaries/mahanadi_hydrobasins/mahanadi_hydrobasins_lev08.geojson")
    delta_geojson = Path("data/processed/phase7/boundaries/mahanadi_hydrobasins/mahanadi_delta_lev08_subbasins.geojson")
    
    out_dir = Path("data/processed/phase7/datasets")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_parquet = out_dir / "dfo3382_native_resolution_dataset.parquet"
    out_csv = out_dir / "dfo3382_native_resolution_dataset.csv"
    out_diag = out_dir / "dfo3382_diagnostic_balanced_sample.parquet"
    out_avail = out_dir / "dfo3382_feature_availability.csv"
    out_summary = out_dir / "dfo3382_label_quality_summary.json"

    # 1. Read DEM bounds and DFO window
    logger.info(f"Reading DEM mosaic bounds from {dem_vrt}...")
    with rasterio.open(dem_vrt) as src_vrt:
        dem_bounds = src_vrt.bounds
        dem_transform = src_vrt.transform
        dem_w = src_vrt.width
        dem_h = src_vrt.height
    
    logger.info(f"DEM mosaic dimensions: {dem_w}x{dem_h}, bounds: {dem_bounds}")

    logger.info(f"Opening DFO 3382 ground truth raster: {dfo_path}...")
    with rasterio.open(dfo_path) as src_dfo:
        dfo_win = from_bounds(
            dem_bounds.left, dem_bounds.bottom, dem_bounds.right, dem_bounds.top, src_dfo.transform
        ).round_offsets().round_lengths()
        
        win_transform = rasterio.windows.transform(dfo_win, src_dfo.transform)
        win_w = int(dfo_win.width)
        win_h = int(dfo_win.height)
        
        logger.info(f"DFO window: {dfo_win}, shape: ({win_h}, {win_w})")
        logger.info("Reading DFO observation bands...")
        flooded_band = src_dfo.read(1, window=dfo_win)
        duration_band = src_dfo.read(2, window=dfo_win)
        clear_views_band = src_dfo.read(3, window=dfo_win)
        clear_perc_band = src_dfo.read(4, window=dfo_win)
        jrc_perm_band = src_dfo.read(5, window=dfo_win)

    # 2. Audit label conditions across DFO window
    logger.info("Evaluating DFO 3382 observation criteria...")
    is_nan = np.isnan(flooded_band) | np.isnan(clear_perc_band) | np.isnan(jrc_perm_band)
    perm_water = (jrc_perm_band == 1.0) & (~is_nan)
    low_clear = (clear_perc_band < 0.70) & (~is_nan) & (~perm_water)
    
    verified_flood = (flooded_band == 1.0) & (jrc_perm_band == 0.0) & (clear_perc_band >= 0.70) & (~is_nan)
    verified_dry = (flooded_band == 0.0) & (jrc_perm_band == 0.0) & (clear_perc_band >= 0.70) & (~is_nan)
    
    raw_flood_on_perm = (flooded_band == 1.0) & (jrc_perm_band == 1.0) & (~is_nan)
    
    eligible_mask = verified_flood | verified_dry
    total_cells = flooded_band.size
    nan_cells = int(is_nan.sum())
    valid_obs_cells = int((~is_nan).sum())
    flood_count = int(verified_flood.sum())
    dry_count = int(verified_dry.sum())
    perm_count = int(perm_water.sum())
    low_clear_count = int(low_clear.sum())
    eligible_count = int(eligible_mask.sum())
    prevalence = (flood_count / eligible_count) * 100.0

    logger.info(f"Total window cells: {total_cells:,}")
    logger.info(f"NaN / Ocean / Off-domain: {nan_cells:,} ({nan_cells/total_cells*100:.2f}%)")
    logger.info(f"Valid observation cells: {valid_obs_cells:,} ({valid_obs_cells/total_cells*100:.2f}%)")
    logger.info(f"  Verified Episodic Flood (Label=1): {flood_count:,} ({flood_count/eligible_count*100:.3f}% natural prevalence)")
    logger.info(f"  Verified Dry (Label=0): {dry_count:,} ({dry_count/eligible_count*100:.3f}%)")
    logger.info(f"  Permanent Water Excluded: {perm_count:,} (includes {int(raw_flood_on_perm.sum()):,} raw flooded on perm water)")
    logger.info(f"  Low Clear Views Excluded: {low_clear_count:,}")
    logger.info(f"  Total Eligible Labeled Cells: {eligible_count:,}")

    # 3. Establish spatial coordinates of eligible cells
    grid_rows, grid_cols = np.where(eligible_mask)
    n_samples = len(grid_rows)
    logger.info(f"Constructing native DFO cell coordinates for {n_samples:,} samples...")

    # Cell centers
    lons, lats = rasterio.transform.xy(win_transform, grid_rows, grid_cols, offset='center')
    lons = np.array(lons, dtype=np.float64)
    lats = np.array(lats, dtype=np.float64)

    # Cell bounds
    ul_xs, ul_ys = rasterio.transform.xy(win_transform, grid_rows, grid_cols, offset='ul')
    lr_xs, lr_ys = rasterio.transform.xy(win_transform, grid_rows, grid_cols, offset='lr')
    lon_mins = np.minimum(ul_xs, lr_xs)
    lon_maxs = np.maximum(ul_xs, lr_xs)
    lat_mins = np.minimum(ul_ys, lr_ys)
    lat_maxs = np.maximum(ul_ys, lr_ys)

    # Cell area in m2 (accounting for latitude)
    lats_rad = np.radians(lats)
    dlat_m = 0.002245788210298804 * 111320.0
    dlon_m = 0.002245788210298804 * 111320.0 * np.cos(lats_rad)
    pixel_area_m2 = dlat_m * dlon_m

    # 4. Map DFO grid rows and cols to 30m DEM mosaic pixel window
    logger.info("Computing exact 30m DEM mosaic pixel slices for all DFO cells...")
    r_edges = []
    for r in range(win_h + 1):
        _, y = rasterio.transform.xy(win_transform, r, 0, offset='ul')
        dem_r, _ = rasterio.transform.rowcol(dem_transform, dem_bounds.left + 0.001, y)
        r_edges.append(np.clip(dem_r, 0, dem_h))
    r_edges = np.array(r_edges, dtype=np.int32)

    c_edges = []
    for c in range(win_w + 1):
        x, _ = rasterio.transform.xy(win_transform, 0, c, offset='ul')
        _, dem_c = rasterio.transform.rowcol(dem_transform, x, dem_bounds.top - 0.001)
        c_edges.append(np.clip(dem_c, 0, dem_w))
    c_edges = np.array(c_edges, dtype=np.int32)

    r0s = r_edges[grid_rows]
    r1s = r_edges[grid_rows + 1]
    c0s = c_edges[grid_cols]
    c1s = c_edges[grid_cols + 1]

    # 5. Spatial boundary masks: Mahanadi Basin and Core Delta Sub-basins
    logger.info("Rasterizing Mahanadi Basin and Core Delta Sub-basin masks...")
    gdf_basin = gpd.read_file(basin_geojson)
    gdf_delta = gpd.read_file(delta_geojson)

    basin_mask = rasterio.features.rasterize(
        [(geom, 1) for geom in gdf_basin.geometry],
        out_shape=(win_h, win_w),
        transform=win_transform,
        fill=0,
        dtype=np.uint8
    )

    delta_mask = rasterio.features.rasterize(
        [(geom, 1) for geom in gdf_delta.geometry],
        out_shape=(win_h, win_w),
        transform=win_transform,
        fill=0,
        dtype=np.uint8
    )

    in_mahanadi = basin_mask[grid_rows, grid_cols] == 1
    in_delta = delta_mask[grid_rows, grid_cols] == 1

    logger.info(f"Mahanadi Basin samples: {in_mahanadi.sum():,} (Flood: {((flooded_band[grid_rows, grid_cols] == 1.0) & in_mahanadi).sum():,}, Prevalence: {((flooded_band[grid_rows, grid_cols] == 1.0) & in_mahanadi).sum() / in_mahanadi.sum() * 100:.3f}%)")
    logger.info(f"Core Delta Sub-basin samples: {in_delta.sum():,} (Flood: {((flooded_band[grid_rows, grid_cols] == 1.0) & in_delta).sum():,}, Prevalence: {((flooded_band[grid_rows, grid_cols] == 1.0) & in_delta).sum() / in_delta.sum() * 100:.3f}%)")

    # 6. Aggregating 30m Rasters
    # Land / Water Mask
    logger.info("Aggregating Land/Water Mask (30m)...")
    with rasterio.open("data/processed/phase7/terrain/mahanadi_land_water_mask_30m.tif") as src:
        arr_mask = src.read(1)
    
    dry_frac = np.empty(n_samples, dtype=np.float32)
    ocean_frac = np.empty(n_samples, dtype=np.float32)
    lake_frac = np.empty(n_samples, dtype=np.float32)
    river_frac = np.empty(n_samples, dtype=np.float32)
    valid_30m_cnt = np.empty(n_samples, dtype=np.int16)
    total_30m_cnt = np.empty(n_samples, dtype=np.int16)

    aggregate_water_mask_proportions(arr_mask, r0s, r1s, c0s, c1s, dry_frac, ocean_frac, lake_frac, river_frac, valid_30m_cnt, total_30m_cnt)
    del arr_mask
    terrain_cov_frac = np.where(total_30m_cnt > 0, valid_30m_cnt / total_30m_cnt, 0.0).astype(np.float32)

    # Elevation
    logger.info("Aggregating Copernicus DEM Elevation (30m)...")
    with rasterio.open("data/processed/phase7/terrain/mahanadi_dem_mosaic_30m.vrt") as src:
        arr_dem = src.read(1)
    
    elev_mean = np.empty(n_samples, dtype=np.float32)
    elev_std = np.empty(n_samples, dtype=np.float32)
    elev_min = np.empty(n_samples, dtype=np.float32)
    elev_max = np.empty(n_samples, dtype=np.float32)
    elev_med = np.empty(n_samples, dtype=np.float32)
    aggregate_continuous_stats(arr_dem, r0s, r1s, c0s, c1s, elev_mean, elev_std, elev_min, elev_max, elev_med, -999999.0)
    del arr_dem

    # Slope
    logger.info("Aggregating Slope (30m)...")
    with rasterio.open("data/processed/phase7/terrain/mahanadi_slope_deg_30m.tif") as src:
        arr_slope = src.read(1)
    
    slope_mean = np.empty(n_samples, dtype=np.float32)
    slope_std = np.empty(n_samples, dtype=np.float32)
    slope_min = np.empty(n_samples, dtype=np.float32)
    slope_max = np.empty(n_samples, dtype=np.float32)
    slope_med = np.empty(n_samples, dtype=np.float32)
    aggregate_continuous_stats(arr_slope, r0s, r1s, c0s, c1s, slope_mean, slope_std, slope_min, slope_max, slope_med, -9999.0)
    del arr_slope

    # Aspect
    logger.info("Aggregating Aspect Circular Statistics (30m)...")
    with rasterio.open("data/processed/phase7/terrain/mahanadi_aspect_deg_30m.tif") as src:
        arr_aspect = src.read(1)
    
    aspect_cos = np.empty(n_samples, dtype=np.float32)
    aspect_sin = np.empty(n_samples, dtype=np.float32)
    aspect_deg = np.empty(n_samples, dtype=np.float32)
    aspect_cvar = np.empty(n_samples, dtype=np.float32)
    aspect_flat = np.empty(n_samples, dtype=np.float32)
    aggregate_aspect_circular(arr_aspect, r0s, r1s, c0s, c1s, aspect_cos, aspect_sin, aspect_deg, aspect_cvar, aspect_flat, -9999.0)
    del arr_aspect

    # Plan Curvature
    logger.info("Aggregating Plan Curvature (30m)...")
    with rasterio.open("data/processed/phase7/terrain/mahanadi_plan_curvature_30m.tif") as src:
        arr_plan = src.read(1)
    
    plan_mean = np.empty(n_samples, dtype=np.float32)
    plan_std = np.empty(n_samples, dtype=np.float32)
    plan_min = np.empty(n_samples, dtype=np.float32)
    plan_max = np.empty(n_samples, dtype=np.float32)
    plan_med = np.empty(n_samples, dtype=np.float32)
    aggregate_continuous_stats(arr_plan, r0s, r1s, c0s, c1s, plan_mean, plan_std, plan_min, plan_max, plan_med, -9999.0)
    del arr_plan

    # Profile Curvature
    logger.info("Aggregating Profile Curvature (30m)...")
    with rasterio.open("data/processed/phase7/terrain/mahanadi_profile_curvature_30m.tif") as src:
        arr_prof = src.read(1)
    
    prof_mean = np.empty(n_samples, dtype=np.float32)
    prof_std = np.empty(n_samples, dtype=np.float32)
    prof_min = np.empty(n_samples, dtype=np.float32)
    prof_max = np.empty(n_samples, dtype=np.float32)
    prof_med = np.empty(n_samples, dtype=np.float32)
    aggregate_continuous_stats(arr_prof, r0s, r1s, c0s, c1s, prof_mean, prof_std, prof_min, prof_max, prof_med, -9999.0)
    del arr_prof

    # TWI
    logger.info("Aggregating Topographic Wetness Index (30m)...")
    with rasterio.open("data/processed/phase7/terrain/mahanadi_twi_30m.tif") as src:
        arr_twi = src.read(1)
    
    twi_mean = np.empty(n_samples, dtype=np.float32)
    twi_std = np.empty(n_samples, dtype=np.float32)
    twi_min = np.empty(n_samples, dtype=np.float32)
    twi_max = np.empty(n_samples, dtype=np.float32)
    twi_med = np.empty(n_samples, dtype=np.float32)
    aggregate_continuous_stats(arr_twi, r0s, r1s, c0s, c1s, twi_mean, twi_std, twi_min, twi_max, twi_med, -9999.0)
    del arr_twi

    # Flow Accumulation
    logger.info("Aggregating Flow Accumulation (30m)...")
    with rasterio.open("data/processed/phase7/terrain/mahanadi_flow_accumulation_30m.tif") as src:
        arr_flow = src.read(1)
    
    flow_mean = np.empty(n_samples, dtype=np.float32)
    flow_max = np.empty(n_samples, dtype=np.float32)
    flow_log_mean = np.empty(n_samples, dtype=np.float32)
    flow_log_max = np.empty(n_samples, dtype=np.float32)
    aggregate_flow_accum(arr_flow, r0s, r1s, c0s, c1s, flow_mean, flow_max, flow_log_mean, flow_log_max)
    del arr_flow

    # Distance to River
    logger.info("Aggregating Distance to River (30m)...")
    with rasterio.open("data/processed/phase7/hydrography/mahanadi_distance_to_river_m_30m.tif") as src:
        arr_driver = src.read(1)
    
    driver_mean = np.empty(n_samples, dtype=np.float32)
    driver_std = np.empty(n_samples, dtype=np.float32)
    driver_min = np.empty(n_samples, dtype=np.float32)
    driver_max = np.empty(n_samples, dtype=np.float32)
    driver_med = np.empty(n_samples, dtype=np.float32)
    aggregate_continuous_stats(arr_driver, r0s, r1s, c0s, c1s, driver_mean, driver_std, driver_min, driver_max, driver_med, -9999.0)
    del arr_driver

    # Distance to Distributary
    logger.info("Aggregating Distance to Distributary (30m)...")
    with rasterio.open("data/processed/phase7/hydrography/mahanadi_distance_to_distributary_m_30m.tif") as src:
        arr_ddistrib = src.read(1)
    
    ddistrib_mean = np.empty(n_samples, dtype=np.float32)
    ddistrib_std = np.empty(n_samples, dtype=np.float32)
    ddistrib_min = np.empty(n_samples, dtype=np.float32)
    ddistrib_max = np.empty(n_samples, dtype=np.float32)
    ddistrib_med = np.empty(n_samples, dtype=np.float32)
    aggregate_continuous_stats(arr_ddistrib, r0s, r1s, c0s, c1s, ddistrib_mean, ddistrib_std, ddistrib_min, ddistrib_max, ddistrib_med, -9999.0)
    del arr_ddistrib

    # Strahler Stream Order
    logger.info("Aggregating Strahler Stream Order (30m)...")
    with rasterio.open("data/processed/phase7/hydrography/mahanadi_strahler_order_30m.tif") as src:
        arr_strahler = src.read(1)
    
    strahler_max = np.empty(n_samples, dtype=np.int8)
    strahler_rep = np.empty(n_samples, dtype=np.int8)
    aggregate_strahler_order(arr_strahler, r0s, r1s, c0s, c1s, strahler_max, strahler_rep)
    del arr_strahler

    # Upstream Catchment Area (km2)
    logger.info("Aggregating Upstream Catchment Area (30m)...")
    with rasterio.open("data/processed/phase7/hydrography/mahanadi_upstream_catchment_area_km2_30m.tif") as src:
        arr_uparea = src.read(1)
    
    uparea_mean = np.empty(n_samples, dtype=np.float32)
    uparea_std = np.empty(n_samples, dtype=np.float32)
    uparea_min = np.empty(n_samples, dtype=np.float32)
    uparea_max = np.empty(n_samples, dtype=np.float32)
    uparea_med = np.empty(n_samples, dtype=np.float32)
    aggregate_continuous_stats(arr_uparea, r0s, r1s, c0s, c1s, uparea_mean, uparea_std, uparea_min, uparea_max, uparea_med, -9999.0)
    del arr_uparea

    # HydroBASINS Subbasin ID (Majority)
    logger.info("Aggregating Subbasin ID (Majority HYBAS_ID)...")
    with rasterio.open("data/processed/phase7/hydrography/mahanadi_subbasin_id_lev08_30m.tif") as src:
        arr_subbasin = src.read(1)
    
    subbasin_majority = np.empty(n_samples, dtype=np.float64)
    aggregate_majority_id(arr_subbasin, r0s, r1s, c0s, c1s, subbasin_majority, 0.0)
    del arr_subbasin
    subbasin_id = subbasin_majority.astype(np.int64)

    # Map subbasin area from GeoJSON
    subbasin_area_map = dict(zip(gdf_basin['HYBAS_ID'], gdf_basin['SUB_AREA']))
    subbasin_area_km2 = np.array([subbasin_area_map.get(sid, np.nan) for sid in subbasin_id], dtype=np.float32)

    # 7. Construct Label Quality and Ground Truth
    logger.info("Determining label quality and categories...")
    flood_labels = (flooded_band[grid_rows, grid_cols] == 1.0).astype(np.int8)
    clear_percs = clear_perc_band[grid_rows, grid_cols].astype(np.float32)

    label_cat = np.where(flood_labels == 1, "VERIFIED_EPISODIC_FLOOD", "VERIFIED_DRY")
    
    # Label quality rubric:
    # HIGH_QUALITY: clear_perc >= 0.90, dry_frac >= 0.90, terrain_cov >= 0.90
    # MEDIUM_QUALITY: clear_perc >= 0.70, dry_frac >= 0.70, terrain_cov >= 0.70
    # MIXED_WATER_MARGIN: dry_frac < 0.70 (bordering perennial water or river)
    label_quality = np.where(
        dry_frac < 0.70,
        "MIXED_WATER_MARGIN",
        np.where(
            (clear_percs >= 0.90) & (dry_frac >= 0.90) & (terrain_cov_frac >= 0.90),
            "HIGH_QUALITY",
            "MEDIUM_QUALITY"
        )
    )

    # 8. Phase 7E Baseline Features & Compatibility Flags
    logger.info("Constructing Phase 7E feature compatibility fields...")
    phase7e_drainage_proxy = (1.0 / (1.0 + driver_mean / 1000.0)).astype(np.float32)
    phase7e_temporal_window = np.full(n_samples, 168.0, dtype=np.float32) # 7-day GFD composite
    phase7e_rain_6h = np.full(n_samples, np.nan, dtype=np.float32)
    phase7e_rain_24h = np.full(n_samples, np.nan, dtype=np.float32)
    phase7e_rain_72h = np.full(n_samples, np.nan, dtype=np.float32)
    phase7e_compatible = np.full(n_samples, False, dtype=bool)
    phase7e_incompat_reason = np.full(n_samples, "RAINFALL_ACCUMULATION_UNAVAILABLE", dtype=object)

    # Missing indicators
    rain_missing_indicator = np.ones(n_samples, dtype=np.int8)
    elev_missing_indicator = np.isnan(elev_mean).astype(np.int8)
    hydro_missing_indicator = np.isnan(driver_mean).astype(np.int8)

    # Cell ID
    dfo_cell_ids = [f"DFO3382_R{r:04d}_C{c:04d}" for r, c in zip(grid_rows, grid_cols)]

    # 9. Assemble DataFrame
    logger.info("Assembling master tabular dataset...")
    df = pd.DataFrame({
        # Identifiers & Geometry
        "dfo_cell_id": dfo_cell_ids,
        "event_id": "DFO_3382",
        "administrative_event_id": "UEI-IMD-FL-2008-0095",
        "basin_name": "Mahanadi",
        "state": "Odisha",
        "grid_row": grid_rows.astype(np.int32),
        "grid_col": grid_cols.astype(np.int32),
        "longitude": lons,
        "latitude": lats,
        "lon_min": lon_mins,
        "lon_max": lon_maxs,
        "lat_min": lat_mins,
        "lat_max": lat_maxs,
        "pixel_area_m2": pixel_area_m2,

        # DFO Native Observations & Ground Truth
        "gfd_flooded_raw": flooded_band[grid_rows, grid_cols].astype(np.float32),
        "gfd_duration": duration_band[grid_rows, grid_cols].astype(np.float32),
        "gfd_clear_views": clear_views_band[grid_rows, grid_cols].astype(np.float32),
        "gfd_clear_perc": clear_percs,
        "gfd_jrc_perm_water": jrc_perm_band[grid_rows, grid_cols].astype(np.float32),
        "flood_label": flood_labels,
        "label_category": label_cat,
        "label_quality": label_quality,
        "in_mahanadi_basin": in_mahanadi,
        "in_delta_corridor": in_delta,

        # High-Resolution Terrain Aggregates (30m)
        "elevation_mean_m": elev_mean,
        "elevation_median_m": elev_med,
        "elevation_min_m": elev_min,
        "elevation_max_m": elev_max,
        "elevation_std_m": elev_std,
        "slope_mean_deg": slope_mean,
        "slope_median_deg": slope_med,
        "slope_max_deg": slope_max,
        "aspect_mean_cos": aspect_cos,
        "aspect_mean_sin": aspect_sin,
        "aspect_mean_deg": aspect_deg,
        "aspect_circular_var": aspect_cvar,
        "aspect_flat_fraction": aspect_flat,
        "plan_curvature_mean": plan_mean,
        "plan_curvature_std": plan_std,
        "profile_curvature_mean": prof_mean,
        "profile_curvature_std": prof_std,
        "twi_mean": twi_mean,
        "twi_median": twi_med,
        "twi_min": twi_min,
        "twi_max": twi_max,
        "flow_accum_mean": flow_mean,
        "flow_accum_max": flow_max,
        "flow_accum_log10_mean": flow_log_mean,
        "flow_accum_log10_max": flow_log_max,

        # Hydrography Aggregates (30m)
        "dist_to_river_mean_m": driver_mean,
        "dist_to_river_min_m": driver_min,
        "dist_to_distributary_mean_m": ddistrib_mean,
        "dist_to_distributary_min_m": ddistrib_min,
        "strahler_order_max": strahler_max,
        "strahler_order_rep": strahler_rep,
        "upstream_catchment_area_max_km2": uparea_max,
        "upstream_catchment_area_mean_km2": uparea_mean,
        "subbasin_id_lev08": subbasin_id,
        "subbasin_area_km2": subbasin_area_km2,

        # Land Cover & Coverage
        "land_water_dry_fraction": dry_frac,
        "land_water_ocean_fraction": ocean_frac,
        "land_water_lake_fraction": lake_frac,
        "land_water_river_fraction": river_frac,
        "valid_30m_pixel_count": valid_30m_cnt,
        "total_30m_pixel_count": total_30m_cnt,
        "terrain_coverage_fraction": terrain_cov_frac,

        # Phase 7E Baseline Compatibility
        "phase7e_elevation_m": elev_mean,
        "phase7e_slope_deg": slope_mean,
        "phase7e_drainage_proxy_score": phase7e_drainage_proxy,
        "phase7e_rainfall_accum_6h_mm": phase7e_rain_6h,
        "phase7e_rainfall_accum_24h_mm": phase7e_rain_24h,
        "phase7e_rainfall_accum_72h_mm": phase7e_rain_72h,
        "phase7e_temporal_window_hours": phase7e_temporal_window,
        "phase7e_model_compatible": phase7e_compatible,
        "phase7e_incompatibility_reason": phase7e_incompat_reason,

        # Missingness Indicators
        "rainfall_missing_indicator": rain_missing_indicator,
        "elevation_missing_indicator": elev_missing_indicator,
        "hydro_missing_indicator": hydro_missing_indicator,
    })

    logger.info(f"Master DataFrame created with shape: {df.shape}")

    # 10. Export Authoritative Parquet Dataset
    logger.info(f"Writing authoritative Parquet dataset to {out_parquet}...")
    df.to_parquet(out_parquet, index=False, engine="pyarrow", compression="snappy")
    parquet_size_mb = out_parquet.stat().st_size / (1024 * 1024)
    logger.info(f"Parquet dataset saved: {parquet_size_mb:.2f} MB")

    # 11. Practical CSV Export (Mahanadi Basin focus)
    logger.info(f"Writing practical CSV export for Mahanadi Basin (N={in_mahanadi.sum():,}) to {out_csv}...")
    df_mahanadi = df[df["in_mahanadi_basin"]].copy()
    df_mahanadi.to_csv(out_csv, index=False)
    csv_size_mb = out_csv.stat().st_size / (1024 * 1024)
    logger.info(f"CSV export saved: {csv_size_mb:.2f} MB")

    # 12. Diagnostic Balanced Sample (1:1 Ratio)
    logger.info("Constructing diagnostic balanced sample (1:1 ratio)...")
    flood_indices = df[df["flood_label"] == 1].index
    dry_indices = df[df["flood_label"] == 0].index
    
    np.random.seed(42)
    sampled_dry = np.random.choice(dry_indices, size=len(flood_indices), replace=False)
    balanced_indices = np.concatenate([flood_indices, sampled_dry])
    np.random.shuffle(balanced_indices)
    
    df_balanced = df.loc[balanced_indices].copy()
    df_balanced["diagnostic_sample"] = True
    df_balanced.to_parquet(out_diag, index=False, engine="pyarrow", compression="snappy")
    diag_size_mb = out_diag.stat().st_size / (1024 * 1024)
    logger.info(f"Diagnostic balanced sample saved: {out_diag} ({len(df_balanced):,} rows, {diag_size_mb:.2f} MB)")

    # 13. Feature Availability Matrix
    logger.info(f"Generating feature availability matrix: {out_avail}...")
    avail_rows = [
        {"feature_name": "elevation_mean_m", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30", "native_resolution": "30m", "aggregation_method": "arithmetic_mean", "status": "AVAILABLE", "phase7e_active": True, "notes": "Aggregated mean elevation in native DFO cell"},
        {"feature_name": "elevation_median_m", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30", "native_resolution": "30m", "aggregation_method": "median", "status": "AVAILABLE", "phase7e_active": False, "notes": "Robust median elevation"},
        {"feature_name": "elevation_min_m", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30", "native_resolution": "30m", "aggregation_method": "minimum", "status": "AVAILABLE", "phase7e_active": False, "notes": "Minimum elevation in cell"},
        {"feature_name": "elevation_max_m", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30", "native_resolution": "30m", "aggregation_method": "maximum", "status": "AVAILABLE", "phase7e_active": False, "notes": "Maximum elevation in cell"},
        {"feature_name": "elevation_std_m", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30", "native_resolution": "30m", "aggregation_method": "standard_deviation", "status": "AVAILABLE", "phase7e_active": False, "notes": "Sub-pixel elevation variation"},
        {"feature_name": "slope_mean_deg", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Horn 1981", "native_resolution": "30m", "aggregation_method": "arithmetic_mean", "status": "AVAILABLE", "phase7e_active": True, "notes": "Mean slope in degrees"},
        {"feature_name": "slope_median_deg", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Horn 1981", "native_resolution": "30m", "aggregation_method": "median", "status": "AVAILABLE", "phase7e_active": False, "notes": "Median slope in degrees"},
        {"feature_name": "slope_max_deg", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Horn 1981", "native_resolution": "30m", "aggregation_method": "maximum", "status": "AVAILABLE", "phase7e_active": False, "notes": "Maximum slope in degrees"},
        {"feature_name": "aspect_mean_cos", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Horn 1981", "native_resolution": "30m", "aggregation_method": "circular_mean_cosine", "status": "AVAILABLE", "phase7e_active": False, "notes": "Circular mean cosine component of aspect"},
        {"feature_name": "aspect_mean_sin", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Horn 1981", "native_resolution": "30m", "aggregation_method": "circular_mean_sine", "status": "AVAILABLE", "phase7e_active": False, "notes": "Circular mean sine component of aspect"},
        {"feature_name": "aspect_mean_deg", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Horn 1981", "native_resolution": "30m", "aggregation_method": "circular_mean_angle", "status": "AVAILABLE", "phase7e_active": False, "notes": "Circular mean direction [0, 360), NaN if 100% flat"},
        {"feature_name": "aspect_circular_var", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Horn 1981", "native_resolution": "30m", "aggregation_method": "circular_variance", "status": "AVAILABLE", "phase7e_active": False, "notes": "Directional dispersion [0, 1]"},
        {"feature_name": "aspect_flat_fraction", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Horn 1981", "native_resolution": "30m", "aggregation_method": "proportion", "status": "AVAILABLE", "phase7e_active": False, "notes": "Proportion of flat pixels (aspect = -1)"},
        {"feature_name": "plan_curvature_mean", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Zevenbergen-Thorne", "native_resolution": "30m", "aggregation_method": "arithmetic_mean", "status": "AVAILABLE", "phase7e_active": False, "notes": "Flow convergence/divergence"},
        {"feature_name": "profile_curvature_mean", "feature_group": "terrain_30m", "source": "Copernicus DEM GLO-30 Zevenbergen-Thorne", "native_resolution": "30m", "aggregation_method": "arithmetic_mean", "status": "AVAILABLE", "phase7e_active": False, "notes": "Flow acceleration/deceleration"},
        {"feature_name": "twi_mean", "feature_group": "terrain_30m", "source": "ln(a / tan(beta))", "native_resolution": "30m", "aggregation_method": "arithmetic_mean", "status": "AVAILABLE", "phase7e_active": False, "notes": "Topographic Wetness Index mean"},
        {"feature_name": "flow_accum_log10_max", "feature_group": "terrain_30m", "source": "D8 Flow Direction", "native_resolution": "30m", "aggregation_method": "log10_maximum", "status": "AVAILABLE", "phase7e_active": False, "notes": "Log10 max upstream 30m cell count"},
        {"feature_name": "dist_to_river_mean_m", "feature_group": "hydrography_30m", "source": "HydroRIVERS Asia v1.0", "native_resolution": "30m", "aggregation_method": "euclidean_mean", "status": "AVAILABLE", "phase7e_active": False, "notes": "Mean distance to stream channel"},
        {"feature_name": "phase7e_drainage_proxy_score", "feature_group": "phase7e_baseline", "source": "Derived: 1 / (1 + dist_m/1000)", "native_resolution": "Native DFO", "aggregation_method": "formula", "status": "DERIVED", "phase7e_active": True, "notes": "Phase 7E drainage proximity proxy"},
        {"feature_name": "phase7e_rainfall_accum_6h_mm", "feature_group": "phase7e_baseline", "source": "N/A (Historical Event 2008)", "native_resolution": "N/A", "aggregation_method": "none", "status": "UNAVAILABLE", "phase7e_active": True, "notes": "Rainfall unobserved locally; NaN preserved"},
        {"feature_name": "phase7e_rainfall_accum_24h_mm", "feature_group": "phase7e_baseline", "source": "N/A (Historical Event 2008)", "native_resolution": "N/A", "aggregation_method": "none", "status": "UNAVAILABLE", "phase7e_active": True, "notes": "Rainfall unobserved locally; NaN preserved"},
        {"feature_name": "phase7e_rainfall_accum_72h_mm", "feature_group": "phase7e_baseline", "source": "N/A (Historical Event 2008)", "native_resolution": "N/A", "aggregation_method": "none", "status": "UNAVAILABLE", "phase7e_active": True, "notes": "Rainfall unobserved locally; NaN preserved"},
        {"feature_name": "phase7e_temporal_window_hours", "feature_group": "phase7e_baseline", "source": "GFD Metadata (8-day composite)", "native_resolution": "Event-level", "aggregation_method": "constant", "status": "AVAILABLE", "phase7e_active": True, "notes": "Nominal duration 168.0h"},
        {"feature_name": "strahler_order_max", "feature_group": "hydrography_30m", "source": "HydroRIVERS Asia v1.0", "native_resolution": "30m", "aggregation_method": "maximum", "status": "AVAILABLE", "phase7e_active": False, "notes": "Max Strahler stream order (0..7)"},
        {"feature_name": "upstream_catchment_area_max_km2", "feature_group": "hydrography_30m", "source": "HydroRIVERS Asia v1.0", "native_resolution": "30m", "aggregation_method": "maximum", "status": "AVAILABLE", "phase7e_active": False, "notes": "Max upstream catchment area (km2)"},
        {"feature_name": "subbasin_id_lev08", "feature_group": "hydrography_30m", "source": "HydroBASINS Level 8", "native_resolution": "30m", "aggregation_method": "mode", "status": "AVAILABLE", "phase7e_active": False, "notes": "Majority Level 8 HYBAS_ID"},
        {"feature_name": "subbasin_area_km2", "feature_group": "hydrography_30m", "source": "HydroBASINS Level 8 Attributes", "native_resolution": "Polygon", "aggregation_method": "lookup", "status": "AVAILABLE", "phase7e_active": False, "notes": "Drainage area of sub-basin"},
        {"feature_name": "land_water_dry_fraction", "feature_group": "land_cover_30m", "source": "Copernicus WBM 30m", "native_resolution": "30m", "aggregation_method": "proportion", "status": "AVAILABLE", "phase7e_active": False, "notes": "Proportion terrestrial dry land"},
        {"feature_name": "terrain_coverage_fraction", "feature_group": "quality", "source": "Copernicus DEM 30m Mask", "native_resolution": "30m", "aggregation_method": "proportion", "status": "AVAILABLE", "phase7e_active": False, "notes": "Fraction of valid 30m pixels overlapping DFO cell"},
    ]
    df_avail = pd.DataFrame(avail_rows)
    df_avail.to_csv(out_avail, index=False)

    # 14. Label Quality and Summary JSON
    logger.info(f"Generating label quality summary JSON: {out_summary}...")
    summary = {
        "event_id": "DFO_3382",
        "administrative_event_id": "UEI-IMD-FL-2008-0095",
        "basin": "Mahanadi",
        "state": "Odisha",
        "raster_grid": {
            "source": "Global Flood Database v1.4 (MODIS GFD)",
            "native_crs": "EPSG:4326",
            "nominal_resolution_m": 250.0,
            "dfo_cell_width_deg": 0.002245788210298804,
            "dfo_cell_height_deg": 0.002245788210298804,
            "window_rows": win_h,
            "window_cols": win_w,
            "total_window_cells": total_cells,
        },
        "observation_audit": {
            "total_cells": total_cells,
            "open_ocean_or_off_domain_cells": nan_cells,
            "valid_observation_cells": valid_obs_cells,
            "raw_flooded_band_cells": int((flooded_band == 1.0).sum()),
            "raw_non_flooded_band_cells": int((flooded_band == 0.0).sum()),
            "permanent_water_excluded_cells": perm_count,
            "raw_flooded_on_permanent_water_excluded": int(raw_flood_on_perm.sum()),
            "low_clear_views_excluded_cells": low_clear_count,
            "eligible_labeled_cells": eligible_count,
            "verified_episodic_flood_cells": flood_count,
            "verified_dry_cells": dry_count,
            "natural_flood_prevalence_percent": round(prevalence, 4),
        },
        "spatial_breakdown": {
            "full_dem_mosaic_domain": {
                "bounds_lon": [84.0, 88.0],
                "bounds_lat": [19.0, 22.0],
                "total_labeled_samples": eligible_count,
                "verified_flood_samples": flood_count,
                "verified_dry_samples": dry_count,
                "natural_prevalence_percent": round(prevalence, 4),
            },
            "mahanadi_basin": {
                "total_labeled_samples": int(in_mahanadi.sum()),
                "verified_flood_samples": int(((flooded_band[grid_rows, grid_cols] == 1.0) & in_mahanadi).sum()),
                "verified_dry_samples": int(((flooded_band[grid_rows, grid_cols] == 0.0) & in_mahanadi).sum()),
                "natural_prevalence_percent": round(int(((flooded_band[grid_rows, grid_cols] == 1.0) & in_mahanadi).sum()) / int(in_mahanadi.sum()) * 100.0, 4),
            },
            "core_delta_subbasins": {
                "total_labeled_samples": int(in_delta.sum()),
                "verified_flood_samples": int(((flooded_band[grid_rows, grid_cols] == 1.0) & in_delta).sum()),
                "verified_dry_samples": int(((flooded_band[grid_rows, grid_cols] == 0.0) & in_delta).sum()),
                "natural_prevalence_percent": round(int(((flooded_band[grid_rows, grid_cols] == 1.0) & in_delta).sum()) / int(in_delta.sum()) * 100.0, 4),
            }
        },
        "label_quality_breakdown": {
            "high_quality_samples": int((label_quality == "HIGH_QUALITY").sum()),
            "medium_quality_samples": int((label_quality == "MEDIUM_QUALITY").sum()),
            "mixed_water_margin_samples": int((label_quality == "MIXED_WATER_MARGIN").sum()),
        },
        "model_compatibility": {
            "phase7e_model_compatible": False,
            "incompatibility_status": "NOT_COMPATIBLE_WITH_PHASE7E_MODEL",
            "incompatibility_reason": "RAINFALL_ACCUMULATION_UNAVAILABLE",
            "missing_active_features": [
                "rainfall_accum_6h_mm",
                "rainfall_accum_24h_mm",
                "rainfall_accum_72h_mm"
            ],
            "recommendation": "Use separate terrain-hydrographic experimental ML architecture; do not force compatibility with Phase 7E baseline."
        },
        "governance": {
            "phase6_engine_status": "SOLE_OPERATIONAL_AUTHORITY",
            "phase7e_artifacts_status": "PRESERVED_UNCHANGED",
            "dfo2507_status": "QUARANTINED_ALREADY_INSPECTED_HOLDOUT_ZERO_ACCESS",
            "generation_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "execution_duration_seconds": round(time.time() - t_start, 2),
        }
    }
    with open(out_summary, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Dataset preparation complete in {time.time() - t_start:.2f}s!")
    return summary

if __name__ == "__main__":
    build_dfo3382_dataset()
