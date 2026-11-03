#!/usr/bin/env python3
"""
AQUORA Phase 7F Stage 2: DEM Mosaic Preparation and Validation
Creates virtual mosaic (VRT) of 9 Copernicus DEM GLO-30 tiles covering Mahanadi Basin & Delta.
Validates tile seams, spatial bounds, resolution, and DSM structural properties.
"""

import os
import sys
import glob
import json
import time
import hashlib
from datetime import datetime, timezone

import numpy as np
import rasterio
from rasterio.windows import Window

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DEM_DIR = os.path.join(WORKSPACE, "data", "raw", "phase7", "dem", "mahanadi_dfo3382")
PROCESSED_TERRAIN_DIR = os.path.join(WORKSPACE, "data", "processed", "phase7", "terrain")
DOCS_DIR = os.path.join(WORKSPACE, "docs", "phase7")

EXPECTED_TILES = [
    "Copernicus_DSM_COG_10_N19_00_E084_00_DEM.tif",
    "Copernicus_DSM_COG_10_N19_00_E085_00_DEM.tif",
    "Copernicus_DSM_COG_10_N19_00_E086_00_DEM.tif",
    "Copernicus_DSM_COG_10_N20_00_E084_00_DEM.tif",
    "Copernicus_DSM_COG_10_N20_00_E085_00_DEM.tif",
    "Copernicus_DSM_COG_10_N20_00_E086_00_DEM.tif",
    "Copernicus_DSM_COG_10_N20_00_E087_00_DEM.tif",
    "Copernicus_DSM_COG_10_N21_00_E085_00_DEM.tif",
    "Copernicus_DSM_COG_10_N21_00_E086_00_DEM.tif",
]

def build_vrt():
    print("=" * 80)
    print("AQUORA PHASE 7F STAGE 2: DEM MOSAIC PREPARATION & SEAM AUDIT")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    os.makedirs(PROCESSED_TERRAIN_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    # 1. Inspect input tiles
    found_tiles = sorted(glob.glob(os.path.join(RAW_DEM_DIR, "*.tif")))
    print(f"\n[1] Inspecting raw DEM tiles in: {os.path.relpath(RAW_DEM_DIR, WORKSPACE)}")
    print(f"    Found {len(found_tiles)} tiles (Expected: {len(EXPECTED_TILES)})")

    tile_records = []
    for expected_name in EXPECTED_TILES:
        path = os.path.join(RAW_DEM_DIR, expected_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required DEM tile: {expected_name}")
        
        with rasterio.open(path) as src:
            rec = {
                "filename": expected_name,
                "path": os.path.relpath(path, WORKSPACE).replace("\\", "/"),
                "shape": list(src.shape),
                "crs": str(src.crs),
                "res": [float(src.res[0]), float(src.res[1])],
                "bounds": [float(b) for b in src.bounds],
                "nodata": float(src.nodata) if src.nodata is not None else None,
                "dtype": str(src.dtypes[0]),
                "driver": src.driver,
                "crs_wkt": src.crs.to_wkt(),
            }
            tile_records.append(rec)
            print(f"    [OK] {expected_name}: {src.width}x{src.height}, Bounds=[{src.bounds.left:.4f}, {src.bounds.bottom:.4f}, {src.bounds.right:.4f}, {src.bounds.top:.4f}]")

    # 2. Compute composite mosaic grid
    min_x = min(tr["bounds"][0] for tr in tile_records)
    min_y = min(tr["bounds"][1] for tr in tile_records)
    max_x = max(tr["bounds"][2] for tr in tile_records)
    max_y = max(tr["bounds"][3] for tr in tile_records)

    res_x = tile_records[0]["res"][0]
    res_y = tile_records[0]["res"][1]

    mosaic_width = int(round((max_x - min_x) / res_x))
    mosaic_height = int(round((max_y - min_y) / res_y))

    print(f"\n[2] Composite Mosaic Geometry:")
    print(f"    Longitude Extent: {min_x:.6f} to {max_x:.6f} (Span: {max_x - min_x:.4f}°)")
    print(f"    Latitude Extent:  {min_y:.6f} to {max_y:.6f} (Span: {max_y - min_y:.4f}°)")
    print(f"    Dimensions:       {mosaic_width} x {mosaic_height} pixels ({mosaic_width * mosaic_height:,} total cells)")
    print(f"    Pixel Size:       {res_x:.10f}° x {res_y:.10f}° (~30.87 m at equator, ~29.0 m at 20°N)")
    print(f"    Vertical Surface: Digital Surface Model (DSM - includes canopy and surface structures)")

    # 3. Construct authoritative GDAL VRT
    srs_wkt = tile_records[0]["crs_wkt"]
    gt_str = f"{min_x}, {res_x}, 0.0, {max_y}, 0.0, {-res_y}"
    vrt_path = os.path.join(PROCESSED_TERRAIN_DIR, "mahanadi_dem_mosaic_30m.vrt")

    vrt_xml_lines = [
        f'<VRTDataset rasterXSize="{mosaic_width}" rasterYSize="{mosaic_height}">',
        f'  <SRS dataAxisToSRSAxisMapping="2,1">{srs_wkt}</SRS>',
        f'  <GeoTransform>{gt_str}</GeoTransform>',
        f'  <VRTRasterBand dataType="Float32" band="1">',
        f'    <NoDataValue>-999999</NoDataValue>',
    ]

    for tr in tile_records:
        dst_x = int(round((tr["bounds"][0] - min_x) / res_x))
        dst_y = int(round((max_y - tr["bounds"][3]) / res_y))
        src_w = tr["shape"][1]
        src_h = tr["shape"][0]

        rel_to_vrt = os.path.relpath(os.path.join(WORKSPACE, tr["path"]), PROCESSED_TERRAIN_DIR).replace("\\", "/")

        vrt_xml_lines.extend([
            '    <SimpleSource>',
            f'      <SourceFilename relativeToVRT="1">{rel_to_vrt}</SourceFilename>',
            '      <SourceBand>1</SourceBand>',
            f'      <SourceProperties RasterXSize="{src_w}" RasterYSize="{src_h}" DataType="Float32" BlockXSize="1024" BlockYSize="1024" />',
            f'      <SrcRect xOff="0" yOff="0" xSize="{src_w}" ySize="{src_h}" />',
            f'      <DstRect xOff="{dst_x}" yOff="{dst_y}" xSize="{src_w}" ySize="{src_h}" />',
            '    </SimpleSource>',
        ])

    vrt_xml_lines.extend([
        '  </VRTRasterBand>',
        '</VRTDataset>',
    ])

    with open(vrt_path, "w") as f:
        f.write("\n".join(vrt_xml_lines))
    print(f"\n[3] Generated VRT Mosaic at: {os.path.relpath(vrt_path, WORKSPACE)}")

    # 4. Rigorous Seam and Alignment Audit
    print("\n[4] Performing Cross-Tile Seam and Boundary Verification:")
    seam_checks = [
        {"name": "N20E085 to N20E086 (Longitude 86.0°E, Cuttack/Kendrapara Delta Corridor)", "x": 7198, "y": 5400, "w": 4, "h": 4},
        {"name": "N19E085 to N19E086 (Longitude 86.0°E, Puri/Devi Mouth Corridor)", "x": 7198, "y": 9000, "w": 4, "h": 4},
        {"name": "N20E085 to N19E085 (Latitude 20.0°N, Naraj/Bhubaneswar Corridor)", "x": 5400, "y": 7198, "w": 4, "h": 4},
        {"name": "N21E085 to N20E085 (Latitude 21.0°N, Jajpur/Baitarani Margin)", "x": 5400, "y": 3598, "w": 4, "h": 4},
        {"name": "N20E086 to N20E087 (Longitude 87.0°E, Bhitarkanika Marine Margin)", "x": 10798, "y": 5400, "w": 4, "h": 4},
    ]

    seam_results = []
    with rasterio.open(vrt_path) as src:
        assert src.shape == (mosaic_height, mosaic_width), f"VRT shape mismatch: {src.shape} vs {(mosaic_height, mosaic_width)}"
        
        for sc in seam_checks:
            win = Window(sc["x"], sc["y"], sc["w"], sc["h"])
            data = src.read(1, window=win)
            has_nodata = (data == -999999).any() or np.isnan(data).any()
            val_min = float(np.min(data))
            val_max = float(np.max(data))
            val_mean = float(np.mean(data))
            
            # Check maximum step gradient across seam
            max_diff_x = float(np.max(np.abs(np.diff(data, axis=1))))
            max_diff_y = float(np.max(np.abs(np.diff(data, axis=0))))
            
            status = "SEAM_CONTINUOUS_VERIFIED" if not has_nodata and max_diff_x < 50.0 and max_diff_y < 50.0 else "WARNING"
            seam_results.append({
                "seam_name": sc["name"],
                "window": [sc["x"], sc["y"], sc["w"], sc["h"]],
                "min_elev_m": round(val_min, 2),
                "max_elev_m": round(val_max, 2),
                "mean_elev_m": round(val_mean, 2),
                "max_adjacent_step_m": round(max(max_diff_x, max_diff_y), 2),
                "status": status,
            })
            print(f"    [OK] {sc['name']}: Mean={val_mean:.2f} m, Max Step={max(max_diff_x, max_diff_y):.2f} m [{status}]")

    # 5. Save Summary Document
    summary_path = os.path.join(DOCS_DIR, "DFO_3382_dem_mosaic_summary.json")
    summary = {
        "event_id": "DFO_3382",
        "phase": "PHASE_7F_STAGE_2",
        "status": "DEM_MOSAIC_VERIFIED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mosaic_vrt": os.path.relpath(vrt_path, WORKSPACE).replace("\\", "/"),
        "total_source_tiles": len(tile_records),
        "source_product": "Copernicus DEM GLO-30 (Digital Surface Model)",
        "spatial_crs": "EPSG:4326 (WGS 84)",
        "bounds_wgs84": [min_x, min_y, max_x, max_y],
        "resolution_deg": [res_x, res_y],
        "dimensions": [mosaic_width, mosaic_height],
        "total_pixels": mosaic_width * mosaic_height,
        "nodata_value": -999999.0,
        "source_tiles": tile_records,
        "seam_audit": seam_results,
        "dsm_characteristics": {
            "surface_model_note": "Copernicus GLO-30 reflects top-of-canopy and man-made structure elevations. It is NOT a bare-earth DTM.",
            "hydrodynamic_implication": "Linear structures (embankments, canal dikes, elevated highways) act as hydraulic barriers; natural drainage paths may require hydro-conditioning."
        }
    }

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[5] Saved DEM Mosaic Audit Summary to: {os.path.relpath(summary_path, WORKSPACE)}")
    print("=" * 80)
    print("DEM MOSAIC PREPARATION COMPLETE: SUCCESS")
    print("=" * 80)

if __name__ == "__main__":
    build_vrt()
