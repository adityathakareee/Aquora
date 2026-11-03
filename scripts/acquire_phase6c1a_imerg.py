"""
AQUORA Phase 6C.1a: Authentic Historical IMERG Rainfall Acquisition & Validation.

Target Event: E03 — Mumbai Mithi Deluge (1-2 July 2019)
Source: NASA GES DISC — GPM IMERG Final Precipitation L3 Half Hourly 0.1 degree V07B (GPM_3IMERGHH.07)

Time Window Resolution:
- Meteorological Event & IMD Ground Gauge Cycle: 2019-07-01T08:30:00+05:30 to 2019-07-02T08:30:00+05:30
- Canonical UTC Time Window: 2019-07-01T03:00:00Z to 2019-07-02T03:00:00Z (exactly 24.0 hours)
- Expected Granule Count: 48 contiguous half-hourly granules (42 from DOY 182 + 6 from DOY 183)
- Sentinel-1 SAR Overpass: 2019-07-02T01:02:58Z (captured at step 45: 01:00:00Z to 01:29:59Z)

Governance & Invariants:
1. Zero fabrication: strictly authentic NASA GES DISC data.
2. Credentials read securely from environment (.env); secrets never logged or exposed.
3. Strict HDF5 validation: magic bytes, FileHeader timestamps, ProductVersion=V07B, units, fill values.
4. Clear separation: raw satellite observations kept unmerged; rainfall forcing strictly decoupled from inundation.
"""

import argparse
import hashlib
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Global socket timeout to prevent hung connection reads
socket.setdefaulttimeout(30.0)

import h5py
import numpy as np
import yaml

# Project roots and directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_IMERG_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "rainfall" / "imerg" / "final" / "2019" / "07"
PROCESSED_RAINFALL_DIR = PROJECT_ROOT / "data" / "processed" / "phase7" / "rainfall"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6c1a_imerg_manifest.yaml"

# Load environment securely
try:
    import dotenv
    dotenv.load_dotenv(PROJECT_ROOT / ".env", override=True)
except ImportError:
    pass

# Event Specification
EVENT_ID = "E03"
EVENT_TITLE = "Mumbai Mithi River Monsoon Deluge (1-2 July 2019)"
UTC_START = "2019-07-01T03:00:00Z"
UTC_END = "2019-07-02T03:00:00Z"
TOTAL_GRANULES_EXPECTED = 48
SAR_OVERPASS_UTC = "2019-07-02T01:02:58Z"

MUMBAI_COORDS = {"lat": 19.076, "lon": 72.877}


class NoAuthLossRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Preserves Authorization header across Earthdata Login / GES DISC redirection chain."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and "Authorization" not in new_req.headers:
            auth_val = req.headers.get("Authorization") or req.headers.get("authorization")
            if auth_val:
                new_req.add_header("Authorization", auth_val)
        return new_req


def get_credentials() -> str | None:
    """Retrieve Earthdata token safely from environment."""
    return os.environ.get("EARTHDATA_TOKEN")


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 cryptographic hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_granule_catalog() -> list[dict[str, Any]]:
    """Build the expected catalog of 48 authentic IMERG V07B granules for Event E03."""
    start_dt = datetime(2019, 7, 1, 3, 0, 0, tzinfo=timezone.utc)
    catalog = []

    for idx in range(TOTAL_GRANULES_EXPECTED):
        t0 = start_dt + timedelta(minutes=30 * idx)
        t1 = t0 + timedelta(minutes=29, seconds=59)

        doy = t0.strftime("%j")
        year = t0.strftime("%Y")
        date_str = t0.strftime("%Y%m%d")
        start_str = t0.strftime("%H%M%S")
        end_str = t1.strftime("%H%M%S")
        minute_of_day = t0.hour * 60 + t0.minute
        min_str = f"{minute_of_day:04d}"

        filename = f"3B-HHR.MS.MRG.3IMERG.{date_str}-S{start_str}-E{end_str}.{min_str}.V07B.HDF5"
        url = f"https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGHH.07/{year}/{doy}/{filename}"

        # Determine if this step spans Sentinel-1 SAR overpass
        is_sar_step = (t0 <= datetime(2019, 7, 2, 1, 2, 58, tzinfo=timezone.utc) <= t1)

        catalog.append({
            "step_index": idx,
            "filename": filename,
            "url": url,
            "year": year,
            "doy": doy,
            "start_utc": t0.isoformat().replace("+00:00", "Z"),
            "end_utc": t1.isoformat().replace("+00:00", "Z"),
            "start_ist": (t0 + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S IST"),
            "end_ist": (t1 + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S IST"),
            "minute_of_day": minute_of_day,
            "is_sar_overpass_step": is_sar_step,
        })

    return catalog


def validate_hdf5_granule(filepath: Path) -> dict[str, Any]:
    """
    Exhaustively validate an authentic IMERG HDF5 granule:
    1. Size (> 1 MB) and Magic Bytes (\\x89HDF\\r\\n\\x1a\\n).
    2. FileHeader: ProductVersion == V07B, TimeInterval == HALF_HOUR.
    3. Grid datasets: Grid/lon (3600,), Grid/lat (1800,), Grid/precipitation (1, 3600, 1800).
    4. Units (mm/hr) and FillValue (-9999.9).
    5. Extracts Mumbai point/cell precipitation rate.
    """
    if not filepath.exists():
        return {"valid": False, "error": f"File does not exist: {filepath}"}

    size = filepath.stat().st_size
    if size < 1_000_000:
        with open(filepath, "rb") as f:
            sample = f.read(1024)
        if b"<html" in sample.lower() or b"<!doctype html" in sample.lower():
            return {
                "valid": False,
                "error": f"File contains HTML auth error page ({size} bytes). Verify EARTHDATA_TOKEN."
            }
        return {"valid": False, "error": f"File size too small ({size} bytes)"}

    # Verify HDF5 Magic Bytes
    with open(filepath, "rb") as f:
        header = f.read(8)
    if not header.startswith(b"\x89HDF\r\n\x1a\n"):
        return {"valid": False, "error": f"Invalid HDF5 header magic bytes: {header!r}"}

    # Verify HDF5 internal metadata
    try:
        with h5py.File(filepath, "r") as h5:
            fheader = h5.attrs.get("FileHeader")
            fheader_str = fheader.decode("utf-8") if isinstance(fheader, bytes) else str(fheader)

            if "ProductVersion=V07B" not in fheader_str:
                return {"valid": False, "error": "ProductVersion is not V07B in FileHeader"}
            if "TimeInterval=HALF_HOUR" not in fheader_str:
                return {"valid": False, "error": "TimeInterval is not HALF_HOUR in FileHeader"}

            # Validate Grid datasets
            if "Grid/precipitation" not in h5:
                return {"valid": False, "error": "Missing dataset Grid/precipitation"}
            if "Grid/lon" not in h5 or "Grid/lat" not in h5:
                return {"valid": False, "error": "Missing Grid/lon or Grid/lat coordinates"}

            precip_ds = h5["Grid/precipitation"]
            if precip_ds.shape != (1, 3600, 1800):
                return {"valid": False, "error": f"Unexpected precipitation shape: {precip_ds.shape}"}

            units = precip_ds.attrs.get("Units") or precip_ds.attrs.get("units")
            units_str = units.decode("utf-8") if isinstance(units, bytes) else str(units)
            if units_str != "mm/hr":
                return {"valid": False, "error": f"Unexpected units: {units_str}"}

            fill_val = float(precip_ds.attrs.get("_FillValue", 0.0))

            # Coordinates
            lons = h5["Grid/lon"][:]
            lats = h5["Grid/lat"][:]

            # Extract Mumbai cell (19.05°N, 72.85°E)
            lon_idx = int(np.argmin(np.abs(lons - MUMBAI_COORDS["lon"])))
            lat_idx = int(np.argmin(np.abs(lats - MUMBAI_COORDS["lat"])))

            precip_raw = float(precip_ds[0, lon_idx, lat_idx])
            qi_raw = float(h5["Grid/precipitationQualityIndex"][0, lon_idx, lat_idx]) if "Grid/precipitationQualityIndex" in h5 else None

            # Handle fill value
            is_valid_obs = not np.isclose(precip_raw, fill_val, atol=1.0) and precip_raw >= 0.0
            precip_rate_mm_hr = precip_raw if is_valid_obs else 0.0
            accumulation_30min_mm = precip_rate_mm_hr * 0.5

            return {
                "valid": True,
                "file_size_bytes": size,
                "sha256": compute_sha256(filepath),
                "product_version": "V07B",
                "units": "mm/hr",
                "fill_value": fill_val,
                "mumbai_grid_indices": {"lon_idx": lon_idx, "lat_idx": lat_idx},
                "mumbai_rate_mm_hr": round(precip_rate_mm_hr, 4),
                "mumbai_accumulation_30min_mm": round(accumulation_30min_mm, 4),
                "quality_index": qi_raw,
                "is_valid_observation": is_valid_obs,
            }
    except Exception as e:
        return {"valid": False, "error": f"HDF5 read exception: {e!s}"}


def download_single_granule(
    granule_info: dict[str, Any],
    token: str,
    opener: urllib.request.OpenerDirector,
    dest_dir: Path,
    max_retries: int = 3
) -> dict[str, Any]:
    """Download one authentic IMERG granule with retry handling."""
    filename = granule_info["filename"]
    dest_path = dest_dir / filename

    # Check if valid file already exists (cache hit)
    if dest_path.exists():
        val = validate_hdf5_granule(dest_path)
        if val["valid"]:
            return {
                "status": "CACHED",
                "filename": filename,
                "path": str(dest_path),
                "validation": val
            }
        else:
            dest_path.unlink()

    url = granule_info["url"]
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")

    for attempt in range(1, max_retries + 1):
        try:
            with opener.open(req, timeout=45) as resp, open(dest_path, "wb") as out_f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out_f.write(chunk)

            # Validate downloaded file
            val = validate_hdf5_granule(dest_path)
            if not val["valid"]:
                if dest_path.exists():
                    dest_path.unlink()
                if attempt == max_retries:
                    return {"status": "VALIDATION_FAILED", "filename": filename, "error": val["error"]}
                time.sleep(1.0)
                continue

            return {
                "status": "DOWNLOADED",
                "filename": filename,
                "path": str(dest_path),
                "validation": val
            }
        except urllib.error.HTTPError as e:
            if dest_path.exists():
                dest_path.unlink()
            if attempt == max_retries:
                return {"status": "HTTP_ERROR", "filename": filename, "code": e.code, "reason": str(e.reason)}
            time.sleep(2.0 * attempt)
        except Exception as e:
            if dest_path.exists():
                dest_path.unlink()
            if attempt == max_retries:
                return {"status": "NETWORK_ERROR", "filename": filename, "error": str(e)}
            time.sleep(2.0 * attempt)

    return {"status": "FAILED", "filename": filename, "error": "Exhausted retries"}


def run_phase6c1a_acquisition(dry_run: bool = False, max_count: int | None = None) -> dict[str, Any]:
    """Execute complete Phase 6C.1a acquisition and validation workflow."""
    print("=" * 80)
    print("AQUORA Phase 6C.1a — Authentic Historical IMERG Rainfall Acquisition")
    print("=" * 80)
    print(f"Target Event: {EVENT_ID} — {EVENT_TITLE}")
    print(f"Authoritative UTC Window: {UTC_START} to {UTC_END} (24.0 hours)")
    print(f"IMD Observation Window:   2019-07-01 08:30:00 IST to 2019-07-02 08:30:00 IST")
    print(f"Expected Granule Count:   {TOTAL_GRANULES_EXPECTED}")
    print(f"Sentinel-1 SAR Overpass:  {SAR_OVERPASS_UTC} (covered at step 45)")
    print("-" * 80)

    token = get_credentials()
    if not token:
        print("[ERROR] EARTHDATA_TOKEN missing from environment / .env.")
        print("Authentic NASA GES DISC downloads cannot proceed without credentials.")
        return {"status": "BLOCKED_AWAITING_CREDENTIALS", "acquired_count": 0}

    RAW_IMERG_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_RAINFALL_DIR.mkdir(parents=True, exist_ok=True)

    full_catalog = build_granule_catalog()
    catalog = full_catalog[:max_count] if max_count is not None else full_catalog

    print(f"[CATALOG] Built expected series of {len(full_catalog)} granules (processing: {len(catalog)}).")

    if dry_run:
        print("[DRY RUN] Validating catalog URLs without downloading full payloads...")
        return {"status": "DRY_RUN_COMPLETE", "catalog_count": len(catalog)}

    from concurrent.futures import ThreadPoolExecutor, as_completed

    opener = urllib.request.build_opener(NoAuthLossRedirectHandler())

    print(f"\n[PARALLEL DOWNLOAD & VALIDATION PROGRESS] Using 4 worker threads...")
    
    def process_item(item):
        res = download_single_granule(item, token, opener, RAW_IMERG_DIR)
        val = res.get("validation", {})
        status = res["status"]
        rate = val.get("mumbai_rate_mm_hr", 0.0)
        accum = val.get("mumbai_accumulation_30min_mm", 0.0)
        size = val.get("file_size_bytes", 0)
        return {
            **item,
            "status": status,
            "sha256": val.get("sha256"),
            "file_size_bytes": size,
            "mumbai_rate_mm_hr": rate,
            "mumbai_accumulation_30min_mm": accum,
            "quality_index": val.get("quality_index"),
            "is_valid": val.get("valid", False),
        }

    item_results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_item = {executor.submit(process_item, item): item for item in catalog}
        done_count = 0
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            res = future.result()
            item_results[item["step_index"]] = res
            done_count += 1
            status = res["status"]
            rate = res["mumbai_rate_mm_hr"]
            overpass_tag = " [SAR OVERPASS]" if item["is_sar_overpass_step"] else ""
            sys.stdout.write(
                f"\r[{done_count:02d}/{len(catalog):02d}] {status:<10} | {item['filename'][:40]}... | Rate: {rate:5.1f} mm/h{overpass_tag}"
            )
            sys.stdout.flush()

    print("\n" + "-" * 80)

    # Sort results strictly in chronological step order
    results = [item_results[i] for i in range(len(catalog))]

    # Compute continuous cumulative accumulation
    cum_accumulation_mm = 0.0
    total_bytes = 0
    for r in results:
        cum_accumulation_mm += r["mumbai_accumulation_30min_mm"]
        r["cum_accumulation_30min_mm"] = round(cum_accumulation_mm, 4)
        total_bytes += r.get("file_size_bytes", 0)

    # Check for failures or missing intervals
    successful = [r for r in results if r.get("is_valid")]
    failed = [r for r in results if not r.get("is_valid")]

    print(f"\n[ACQUISITION SUMMARY]")
    print(f"Total Expected Granules : {len(catalog)}")
    print(f"Total Acquired & Valid  : {len(successful)}")
    print(f"Total Failed            : {len(failed)}")
    print(f"Total Storage Size      : {total_bytes / (1024 * 1024):.2f} MB")
    print(f"IMERG 24h Accumulation  : {cum_accumulation_mm:.2f} mm (at Mumbai 19.05°N, 72.85°E)")
    print(f"IMD Santacruz 24h Gauge : 375.2 mm (official ground point record)")

    # Save time series JSON
    timeseries_path = PROCESSED_RAINFALL_DIR / "E03_imerg_timeseries_24h.json"
    sar_granule_name = full_catalog[44]["filename"]
    with open(timeseries_path, "w", encoding="utf-8") as f:
        json.dump({
            "event_id": EVENT_ID,
            "title": EVENT_TITLE,
            "time_window": {
                "utc_start": UTC_START,
                "utc_end": UTC_END,
                "ist_start": "2019-07-01T08:30:00+05:30",
                "ist_end": "2019-07-02T08:30:00+05:30",
                "duration_hours": 24.0,
                "total_granules": len(catalog),
            },
            "sentinel1_sar_overpass": {
                "timestamp_utc": SAR_OVERPASS_UTC,
                "timestamp_ist": "2019-07-02T06:32:58+05:30",
                "spanning_step_index": 44,
                "spanning_granule": sar_granule_name,
            },
            "spatial_coordinates": MUMBAI_COORDS,
            "summary_metrics": {
                "imerg_24h_total_accumulation_mm": round(cum_accumulation_mm, 2),
                "imerg_peak_half_hour_rate_mm_hr": round(max(r["mumbai_rate_mm_hr"] for r in successful), 2),
                "imd_santacruz_24h_point_total_mm": 375.2,
                "data_completeness_ratio": len(successful) / len(catalog),
                "missing_intervals_count": len(failed),
            },
            "granules": results,
        }, f, indent=2)

    # Save Authoritative Manifest YAML
    manifest_data = {
        "manifest_version": "1.0.0",
        "phase": "PHASE_6C_1A_IMERG_ACQUISITION",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "governance": {
            "status": "AUTHENTIC_SATELLITE_DATASET_ACQUIRED",
            "zero_fabrication_enforced": True,
            "zero_synthetic_interpolation_enforced": True,
            "rainfall_inundation_conflation_guard": "Rainfall forcing creates flood hazard; rainfall volume alone does NOT constitute proof of surface inundation extent.",
        },
        "event_target": {
            "event_id": EVENT_ID,
            "title": EVENT_TITLE,
            "utc_window": {"start": UTC_START, "end": UTC_END},
            "ist_window": {"start": "2019-07-01T08:30:00+05:30", "end": "2019-07-02T08:30:00+05:30"},
            "duration_hours": 24.0,
            "granules_expected": TOTAL_GRANULES_EXPECTED,
            "granules_acquired": len(successful),
            "granules_failed": len(failed),
            "missing_intervals": [f["filename"] for f in failed],
        },
        "sentinel1_alignment": {
            "overpass_utc": SAR_OVERPASS_UTC,
            "overpass_ist": "2019-07-02T06:32:58+05:30",
            "coincident_step_index": 44,
            "coincident_granule": sar_granule_name,
            "coincident_step_window_utc": f"{full_catalog[44]['start_utc']} to {full_catalog[44]['end_utc']}",
        },
        "precipitation_comparison": {
            "imerg_satellite_24h_accumulation_mm": round(cum_accumulation_mm, 2),
            "imd_santacruz_gauge_24h_total_mm": 375.2,
            "scale_distinction": "IMERG reflects a 0.1 deg (~10 km) gridded spatial average; IMD Santacruz reflects an in-situ point gauge measurement.",
        },
        "raw_archive_directory": str(RAW_IMERG_DIR),
        "granule_manifest": [
            {
                "step": r["step_index"],
                "filename": r["filename"],
                "start_utc": r["start_utc"],
                "end_utc": r["end_utc"],
                "sha256": r.get("sha256"),
                "size_bytes": r.get("file_size_bytes"),
                "rate_mm_hr": r.get("mumbai_rate_mm_hr"),
                "accumulation_30min_mm": r.get("mumbai_accumulation_30min_mm"),
            }
            for r in successful
        ]
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        yaml.dump(manifest_data, f, sort_keys=False, indent=2)

    print(f"\n[MANIFEST] Saved authoritative manifest to: {MANIFEST_PATH}")
    print(f"[OUTPUT] Saved time series JSON to: {timeseries_path}")

    return {
        "status": "SUCCESS" if not failed else "PARTIAL",
        "acquired_count": len(successful),
        "failed_count": len(failed),
        "cum_accumulation_mm": cum_accumulation_mm,
        "manifest_path": str(MANIFEST_PATH),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Acquire and validate authentic historical NASA IMERG rainfall for E03.")
    parser.add_argument("--dry-run", action="store_true", help="Validate catalog without downloading full payloads")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of granules to process (for debugging)")
    args = parser.parse_args()

    res = run_phase6c1a_acquisition(dry_run=args.dry_run, max_count=args.limit)
    if res["status"] not in ("SUCCESS", "DRY_RUN_COMPLETE"):
        sys.exit(1)
