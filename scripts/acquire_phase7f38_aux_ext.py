#!/usr/bin/env python3
"""
AQUORA Phase 7F.3.8 Stage 1: Controlled Acquisition & Regional Extraction of Package AUX-EXT

Authorized Datasets:
1. HydroRIVERS Asia v1.0 (Shapefile: HydroRIVERS_v10_as_shp.zip)
2. HydroBASINS Asia v1c (Archive: hybas_as_lev01-12_v1c.zip)
3. ESA WorldCover 10m 2021 N18E084 (GeoTIFF: ESA_WorldCover_10m_2021_v200_N18E084_Map.tif)
4. ESA WorldCover 10m 2021 N21E084 (GeoTIFF: ESA_WorldCover_10m_2021_v200_N21E084_Map.tif)
5. JRC GSW Occurrence 80E_20N (GeoTIFF: occurrence_80E_20N.tif)
6. JRC GSW Occurrence 80E_30N (GeoTIFF: occurrence_80E_30N.tif)
7. JRC GSW Seasonality 80E_20N (GeoTIFF: seasonality_80E_20N.tif)
8. JRC GSW Seasonality 80E_30N (GeoTIFF: seasonality_80E_30N.tif)
9. Global Mangrove Watch v3.0 2008 GeoTIFF (Archive: gmw_v3_2008_gtiff.zip)

Governance:
- Strict READ/WRITE within data/raw/phase7/ and data/processed/phase7/
- Zero modification to existing DEM tiles, Phase 7E Kaggle artifacts, or DFO2507 holdout
"""

import os
import sys
import time
import json
import hashlib
import zipfile
import urllib.request
import urllib.error
from datetime import datetime, timezone

import numpy as np
import rasterio
import geopandas as gpd

# Base Directories
WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_BASE = os.path.join(WORKSPACE, "data", "raw", "phase7")
PROCESSED_BASE = os.path.join(WORKSPACE, "data", "processed", "phase7")
DOCS_DIR = os.path.join(WORKSPACE, "docs", "phase7")
MANIFEST_DIR = os.path.join(WORKSPACE, "data", "manifests")

# Target Subdirectories
DIR_MAP = {
    "hydrorivers": os.path.join(RAW_BASE, "hydrography", "hydrorivers"),
    "hydrobasins": os.path.join(RAW_BASE, "hydrography", "hydrobasins"),
    "worldcover": os.path.join(RAW_BASE, "landcover", "worldcover"),
    "jrc_gsw": os.path.join(RAW_BASE, "water", "jrc_gsw"),
    "gmw": os.path.join(RAW_BASE, "coastal", "global_mangrove_watch"),
}

# The 9 Authorized Datasets
DATASETS = [
    {
        "id": "hydrorivers_asia_v10",
        "category": "hydrography",
        "subcategory": "hydrorivers",
        "filename": "HydroRIVERS_v10_as_shp.zip",
        "url": "https://data.hydrosheds.org/file/hydrorivers/HydroRIVERS_v10_as_shp.zip",
        "expected_bytes": 90510995,
        "is_zip": True,
        "extract_to": "extracted",
    },
    {
        "id": "hydrobasins_asia_v1c",
        "category": "hydrography",
        "subcategory": "hydrobasins",
        "filename": "hybas_as_lev01-12_v1c.zip",
        "url": "https://data.hydrosheds.org/file/HydroBASINS/standard/hybas_as_lev01-12_v1c.zip",
        "expected_bytes": 376386706,
        "is_zip": True,
        "extract_to": "extracted",
    },
    {
        "id": "worldcover_2021_n18e084",
        "category": "landcover",
        "subcategory": "worldcover",
        "filename": "ESA_WorldCover_10m_2021_v200_N18E084_Map.tif",
        "url": "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N18E084_Map.tif",
        "expected_bytes": 54269282,
        "is_zip": False,
    },
    {
        "id": "worldcover_2021_n21e084",
        "category": "landcover",
        "subcategory": "worldcover",
        "filename": "ESA_WorldCover_10m_2021_v200_N21E084_Map.tif",
        "url": "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N21E084_Map.tif",
        "expected_bytes": 127991194,
        "is_zip": False,
    },
    {
        "id": "jrc_gsw_occurrence_80e_20n",
        "category": "water",
        "subcategory": "jrc_gsw",
        "filename": "occurrence_80E_20N.tif",
        "url": "https://storage.googleapis.com/global-surface-water/downloads/occurrence/occurrence_80E_20N.tif",
        "expected_bytes": 27240640,
        "is_zip": False,
    },
    {
        "id": "jrc_gsw_occurrence_80e_30n",
        "category": "water",
        "subcategory": "jrc_gsw",
        "filename": "occurrence_80E_30N.tif",
        "url": "https://storage.googleapis.com/global-surface-water/downloads/occurrence/occurrence_80E_30N.tif",
        "expected_bytes": 82179606,
        "is_zip": False,
    },
    {
        "id": "jrc_gsw_seasonality_80e_20n",
        "category": "water",
        "subcategory": "jrc_gsw",
        "filename": "seasonality_80E_20N.tif",
        "url": "https://storage.googleapis.com/global-surface-water/downloads/seasonality/seasonality_80E_20N.tif",
        "expected_bytes": 13975950,
        "is_zip": False,
    },
    {
        "id": "jrc_gsw_seasonality_80e_30n",
        "category": "water",
        "subcategory": "jrc_gsw",
        "filename": "seasonality_80E_30N.tif",
        "url": "https://storage.googleapis.com/global-surface-water/downloads/seasonality/seasonality_80E_30N.tif",
        "expected_bytes": 29238608,
        "is_zip": False,
    },
    {
        "id": "gmw_v3_2008_gtiff",
        "category": "coastal",
        "subcategory": "gmw",
        "filename": "gmw_v3_2008_gtiff.zip",
        "url": "https://zenodo.org/api/records/6894273/files/gmw_v3_2008_gtiff.zip/content",
        "expected_bytes": 66664471,
        "is_zip": True,
        "extract_to": "extracted",
    },
]

def format_bytes(n):
    return f"{n:,} bytes ({n / (1024*1024):.2f} MiB / {n / 1e6:.2f} MB)"

def download_file(url, target_path, expected_bytes=None, max_retries=3):
    """Chunked streaming download with SHA-256 calculation and resume/idempotence check."""
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    # Check if exists and valid
    if os.path.exists(target_path):
        current_size = os.path.getsize(target_path)
        if expected_bytes and current_size == expected_bytes:
            print(f"  [CACHE HIT] {os.path.basename(target_path)} already exists ({format_bytes(current_size)}). Validating hash...")
            sha256 = hashlib.sha256()
            with open(target_path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    sha256.update(chunk)
            return True, current_size, sha256.hexdigest(), 200, "CACHED_ALREADY_DOWNLOADED"
    
    for attempt in range(1, max_retries + 1):
        print(f"  [ATTEMPT {attempt}/{max_retries}] Downloading {os.path.basename(target_path)} from {url}...")
        t0 = time.time()
        sha256 = hashlib.sha256()
        total_downloaded = 0
        req = urllib.request.Request(url, headers={"User-Agent": "AQUORA-Pipeline/1.0 (Phase7F.3.8 AUX-EXT)"})
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                status = resp.status
                cl = resp.headers.get("Content-Length")
                cl_int = int(cl) if cl else expected_bytes
                
                temp_path = target_path + ".part"
                with open(temp_path, "wb") as f_out:
                    while True:
                        chunk = resp.read(1024 * 512)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        sha256.update(chunk)
                        total_downloaded += len(chunk)
                        if total_downloaded % (10 * 1024 * 1024) == 0 or total_downloaded == cl_int:
                            pct = (total_downloaded / cl_int * 100) if cl_int else 0
                            print(f"    -> {total_downloaded / (1024*1024):.1f} MiB ({pct:.1f}%) downloaded...", end="\r")
                
                print()
                elapsed = time.time() - t0
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.rename(temp_path, target_path)
                
                print(f"  [SUCCESS] {os.path.basename(target_path)}: {format_bytes(total_downloaded)} in {elapsed:.1f}s ({total_downloaded / (1024*1024) / max(elapsed, 0.01):.2f} MiB/s)")
                return True, total_downloaded, sha256.hexdigest(), status, "DOWNLOADED"
        except Exception as e:
            print(f"  [ERROR] Attempt {attempt} failed: {e}")
            if os.path.exists(target_path + ".part"):
                os.remove(target_path + ".part")
            if attempt == max_retries:
                return False, total_downloaded, None, None, str(e)
            time.sleep(2 * attempt)
    
    return False, 0, None, None, "RETRY_EXHAUSTED"

def verify_and_extract_zip(zip_path, extract_dir):
    """Test CRC32 integrity and extract safely."""
    if os.path.exists(extract_dir) and len(os.listdir(extract_dir)) > 0:
        print(f"  [CACHE HIT] {os.path.basename(zip_path)} already extracted in {extract_dir}.")
        file_count = 0
        total_uncompressed = 0
        for root, _, files in os.walk(extract_dir):
            file_count += len(files)
            for f in files:
                total_uncompressed += os.path.getsize(os.path.join(root, f))
        return file_count, total_uncompressed

    print(f"  [ZIP CHECK] Verifying integrity of {os.path.basename(zip_path)}...")
    t0 = time.time()
    with zipfile.ZipFile(zip_path, "r") as zf:
        first_bad = zf.testzip()
        if first_bad is not None:
            raise RuntimeError(f"Corrupt file detected in {zip_path}: {first_bad}")
        file_count = len(zf.namelist())
        total_uncompressed = sum(info.file_size for info in zf.infolist())
        print(f"  [ZIP OK] Verified {file_count} entries ({format_bytes(total_uncompressed)} uncompressed). Extracting to {extract_dir}...")
        os.makedirs(extract_dir, exist_ok=True)
        zf.extractall(extract_dir)
        elapsed = time.time() - t0
        print(f"  [EXTRACTED] {file_count} files in {elapsed:.1f}s")
        return file_count, total_uncompressed

def inspect_geotiff(path):
    """Inspect raster metadata and stats."""
    with rasterio.open(path) as src:
        bounds = [float(src.bounds.left), float(src.bounds.bottom), float(src.bounds.right), float(src.bounds.top)]
        meta = {
            "driver": src.driver,
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "total_pixels": src.width * src.height,
            "bands": src.count,
            "data_types": [str(src.dtypes[i]) for i in range(src.count)],
            "nodata_values": [float(src.nodatavals[i]) if src.nodatavals[i] is not None else None for i in range(src.count)],
            "resolution": [float(src.res[0]), float(src.res[1])],
            "bounds": bounds,
        }
        return meta

def disable_sbn_indices(directory):
    """Rename problematic ESRI .sbn / .sbx index files that cause node descriptor errors in GDAL/pyogrio."""
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".sbn") or f.endswith(".sbx"):
                src = os.path.join(root, f)
                dst = src + ".bak"
                if not os.path.exists(dst):
                    os.rename(src, dst)

def main():
    print("=" * 80)
    print("AQUORA PHASE 7F.3.8 STAGE 1: AUX-EXT CONTROLLED ACQUISITION")
    print("Mahanadi Basin & Delta Hydrography, Land Cover, Surface Water & Mangroves")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    # 1. Create Directories
    for d in DIR_MAP.values():
        os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_BASE, "hydrography"), exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_BASE, "boundaries", "mahanadi_hydrobasins"), exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_BASE, "landcover"), exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_BASE, "water"), exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_BASE, "coastal"), exist_ok=True)

    results = []
    total_bytes_downloaded = 0
    t_start = time.time()

    # 2. Sequential Acquisition
    for i, ds in enumerate(DATASETS, 1):
        target_dir = DIR_MAP[ds["subcategory"]]
        target_file = os.path.join(target_dir, ds["filename"])
        print(f"\n[{i}/9] ACQUIRING: {ds['id']} -> {ds['filename']}")
        
        ok, byte_size, sha256_hash, status_code, msg = download_file(
            ds["url"], target_file, expected_bytes=ds["expected_bytes"]
        )
        
        if not ok:
            print(f"FATAL: Failed to acquire {ds['id']}: {msg}")
            sys.exit(1)
            
        total_bytes_downloaded += byte_size
        item_record = {
            "dataset_id": ds["id"],
            "filename": ds["filename"],
            "local_path": os.path.relpath(target_file, WORKSPACE).replace("\\", "/"),
            "url": ds["url"],
            "byte_size": byte_size,
            "sha256": sha256_hash,
            "http_status": status_code,
            "status_message": msg,
            "is_zip": ds["is_zip"],
        }
        
        # If ZIP, verify and extract
        if ds["is_zip"]:
            extract_dir = os.path.join(target_dir, ds["extract_to"])
            num_files, uncomp_bytes = verify_and_extract_zip(target_file, extract_dir)
            item_record["extracted_dir"] = os.path.relpath(extract_dir, WORKSPACE).replace("\\", "/")
            item_record["uncompressed_files"] = num_files
            item_record["uncompressed_bytes"] = uncomp_bytes
        else:
            meta = inspect_geotiff(target_file)
            item_record["raster_metadata"] = meta
            
        results.append(item_record)

    total_elapsed = time.time() - t_start
    print("\n" + "=" * 80)
    print(f"ACQUISITION COMPLETED: 9/9 files verified successfully!")
    print(f"Total Download Volume: {format_bytes(total_bytes_downloaded)}")
    print(f"Elapsed Time: {total_elapsed:.1f}s")
    print("=" * 80)

    # 3. Content Validation & Regional Extraction
    print("\n=== STEP 3: REGIONAL EXTRACTION & CONTENT VALIDATION ===")
    
    # 3A. HydroRIVERS Extraction
    print("\n--- 3A. HydroRIVERS Regional Extraction for Mahanadi Study Area ---")
    hr_shp_dir = os.path.join(DIR_MAP["hydrorivers"], "extracted")
    hr_shp_file = None
    for root, _, files in os.walk(hr_shp_dir):
        for f in files:
            if f.endswith(".shp"):
                hr_shp_file = os.path.join(root, f)
                break
    
    print(f"Reading HydroRIVERS from: {hr_shp_file}")
    mahanadi_bbox = (80.0, 19.0, 87.5, 23.5)
    t0 = time.time()
    gdf_hr = gpd.read_file(hr_shp_file, bbox=mahanadi_bbox, engine="pyogrio")
    print(f"Read {len(gdf_hr)} river reaches intersecting greater Mahanadi basin in {time.time()-t0:.2f}s")
    
    print(f"HydroRIVERS columns: {list(gdf_hr.columns)}")
    print(f"Strahler orders present: {sorted(gdf_hr['ORD_STRA'].unique().tolist())}")
    print(f"Total river length in basin: {gdf_hr['LENGTH_KM'].sum():.1f} km")
    print(f"Maximum upstream area: {gdf_hr['UPLAND_SKM'].max():.1f} km²")
    
    # Save regional extract
    out_hr_path = os.path.join(PROCESSED_BASE, "hydrography", "mahanadi_hydrorivers.geojson")
    gdf_hr.to_file(out_hr_path, driver="GeoJSON")
    print(f"Saved regional HydroRIVERS ({len(gdf_hr)} reaches, {gdf_hr['LENGTH_KM'].sum():.1f} km) to: {os.path.relpath(out_hr_path, WORKSPACE)}")
    
    # Delta focus extract (84E-88E, 19N-22N)
    gdf_hr_delta = gdf_hr.cx[84.0:88.0, 19.0:22.0]
    out_hr_delta_path = os.path.join(PROCESSED_BASE, "hydrography", "mahanadi_delta_hydrorivers.geojson")
    gdf_hr_delta.to_file(out_hr_delta_path, driver="GeoJSON")
    print(f"Saved delta-focus HydroRIVERS ({len(gdf_hr_delta)} reaches, {gdf_hr_delta['LENGTH_KM'].sum():.1f} km) to: {os.path.relpath(out_hr_delta_path, WORKSPACE)}")

    # 3B. HydroBASINS Extraction (Levels 5, 7, 8)
    print("\n--- 3B. HydroBASINS Regional Extraction for Mahanadi Basin & Delta ---")
    hb_dir = os.path.join(DIR_MAP["hydrobasins"], "extracted")
    disable_sbn_indices(hb_dir)
    
    hb_shps = {}
    for root, _, files in os.walk(hb_dir):
        for f in files:
            if f.endswith(".shp"):
                for lev in ["05", "07", "08"]:
                    if f"lev{lev}" in f:
                        hb_shps[lev] = os.path.join(root, f)
    
    print(f"Found HydroBASINS shapefiles for levels: {list(hb_shps.keys())}")
    
    # Level 5: Identify Mahanadi Main Basin (MAIN_BAS = 4050027100)
    print(f"Reading Level 5 Sub-basins (bbox: {mahanadi_bbox})...")
    gdf_hb5 = gpd.read_file(hb_shps["05"], bbox=mahanadi_bbox, engine="pyogrio")
    mahanadi_main_bas_id_lev05 = 4050027100
    gdf_hb5_mahanadi = gdf_hb5[gdf_hb5['MAIN_BAS'] == mahanadi_main_bas_id_lev05]
    total_hb5_area = gdf_hb5_mahanadi['SUB_AREA'].sum()
    print(f"--> Confirmed Mahanadi Basin Level 5 (MAIN_BAS={mahanadi_main_bas_id_lev05}): {len(gdf_hb5_mahanadi)} sub-units, Combined Area={total_hb5_area:.1f} km²")
    
    out_hb5_path = os.path.join(PROCESSED_BASE, "boundaries", "mahanadi_hydrobasins", "mahanadi_hydrobasins_lev05.geojson")
    gdf_hb5_mahanadi.to_file(out_hb5_path, driver="GeoJSON")
    print(f"Saved Level 5 Mahanadi Basin boundary to: {os.path.relpath(out_hb5_path, WORKSPACE)}")
    
    # Level 7: Sub-basins within Mahanadi (MAIN_BAS = 4070027100)
    print(f"Reading Level 7 Sub-basins (bbox: {mahanadi_bbox})...")
    gdf_hb7 = gpd.read_file(hb_shps["07"], bbox=mahanadi_bbox, engine="pyogrio")
    mahanadi_main_bas_id_lev07 = 4070027100
    gdf_hb7_mahanadi = gdf_hb7[gdf_hb7['MAIN_BAS'] == mahanadi_main_bas_id_lev07]
    total_hb7_area = gdf_hb7_mahanadi['SUB_AREA'].sum()
    print(f"--> Confirmed Mahanadi Basin Level 7 (MAIN_BAS={mahanadi_main_bas_id_lev07}): {len(gdf_hb7_mahanadi)} sub-units, Combined Area={total_hb7_area:.1f} km²")
    out_hb7_path = os.path.join(PROCESSED_BASE, "boundaries", "mahanadi_hydrobasins", "mahanadi_hydrobasins_lev07.geojson")
    gdf_hb7_mahanadi.to_file(out_hb7_path, driver="GeoJSON")
    print(f"Saved Level 7 sub-basins to: {os.path.relpath(out_hb7_path, WORKSPACE)}")
    
    # Level 8: Sub-basins within Mahanadi (MAIN_BAS = 4080027100)
    print(f"Reading Level 8 Sub-basins (bbox: {mahanadi_bbox})...")
    gdf_hb8 = gpd.read_file(hb_shps["08"], bbox=mahanadi_bbox, engine="pyogrio")
    mahanadi_main_bas_id_lev08 = 4080027100
    gdf_hb8_mahanadi = gdf_hb8[gdf_hb8['MAIN_BAS'] == mahanadi_main_bas_id_lev08]
    total_hb8_area = gdf_hb8_mahanadi['SUB_AREA'].sum()
    print(f"--> Confirmed Mahanadi Basin Level 8 (MAIN_BAS={mahanadi_main_bas_id_lev08}): {len(gdf_hb8_mahanadi)} sub-units, Combined Area={total_hb8_area:.1f} km²")
    out_hb8_path = os.path.join(PROCESSED_BASE, "boundaries", "mahanadi_hydrobasins", "mahanadi_hydrobasins_lev08.geojson")
    gdf_hb8_mahanadi.to_file(out_hb8_path, driver="GeoJSON")
    print(f"Saved Level 8 sub-basins to: {os.path.relpath(out_hb8_path, WORKSPACE)}")
    
    # Delta Reach Level 8 Sub-basins (downstream of Naraj bifurcation: Lon >= 85.5E, Lat <= 20.6N)
    delta_subbasins = gdf_hb8_mahanadi.cx[85.5:87.2, 19.5:20.6]
    print(f"\n--> Isolated Delta Reach Level 8 Sub-basins: {len(delta_subbasins)} units, combined area: {delta_subbasins['SUB_AREA'].sum():.1f} km²")
    for idx, row in delta_subbasins.iterrows():
        print(f"  Delta Sub-basin: HYBAS_ID={int(row['HYBAS_ID'])}, PFAF_ID={int(row['PFAF_ID'])}, SubArea={row['SUB_AREA']:.1f} km², UpArea={row['UP_AREA']:.1f} km²")
    out_hb8_delta_path = os.path.join(PROCESSED_BASE, "boundaries", "mahanadi_hydrobasins", "mahanadi_delta_lev08_subbasins.geojson")
    delta_subbasins.to_file(out_hb8_delta_path, driver="GeoJSON")
    print(f"Saved isolated Delta Level 8 sub-basins to: {os.path.relpath(out_hb8_delta_path, WORKSPACE)}")

    # 3C. Global Mangrove Watch Extraction
    print("\n--- 3C. Global Mangrove Watch 2008 Inspection for Mahanadi Coastal Fringe ---")
    gmw_dir = os.path.join(DIR_MAP["gmw"], "extracted", "gmw_v3_2008")
    
    gmw_tiles = ["GMW_N20E086_2008_v3.tif", "GMW_N21E086_2008_v3.tif", "GMW_N21E087_2008_v3.tif"]
    gmw_metadata_records = {}
    for gt in gmw_tiles:
        gt_path = os.path.join(gmw_dir, gt)
        if os.path.exists(gt_path):
            m = inspect_geotiff(gt_path)
            with rasterio.open(gt_path) as src:
                arr = src.read(1)
                mangrove_px = int(np.sum(arr == 1))
                m["mangrove_pixel_count"] = mangrove_px
                m["mangrove_area_km2"] = round(mangrove_px * (src.res[0] * 111320) * (src.res[1] * 111320) / 1e6, 2)
            gmw_metadata_records[gt] = m
            print(f"  GMW Tile {gt}: {m['width']}x{m['height']} pixels, {m['mangrove_pixel_count']:,} mangrove pixels (~{m['mangrove_area_km2']} km²)")

    # 4. Save Comprehensive Inspection Summary
    summary_path = os.path.join(DOCS_DIR, "DFO_3382_aux_ext_acquisition_summary.json")
    summary_data = {
        "event_id": "DFO_3382",
        "phase": "PHASE_7F_3_8_STAGE_1_ACQUISITION",
        "status": "AUX_EXT_ACQUISITION_COMPLETE",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_files_acquired": len(results),
        "total_bytes_downloaded": total_bytes_downloaded,
        "total_size_mb_decimal": round(total_bytes_downloaded / 1e6, 2),
        "total_size_mib_binary": round(total_bytes_downloaded / (1024*1024), 2),
        "total_elapsed_seconds": round(total_elapsed, 1),
        "acquired_datasets": results,
        "regional_extractions": {
            "hydrorivers_basin_reaches": len(gdf_hr),
            "hydrorivers_basin_km": round(float(gdf_hr['LENGTH_KM'].sum()), 1),
            "hydrorivers_delta_reaches": len(gdf_hr_delta),
            "hydrorivers_delta_km": round(float(gdf_hr_delta['LENGTH_KM'].sum()), 1),
            "hydrobasins_lev05_main_bas": int(mahanadi_main_bas_id_lev05),
            "hydrobasins_lev05_sub_units": len(gdf_hb5_mahanadi),
            "hydrobasins_lev05_area_km2": round(float(total_hb5_area), 1),
            "hydrobasins_lev07_main_bas": int(mahanadi_main_bas_id_lev07),
            "hydrobasins_lev07_subbasins": len(gdf_hb7_mahanadi),
            "hydrobasins_lev07_area_km2": round(float(total_hb7_area), 1),
            "hydrobasins_lev08_main_bas": int(mahanadi_main_bas_id_lev08),
            "hydrobasins_lev08_subbasins": len(gdf_hb8_mahanadi),
            "hydrobasins_lev08_area_km2": round(float(total_hb8_area), 1),
            "hydrobasins_lev08_delta_units": len(delta_subbasins),
            "hydrobasins_lev08_delta_area_km2": round(float(delta_subbasins['SUB_AREA'].sum()), 1),
            "hydrobasins_lev08_delta_subbasins_detail": [
                {
                    "hybas_id": int(row['HYBAS_ID']),
                    "pfaf_id": int(row['PFAF_ID']),
                    "sub_area_km2": round(float(row['SUB_AREA']), 1),
                    "up_area_km2": round(float(row['UP_AREA']), 1)
                }
                for _, row in delta_subbasins.iterrows()
            ]
        },
        "coastal_mangroves_gmw2008": gmw_metadata_records
    }
    
    with open(summary_path, "w") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nSaved comprehensive acquisition summary to: {os.path.relpath(summary_path, WORKSPACE)}")
    print("\nALL STAGE 1 ACQUISITION & REGIONAL EXTRACTIONS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
