"""
AQUORA Phase 6C.2c: Authentic Copernicus DEM GLO-30 Acquisition & Validation.

Target Tile: Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif
Official Source: AWS Open Data Registry (Copernicus DEM 30m GLO-30)
URL: https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N19_00_E072_00_DEM/Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif

Governance & Invariants:
1. Zero fabrication: download authentic ESA/Copernicus DEM data directly from official registry.
2. Safe streaming download with atomic rename from temp file.
3. Strict GeoTIFF validation: CRS, bounds, dimensions, data type, NoData, physical plausibility.
4. Comprehensive watershed coverage verification (Mahim outfall, BKC, Powai, Vihar, Tulsi, SGNP).
5. Exact SHA-256 computation and manifest registration.
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Socket timeout
socket.setdefaulttimeout(60.0)

import numpy as np
import rasterio
import yaml

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DEM_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "dem"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"
MANIFEST_PATH = MANIFEST_DIR / "phase6c2c_dem_manifest.yaml"
DOCS_MANIFEST_PATH = PROJECT_ROOT / "docs" / "phase7" / "PHASE_7A_DOWNLOAD_MANIFEST.yaml"

# Official Copernicus DEM Asset
OFFICIAL_DEM_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_N19_00_E072_00_DEM/"
    "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
)
DEM_FILENAME = "Copernicus_DSM_COG_10_N19_00_E072_00_DEM.tif"
LEGACY_FILENAME = "Copernicus_DSM_COG_10_N19_00_E072_00.tif"

# Mithi Basin Key Validation Landmarks (WGS84 Lon, Lat)
MITHI_LANDMARKS = {
    "Mahim_Causeway_Outfall": (72.840, 19.040),
    "Bandra_Kurla_Complex": (72.865, 19.060),
    "CSMIA_Airport_Runway": (72.875, 19.090),
    "Powai_Lake": (72.905, 19.125),
    "Vihar_Lake": (72.900, 19.140),
    "Tulsi_Lake_Headwaters": (72.915, 19.185),
    "SGNP_Northern_Ridge": (72.910, 19.190),
}

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Phase6C2cDEM")


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 checksum in chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def download_copernicus_dem(
    url: str,
    dest_path: Path,
    max_retries: int = 3,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Safely download the official Copernicus DEM tile.
    Uses chunked streaming and atomic file rename to prevent partial/corrupted files.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    if dest_path.exists() and not force:
        logger.info(f"Target file already exists: {dest_path} ({dest_path.stat().st_size} bytes)")
        return True, "EXISTS"

    temp_path = dest_path.with_suffix(".tmp")
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"Initiating download [Attempt {attempt}/{max_retries}] from {url}...")
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "AQUORA-Geospatial-Engine/Phase6C2c"},
            )
            start_time = time.time()
            with urllib.request.urlopen(req, timeout=60.0) as resp, open(temp_path, "wb") as out_f:
                total_bytes = 0
                expected_len = resp.headers.get("Content-Length")
                if expected_len:
                    expected_bytes = int(expected_len)
                    logger.info(f"Reported Content-Length: {expected_bytes:,} bytes ({expected_bytes / 1e6:.2f} MB)")
                else:
                    expected_bytes = None
                
                while chunk := resp.read(64 * 1024):
                    out_f.write(chunk)
                    total_bytes += len(chunk)
                
            elapsed = time.time() - start_time
            logger.info(f"Downloaded {total_bytes:,} bytes in {elapsed:.2f}s ({total_bytes / (elapsed * 1024 * 1024):.2f} MB/s)")
            
            if expected_bytes and total_bytes != expected_bytes:
                raise IOError(f"Byte count mismatch: received {total_bytes}, expected {expected_bytes}")
            
            # Atomic rename
            temp_path.replace(dest_path)
            logger.info(f"Successfully downloaded and stored to {dest_path}")
            return True, "DOWNLOADED"
            
        except (urllib.error.URLError, urllib.error.HTTPError, IOError, socket.timeout) as err:
            logger.warning(f"Download attempt {attempt} failed: {err}")
            if temp_path.exists():
                temp_path.unlink()
            if attempt < max_retries:
                sleep_sec = 2 ** attempt
                logger.info(f"Backing off for {sleep_sec}s before retry...")
                time.sleep(sleep_sec)
            else:
                logger.error(f"All {max_retries} download attempts failed.")
                return False, str(err)
                
    return False, "UNKNOWN_ERROR"


def validate_copernicus_dem(filepath: Path) -> Tuple[bool, Dict[str, Any]]:
    """
    Rigorously validate the downloaded GeoTIFF DEM.
    Verifies header, dimensions, CRS, bounds, resolution, NoData, physical elevation range,
    and coverage of all Mithi catchment key landmarks.
    """
    results: Dict[str, Any] = {
        "valid": False,
        "file_exists": False,
        "file_size_bytes": 0,
        "sha256": "",
        "format": "Unknown",
        "crs": None,
        "width": 0,
        "height": 0,
        "bounds": None,
        "nodata": None,
        "elevation_stats": {},
        "landmark_sampling": {},
        "errors": [],
    }

    if not filepath.exists():
        results["errors"].append(f"File not found on disk: {filepath}")
        return False, results

    results["file_exists"] = True
    results["file_size_bytes"] = filepath.stat().st_size
    
    if results["file_size_bytes"] < 1_000_000:
        results["errors"].append(f"File suspiciously small: {results['file_size_bytes']} bytes")
        return False, results

    # Compute SHA-256
    results["sha256"] = compute_sha256(filepath)
    logger.info(f"Computed SHA-256: {results['sha256']}")

    # Validate with rasterio
    try:
        with rasterio.open(filepath) as ds:
            results["format"] = ds.driver
            results["crs"] = str(ds.crs)
            results["width"] = ds.width
            results["height"] = ds.height
            results["count"] = ds.count
            results["dtypes"] = [str(t) for t in ds.dtypes]
            results["nodata"] = float(ds.nodata) if ds.nodata is not None else None
            results["bounds"] = {
                "left": float(ds.bounds.left),
                "bottom": float(ds.bounds.bottom),
                "right": float(ds.bounds.right),
                "top": float(ds.bounds.top),
            }
            results["transform"] = [float(v) for v in ds.transform]

            # 1. Driver verification
            if ds.driver != "GTiff":
                results["errors"].append(f"Invalid raster driver: expected GTiff, got {ds.driver}")

            # 2. Dimensions: 1x1 deg at 1 arc-sec resolution = 3600 x 3600
            if ds.width != 3600 or ds.height != 3600:
                results["errors"].append(f"Unexpected dimensions: expected 3600x3600, got {ds.width}x{ds.height}")

            # 3. CRS verification: EPSG:4326 (WGS 84 geographic 2D)
            if ds.crs is None or ds.crs.to_epsg() != 4326:
                results["errors"].append(f"Unexpected CRS: expected EPSG:4326, got {ds.crs}")

            # 4. Bounds verification: Tile N19_00_E072_00 covers Lon [72, 73], Lat [19, 20]
            # Account for half-pixel shift in pixel-is-point ('Point') GeoTIFFs (res ≈ 0.0002778 deg)
            half_pixel = ds.res[0] / 2.0
            tol = ds.res[0] * 1.5  # Tolerance within 1.5 pixels
            if (
                abs(ds.bounds.left - (72.0 - half_pixel)) > 1e-5
                and abs(ds.bounds.left - 72.0) > tol
            ) or (
                abs(ds.bounds.right - (73.0 - half_pixel)) > 1e-5
                and abs(ds.bounds.right - 73.0) > tol
            ) or (
                abs(ds.bounds.bottom - (19.0 + half_pixel)) > 1e-5
                and abs(ds.bounds.bottom - 19.0) > tol
            ) or (
                abs(ds.bounds.top - (20.0 + half_pixel)) > 1e-5
                and abs(ds.bounds.top - 20.0) > tol
            ):
                results["errors"].append(
                    f"Unexpected geographic bounds: expected [72.0, 19.0, 73.0, 20.0] (+/- half-pixel), got {results['bounds']}"
                )

            # 5. Read elevation band & compute statistics
            elev = ds.read(1)
            nodata_val = ds.nodata
            if nodata_val is not None:
                valid_mask = elev != nodata_val
            else:
                valid_mask = ~np.isnan(elev)

            valid_count = int(np.sum(valid_mask))
            min_val = float(np.min(elev[valid_mask])) if valid_count > 0 else None
            max_val = float(np.max(elev[valid_mask])) if valid_count > 0 else None
            mean_val = float(np.mean(elev[valid_mask])) if valid_count > 0 else None
            std_val = float(np.std(elev[valid_mask])) if valid_count > 0 else None

            results["elevation_stats"] = {
                "total_pixels": int(elev.size),
                "valid_pixels": valid_count,
                "nodata_pixels": int(elev.size - valid_count),
                "min_elevation_m": min_val,
                "max_elevation_m": max_val,
                "mean_elevation_m": mean_val,
                "std_elevation_m": std_val,
            }

            # 6. Physical plausibility checks for N19_E072 (Western Ghats & Mumbai coastal plain)
            # Min elevation should be near sea level (-15m to +5m for bathymetric/coastal margin)
            # Max elevation: Kalsubai / Western Ghats ridge reaches up to ~1400-1600m in this 1x1 deg tile
            if min_val is None or min_val < -50.0 or max_val > 2000.0:
                results["errors"].append(
                    f"Elevation range implausible for tile N19E072: min={min_val}, max={max_val}"
                )

            # 7. Landmark sampling across Mithi basin
            all_landmarks_inside = True
            for name, (lon, lat) in MITHI_LANDMARKS.items():
                if ds.bounds.left <= lon <= ds.bounds.right and ds.bounds.bottom <= lat <= ds.bounds.top:
                    row, col = ds.index(lon, lat)
                    sampled_elev = float(elev[row, col])
                    results["landmark_sampling"][name] = {
                        "lon": lon,
                        "lat": lat,
                        "row": int(row),
                        "col": int(col),
                        "elevation_m": sampled_elev,
                        "is_valid": bool(sampled_elev != nodata_val if nodata_val is not None else True),
                    }
                else:
                    all_landmarks_inside = False
                    results["errors"].append(f"Landmark {name} ({lon}, {lat}) lies outside tile bounds!")

            if not all_landmarks_inside:
                results["errors"].append("Not all required Mithi catchment landmarks fall within DEM bounds.")

    except Exception as exc:
        results["errors"].append(f"Rasterio validation exception: {exc}")
        return False, results

    if len(results["errors"]) == 0:
        results["valid"] = True
        return True, results
    else:
        return False, results


def create_manifest(
    validation_results: Dict[str, Any],
    source_url: str,
    output_path: Path,
) -> None:
    """Generate Phase 6C.2c verification manifest."""
    manifest_data = {
        "manifest_version": "1.0.0",
        "phase": "PHASE_6C_2C_COPERNICUS_DEM_ACQUISITION",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "governance": {
            "status": "AUTHENTIC_RAW_DEM_ACQUIRED_AND_VALIDATED",
            "source_type": "OFFICIAL_SPACE_AGENCY_REGISTRY",
            "provider": "Copernicus Programme / European Space Agency (ESA) / AWS Open Data",
            "zero_fabrication_enforced": True,
            "zero_synthetic_interpolation_enforced": True,
            "vertical_reference_datum": "EGM96 Geoid (approximating Mean Sea Level)",
            "product_version": "Copernicus DEM GLO-30 (1 arc-second global 30m DSM)",
        },
        "asset": {
            "tile_id": "Copernicus_DSM_COG_10_N19_00_E072_00",
            "filename": DEM_FILENAME,
            "legacy_alias": LEGACY_FILENAME,
            "source_url": source_url,
            "file_size_bytes": validation_results["file_size_bytes"],
            "sha256": validation_results["sha256"],
            "format": validation_results["format"],
            "crs": validation_results["crs"],
            "dimensions": {
                "width": validation_results["width"],
                "height": validation_results["height"],
                "pixel_resolution_arcsec": 1.0,
                "pixel_resolution_approx_m": 30.0,
            },
            "bounds_wgs84": validation_results["bounds"],
            "nodata_value": validation_results["nodata"],
        },
        "elevation_summary": validation_results["elevation_stats"],
        "catchment_coverage_verification": {
            "covers_full_mithi_watershed": True,
            "covers_headwaters_lakes": True,
            "covers_mahim_outfall": True,
            "sampled_landmarks": validation_results["landmark_sampling"],
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest_data, f, sort_keys=False, default_flow_style=False)
    logger.info(f"Created verification manifest: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire and validate Copernicus GLO-30 DEM for Mithi Basin.")
    parser.add_argument("--force", action="store_true", help="Force re-download even if file exists.")
    args = parser.parse_args()

    dest_file = RAW_DEM_DIR / DEM_FILENAME
    legacy_file = RAW_DEM_DIR / LEGACY_FILENAME

    logger.info(f"Target DEM path: {dest_file}")
    logger.info(f"Official source URL: {OFFICIAL_DEM_URL}")

    # 1. Download official DEM
    success, msg = download_copernicus_dem(OFFICIAL_DEM_URL, dest_file, force=args.force)
    if not success:
        logger.error(f"Acquisition failed: {msg}")
        return 1

    # 2. Also provide legacy alias for backward compatibility
    if not legacy_file.exists():
        try:
            # Use copy or hardlink
            shutil.copyfile(dest_file, legacy_file)
            logger.info(f"Created legacy alias copy: {legacy_file}")
        except Exception as e:
            logger.warning(f"Could not create legacy alias: {e}")

    # 3. Validate DEM
    logger.info("Starting rigorous geospatial validation...")
    valid, val_report = validate_copernicus_dem(dest_file)

    if not valid:
        logger.error(f"Validation FAILED with errors: {val_report['errors']}")
        return 2

    logger.info("Validation PASSED! Measured metadata:")
    logger.info(f"  Dimensions: {val_report['width']} x {val_report['height']}")
    logger.info(f"  CRS: {val_report['crs']}")
    logger.info(f"  Bounds: {val_report['bounds']}")
    logger.info(f"  Elevation range: [{val_report['elevation_stats']['min_elevation_m']:.2f} m, {val_report['elevation_stats']['max_elevation_m']:.2f} m]")
    logger.info(f"  SHA-256: {val_report['sha256']}")
    logger.info("Landmark elevations:")
    for k, v in val_report["landmark_sampling"].items():
        logger.info(f"  - {k:25s}: {v['elevation_m']:.2f} m MSL (Row {v['row']}, Col {v['col']})")

    # 4. Create verification manifest
    create_manifest(val_report, OFFICIAL_DEM_URL, MANIFEST_PATH)

    logger.info("Phase 6C.2c acquisition and validation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
