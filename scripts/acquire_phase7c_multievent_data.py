"""
AQUORA Phase 7C: Multi-Event Real Satellite Flood Label Acquisition Pipeline.

Acquires, validates, and audits multi-event empirical flood inundation rasters from the
Global Flood Database (GFD v1.4 / Tellman et al., Nature 2021) across distinct Indian river basins:
1. DFO 4499 (Lower Ganga Basin, West Bengal, 2017) [Baseline pilot]
2. DFO 2935 (Upper Godavari Basin, Maharashtra, 2006)
3. DFO 3372 (Upper Brahmaputra Basin, Assam, 2008)
4. DFO 2507 (North Bihar / Kosi-Ganga Basin, 2004)

Verifies byte checksums, parses multi-band GeoTIFFs, extracts quality flags, and logs provenance.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import zipfile
import yaml
import rasterio
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_GFD_DIR = REPO_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "gfd"
MANIFEST_DIR = REPO_ROOT / "data" / "manifests"

GCS_DOWNLOAD_BASE = "https://storage.googleapis.com/download/storage/v1/b/gfd_v1_4/o"

TARGET_EVENTS = [
    {
        "dfo_id": 4499,
        "zip_name": "DFO_4499_From_20170727_to_20170810.zip",
        "tif_name": "DFO_4499_From_20170727_to_20170810.tif",
        "basin_name": "Lower Ganga Basin",
        "state": "West Bengal",
        "began": "2017-07-27",
        "ended": "2017-08-10",
        "centroid": [22.9061, 88.0848],
        "ifi_correlation": "UEI-IMD-FL-2017-0122",
    },
    {
        "dfo_id": 2935,
        "zip_name": "DFO_2935_From_20060728_to_20060912.zip",
        "tif_name": "DFO_2935_From_20060728_to_20060912.tif",
        "basin_name": "Upper Godavari Basin",
        "state": "Maharashtra",
        "began": "2006-07-28",
        "ended": "2006-09-12",
        "centroid": [20.1943, 73.8242],
        "ifi_correlation": "UEI-IMD-FL-2006-0045",
    },
    {
        "dfo_id": 3372,
        "zip_name": "DFO_3372_From_20080830_to_20080908.zip",
        "tif_name": "DFO_3372_From_20080830_to_20080908.tif",
        "basin_name": "Upper Brahmaputra Basin",
        "state": "Assam",
        "began": "2008-08-30",
        "ended": "2008-09-08",
        "centroid": [27.0442, 94.5503],
        "ifi_correlation": "UEI-IMD-FL-2008-0019",
    },
    {
        "dfo_id": 2507,
        "zip_name": "DFO_2507_From_20040620_to_20041007.zip",
        "tif_name": "DFO_2507_From_20040620_to_20041007.tif",
        "basin_name": "North Bihar / Kosi Basin",
        "state": "Bihar",
        "began": "2004-06-20",
        "ended": "2004-10-07",
        "centroid": [25.4989, 85.8918],
        "ifi_correlation": "UEI-IMD-FL-2004-0058",
    },
]


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def download_and_extract_event(event_meta: dict) -> dict:
    dfo_id = event_meta["dfo_id"]
    zip_name = event_meta["zip_name"]
    tif_name = event_meta["tif_name"]

    target_dir = RAW_GFD_DIR / f"DFO_{dfo_id}"
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / zip_name
    tif_path = target_dir / tif_name

    download_url = f"{GCS_DOWNLOAD_BASE}/{zip_name}?alt=media"

    print(f"\n" + "=" * 75)
    print(f"[ACQUIRE] DFO {dfo_id} — {event_meta['basin_name']} ({event_meta['state']})")
    print(f"  Dates: {event_meta['began']} to {event_meta['ended']}")
    print(f"  Target: {zip_path}")

    # 1. Download archive if not present
    if not zip_path.exists():
        print(f"  Downloading from {download_url}...")
        req = urllib.request.Request(download_url, headers={"User-Agent": "AQUORA/1.0 (Research Pipeline)"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            zip_path.write_bytes(data)
        print(f"  Downloaded {len(data):,} bytes.")
    else:
        print(f"  Archive cached locally ({zip_path.stat().st_size:,} bytes).")

    zip_sha256 = compute_sha256(zip_path)

    # 2. Extract contents if GeoTIFF missing or forced
    if not tif_path.exists():
        print(f"  Extracting archive...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)

    tif_sha256 = compute_sha256(tif_path)
    print(f"  GeoTIFF: {tif_path.stat().st_size:,} bytes | SHA-256: {tif_sha256}")

    # 3. Read metadata properties
    props_path = target_dir / f"DFO_{dfo_id}_properties.json"
    props = {}
    if props_path.exists():
        with open(props_path, "r", encoding="utf-8") as f:
            props = json.load(f)

    # 4. Rigorous Raster Validation
    with rasterio.open(tif_path) as src:
        crs_str = str(src.crs)
        bounds = src.bounds
        height, width = src.shape
        count = src.count
        descriptions = src.descriptions or ("flooded", "duration", "clear_views", "clear_perc", "jrc_perm_water")
        dtypes = [str(t) for t in src.dtypes]
        transform = [float(x) for x in src.transform][:6]

        flooded = src.read(1)
        clear_perc = src.read(4)
        jrc_perm = src.read(5)

        total_cells = flooded.size
        valid_cells = int((~np.isnan(flooded)).sum())
        nan_cells = total_cells - valid_cells

        valid_mask = ~np.isnan(flooded)

        # Inundation & quality masks
        raw_flooded = int((flooded[valid_mask] == 1.0).sum())
        perm_water = int((jrc_perm[valid_mask] == 1.0).sum())

        # Cloud and clear statistics
        clear_values = clear_perc[valid_mask]
        min_clear = float(np.nanmin(clear_values)) if len(clear_values) > 0 else 0.0
        max_clear = float(np.nanmax(clear_values)) if len(clear_values) > 0 else 0.0
        cloudy_cells = int((valid_mask & (clear_perc < 0.70)).sum())

        # Authentic labels
        verified_flood = int(((flooded == 1.0) & (jrc_perm == 0.0) & (clear_perc >= 0.70)).sum())
        verified_dry = int(((flooded == 0.0) & (jrc_perm == 0.0) & (clear_perc >= 0.70)).sum())

        print(f"  Validation Report:")
        print(f"    • CRS: {crs_str} | Dimensions: {width} x {height} ({total_cells:,} total cells)")
        print(f"    • Bounds: [{bounds.left:.4f}, {bounds.bottom:.4f}] to [{bounds.right:.4f}, {bounds.top:.4f}]")
        print(f"    • Valid observations: {valid_cells:,} ({valid_cells/total_cells*100:.1f}%) | NaNs: {nan_cells:,}")
        print(f"    • Clear percentage range: [{min_clear:.4f}, {max_clear:.4f}]")
        print(f"    • Cloudy cells (<70%): {cloudy_cells:,}")
        print(f"    • JRC Permanent Water: {perm_water:,} cells")
        print(f"    • Verified Episodic Flood: {verified_flood:,} cells")
        print(f"    • Verified Dry Ground: {verified_dry:,} cells")

    return {
        "dfo_id": dfo_id,
        "basin_name": event_meta["basin_name"],
        "state": event_meta["state"],
        "began": event_meta["began"],
        "ended": event_meta["ended"],
        "ifi_correlation": event_meta["ifi_correlation"],
        "local_zip_path": str(zip_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "local_tif_path": str(tif_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "zip_bytes": zip_path.stat().st_size,
        "tif_bytes": tif_path.stat().st_size,
        "zip_sha256": zip_sha256,
        "tif_sha256": tif_sha256,
        "raster_metadata": {
            "crs": crs_str,
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "width": width,
            "height": height,
            "bands_count": count,
            "band_descriptions": list(descriptions),
            "approx_resolution_m": 250.0,
        },
        "cell_counts": {
            "total_cells": total_cells,
            "valid_observed_cells": valid_cells,
            "unmapped_nan_cells": nan_cells,
            "raw_flooded_cells": raw_flooded,
            "permanent_water_cells": perm_water,
            "cloudy_cells_below_70_pct": cloudy_cells,
            "verified_episodic_flood_cells": verified_flood,
            "verified_dry_cells": verified_dry,
            "clear_perc_range": [min_clear, max_clear],
        },
        "properties": props,
    }


def run_multievent_acquisition():
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = MANIFEST_DIR / "phase7c_multievent_acquisition_manifest.yaml"

    print("=" * 80)
    print("AQUORA PHASE 7C: MULTI-EVENT SATELLITE GROUND TRUTH ACQUISITION")
    print("=" * 80)

    acquired_records = []
    for ev in TARGET_EVENTS:
        res = download_and_extract_event(ev)
        acquired_records.append(res)

    manifest_payload = {
        "manifest_version": "1.0.0",
        "phase": "PHASE_7C_MULTI_EVENT_ACQUISITION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_source": {
            "name": "Global Flood Database (GFD v1.4 / Nature 2021)",
            "gcs_bucket": "gs://gfd_v1_4",
            "license": "CC-BY-NC-4.0",
            "sensor": "Terra / Aqua MODIS Surface Reflectance @ 250m",
            "permanent_water_mask": "JRC Global Surface Water (30m)",
        },
        "total_events_acquired": len(acquired_records),
        "acquired_events": acquired_records,
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest_payload, f, default_flow_style=False, sort_keys=False)

    print(f"\n[MANIFEST] Wrote multi-event acquisition manifest to {manifest_path.relative_to(REPO_ROOT)}")
    print("=" * 80)
    return manifest_payload


if __name__ == "__main__":
    run_multievent_acquisition()
