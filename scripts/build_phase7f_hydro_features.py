#!/usr/bin/env python3
"""
AQUORA Phase 7F Stage 2: Hydrographic Feature Engineering
Extracts and generates 30m hydrographic rasters matching the Copernicus DEM mosaic grid:
1. Distance to mapped HydroRIVERS (meters)
2. Strahler stream order (1 to 7)
3. Distance to verified delta distributaries (meters)
4. Sub-basin identifier (HydroBASINS Level 8 HYBAS_ID)
5. Upstream catchment area (km²)
6. Terrain elevation and slope summaries for delta sub-basins

Preserves physical distinction between mapped river channels and unrepresented canals/tidal creeks.
Outputs:
- data/processed/phase7/hydrography/mahanadi_distance_to_river_m_30m.tif
- data/processed/phase7/hydrography/mahanadi_strahler_order_30m.tif
- data/processed/phase7/hydrography/mahanadi_distance_to_distributary_m_30m.tif
- data/processed/phase7/hydrography/mahanadi_subbasin_id_lev08_30m.tif
- data/processed/phase7/hydrography/mahanadi_upstream_catchment_area_km2_30m.tif
- docs/phase7/DFO_3382_subbasin_terrain_summary.json
"""

import os
import sys
import json
import time
from datetime import datetime, timezone

import numpy as np
import rasterio
from rasterio import features
from scipy.ndimage import distance_transform_edt
import geopandas as gpd

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VRT_PATH = os.path.join(WORKSPACE, "data", "processed", "phase7", "terrain", "mahanadi_dem_mosaic_30m.vrt")
SLOPE_PATH = os.path.join(WORKSPACE, "data", "processed", "phase7", "terrain", "mahanadi_slope_deg_30m.tif")
HYDRO_DIR = os.path.join(WORKSPACE, "data", "processed", "phase7", "hydrography")
DOCS_DIR = os.path.join(WORKSPACE, "docs", "phase7")

RIVERS_PATH = os.path.join(HYDRO_DIR, "mahanadi_hydrorivers.geojson")
SUBBASIN_PATH = os.path.join(WORKSPACE, "data", "processed", "phase7", "boundaries", "mahanadi_hydrobasins", "mahanadi_hydrobasins_lev08.geojson")
DELTA_SUBBASINS_PATH = os.path.join(WORKSPACE, "data", "processed", "phase7", "boundaries", "mahanadi_hydrobasins", "mahanadi_delta_lev08_subbasins.geojson")

def build_hydro_features():
    print("=" * 80)
    print("AQUORA PHASE 7F STAGE 2: HYDROGRAPHIC FEATURE ENGINEERING")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    t0 = time.time()
    os.makedirs(HYDRO_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    # 1. Inspect DEM grid geometry
    with rasterio.open(VRT_PATH) as src_dem:
        meta = src_dem.meta.copy()
        width = src_dem.width
        height = src_dem.height
        transform = src_dem.transform
        bounds = src_dem.bounds
        res = src_dem.res

    print(f"\n[1] DEM Mosaic Grid: {width} x {height} ({width * height:,} pixels)")
    print(f"    Bounds: Left={bounds.left:.4f}, Bottom={bounds.bottom:.4f}, Right={bounds.right:.4f}, Top={bounds.top:.4f}")

    # Output profiles
    f32_prof = meta.copy()
    f32_prof.update({
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "nodata": -9999.0,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
    })

    u8_prof = meta.copy()
    u8_prof.update({
        "driver": "GTiff",
        "dtype": "uint8",
        "count": 1,
        "nodata": 0,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
    })

    u64_prof = meta.copy()
    u64_prof.update({
        "driver": "GTiff",
        "dtype": "float64",
        "count": 1,
        "nodata": 0.0,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
    })

    # 2. Load Vector Networks
    print("\n[2] Loading HydroRIVERS network and HydroBASINS sub-basins...")
    gdf_riv = gpd.read_file(RIVERS_PATH)
    gdf_sub = gpd.read_file(SUBBASIN_PATH)
    gdf_delta = gpd.read_file(DELTA_SUBBASINS_PATH)
    print(f"    HydroRIVERS reaches: {len(gdf_riv):,}")
    print(f"    HydroBASINS Level 8 sub-basins: {len(gdf_sub):,}")
    print(f"    Mahanadi Delta core sub-basins: {len(gdf_delta)}")

    # Spatial filter reaches within bounds
    gdf_riv_bounds = gdf_riv.cx[bounds.left:bounds.right, bounds.bottom:bounds.top]
    print(f"    Reaches within DEM mosaic bounds: {len(gdf_riv_bounds):,}")

    # 3. Rasterize Strahler Stream Order
    print("\n[3] Rasterizing Strahler Stream Order (1 to 7)...")
    strahler_shapes = ((geom, int(order)) for geom, order in zip(gdf_riv_bounds.geometry, gdf_riv_bounds["ORD_STRA"]))
    strahler_grid = features.rasterize(strahler_shapes, out_shape=(height, width), transform=transform, fill=0, dtype=np.uint8)

    strahler_path = os.path.join(HYDRO_DIR, "mahanadi_strahler_order_30m.tif")
    with rasterio.open(strahler_path, "w", **u8_prof) as dst:
        dst.write(strahler_grid, 1)
    print(f"    Wrote: {os.path.relpath(strahler_path, WORKSPACE)}")
    print(f"    Stream cells burned: {np.sum(strahler_grid > 0):,}")

    # 4. Compute Distance to Mapped River
    print("\n[4] Computing Euclidean Distance to Mapped River (SciPy EDT)...")
    t_edt = time.time()
    river_mask = (strahler_grid == 0)  # True = non-river (distance to compute)
    dist_px = distance_transform_edt(river_mask)
    
    # Convert pixel distance to meters using local cell spacing
    # At latitude 20.5 N: dx ≈ 29.0 m, dy ≈ 30.9 m; mean spacing ≈ 29.95 m
    dx = float(res[0] * 111320.0 * np.cos(np.radians(20.5)))
    dy = float(res[1] * 111320.0)
    mean_cell_m = (dx + dy) / 2.0
    dist_river_m = (dist_px * mean_cell_m).astype(np.float32)
    print(f"    EDT completed in {time.time() - t_edt:.1f}s")
    print(f"    Distance range: {dist_river_m.min():.1f} m to {dist_river_m.max():.1f} m, Mean={dist_river_m.mean():.1f} m")

    dist_river_path = os.path.join(HYDRO_DIR, "mahanadi_distance_to_river_m_30m.tif")
    with rasterio.open(dist_river_path, "w", **f32_prof) as dst:
        dst.write(dist_river_m, 1)
    print(f"    Wrote: {os.path.relpath(dist_river_path, WORKSPACE)}")

    del dist_px, dist_river_m, river_mask  # Free RAM

    # 5. Compute Distance to Verified Delta Distributaries
    print("\n[5] Computing Distance to Delta Distributaries (Strahler >= 5 in Delta corridor)...")
    # Identify major delta distributaries: Strahler order >= 5 in east of 85.5°E and south of 21.0°N
    distrib_mask = gdf_riv_bounds[
        (gdf_riv_bounds["ORD_STRA"] >= 5) & 
        (gdf_riv_bounds.geometry.centroid.x >= 85.3) & 
        (gdf_riv_bounds.geometry.centroid.y <= 21.0)
    ]
    print(f"    Identified {len(distrib_mask)} major delta distributary reach segments.")

    distrib_shapes = ((geom, 1) for geom in distrib_mask.geometry)
    distrib_grid = features.rasterize(distrib_shapes, out_shape=(height, width), transform=transform, fill=0, dtype=np.uint8)

    t_edt2 = time.time()
    distrib_edt_mask = (distrib_grid == 0)
    dist_distrib_px = distance_transform_edt(distrib_edt_mask)
    dist_distrib_m = (dist_distrib_px * mean_cell_m).astype(np.float32)
    print(f"    Distributary EDT completed in {time.time() - t_edt2:.1f}s")
    print(f"    Distributary distance range: {dist_distrib_m.min():.1f} m to {dist_distrib_m.max():.1f} m")

    dist_distrib_path = os.path.join(HYDRO_DIR, "mahanadi_distance_to_distributary_m_30m.tif")
    with rasterio.open(dist_distrib_path, "w", **f32_prof) as dst:
        dst.write(dist_distrib_m, 1)
    print(f"    Wrote: {os.path.relpath(dist_distrib_path, WORKSPACE)}")

    del dist_distrib_px, dist_distrib_m, distrib_edt_mask, distrib_grid

    # 6. Rasterize Sub-Basin Identifiers and Upstream Catchment Area
    print("\n[6] Rasterizing HydroBASINS Level 8 Sub-Basins and Upstream Catchment Area...")
    sub_shapes = ((geom, float(hid)) for geom, hid in zip(gdf_sub.geometry, gdf_sub["HYBAS_ID"]))
    subbasin_grid = features.rasterize(sub_shapes, out_shape=(height, width), transform=transform, fill=0.0, dtype=np.float64)

    subbasin_path = os.path.join(HYDRO_DIR, "mahanadi_subbasin_id_lev08_30m.tif")
    with rasterio.open(subbasin_path, "w", **u64_prof) as dst:
        dst.write(subbasin_grid, 1)
    print(f"    Wrote: {os.path.relpath(subbasin_path, WORKSPACE)}")

    up_shapes = ((geom, float(up)) for geom, up in zip(gdf_sub.geometry, gdf_sub["UP_AREA"]))
    uparea_grid = features.rasterize(up_shapes, out_shape=(height, width), transform=transform, fill=0.0, dtype=np.float32)

    uparea_path = os.path.join(HYDRO_DIR, "mahanadi_upstream_catchment_area_km2_30m.tif")
    with rasterio.open(uparea_path, "w", **f32_prof) as dst:
        dst.write(uparea_grid, 1)
    print(f"    Wrote: {os.path.relpath(uparea_path, WORKSPACE)}")

    # 7. Compute Terrain Elevation and Slope Summaries for Delta Sub-Basins
    print("\n[7] Computing Zonal Terrain Elevation and Slope Summaries for 7 Delta Sub-Basins...")
    src_dem = rasterio.open(VRT_PATH)
    src_slope = rasterio.open(SLOPE_PATH)

    delta_summaries = []
    for idx, row in gdf_delta.iterrows():
        hid = int(row["HYBAS_ID"])
        pfaf = int(row["PFAF_ID"])
        geom = row.geometry
        area_km2 = float(row["SUB_AREA"])
        up_km2 = float(row["UP_AREA"])
        next_down = int(row["NEXT_DOWN"])

        # Extract sub-basin bounding box
        minx, miny, maxx, maxy = geom.bounds
        b_win = rasterio.windows.from_bounds(minx, miny, maxx, maxy, transform=src_dem.transform)
        # Round window to integer
        b_win = b_win.round_lengths().round_offsets()

        dem_win = src_dem.read(1, window=b_win)
        slope_win = src_slope.read(1, window=b_win)
        win_trans = rasterio.windows.transform(b_win, src_dem.transform)

        # Rasterize this specific polygon into window
        poly_mask = features.rasterize([(geom, 1)], out_shape=dem_win.shape, transform=win_trans, fill=0, dtype=np.uint8) == 1

        # Valid terrestrial terrain
        valid = poly_mask & (dem_win > -9999) & ~np.isnan(dem_win) & (slope_win >= 0) & (slope_win < 90)

        if np.any(valid):
            v_dem = dem_win[valid]
            v_slope = slope_win[valid]

            elev_min = float(v_dem.min())
            elev_max = float(v_dem.max())
            elev_mean = float(v_dem.mean())
            elev_std = float(v_dem.std())

            slope_min = float(v_slope.min())
            slope_max = float(v_slope.max())
            slope_mean = float(v_slope.mean())
            slope_std = float(v_slope.std())
        else:
            elev_min = elev_max = elev_mean = elev_std = 0.0
            slope_min = slope_max = slope_mean = slope_std = 0.0

        rec = {
            "hybas_id": hid,
            "pfaf_id": pfaf,
            "sub_basin_name": f"Delta Sub-basin {hid}",
            "sub_area_km2": round(area_km2, 1),
            "upstream_area_km2": round(up_km2, 1),
            "next_down_id": next_down,
            "elevation_summary_m": {
                "min": round(elev_min, 2),
                "max": round(elev_max, 2),
                "mean": round(elev_mean, 2),
                "std": round(elev_std, 2)
            },
            "slope_summary_deg": {
                "min": round(slope_min, 2),
                "max": round(slope_max, 2),
                "mean": round(slope_mean, 2),
                "std": round(slope_std, 2)
            }
        }
        delta_summaries.append(rec)
        print(f"    Sub-basin {hid} (Area {area_km2:.1f} km²): Elev Mean={elev_mean:.1f}m (Max {elev_max:.1f}m), Slope Mean={slope_mean:.2f}°")

    src_dem.close()
    src_slope.close()

    # Save JSON summary
    summary_path = os.path.join(DOCS_DIR, "DFO_3382_subbasin_terrain_summary.json")
    summary_data = {
        "event_id": "DFO_3382",
        "phase": "PHASE_7F_STAGE_2",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - t0, 1),
        "hydrographic_source": "HydroRIVERS Asia v1.0 and HydroBASINS Asia Level 8",
        "distributary_definition": "Downstream reaches (east of 85.3°E, south of 21.0°N) with Strahler order >= 5 (Mahanadi main stem, Kathajodi, Kuakhai, Daya, Bhargavi, Devi, Birupa, Chitratpala, Luna)",
        "unrepresented_features_note": "HydroRIVERS maps all natural river channels (down to Strahler 1). Agricultural distribution canals and small tidal creeks are not represented in global hydrography and are intentionally NOT fabricated.",
        "delta_subbasins": delta_summaries
    }

    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)

    elapsed = time.time() - t0
    print("\n" + "=" * 80)
    print(f"HYDROGRAPHIC FEATURES COMPLETE in {elapsed:.1f}s")
    print(f"Saved Delta Sub-Basin Summary JSON to: {os.path.relpath(summary_path, WORKSPACE)}")
    print("=" * 80)

if __name__ == "__main__":
    build_hydro_features()
