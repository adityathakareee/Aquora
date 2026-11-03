"""AQUORA Phase 7F.3.6: Controlled Acquisition & Inspection of Copernicus DEM GLO-30 Tiles for DFO 3382.

Authorized Package: Corrected Package B (9 tiles)
Target Directory: data/raw/phase7/dem/mahanadi_dfo3382/
"""

import datetime
import hashlib
import json
import os
import sys
import time
import urllib.request
import numpy as np
import rasterio

TILES = [
    {
        "tile_id": "N19E084",
        "lat": "N19",
        "lon": "E084",
        "lat_bounds": [19.0, 20.0],
        "lon_bounds": [84.0, 85.0],
        "role": "Southwestern 5km terrestrial buffer for N19E085"
    },
    {
        "tile_id": "N19E085",
        "lat": "N19",
        "lon": "E085",
        "lat_bounds": [19.0, 20.0],
        "lon_bounds": [85.0, 86.0],
        "role": "Southern delta plain / Puri / Chilika lagoon / Daya-Bhargavi"
    },
    {
        "tile_id": "N19E086",
        "lat": "N19",
        "lon": "E086",
        "lat_bounds": [19.0, 20.0],
        "lon_bounds": [86.0, 87.0],
        "role": "Coastal margin / Devi river estuary / Coastal buffer"
    },
    {
        "tile_id": "N20E084",
        "lat": "N20",
        "lon": "E084",
        "lat_bounds": [20.0, 21.0],
        "lon_bounds": [84.0, 85.0],
        "role": "Western 5km terrestrial buffer and Banki gorge inflow reach"
    },
    {
        "tile_id": "N20E085",
        "lat": "N20",
        "lon": "E085",
        "lat_bounds": [20.0, 21.0],
        "lon_bounds": [85.0, 86.0],
        "role": "Delta apex / Cuttack / Bhubaneswar / Naraj barrage"
    },
    {
        "tile_id": "N20E086",
        "lat": "N20",
        "lon": "E086",
        "lat_bounds": [20.0, 21.0],
        "lon_bounds": [86.0, 87.0],
        "role": "Eastern delta plain / Kendrapara / Jagatsinghpur / Mahanadi mouth"
    },
    {
        "tile_id": "N20E087",
        "lat": "N20",
        "lon": "E087",
        "lat_bounds": [20.0, 21.0],
        "lon_bounds": [87.0, 88.0],
        "role": "Eastern terrestrial spit / Gahirmatha / Bhitarkanika mangrove"
    },
    {
        "tile_id": "N21E085",
        "lat": "N21",
        "lon": "E085",
        "lat_bounds": [21.0, 22.0],
        "lon_bounds": [85.0, 86.0],
        "role": "Northern buffer & Jajpur / Baitarani-Brahmani confluence"
    },
    {
        "tile_id": "N21E086",
        "lat": "N21",
        "lon": "E086",
        "lat_bounds": [21.0, 22.0],
        "lon_bounds": [86.0, 87.0],
        "role": "Northern buffer & Bhadrak / Dhamra river estuary"
    }
]

BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
OUTPUT_DIR = "data/raw/phase7/dem/mahanadi_dfo3382"


def download_tile(tile_info):
    tile_id = tile_info["tile_id"]
    lat = tile_info["lat"]
    lon = tile_info["lon"]
    obj_name = f"Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM"
    filename = f"{obj_name}.tif"
    url = f"{BASE_URL}/{obj_name}/{filename}"
    out_path = os.path.join(OUTPUT_DIR, filename)
    part_path = out_path + ".part"

    print(f"\n[ACQUIRING] {tile_id} from {url}...")
    start_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = time.time()

    # Pre-check HEAD
    req_head = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req_head, timeout=15) as resp:
        content_length = int(resp.headers.get("Content-Length", 0))

    print(f"  Remote Content-Length: {content_length} bytes ({content_length / (1024*1024):.2f} MB)")

    # Check if already present and valid
    if os.path.exists(out_path):
        actual_size = os.path.getsize(out_path)
        if actual_size == content_length:
            print(f"  [ALREADY EXISTS] Verifying local checksum...")
            sha256 = hashlib.sha256()
            with open(out_path, "rb") as f_in:
                while chunk := f_in.read(1024 * 1024):
                    sha256.update(chunk)
            digest = sha256.hexdigest()
            print(f"  [VERIFIED] Size {actual_size} bytes matches remote. SHA256: {digest}")
            return {
                "tile_id": tile_id,
                "copernicus_filename": filename,
                "local_path": out_path.replace("\\", "/"),
                "source_url": url,
                "http_status": 200,
                "download_start_utc": start_time,
                "download_end_utc": start_time,
                "download_elapsed_seconds": 0.0,
                "file_size_bytes": actual_size,
                "file_size_mb": round(actual_size / (1024 * 1024), 2),
                "sha256": digest,
                "role": tile_info["role"],
                "lat_bounds": tile_info["lat_bounds"],
                "lon_bounds": tile_info["lon_bounds"]
            }

    # Download with progress
    req = urllib.request.Request(url)
    sha256 = hashlib.sha256()
    downloaded = 0

    with urllib.request.urlopen(req, timeout=30) as response, open(part_path, "wb") as f_out:
        chunk_size = 1024 * 1024  # 1MB
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            f_out.write(chunk)
            sha256.update(chunk)
            downloaded += len(chunk)
            pct = (downloaded / content_length) * 100 if content_length > 0 else 0
            sys.stdout.write(f"\r  Progress: {downloaded/(1024*1024):.1f}/{content_length/(1024*1024):.1f} MB ({pct:.1f}%)")
            sys.stdout.flush()

    sys.stdout.write("\n")
    elapsed = time.time() - t0
    end_time = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if downloaded != content_length:
        raise ValueError(f"Download size mismatch for {tile_id}: expected {content_length}, got {downloaded}")

    # Move part to final destination safely
    if os.path.exists(out_path):
        os.remove(out_path)
    os.rename(part_path, out_path)

    actual_sha256 = sha256.hexdigest()
    actual_size = os.path.getsize(out_path)
    print(f"  [SUCCESS] {tile_id} downloaded in {elapsed:.1f}s. SHA256: {actual_sha256}")

    return {
        "tile_id": tile_id,
        "copernicus_filename": filename,
        "local_path": out_path.replace("\\", "/"),
        "source_url": url,
        "http_status": 200,
        "download_start_utc": start_time,
        "download_end_utc": end_time,
        "download_elapsed_seconds": round(elapsed, 2),
        "file_size_bytes": actual_size,
        "file_size_mb": round(actual_size / (1024 * 1024), 2),
        "sha256": actual_sha256,
        "role": tile_info["role"],
        "lat_bounds": tile_info["lat_bounds"],
        "lon_bounds": tile_info["lon_bounds"]
    }


def inspect_tile(local_path):
    with rasterio.open(local_path) as src:
        crs_str = src.crs.to_string() if src.crs else None
        width = src.width
        height = src.height
        bounds = list(src.bounds)
        res = [src.res[0], src.res[1]]
        nodata = src.nodata
        data_type = src.dtypes[0]

        data = src.read(1)

        # Check nodata and valid pixels safely
        if nodata is not None and not (isinstance(nodata, float) and np.isnan(nodata)):
            nodata_mask = (data == nodata)
            nodata_val = float(nodata)
        else:
            nodata_mask = np.isnan(data)
            nodata_val = "NaN"

        total_pixels = data.size
        nodata_count = int(np.sum(nodata_mask))
        valid_count = int(total_pixels - nodata_count)

        if valid_count > 0:
            valid_data = data[~nodata_mask]
            min_elev = float(np.min(valid_data))
            max_elev = float(np.max(valid_data))
            mean_elev = float(np.mean(valid_data))
            median_elev = float(np.median(valid_data))
            std_elev = float(np.std(valid_data))
            pct_below_0 = float(np.sum(valid_data < 0.0) / valid_count * 100.0)
            pct_0_to_15 = float(np.sum((valid_data >= 0.0) & (valid_data <= 15.0)) / valid_count * 100.0)
        else:
            min_elev = max_elev = mean_elev = median_elev = std_elev = None
            pct_below_0 = pct_0_to_15 = 0.0

        return {
            "crs": crs_str,
            "width": width,
            "height": height,
            "total_pixels": total_pixels,
            "valid_pixels": valid_count,
            "nodata_pixels": nodata_count,
            "nodata_percentage": round(nodata_count / total_pixels * 100.0, 4),
            "bounds": bounds,
            "pixel_resolution_deg": res,
            "data_type": data_type,
            "nodata_value": nodata_val,
            "elevation_stats_meters": {
                "min": round(min_elev, 2) if min_elev is not None else None,
                "max": round(max_elev, 2) if max_elev is not None else None,
                "mean": round(mean_elev, 2) if mean_elev is not None else None,
                "median": round(median_elev, 2) if median_elev is not None else None,
                "std": round(std_elev, 2) if std_elev is not None else None,
                "pct_below_sea_level": round(pct_below_0, 2),
                "pct_lowland_delta_0_to_15m": round(pct_0_to_15, 2)
            }
        }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []

    print("=" * 80)
    print("AQUORA Phase 7F.3.6: Controlled DEM Acquisition (Package B - 9 Tiles)")
    print(f"Target Directory: {OUTPUT_DIR}")
    print("=" * 80)

    total_bytes = 0
    t0_all = time.time()

    for tile in TILES:
        res = download_tile(tile)
        total_bytes += res["file_size_bytes"]

        # Inspect
        print(f"  [INSPECTING] {res['tile_id']} metadata and pixel distributions...")
        metadata = inspect_tile(res["local_path"])
        res["raster_inspection"] = metadata
        results.append(res)

    total_elapsed = time.time() - t0_all
    print("\n" + "=" * 80)
    print(f"ACQUISITION COMPLETE: 9 of 9 tiles acquired in {total_elapsed:.1f}s.")
    print(f"Total Acquired Volume: {total_bytes / (1024*1024):.2f} MB ({total_bytes} bytes)")
    print("=" * 80)

    summary_out = "docs/phase7/DFO_3382_dem_acquisition_summary.json"
    with open(summary_out, "w") as f:
        json.dump({
            "phase": "PHASE_7F_3_6_STAGE_3_DEM_ACQUISITION",
            "package_id": "CORRECTED_PACKAGE_B",
            "status": "DEM_ACQUISITION_COMPLETE",
            "total_tiles": len(results),
            "total_size_bytes": total_bytes,
            "total_size_mb": round(total_bytes / (1024*1024), 2),
            "total_elapsed_seconds": round(total_elapsed, 1),
            "tiles": results
        }, f, indent=2)

    print(f"Inspection summary saved to {summary_out}")


if __name__ == "__main__":
    main()
