"""
AQUORA — Feature Separation & Alignment Script:
1. Derives authentic JRC permanent water distance for Vijayawada from raw JRC GSW occurrence raster.
2. Ensures clear semantic and physical separation between:
   - distance_to_river_m (JRC permanent open surface water distance, Phase 7E model predictor)
   - hydrorivers_reach_distance_m (HydroRIVERS reach centerline distance, independent hydrography metric)
"""

import math
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from scipy.ndimage import distance_transform_edt, zoom

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROC_DEM = DATA_DIR / "processed" / "dem"
PROC_TERRAIN = DATA_DIR / "processed" / "terrain"
JRC_OCCURRENCE_20N = DATA_DIR / "raw" / "phase7" / "water" / "jrc_gsw" / "occurrence_80E_20N.tif"
JRC_OCCURRENCE_30N = DATA_DIR / "raw" / "phase7" / "water" / "jrc_gsw" / "occurrence_80E_30N.tif"

def generate_vijayawada_jrc_water_distance():
    dem_path = PROC_DEM / "krishna_vijayawada_elevation_30m.tif"
    out_path = PROC_TERRAIN / "krishna_vijayawada_jrc_water_distance_30m.tif"
    
    with rasterio.open(dem_path) as dem_src:
        dem_meta = dem_src.meta.copy()
        dem_bounds = dem_src.bounds
        height, width = dem_src.shape

    print(f"Aligning JRC permanent water to Vijayawada DEM grid ({width}x{height} cells)...")
    
    pad_deg = 0.20
    with rasterio.open(JRC_OCCURRENCE_20N) as jrc_src:
        win = from_bounds(
            dem_bounds.left - pad_deg,
            dem_bounds.bottom - pad_deg,
            dem_bounds.right + pad_deg,
            dem_bounds.top + pad_deg,
            jrc_src.transform
        )
        arr = jrc_src.read(1, window=win)
        win_bounds = rasterio.windows.bounds(win, jrc_src.transform)

        perm = (arr >= 80).astype(np.uint8)
        inv = (perm == 0).astype(np.uint8)
        
        cell_y_m = jrc_src.res[1] * 111320.0
        cell_x_m = jrc_src.res[0] * 111320.0 * math.cos(math.radians(16.51))
        
        dist_padded = distance_transform_edt(inv, sampling=(cell_y_m, cell_x_m))
        
        c_min = int(round((dem_bounds.left - win_bounds[0]) / jrc_src.res[0]))
        c_max = int(round((dem_bounds.right - win_bounds[0]) / jrc_src.res[0]))
        r_min = int(round((win_bounds[3] - dem_bounds.top) / jrc_src.res[1]))
        r_max = int(round((win_bounds[3] - dem_bounds.bottom) / jrc_src.res[1]))
        
        dist_crop = dist_padded[r_min:r_max, c_min:c_max]
        zoom_factors = (height / dist_crop.shape[0], width / dist_crop.shape[1])
        dist_resampled = zoom(dist_crop, zoom_factors, order=1).astype(np.float32)

    dem_meta.update({
        "dtype": "float32",
        "nodata": -9999.0,
    })
    
    with rasterio.open(out_path, "w", **dem_meta) as dst:
        dst.write(dist_resampled, 1)
        
    print(f"Generated {out_path}: {dist_resampled.shape}, Min={dist_resampled.min():.1f}m, Mean={dist_resampled.mean():.1f}m, Max={dist_resampled.max():.1f}m")

def generate_patna_jrc_water_distance():
    dem_path = PROC_DEM / "ganga_patna_elevation_30m.tif"
    out_path = PROC_TERRAIN / "ganga_patna_jrc_water_distance_30m.tif"
    
    with rasterio.open(dem_path) as dem_src:
        dem_meta = dem_src.meta.copy()
        dem_bounds = dem_src.bounds
        height, width = dem_src.shape

    print(f"Aligning JRC permanent water to Patna DEM grid ({width}x{height} cells)...")
    
    pad_deg = 0.20
    with rasterio.open(JRC_OCCURRENCE_30N) as jrc_src:
        win = from_bounds(
            dem_bounds.left - pad_deg,
            dem_bounds.bottom - pad_deg,
            dem_bounds.right + pad_deg,
            dem_bounds.top + pad_deg,
            jrc_src.transform
        )
        arr = jrc_src.read(1, window=win)
        win_bounds = rasterio.windows.bounds(win, jrc_src.transform)

        perm = (arr >= 80).astype(np.uint8)
        inv = (perm == 0).astype(np.uint8)
        
        cell_y_m = jrc_src.res[1] * 111320.0
        cell_x_m = jrc_src.res[0] * 111320.0 * math.cos(math.radians(25.60))
        
        dist_padded = distance_transform_edt(inv, sampling=(cell_y_m, cell_x_m))
        
        c_min = int(round((dem_bounds.left - win_bounds[0]) / jrc_src.res[0]))
        c_max = int(round((dem_bounds.right - win_bounds[0]) / jrc_src.res[0]))
        r_min = int(round((win_bounds[3] - dem_bounds.top) / jrc_src.res[1]))
        r_max = int(round((win_bounds[3] - dem_bounds.bottom) / jrc_src.res[1]))
        
        dist_crop = dist_padded[r_min:r_max, c_min:c_max]
        zoom_factors = (height / dist_crop.shape[0], width / dist_crop.shape[1])
        dist_resampled = zoom(dist_crop, zoom_factors, order=1).astype(np.float32)

    dem_meta.update({
        "dtype": "float32",
        "nodata": -9999.0,
    })
    
    with rasterio.open(out_path, "w", **dem_meta) as dst:
        dst.write(dist_resampled, 1)
        
    print(f"Generated {out_path}: {dist_resampled.shape}, Min={dist_resampled.min():.1f}m, Mean={dist_resampled.mean():.1f}m, Max={dist_resampled.max():.1f}m")

if __name__ == "__main__":
    generate_vijayawada_jrc_water_distance()
    generate_patna_jrc_water_distance()
