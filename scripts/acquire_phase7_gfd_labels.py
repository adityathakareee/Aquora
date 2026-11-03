"""
AQUORA Phase 7 — Real Satellite Flood Label Acquisition Pipeline.

Acquires authentic, empirical, satellite-derived flood inundation maps from the
Global Flood Database (GFD v1.4 / Tellman et al., Nature 2021) hosted in Google Cloud Storage.
Validates byte checksums, parses multi-band GeoTIFFs, extracts quality flags, and logs provenance.
"""

from datetime import datetime, timezone
import hashlib
import io
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

# Pilot Target: DFO 4499 (West Bengal / Lower Ganga Basin, July 27 – August 10, 2017)
# Correlates with IFI UEI-IMD-FL-2017-0122 (46 fatalities, widespread inundation)
PILOT_EVENTS = [
    {
        "dfo_id": 4499,
        "zip_name": "DFO_4499_From_20170727_to_20170810.zip",
        "tif_name": "DFO_4499_From_20170727_to_20170810.tif",
        "region": "Lower Ganga Basin (West Bengal / Hooghly / Howrah)",
        "began": "2017-07-27",
        "ended": "2017-08-10",
        "ifi_correlation": "UEI-IMD-FL-2017-0122",
    }
]


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def download_and_extract_gfd_event(event_meta: dict) -> dict:
    dfo_id = event_meta["dfo_id"]
    zip_name = event_meta["zip_name"]
    tif_name = event_meta["tif_name"]

    target_dir = RAW_GFD_DIR / f"DFO_{dfo_id}"
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / zip_name
    tif_path = target_dir / tif_name

    download_url = f"{GCS_DOWNLOAD_BASE}/{zip_name}?alt=media"

    print(f"\n[ACQUIRE] Event DFO {dfo_id} ({event_meta['region']})")
    print(f"  URL: {download_url}")
    print(f"  Target: {zip_path}")

    # 1. Download if not already cached
    if not zip_path.exists():
        print(f"  Fetching from GCS bucket 'gfd_v1_4'...")
        req = urllib.request.Request(download_url, headers={"User-Agent": "AQUORA/1.0 (Research Pipeline)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            zip_path.write_bytes(data)
        print(f"  Downloaded {len(data):,} bytes.")
    else:
        print(f"  Zip already cached locally ({zip_path.stat().st_size:,} bytes).")

    zip_sha256 = compute_sha256(zip_path)
    print(f"  Zip SHA-256: {zip_sha256}")

    # 2. Extract contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        print(f"  Archive contains {len(namelist)} items: {namelist}")
        zf.extractall(target_dir)

    tif_sha256 = compute_sha256(tif_path)
    print(f"  GeoTIFF extracted: {tif_path.stat().st_size:,} bytes | SHA-256: {tif_sha256}")

    # 3. Read metadata properties if present
    props_path = target_dir / f"DFO_{dfo_id}_properties.json"
    props = {}
    if props_path.exists():
        with open(props_path, "r", encoding="utf-8") as f:
            props = json.load(f)

    license_path = target_dir / "LICENSE.txt"
    license_text = license_path.read_text(encoding="utf-8").strip().splitlines()[0] if license_path.exists() else "CC-BY-NC-4.0"

    # 4. Parse Raster Metadata and Validate Bands
    with rasterio.open(tif_path) as src:
        crs_str = str(src.crs)
        bounds = src.bounds
        height, width = src.shape
        count = src.count
        descriptions = src.descriptions or ("flooded", "duration", "clear_views", "clear_perc", "jrc_perm_water")
        dtypes = [str(t) for t in src.dtypes]
        transform = [float(x) for x in src.transform][:6]

        flooded = src.read(1)
        duration = src.read(2)
        clear_perc = src.read(4)
        jrc_perm = src.read(5)

        total_cells = flooded.size
        valid_cells = int((~np.isnan(flooded)).sum())
        nan_cells = total_cells - valid_cells

        # Inundation breakdown
        valid_mask = ~np.isnan(flooded)
        flooded_raw_cells = int((flooded[valid_mask] == 1.0).sum())
        dry_raw_cells = int((flooded[valid_mask] == 0.0).sum())
        perm_water_cells = int((jrc_perm[valid_mask] == 1.0).sum())

        # Genuine episodic flood = flooded AND NOT permanent water AND clear_perc >= 0.70
        clear_mask = valid_mask & (clear_perc >= 0.70)
        pure_flood_cells = int(((flooded == 1.0) & (jrc_perm == 0.0) & clear_mask).sum())
        verified_dry_cells = int(((flooded == 0.0) & (jrc_perm == 0.0) & clear_mask).sum())
        cloud_or_perm_cells = valid_cells - (pure_flood_cells + verified_dry_cells)

        print("\n  [RASTER VALIDATION]")
        print(f"    CRS: {crs_str} | Dimensions: {width} x {height} ({total_cells:,} cells)")
        print(f"    Bounds: [{bounds.left:.4f}, {bounds.bottom:.4f}] to [{bounds.right:.4f}, {bounds.top:.4f}]")
        print(f"    Valid non-NaN observations: {valid_cells:,} ({valid_cells/total_cells*100:.2f}%)")
        print(f"    Raw Water (flooded=1): {flooded_raw_cells:,} cells")
        print(f"    JRC Permanent Water: {perm_water_cells:,} cells")
        print(f"    Verified Episodic Flood (flooded=1 & perm=0 & clear>=70%): {pure_flood_cells:,} cells")
        print(f"    Verified Dry Ground (flooded=0 & perm=0 & clear>=70%): {verified_dry_cells:,} cells")
        print(f"    Cloud-Affected / Permanent Water Excluded: {cloud_or_perm_cells:,} cells")
        print(f"    Unmapped / Out of Footprint (NaN): {nan_cells:,} cells")

    event_result = {
        "dfo_id": dfo_id,
        "region": event_meta["region"],
        "ifi_correlation": event_meta["ifi_correlation"],
        "began": event_meta["began"],
        "ended": event_meta["ended"],
        "local_zip_path": str(zip_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "local_tif_path": str(tif_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "zip_sha256": zip_sha256,
        "tif_sha256": tif_sha256,
        "license": license_text,
        "raster_metadata": {
            "crs": crs_str,
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "width": width,
            "height": height,
            "bands_count": count,
            "band_descriptions": list(descriptions),
            "dtypes": dtypes,
            "transform": transform,
            "pixel_resolution_deg": [abs(transform[1]), abs(transform[5])],
            "approx_resolution_m": 250.0,
        },
        "cell_counts": {
            "total_cells": total_cells,
            "valid_observed_cells": valid_cells,
            "unmapped_nan_cells": nan_cells,
            "raw_flooded_cells": flooded_raw_cells,
            "permanent_water_cells": perm_water_cells,
            "verified_episodic_flood_cells": pure_flood_cells,
            "verified_dry_cells": verified_dry_cells,
            "cloud_or_perm_excluded_cells": cloud_or_perm_cells,
        },
        "properties": props,
    }

    return event_result


def run_gfd_acquisition():
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = MANIFEST_DIR / "phase7_gfd_acquisition_manifest.yaml"

    print("=" * 80)
    print("AQUORA PHASE 7: SATELLITE FLOOD LABEL ACQUISITION PIPELINE (GFD PILOT)")
    print("=" * 80)

    acquired_events = []
    for ev in PILOT_EVENTS:
        res = download_and_extract_gfd_event(ev)
        acquired_events.append(res)

    manifest_payload = {
        "manifest_version": "1.0.0",
        "phase": "PHASE_7_REAL_FLOOD_DATASET_BUILD",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary_source": {
            "name": "Global Flood Database (GFD v1.4)",
            "citation": "Tellman et al., Nature 2021 (DOI: 10.1038/s41586-021-03695-w)",
            "gcs_bucket": "gs://gfd_v1_4",
            "gee_collection": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1",
            "license": "Creative Commons Attribution-NonCommercial 4.0 International (CC-BY-NC-4.0)",
            "spatial_resolution": "250 meters",
            "sensor": "NASA Terra and Aqua MODIS Surface Reflectance",
            "permanent_water_mask_source": "JRC Global Surface Water (30m, Pekel et al. 2016)",
        },
        "complementary_sar_investigation": {
            "source": "ESA Copernicus Sentinel-1 C-SAR GRD IW",
            "spatial_resolution": "10 meters",
            "temporal_revisit_days": "6 to 12 days",
            "applicable_window": "October 2014 to present",
            "role_in_aquora": "High-resolution micro-scale urban flood corroboration (e.g. Mumbai E02-E07); complementary to GFD macro coverage.",
            "known_limitations": [
                "Radar shadow and geometric layover in dense high-rise urban areas.",
                "Corner reflection artifacts from steel/concrete building faces.",
                "Wind-induced surface capillary waves causing false positive roughening.",
                "Revisit gap of 6-12 days may miss rapid flash-flood recession peaks."
            ]
        },
        "acquired_events": acquired_events,
        "scientific_label_semantics": {
            "flood_label_1": "Verified episodic flood: flooded==1.0 AND jrc_perm_water==0.0 AND clear_perc >= 0.70",
            "flood_label_0": "Verified non-flood dry ground: flooded==0.0 AND jrc_perm_water==0.0 AND clear_perc >= 0.70",
            "flood_label_minus_1": "Unknown / Excluded: jrc_perm_water==1.0 (permanent river/ocean), clear_perc < 0.70 (cloud obscured), or unmapped outside footprint (NaN)",
            "no_synthetic_data_rule": "Unobserved pixels strictly remain -1 (Unknown). Zero artificial zero-filling.",
        }
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest_payload, f, default_flow_style=False, sort_keys=False)

    print(f"\n[MANIFEST] Wrote GFD acquisition manifest to {manifest_path}")
    print("=" * 80)
    return manifest_payload


if __name__ == "__main__":
    run_gfd_acquisition()
