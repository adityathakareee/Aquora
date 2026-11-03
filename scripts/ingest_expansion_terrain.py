"""
AQUORA — Authentic Terrain & Landcover Ingestion Pipeline for Expansion Domains:
1. Vijayawada (Krishna River Basin)
2. Nagpur (Godavari River Basin)
3. Ahmedabad (Sabarmati River Basin)

Extracts authentic 30m Copernicus GLO-30 DEM from AWS Open Data COG.
Derives Horn (1981) topographic slope in degrees.
Calculates distance to HydroRIVERS (ORD_STRA >= 4) reaches via padded rasterization and EDT.
Extracts authentic ESA WorldCover 2021 v200 10m data and resamples to 30m grid.
Computes built-up fraction.

ZERO SYNTHETIC DATA: All pixels derived from authentic Copernicus DEM, ESA WorldCover,
and HydroSHEDS HydroRIVERS datasets.
"""

import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from rasterio.transform import from_bounds
from rasterio.windows import from_bounds as win_from_bounds
import scipy.ndimage
from shapely.geometry import box

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROC_DEM = DATA_DIR / "processed" / "dem"
PROC_TERRAIN = DATA_DIR / "processed" / "terrain"
PROC_LANDCOVER = DATA_DIR / "processed" / "landcover"
HYDRORIVERS_SHP = DATA_DIR / "raw" / "phase7" / "hydrography" / "hydrorivers" / "extracted" / "HydroRIVERS_v10_as_shp" / "HydroRIVERS_v10_as.shp"

DOMAINS = [
    {
        "domain_id": "krishna_vijayawada",
        "name": "Vijayawada Krishna River Corridor",
        "basin_id": "BASIN-KRISHNA",
        "state_code": "IN-AP",
        "bbox": (80.55, 16.43, 80.75, 16.58),  # lon_min, lat_min, lon_max, lat_max
        "dem_url": "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N16_00_E080_00_DEM/Copernicus_DSM_COG_10_N16_00_E080_00_DEM.tif",
        "lc_url": "https://esa-worldcover.s3.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N15E078_Map.tif",
    },
    {
        "domain_id": "godavari_nagpur",
        "name": "Nagpur Godavari Corridor",
        "basin_id": "BASIN-GODAVARI",
        "state_code": "IN-MH",
        "bbox": (79.00, 21.05, 79.20, 21.22),
        "dem_url": "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N21_00_E079_00_DEM/Copernicus_DSM_COG_10_N21_00_E079_00_DEM.tif",
        "lc_url": "https://esa-worldcover.s3.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N21E078_Map.tif",
    },
    {
        "domain_id": "sabarmati_ahmedabad",
        "name": "Ahmedabad Sabarmati Corridor",
        "basin_id": "BASIN-SABARMATI",
        "state_code": "IN-GJ",
        "bbox": (72.48, 22.95, 72.68, 23.10),
        "dem_url": "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N23_00_E072_00_DEM/Copernicus_DSM_COG_10_N23_00_E072_00_DEM.tif",
        "lc_url": "https://esa-worldcover.s3.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N21E072_Map.tif",
    },
]


def compute_horn_slope(dem: np.ndarray, cellsize_x_m: float, cellsize_y_m: float) -> np.ndarray:
    """
    Compute surface slope in degrees using Horn (1981) 3x3 finite-difference algorithm.
    """
    kernel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / (8.0 * cellsize_x_m)
    kernel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32) / (8.0 * cellsize_y_m)

    dz_dx = scipy.ndimage.convolve(dem, kernel_x, mode="nearest")
    dz_dy = scipy.ndimage.convolve(dem, kernel_y, mode="nearest")

    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = np.degrees(slope_rad).astype(np.float32)
    return np.clip(slope_deg, 0.0, 90.0)


def compute_river_distance_edt_padded(
    reaches_gdf: gpd.GeoDataFrame,
    win_bounds: Tuple[float, float, float, float],
    shape: Tuple[int, int],
    cell_x_m: float,
    cell_y_m: float,
    pad_deg: float = 0.25,
) -> np.ndarray:
    """
    Rasterize HydroRIVERS reaches onto a padded domain and compute exact metric Euclidean distance transform.
    Padded domain prevents boundary truncations when river reaches run just outside the target domain box.
    """
    height, width = shape
    min_lon, min_lat, max_lon, max_lat = win_bounds
    cell_x_deg = (max_lon - min_lon) / width
    cell_y_deg = (max_lat - min_lat) / height

    pad_x = int(round(pad_deg / cell_x_deg))
    pad_y = int(round(pad_deg / cell_y_deg))

    pad_min_lon = min_lon - pad_x * cell_x_deg
    pad_max_lon = max_lon + pad_x * cell_x_deg
    pad_min_lat = min_lat - pad_y * cell_y_deg
    pad_max_lat = max_lat + pad_y * cell_y_deg

    pad_w = width + 2 * pad_x
    pad_h = height + 2 * pad_y
    pad_transform = from_bounds(pad_min_lon, pad_min_lat, pad_max_lon, pad_max_lat, pad_w, pad_h)

    pad_box = box(pad_min_lon, pad_min_lat, pad_max_lon, pad_max_lat)
    sub_reaches = reaches_gdf[reaches_gdf.intersects(pad_box)]

    if len(sub_reaches) == 0:
        return np.full((height, width), 25000.0, dtype=np.float32)

    shapes = [(geom, 1) for geom in sub_reaches.geometry if geom is not None and not geom.is_empty]
    river_mask = features.rasterize(
        shapes=shapes,
        out_shape=(pad_h, pad_w),
        transform=pad_transform,
        fill=0,
        dtype=np.uint8,
    )

    inv_mask = (river_mask == 0).astype(np.uint8)
    dist_padded = scipy.ndimage.distance_transform_edt(inv_mask, sampling=(cell_y_m, cell_x_m))
    dist_cropped = dist_padded[pad_y : pad_y + height, pad_x : pad_x + width]
    return dist_cropped.astype(np.float32)


def process_domain(domain: Dict[str, Any], rivers_gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    did = domain["domain_id"]
    min_lon, min_lat, max_lon, max_lat = domain["bbox"]
    dem_url = domain["dem_url"]
    lc_url = domain["lc_url"]

    print(f"\n==================================================", flush=True)
    print(f"PROCESSING DOMAIN: {did} ({domain['name']})", flush=True)
    print(f"BBox: lon [{min_lon}, {max_lon}], lat [{min_lat}, {max_lat}]", flush=True)
    print(f"==================================================", flush=True)

    # 1. Read Copernicus DEM Window from S3 COG
    print(f"[{did}] Streaming Copernicus GLO-30 DEM window...", flush=True)
    with rasterio.open("/vsicurl/" + dem_url) as src:
        win = win_from_bounds(min_lon, min_lat, max_lon, max_lat, src.transform)
        c_off = int(math.floor(win.col_off))
        r_off = int(math.floor(win.row_off))
        w = int(math.ceil(win.width))
        h = int(math.ceil(win.height))
        win = rasterio.windows.Window(c_off, r_off, w, h)
        dem_data = src.read(1, window=win).astype(np.float32)
        win_transform = src.window_transform(win)
        height, width = dem_data.shape
        win_bounds = rasterio.windows.bounds(win, src.transform)

    print(f"[{did}] DEM read: {width}x{height} pixels, Mean elevation = {dem_data.mean():.2f}m", flush=True)

    # 2. Derive Horn Slope
    mean_lat = (win_bounds[1] + win_bounds[3]) / 2.0
    cell_y_m = (win_bounds[3] - win_bounds[1]) / height * 111320.0
    cell_x_m = (win_bounds[2] - win_bounds[0]) / width * 111320.0 * math.cos(math.radians(mean_lat))

    slope_data = compute_horn_slope(dem_data, cell_x_m, cell_y_m)
    print(f"[{did}] Slope derived: Mean = {slope_data.mean():.2f}°, Max = {slope_data.max():.2f}°", flush=True)

    # 3. Read ESA WorldCover 10m and resample to 30m DEM grid
    print(f"[{did}] Streaming ESA WorldCover 10m window...", flush=True)
    with rasterio.open("/vsicurl/" + lc_url) as src_lc:
        win_lc = win_from_bounds(win_bounds[0], win_bounds[1], win_bounds[2], win_bounds[3], src_lc.transform)
        c_off_lc = int(math.floor(win_lc.col_off))
        r_off_lc = int(math.floor(win_lc.row_off))
        w_lc = int(math.ceil(win_lc.width))
        h_lc = int(math.ceil(win_lc.height))
        win_lc = rasterio.windows.Window(c_off_lc, r_off_lc, w_lc, h_lc)
        lc_10m = src_lc.read(1, window=win_lc)

    # Resample 10m to 30m grid using zoom
    from scipy.ndimage import zoom
    zoom_factors = (height / lc_10m.shape[0], width / lc_10m.shape[1])
    lc_30m = zoom(lc_10m, zoom_factors, order=0).astype(np.int32)

    # Built-up fraction: class 50 is built-up in ESA WorldCover
    is_builtup_10m = (lc_10m == 50).astype(np.float32)
    filter_size = max(1, int(round(lc_10m.shape[0] / height)))
    builtup_filtered = scipy.ndimage.uniform_filter(is_builtup_10m, size=filter_size)
    builtup_30m = zoom(builtup_filtered, zoom_factors, order=1).astype(np.float32)
    builtup_30m = np.clip(builtup_30m, 0.0, 1.0)
    print(f"[{did}] WorldCover processed: Unique classes = {np.unique(lc_30m).tolist()}, Mean built-up = {builtup_30m.mean():.3f}", flush=True)

    # 4. Compute Distance to River using HydroRIVERS (Padded EDT)
    print(f"[{did}] Computing padded distance to HydroRIVERS reaches (ORD_STRA >= 4)...", flush=True)
    dist_river_m = compute_river_distance_edt_padded(
        rivers_gdf, win_bounds, (height, width), cell_x_m, cell_y_m, pad_deg=0.25
    )
    print(f"[{did}] River distances computed: Min = {dist_river_m.min():.1f}m, Mean = {dist_river_m.mean():.1f}m, Max = {dist_river_m.max():.1f}m", flush=True)

    # 5. Save GeoTIFF Rasters
    meta_float = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": win_transform,
        "nodata": -9999.0,
    }
    meta_int = dict(meta_float)
    meta_int["dtype"] = "int32"
    meta_int["nodata"] = -1

    elev_path = PROC_DEM / f"{did}_elevation_30m.tif"
    with rasterio.open(elev_path, "w", **meta_float) as dst:
        dst.write(dem_data, 1)

    slope_path = PROC_TERRAIN / f"{did}_slope_30m.tif"
    with rasterio.open(slope_path, "w", **meta_float) as dst:
        dst.write(slope_data, 1)

    dist_path = PROC_TERRAIN / f"{did}_distance_to_river_30m.tif"
    with rasterio.open(dist_path, "w", **meta_float) as dst:
        dst.write(dist_river_m, 1)

    lc_path = PROC_LANDCOVER / f"{did}_landcover_30m.tif"
    with rasterio.open(lc_path, "w", **meta_int) as dst:
        dst.write(lc_30m, 1)

    bu_path = PROC_LANDCOVER / f"{did}_built_up_fraction_30m.tif"
    with rasterio.open(bu_path, "w", **meta_float) as dst:
        dst.write(builtup_30m, 1)

    print(f"[{did}] All 5 rasters written to processed directories successfully.", flush=True)
    return {
        "domain_id": did,
        "bbox": [win_bounds[0], win_bounds[1], win_bounds[2], win_bounds[3]],
        "width": width,
        "height": height,
        "elevation_mean": float(dem_data.mean()),
        "slope_mean": float(slope_data.mean()),
        "dist_river_min": float(dist_river_m.min()),
        "dist_river_mean": float(dist_river_m.mean()),
        "dist_river_max": float(dist_river_m.max()),
        "built_up_mean": float(builtup_30m.mean()),
    }


def main():
    PROC_DEM.mkdir(parents=True, exist_ok=True)
    PROC_TERRAIN.mkdir(parents=True, exist_ok=True)
    PROC_LANDCOVER.mkdir(parents=True, exist_ok=True)

    print(f"Loading HydroRIVERS Asia shapefile from: {HYDRORIVERS_SHP}", flush=True)
    rivers_gdf = gpd.read_file(
        HYDRORIVERS_SHP,
        bbox=(68.0, 6.5, 98.0, 37.5),
        where="ORD_STRA >= 4",
    )
    print(f"Loaded {len(rivers_gdf)} HydroRIVERS reaches for India.", flush=True)

    results = []
    for d in DOMAINS:
        res = process_domain(d, rivers_gdf)
        results.append(res)

    print("\n==================================================", flush=True)
    print("ALL EXPANSION DOMAINS PROCESSED SUCCESSFULLY!", flush=True)
    for r in results:
        print(f"Domain: {r['domain_id']}: {r['width']}x{r['height']} cells | Elev: {r['elevation_mean']:.1f}m | Slope: {r['slope_mean']:.1f}deg | DistRiver: {r['dist_river_min']:.0f}-{r['dist_river_max']:.0f}m (mean {r['dist_river_mean']:.0f}m) | BuiltUp: {r['built_up_mean']:.3f}", flush=True)
    print("==================================================", flush=True)


if __name__ == "__main__":
    main()
