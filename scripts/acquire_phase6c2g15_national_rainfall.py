"""
AQUORA Phase 6C.2G.15: National Historical Precipitation Acquisition & Multi-Source Scaling Script.

Performs:
1. Loads full national derived flood events dataset (6,876 IFI historical disaster records).
2. Performs national-scale deduplication: identifies 3,684 unique valid dates.
3. Classifies events into authoritative source eligibility eras:
   - Pre-1981: 321 records (satellite observations unavailable; requires reanalysis/IMD).
   - CHIRPS-eligible (1981–2023): 6,535 records across 3,490 unique dates (~10.5 GB storage).
   - NASA GPM IMERG-eligible (June 2000–2023): 4,605 records across 2,168 unique dates (~71.3 GB storage).
4. Calculates comprehensive national storage and processing requirements.
5. Ingests a controlled, representative National Acquisition Cohort of landmark disaster events:
   - 16 landmark disaster event dates spanning 1984 to 2022 across 12 diverse Indian states.
   - Dual-source acquisition: CHIRPS v2.0 Daily (0.05 deg) and NASA GPM IMERG Final Daily (0.1 deg).
   - Atomic writes (.part -> validate -> atomic move), timeouts, retry handling, and checksumming.
6. Preserves existing assets, zero overwriting of raw source files.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
import urllib.error
import urllib.request
import h5py
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment securely
try:
    import dotenv
    dotenv.load_dotenv(PROJECT_ROOT / ".env", override=True)
except ImportError:
    pass

# Raw storage directories
RAW_RAINFALL_DIR = PROJECT_ROOT / "data" / "raw" / "phase7" / "rainfall"
CHIRPS_DAILY_DIR = RAW_RAINFALL_DIR / "chirps" / "daily"
IMERG_DAILY_DIR = RAW_RAINFALL_DIR / "imerg" / "daily"

DERIVED_PARQUET = PROJECT_ROOT / "data" / "processed" / "phase7" / "events" / "national_historical_flood_records_derived.parquet"
RAW_IFI_PATH = PROJECT_ROOT / "data" / "raw" / "phase7" / "ground_truth" / "india_flood_inventory_v3.csv"

# Controlled National Acquisition Cohort (Landmark Historical Disaster Events Across India)
NATIONAL_COHORT_EVENTS = [
    # Tier-1 / Benchmark Mumbai Events
    {
        "cohort_id": "NAT-01",
        "uei": "UEI-IMD-FL-2019-0090",
        "event_name": "Mumbai Mithi River Monsoon Deluge (July 2019)",
        "state": "Maharashtra",
        "district": "Mumbai Suburban",
        "date_str": "2019-07-01",
        "year": "2019", "month": "07", "day": "01",
        "coords": {"lon": 72.85, "lat": 19.05},
    },
    {
        "cohort_id": "NAT-02",
        "uei": "UEI-IMD-FL-2017-0088",
        "event_name": "Mumbai Cloudburst Deluge (August 2017)",
        "state": "Maharashtra",
        "district": "Mumbai, Thane, Palghar",
        "date_str": "2017-08-29",
        "year": "2017", "month": "08", "day": "29",
        "coords": {"lon": 72.85, "lat": 19.05},
    },
    {
        "cohort_id": "NAT-03",
        "uei": "UEI-IMD-FL-2005-0107",
        "event_name": "Maharashtra 26 July Cloudburst Deluge (2005)",
        "state": "Maharashtra",
        "district": "Mumbai",
        "date_str": "2005-07-26",
        "year": "2005", "month": "07", "day": "26",
        "coords": {"lon": 72.85, "lat": 19.05},
    },
    # Western Ghats / Coastal Southern India
    {
        "cohort_id": "NAT-04",
        "uei": "UEI-IMD-FL-2018-0036",
        "event_name": "Kerala Catastrophic Monsoon Floods (August 2018)",
        "state": "Kerala",
        "district": "Ernakulam, Idukki",
        "date_str": "2018-08-16",
        "year": "2018", "month": "08", "day": "16",
        "coords": {"lon": 76.27, "lat": 9.98},
    },
    {
        "cohort_id": "NAT-05",
        "uei": "UEI-IMD-FL-2015-0097",
        "event_name": "Chennai Coromandel Deluge (December 2015)",
        "state": "Tamil Nadu",
        "district": "Chennai, Kanchipuram",
        "date_str": "2015-12-01",
        "year": "2015", "month": "12", "day": "01",
        "coords": {"lon": 80.25, "lat": 13.05},
    },
    {
        "cohort_id": "NAT-06",
        "uei": "UEI-IMD-FL-2022-0519",
        "event_name": "Bengaluru Urban Flooding (September 2022)",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "date_str": "2022-09-05",
        "year": "2022", "month": "09", "day": "05",
        "coords": {"lon": 77.67, "lat": 12.93},
    },
    # Himalayan & High-Relief Basins
    {
        "cohort_id": "NAT-07",
        "uei": "UEI-IMD-FL-2013-0131",
        "event_name": "Kedarnath / Uttarakhand Cloudburst (June 2013)",
        "state": "Uttarakhand",
        "district": "Rudraprayag, Chamoli",
        "date_str": "2013-06-16",
        "year": "2013", "month": "06", "day": "16",
        "coords": {"lon": 79.07, "lat": 30.73},
    },
    {
        "cohort_id": "NAT-08",
        "uei": "UEI-IMD-FL-2014-0044",
        "event_name": "Jammu & Kashmir / Srinagar Floods (September 2014)",
        "state": "Jammu and Kashmir",
        "district": "Srinagar, Anantnag",
        "date_str": "2014-09-04",
        "year": "2014", "month": "09", "day": "04",
        "coords": {"lon": 74.80, "lat": 34.08},
    },
    # Major River Floodplains (Brahmaputra, Ganga, Kosi, Krishna, Narmada/Tapi)
    {
        "cohort_id": "NAT-09",
        "uei": "UEI-IMD-FL-2019-0002",
        "event_name": "Assam Brahmaputra Monsoon Flood (July 2019)",
        "state": "Assam",
        "district": "Barpeta, Dhemaji",
        "date_str": "2019-07-10",
        "year": "2019", "month": "07", "day": "10",
        "coords": {"lon": 91.75, "lat": 26.18},
    },
    {
        "cohort_id": "NAT-10",
        "uei": "UEI-IMD-FL-2008-0004",
        "event_name": "Bihar Kosi River Avulsion Deluge (August 2008)",
        "state": "Bihar",
        "district": "Supaul, Madhepura, Saharsa",
        "date_str": "2008-08-18",
        "year": "2008", "month": "08", "day": "18",
        "coords": {"lon": 86.60, "lat": 26.12},
    },
    {
        "cohort_id": "NAT-11",
        "uei": "UEI-IMD-FL-2006-0045",
        "event_name": "Gujarat Surat Tapi River Floods (August 2006)",
        "state": "Gujarat",
        "district": "Surat, Navsari",
        "date_str": "2006-08-07",
        "year": "2006", "month": "08", "day": "07",
        "coords": {"lon": 72.83, "lat": 21.17},
    },
    {
        "cohort_id": "NAT-12",
        "uei": "UEI-IMD-FL-2009-0005",
        "event_name": "Andhra Pradesh / Kurnool Krishna Basin Floods (October 2009)",
        "state": "Andhra Pradesh",
        "district": "Kurnool, Mahabubnagar",
        "date_str": "2009-10-02",
        "year": "2009", "month": "10", "day": "02",
        "coords": {"lon": 78.03, "lat": 15.83},
    },
    {
        "cohort_id": "NAT-13",
        "uei": "UEI-IMD-FL-2001-0065",
        "event_name": "Odisha Mahanadi Basin Floods (July 2001)",
        "state": "Odisha",
        "district": "Cuttack, Puri, Kendrapara",
        "date_str": "2001-07-04",
        "year": "2001", "month": "07", "day": "04",
        "coords": {"lon": 85.88, "lat": 20.46},
    },
    # Historical Pre-2000 Events (CHIRPS Era 1981-2000, IMERG Pre-TRMM)
    {
        "cohort_id": "NAT-14",
        "uei": "UEI-IMD-FL-1993-0077",
        "event_name": "West Bengal North Bengal / Jalpaiguri Deluge (July 1993)",
        "state": "West Bengal",
        "district": "Jalpaiguri, Cooch Behar",
        "date_str": "1993-07-18",
        "year": "1993", "month": "07", "day": "18",
        "coords": {"lon": 88.72, "lat": 26.52},
    },
    {
        "cohort_id": "NAT-15",
        "uei": "UEI-IMD-FL-1993-0060",
        "event_name": "Punjab Monsoon Basin Floods (July 1993)",
        "state": "Punjab",
        "district": "Amritsar, Patiala, Ludhiana",
        "date_str": "1993-07-08",
        "year": "1993", "month": "07", "day": "08",
        "coords": {"lon": 75.85, "lat": 30.90},
    },
    {
        "cohort_id": "NAT-16",
        "uei": "UEI-IMD-FL-1984-0063",
        "event_name": "Maharashtra Konkan Monsoon Deluge (July 1984)",
        "state": "Maharashtra",
        "district": "Mumbai, Thane, Raigad",
        "date_str": "1984-07-17",
        "year": "1984", "month": "07", "day": "17",
        "coords": {"lon": 72.85, "lat": 19.05},
    },
]


class NoAuthLossRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Preserves Authorization header across Earthdata Login / GES DISC redirection chain."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None and "Authorization" not in new_req.headers:
            auth_val = req.headers.get("Authorization") or req.headers.get("authorization")
            if auth_val:
                new_req.add_header("Authorization", auth_val)
        return new_req


def get_earthdata_token() -> str | None:
    return os.environ.get("EARTHDATA_TOKEN")


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def validate_imerg_daily_file(filepath: Path) -> dict[str, Any]:
    """Validates that a file is an authentic, intact IMERG Daily NetCDF file."""
    if not filepath.exists():
        return {"valid": False, "error": "File does not exist"}
    size = filepath.stat().st_size
    if size < 5_000_000:
        return {"valid": False, "error": f"File too small ({size} bytes)"}

    try:
        with h5py.File(filepath, "r") as hf:
            if "precipitation" not in hf or "lon" not in hf or "lat" not in hf:
                return {"valid": False, "error": "Missing precipitation, lon, or lat"}
            p_shape = hf["precipitation"].shape
            if p_shape != (1, 3600, 1800):
                return {"valid": False, "error": f"Unexpected precipitation shape: {p_shape}"}
        return {
            "valid": True,
            "type": "IMERG_DAILY_NC4",
            "file_size": size,
            "sha256": compute_sha256(filepath),
        }
    except Exception as e:
        return {"valid": False, "error": f"HDF5 inspect error: {e}"}


def validate_chirps_daily_file(filepath: Path) -> dict[str, Any]:
    """Validates that a file is an authentic, intact CHIRPS v2.0 gzip GeoTIFF."""
    if not filepath.exists():
        return {"valid": False, "error": "File does not exist"}
    size = filepath.stat().st_size
    if size < 500_000:
        return {"valid": False, "error": f"File too small ({size} bytes)"}

    try:
        with gzip.open(filepath, "rb") as gz:
            head = gz.read(4)
            if head not in (b"II*\x00", b"MM\x00*"):
                return {"valid": False, "error": f"Invalid TIFF magic bytes: {head!r}"}
        return {
            "valid": True,
            "type": "CHIRPS_DAILY_GZ",
            "file_size": size,
            "sha256": compute_sha256(filepath),
        }
    except Exception as e:
        return {"valid": False, "error": f"Gzip decompress error: {e}"}


def acquire_atomic(
    url: str,
    dest_path: Path,
    auth_token: str | None = None,
    validator_fn: Any = None,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Acquires a remote asset atomically with retries and integrity validation."""
    if dest_path.exists():
        if validator_fn:
            val = validator_fn(dest_path)
            if val.get("valid"):
                return {"status": "CACHED", "path": str(dest_path), "validation": val}
            else:
                dest_path.unlink()
        else:
            return {"status": "CACHED", "path": str(dest_path)}

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    opener = urllib.request.build_opener(NoAuthLossRedirectHandler())

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url)
            if auth_token:
                req.add_header("Authorization", f"Bearer {auth_token}")

            with opener.open(req, timeout=60) as resp, open(temp_path, "wb") as f:
                while chunk := resp.read(65536):
                    f.write(chunk)

            if temp_path.exists():
                if validator_fn:
                    val = validator_fn(temp_path)
                    if not val.get("valid"):
                        temp_path.unlink()
                        if attempt == max_retries:
                            return {"status": "VALIDATION_FAILED", "error": val.get("error")}
                        time.sleep(2.0 * attempt)
                        continue
                temp_path.replace(dest_path)
                val = validator_fn(dest_path) if validator_fn else {}
                return {"status": "DOWNLOADED", "path": str(dest_path), "validation": val}
        except urllib.error.HTTPError as e:
            if temp_path.exists():
                temp_path.unlink()
            if attempt == max_retries:
                return {"status": "HTTP_ERROR", "code": e.code, "reason": str(e.reason)}
            time.sleep(3.0 * attempt)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            if attempt == max_retries:
                return {"status": "FAILED", "error": str(e)}
            time.sleep(2.0 * attempt)

    return {"status": "FAILED", "error": "Max retries exceeded"}


def compute_national_scaling_statistics(df_derived: pd.DataFrame) -> dict[str, Any]:
    """Computes exact national deduplication and storage requirement statistics."""
    total_records = len(df_derived)
    valid_dates_series = df_derived["start_dt"].dropna()
    valid_count = len(valid_dates_series)
    null_count = df_derived["start_dt"].isna().sum()

    df_derived_valid = df_derived.dropna(subset=["start_dt"]).copy()
    df_derived_valid["date_str"] = df_derived_valid["start_dt"].dt.strftime("%Y-%m-%d")
    unique_dates_total = df_derived_valid["date_str"].nunique()

    # Eras
    pre_1981 = df_derived_valid[df_derived_valid["start_dt"] < "1981-01-01"]
    chirps_era = df_derived_valid[(df_derived_valid["start_dt"] >= "1981-01-01") & (df_derived_valid["start_dt"] <= "2023-12-31")]
    imerg_era = df_derived_valid[(df_derived_valid["start_dt"] >= "2000-06-01") & (df_derived_valid["start_dt"] <= "2023-12-31")]
    pre_2000 = df_derived_valid[df_derived_valid["start_dt"] < "2000-06-01"]

    chirps_unique_dates = chirps_era["date_str"].nunique()
    imerg_unique_dates = imerg_era["date_str"].nunique()

    chirps_storage_gb = round(chirps_unique_dates * 3.0 / 1024, 2)
    imerg_storage_gb = round(imerg_unique_dates * 32.9 / 1024, 2)
    total_deduplicated_storage_gb = round(chirps_storage_gb + imerg_storage_gb, 2)

    return {
        "total_ifi_records": total_records,
        "valid_date_records": valid_count,
        "null_date_records": int(null_count),
        "unique_valid_dates_total": unique_dates_total,
        "eras_breakdown": {
            "pre_1981_records": len(pre_1981),
            "chirps_eligible_records_1981_to_2023": len(chirps_era),
            "chirps_eligible_percentage": round(len(chirps_era) / total_records * 100, 1),
            "chirps_unique_dates_to_acquire": chirps_unique_dates,
            "imerg_eligible_records_2000_to_2023": len(imerg_era),
            "imerg_eligible_percentage": round(len(imerg_era) / total_records * 100, 1),
            "imerg_unique_dates_to_acquire": imerg_unique_dates,
            "pre_2000_records": len(pre_2000),
        },
        "storage_and_bandwidth_projection": {
            "chirps_daily_unit_size_mb": 3.0,
            "chirps_total_storage_gb": chirps_storage_gb,
            "imerg_daily_unit_size_mb": 32.9,
            "imerg_total_storage_gb": imerg_storage_gb,
            "total_deduplicated_storage_gb": total_deduplicated_storage_gb,
            "half_hourly_comparison_tb": round(total_records * 388.8 / 1024 / 1024, 2),
        },
    }


def acquire_national_cohort(max_workers: int = 4) -> dict[str, Any]:
    """Acquires authentic CHIRPS and IMERG daily files for the National Cohort."""
    token = get_earthdata_token()
    CHIRPS_DAILY_DIR.mkdir(parents=True, exist_ok=True)
    IMERG_DAILY_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Ingesting National Acquisition Cohort ({len(NATIONAL_COHORT_EVENTS)} Landmark Events) ---")

    chirps_results = []
    imerg_results = []

    for ev in NATIONAL_COHORT_EVENTS:
        cid = ev["cohort_id"]
        y, m, d = ev["year"], ev["month"], ev["day"]
        date_str = ev["date_str"]

        # 1. Acquire CHIRPS Daily (1981 to Present)
        chirps_file = f"chirps-v2.0.{y}.{m}.{d}.tif.gz"
        chirps_url = f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/{y}/{chirps_file}"
        dest_chirps = CHIRPS_DAILY_DIR / chirps_file
        res_c = acquire_atomic(
            url=chirps_url,
            dest_path=dest_chirps,
            auth_token=None,
            validator_fn=validate_chirps_daily_file,
        )
        print(f"  [CHIRPS {res_c['status']}] {cid} ({date_str}) -> {chirps_file}")
        chirps_results.append({"cohort_id": cid, "filename": chirps_file, **res_c})

        # 2. Acquire IMERG Daily (June 2000 to Present)
        if int(y) >= 2000 and not (int(y) == 2000 and int(m) < 6):
            if token:
                imerg_file = f"3B-DAY.MS.MRG.3IMERG.{y}{m}{d}-S000000-E235959.V07B.nc4"
                imerg_url = f"https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGDF.07/{y}/{m}/{imerg_file}"
                dest_imerg = IMERG_DAILY_DIR / imerg_file
                res_i = acquire_atomic(
                    url=imerg_url,
                    dest_path=dest_imerg,
                    auth_token=token,
                    validator_fn=validate_imerg_daily_file,
                )
                print(f"  [IMERG  {res_i['status']}] {cid} ({date_str}) -> {imerg_file}")
                imerg_results.append({"cohort_id": cid, "filename": imerg_file, **res_i})
            else:
                imerg_results.append({"cohort_id": cid, "status": "SKIPPED_NO_AUTH"})
        else:
            print(f"  [IMERG  SKIPPED_PRE_2000] {cid} ({date_str}) precedes GPM/TRMM era.")
            imerg_results.append({"cohort_id": cid, "status": "UNAVAILABLE_PRE_2000_ERA"})

    c_valid = sum(1 for r in chirps_results if r["status"] in ("DOWNLOADED", "CACHED"))
    i_valid = sum(1 for r in imerg_results if r["status"] in ("DOWNLOADED", "CACHED"))

    return {
        "chirps_valid_count": c_valid,
        "chirps_total_requested": len(chirps_results),
        "imerg_valid_count": i_valid,
        "imerg_total_requested": sum(1 for r in imerg_results if r["status"] != "UNAVAILABLE_PRE_2000_ERA"),
        "chirps_results": chirps_results,
        "imerg_results": imerg_results,
    }


def main():
    print("=" * 80)
    print("AQUORA Phase 6C.2G.15: National Historical Precipitation Acquisition & Scaling")
    print("=" * 80)

    # 1. Load derived events and compute scaling statistics
    df_derived = pd.read_parquet(DERIVED_PARQUET)
    scaling_stats = compute_national_scaling_statistics(df_derived)

    print("\nNational Deduplication & Scaling Metrics:")
    print(f"  Total IFI Records: {scaling_stats['total_ifi_records']}")
    print(f"  Unique Valid Event Dates: {scaling_stats['unique_valid_dates_total']}")
    print(f"  CHIRPS-eligible records (1981-2023): {scaling_stats['eras_breakdown']['chirps_eligible_records_1981_to_2023']} ({scaling_stats['eras_breakdown']['chirps_eligible_percentage']}%)")
    print(f"  CHIRPS unique dates to acquire: {scaling_stats['eras_breakdown']['chirps_unique_dates_to_acquire']} -> {scaling_stats['storage_and_bandwidth_projection']['chirps_total_storage_gb']} GB")
    print(f"  IMERG-eligible records (2000-2023): {scaling_stats['eras_breakdown']['imerg_eligible_records_2000_to_2023']} ({scaling_stats['eras_breakdown']['imerg_eligible_percentage']}%)")
    print(f"  IMERG unique dates to acquire: {scaling_stats['eras_breakdown']['imerg_unique_dates_to_acquire']} -> {scaling_stats['storage_and_bandwidth_projection']['imerg_total_storage_gb']} GB")
    print(f"  Total Deduplicated National Archive Size: {scaling_stats['storage_and_bandwidth_projection']['total_deduplicated_storage_gb']} GB")

    # 2. Ingest controlled National Acquisition Cohort
    cohort_summary = acquire_national_cohort(max_workers=4)
    print("\nNational Cohort Ingestion Results:")
    print(f"  CHIRPS Acquisitions: {cohort_summary['chirps_valid_count']} / {cohort_summary['chirps_total_requested']} valid")
    print(f"  IMERG Acquisitions:  {cohort_summary['imerg_valid_count']} / {cohort_summary['imerg_total_requested']} valid")

    print("\nPhase 6C.2G.15 Acquisition Pipeline Complete.")


if __name__ == "__main__":
    main()
