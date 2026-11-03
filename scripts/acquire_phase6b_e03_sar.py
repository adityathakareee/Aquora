"""
AQUORA Phase 6B.2: Authentic Sentinel-1 SAR Acquisition Script for Event E03 (Mumbai, 2 July 2019).

Purpose:
Acquires authentic Copernicus Sentinel-1A Level-1 GRD-HD SAR archives from official ASF DAAC
endpoints for Event E03 flood analysis across the Mumbai / Mithi River catchment.

Security & Integrity Invariants:
1. Credentials read exclusively from environment variables or ignored .env.
2. Zero hardcoded credentials. Never prints or logs secrets.
3. If credentials missing, halts cleanly before network transfer.
4. Checks available disk space (>10 GB required) before proceeding.
5. Supports resuming interrupted downloads via HTTP Range headers.
6. Writes exclusively into git-ignored directory: data/raw/phase7/sentinel1/E03/.
7. Validates archive integrity (ZIP test), exact file size, and provider MD5 checksum.
8. Never marks incomplete or unauthenticated archives as validated.
9. Zero fabrication: never creates synthetic SAR images or fake flood labels.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_SAR_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "sentinel1" / "E03"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase6b_e03_sar_manifest.yaml"

# Load local .env if available
try:
    import dotenv
    dotenv.load_dotenv(PROJECT_ROOT / ".env", override=True)
except ImportError:
    pass

# Event E03 Catalog Specifications (Verified from ASF DAAC)
E03_SCENES = {
    "pre_event": {
        "granule_name": "S1A_IW_GRDH_1SDV_20190608T010256_20190608T010321_027581_031CCA_FBE2",
        "role": "PRE_EVENT_DRY_BASELINE",
        "date_utc": "2019-06-08T01:02:56Z",
        "date_ist": "2019-06-08 06:32:56 IST",
        "exact_bytes": 925313923,
        "provider_md5": "b5dfcdfdabe7065522b60ec697541d92",
        "url": "https://datapool.asf.alaska.edu/GRD_HD/SA/S1A_IW_GRDH_1SDV_20190608T010256_20190608T010321_027581_031CCA_FBE2.zip",
    },
    "co_event": {
        "granule_name": "S1A_IW_GRDH_1SDV_20190702T010258_20190702T010323_027931_03274B_DDDA",
        "role": "CO_EVENT_PEAK_FLOOD_CRISIS",
        "date_utc": "2019-07-02T01:02:58Z",
        "date_ist": "2019-07-02 06:32:58 IST",
        "exact_bytes": 981880378,
        "provider_md5": "10c400e13cd5b57cb3adb229bee87ee9",
        "url": "https://datapool.asf.alaska.edu/GRD_HD/SA/S1A_IW_GRDH_1SDV_20190702T010258_20190702T010323_027931_03274B_DDDA.zip",
    },
    "post_event": {
        "granule_name": "S1A_IW_GRDH_1SDV_20190714T010258_20190714T010323_028106_032C97_F1F5",
        "role": "POST_EVENT_MONSOON_BASELINE",
        "date_utc": "2019-07-14T01:02:58Z",
        "date_ist": "2019-07-14 06:32:58 IST",
        "exact_bytes": 978935209,
        "provider_md5": "14b2f99019a971f53fc519c6f524ff59",
        "url": "https://datapool.asf.alaska.edu/GRD_HD/SA/S1A_IW_GRDH_1SDV_20190714T010258_20190714T010323_028106_032C97_F1F5.zip",
    }
}


def get_credentials() -> tuple[str | None, str | None, str | None]:
    """Retrieve Earthdata credentials safely from environment."""
    token = os.environ.get("EARTHDATA_TOKEN")
    user = os.environ.get("NASA_EARTHDATA_USERNAME")
    password = os.environ.get("NASA_EARTHDATA_PASSWORD")
    return user, password, token


def check_disk_space(required_gb: float = 10.0) -> dict:
    """Verify sufficient free disk space exists on the destination drive."""
    drive = Path(RAW_SAR_DIR.anchor or "/")
    total, used, free = shutil.disk_usage(drive)
    free_gb = free / (1024 ** 3)
    sufficient = free_gb >= required_gb
    return {
        "drive": str(drive),
        "total_gb": round(total / (1024 ** 3), 2),
        "free_gb": round(free_gb, 2),
        "required_gb": required_gb,
        "sufficient": sufficient
    }


def compute_checksums(filepath: Path) -> tuple[str, str]:
    """Compute MD5 and SHA-256 checksums in a single pass."""
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha256.hexdigest()


def validate_sar_archive(filepath: Path, spec: dict) -> dict:
    """
    Validate a downloaded Sentinel-1 SAR ZIP archive:
    1. Existence and minimum file size
    2. Check for HTML authentication redirect / error pages
    3. Exact byte count check against provider catalog
    4. Provider MD5 checksum verification
    5. ZIP format and internal directory structure verification (testzip)
    """
    if not filepath.exists():
        return {"valid": False, "error": f"File not found: {filepath}"}

    size = filepath.stat().st_size

    # Check for HTML redirect/auth failure
    if size < 2_000_000 and spec.get("exact_bytes", 0) > 2_000_000:
        with open(filepath, "rb") as f:
            sample = f.read(1024)
        if b"<html" in sample.lower() or b"<!doctype html" in sample.lower():
            return {
                "valid": False,
                "error": f"File contains HTML authentication redirect page ({size} bytes). Earthdata credentials invalid or expired."
            }
        return {"valid": False, "error": f"File size too small for Sentinel-1 GRD: {size} bytes"}

    if size != spec["exact_bytes"]:
        return {
            "valid": False,
            "error": f"Byte count mismatch: expected {spec['exact_bytes']} bytes, got {size} bytes (difference: {size - spec['exact_bytes']} bytes)"
        }

    # Verify provider MD5 checksum
    actual_md5, actual_sha256 = compute_checksums(filepath)
    if actual_md5.lower() != spec["provider_md5"].lower():
        return {
            "valid": False,
            "error": f"MD5 mismatch: expected {spec['provider_md5']}, got {actual_md5}"
        }

    # Verify ZIP integrity
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            bad_file = zf.testzip()
            if bad_file:
                return {"valid": False, "error": f"Corrupted file inside ZIP archive: {bad_file}"}
            namelist = zf.namelist()
            has_safe = any(n.endswith("manifest.safe") for n in namelist)
            has_measurement = any("measurement/" in n and n.endswith(".tiff") for n in namelist)
            if not (has_safe and has_measurement):
                return {"valid": False, "error": "Missing expected SAFE manifest or measurement TIFFs inside archive"}
    except zipfile.BadZipFile as e:
        return {"valid": False, "error": f"Invalid or incomplete ZIP archive: {e}"}

    return {
        "valid": True,
        "granule_name": spec["granule_name"],
        "file_size_bytes": size,
        "md5": actual_md5,
        "sha256": actual_sha256,
        "validation_status": "VALIDATED_AUTHENTIC_SAFE_ZIP"
    }


def download_scene(key: str, spec: dict, force: bool = False, dry_run: bool = False) -> dict:
    """Download a single Sentinel-1 scene with resumable transfer and integrity checks."""
    RAW_SAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{spec['granule_name']}.zip"
    dest_path = RAW_SAR_DIR / filename
    part_path = RAW_SAR_DIR / f"{filename}.part"

    user, password, token = get_credentials()
    has_creds = bool(token or (user and password))

    print(f"\n[{key.upper()}] Target: {spec['granule_name']}")
    print(f"  Role: {spec['role']}")
    print(f"  Acquisition: {spec['date_ist']} ({spec['date_utc']})")
    print(f"  Expected Size: {spec['exact_bytes'] / (1024**2):.2f} MB ({spec['exact_bytes']} bytes)")
    print(f"  Destination: {dest_path}")

    # Check existing valid archive
    if dest_path.exists() and not force:
        val = validate_sar_archive(dest_path, spec)
        if val["valid"]:
            print(f"  [CACHE HIT] Valid authentic archive already present ({val['file_size_bytes']} bytes).")
            print(f"  MD5: {val['md5']} | SHA-256: {val['sha256']}")
            return {"status": "CACHED", "validation": val, "path": str(dest_path)}
        else:
            print(f"  [CACHE INVALID] Existing file failed validation: {val['error']}. Re-downloading...")
            dest_path.unlink()

    if dry_run:
        print("  [DRY RUN] Download skipped per --dry-run flag.")
        return {"status": "DRY_RUN", "granule": spec["granule_name"], "url": spec["url"]}

    if not has_creds:
        print("\n  [BLOCKED] NASA Earthdata credentials missing!")
        print("  Set EARTHDATA_TOKEN in .env or environment before downloading.")
        return {"status": "BLOCKED_AWAITING_CREDENTIALS", "granule": spec["granule_name"]}

    class NoAuthLossRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
            if new_req and "Authorization" in req.headers:
                new_req.headers["Authorization"] = req.headers["Authorization"]
            return new_req

    opener = urllib.request.build_opener(NoAuthLossRedirectHandler())

    # Setup request with authentication and resumable Range header
    req = urllib.request.Request(spec["url"])
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    elif user and password:
        import base64
        creds = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", f"Basic {creds}")

    existing_bytes = 0
    if part_path.exists() and not force:
        existing_bytes = part_path.stat().st_size
        if existing_bytes < spec["exact_bytes"]:
            req.add_header("Range", f"bytes={existing_bytes}-")
            print(f"  [RESUMING] Found partial file: {existing_bytes / (1024**2):.2f} MB. Requesting remaining bytes...")
        else:
            existing_bytes = 0

    mode = "ab" if existing_bytes > 0 else "wb"

    try:
        print(f"  [DOWNLOADING] Connecting to {spec['url']}...")
        with opener.open(req, timeout=120) as resp, open(part_path, mode) as out_file:
            # Check for HTTP 206 Partial Content or 200 OK
            if existing_bytes > 0 and resp.status == 200:
                print("  [RANGE NOT SUPPORTED] Server returned 200 OK; restarting download from 0...")
                out_file.seek(0)
                out_file.truncate()
                existing_bytes = 0

            chunk_size = 1048576  # 1 MB chunks
            downloaded = existing_bytes
            total = spec["exact_bytes"]

            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                pct = (downloaded / total) * 100 if total > 0 else 0
                sys.stdout.write(f"\r  Progress: {downloaded / (1024**2):.1f}/{total / (1024**2):.1f} MB ({pct:.1f}%)")
                sys.stdout.flush()
        print("\n  [DOWNLOAD STREAM COMPLETED]")
    except urllib.error.HTTPError as e:
        print(f"\n  [HTTP ERROR {e.code}] {e.reason}")
        return {"status": "HTTP_ERROR", "code": e.code, "reason": str(e.reason)}
    except Exception as e:
        print(f"\n  [NETWORK ERROR] {e!s}")
        return {"status": "NETWORK_ERROR", "error": str(e)}

    # Move .part to final destination
    if part_path.exists():
        part_path.rename(dest_path)

    # Validate downloaded archive
    val = validate_sar_archive(dest_path, spec)
    if not val["valid"]:
        print(f"  [VALIDATION FAILED] {val['error']}")
        if dest_path.exists():
            dest_path.unlink()
        return {"status": "VALIDATION_FAILED", "error": val["error"]}

    print(f"  [VALIDATION PASSED] Size: {val['file_size_bytes']} bytes | MD5: {val['md5']}")
    return {"status": "SUCCESS", "validation": val, "path": str(dest_path)}


def run_e03_acquisition(
    dry_run: bool = False,
    force: bool = False,
    include_post_event: bool = False,
    check_only: bool = False
) -> dict:
    """Run acquisition workflow for Event E03 Sentinel-1 SAR archives."""
    print("=" * 80)
    print("AQUORA PHASE 6B.2: EVENT E03 SENTINEL-1 SAR ACQUISITION WORKFLOW")
    print("=" * 80)
    print(f"Study Domain: Mumbai Mithi River Catchment (EPSG:32643)")
    print(f"Target Event: E03 (1-2 July 2019 Monsoon Cloudburst Deluge)")
    print(f"Destination Directory: {RAW_SAR_DIR}")
    print(f"Execution Mode: {'CHECK ONLY' if check_only else ('DRY RUN' if dry_run else 'ACTIVE ACQUISITION')}")
    print("-" * 80)

    # 1. Credentials Check
    user, password, token = get_credentials()
    has_creds = bool(token or (user and password))
    print(f"Earthdata Credentials: {'CONFIGURED (Token/User detected)' if has_creds else 'NOT CONFIGURED'}")

    # 2. Disk Space Check
    required_gb = 10.0 if not include_post_event else 15.0
    disk = check_disk_space(required_gb=required_gb)
    print(f"Disk Space on {disk['drive']}: {disk['free_gb']:.2f} GB free (Required: >{disk['required_gb']} GB) -> {'SUFFICIENT' if disk['sufficient'] else 'INSUFFICIENT'}")
    if not disk["sufficient"]:
        print(f"[HALTED] Insufficient disk space on drive {disk['drive']}. Free at least {required_gb} GB.")
        return {"status": "ERROR_INSUFFICIENT_DISK", "disk": disk}

    # 3. Target Granules Selection
    targets = ["pre_event", "co_event"]
    if include_post_event:
        targets.append("post_event")

    results = {}
    for key in targets:
        spec = E03_SCENES[key]
        if check_only:
            dest_path = RAW_SAR_DIR / f"{spec['granule_name']}.zip"
            val = validate_sar_archive(dest_path, spec)
            results[key] = {"status": "CHECKED", "validation": val, "path": str(dest_path)}
            print(f"[{key.upper()}] {'VALID' if val['valid'] else 'MISSING/INVALID'}: {val.get('error', 'Integrity verified')}")
        else:
            res = download_scene(key, spec, force=force, dry_run=dry_run)
            results[key] = res

    print("\n" + "=" * 80)
    print("ACQUISITION WORKFLOW SUMMARY")
    print("=" * 80)
    for k, v in results.items():
        print(f"  {k}: {v.get('status')} ({E03_SCENES[k]['granule_name']})")
    print("=" * 80)
    return {"status": "COMPLETED", "results": results, "disk": disk}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AQUORA Phase 6B.2 E03 Sentinel-1 SAR Acquisition Workflow")
    parser.add_argument("--dry-run", action="store_true", help="Perform credentials, catalog, and disk readiness checks without downloading")
    parser.add_argument("--force", action="store_true", help="Force re-download even if archive exists")
    parser.add_argument("--include-post-event", action="store_true", help="Also acquire optional 14 July 2019 recession scene")
    parser.add_argument("--check-only", action="store_true", help="Validate existing archives on disk without network transfers")
    args = parser.parse_args()

    run_e03_acquisition(
        dry_run=args.dry_run,
        force=args.force,
        include_post_event=args.include_post_event,
        check_only=args.check_only
    )
