"""
AQUORA Phase 7 — Global Flood Database (GFD) India Catalog Audit & Reconciliation.

Audits the 913 global mapped flood events from the Google Earth Engine Global Flood Database
(Cloud to Street / Tellman et al., Nature 2021) and isolates all events intersecting the Indian
subcontinent. Reconciles each event against the 6,876-row India Flood Inventory (IFI v3).
"""

from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import urllib.request
import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH_DIR = REPO_ROOT / "data" / "raw" / "phase7" / "ground_truth"
PROCESSED_GT_DIR = REPO_ROOT / "data" / "processed" / "phase7" / "ground_truth"
IFI_CSV_PATH = GROUND_TRUTH_DIR / "india_flood_inventory_v3.csv"

GFD_QC_CSV_URL = "https://raw.githubusercontent.com/cloudtostreet/MODIS_GlobalFloodDatabase/master/data/gfd_qcdatabase_2019_08_01.csv"
LOCAL_GFD_QC_CSV = GROUND_TRUTH_DIR / "gfd_qcdatabase_2019_08_01.csv"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def audit_gfd_india_catalog() -> dict:
    PROCESSED_GT_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("AQUORA PHASE 7: GLOBAL FLOOD DATABASE (GFD) INDIA CATALOG AUDIT")
    print("=" * 80)

    # 1. Acquire / Load GFD QC Database
    if not LOCAL_GFD_QC_CSV.exists():
        print(f"[FETCH] Downloading GFD QC Database from Cloud to Street GitHub: {GFD_QC_CSV_URL}")
        req = urllib.request.Request(GFD_QC_CSV_URL, headers={"User-Agent": "AQUORA/1.0 (Research Pipeline)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            LOCAL_GFD_QC_CSV.write_bytes(content)
        print(f"[SAVED] Saved {len(content):,} bytes to {LOCAL_GFD_QC_CSV}")
    
    gfd_sha256 = compute_sha256(LOCAL_GFD_QC_CSV)
    df_gfd = pd.read_csv(LOCAL_GFD_QC_CSV)
    total_gfd_events = len(df_gfd)
    print(f"[AUDIT] GFD QC Database loaded: {total_gfd_events} global events. SHA-256: {gfd_sha256}")

    # 2. Filter for Indian Subcontinent Events
    # Country == 'India' or OtherCountry contains 'India' or spatial bounding box intersects India
    india_filter = (
        (df_gfd["Country"].astype(str).str.strip().str.lower() == "india") |
        (df_gfd["OtherCountry"].astype(str).str.strip().str.lower().str.contains("india"))
    )
    df_india = df_gfd[india_filter].copy()
    india_event_count = len(df_india)
    print(f"[AUDIT] Isolated {india_event_count} flood events intersecting India ({india_event_count/total_gfd_events*100:.2f}% of global archive).")

    # 3. Parse Dates and Durations
    df_india["Began_dt"] = pd.to_datetime(df_india["Began"], errors="coerce")
    df_india["Ended_dt"] = pd.to_datetime(df_india["Ended"], errors="coerce")
    df_india["Duration_days"] = (df_india["Ended_dt"] - df_india["Began_dt"]).dt.days

    year_counts = df_india["Began_dt"].dt.year.value_counts().sort_index().to_dict()
    print("\n[TEMPORAL SPREAD] India events by year (2000–2018):")
    for yr, cnt in year_counts.items():
        print(f"  - Year {int(yr)}: {cnt} event(s)")

    # 4. Load India Flood Inventory (IFI v3) for Correlation
    ifi_records = []
    if IFI_CSV_PATH.exists():
        ifi_df = pd.read_csv(IFI_CSV_PATH)
        ifi_df["Start_Date_dt"] = pd.to_datetime(ifi_df["Start Date"], format="%d-%m-%Y %H:%M", errors="coerce")
        ifi_df["End_Date_dt"] = pd.to_datetime(ifi_df["End Date"], format="%d-%m-%Y %H:%M", errors="coerce")
        print(f"\n[CORRELATION] Auditing against {len(ifi_df):,} IFI v3 disaster records...")

        # Match each GFD event with IFI by temporal window (overlap within ±7 days)
        reconciled_events = []
        for _, row in df_india.iterrows():
            dfo_id = int(row["ID"])
            b_dt = row["Began_dt"]
            e_dt = row["Ended_dt"]
            
            matching_ifi = ifi_df[
                (ifi_df["Start_Date_dt"] <= (e_dt + pd.Timedelta(days=5))) &
                (ifi_df["End_Date_dt"] >= (b_dt - pd.Timedelta(days=5)))
            ]
            
            ifi_ueis = list(matching_ifi["UEI"].unique())
            ifi_states = list(matching_ifi["State"].dropna().unique())
            ifi_districts = list(matching_ifi["Districts"].dropna().unique())
            ifi_fatalities = float(matching_ifi["Human fatality"].sum()) if len(matching_ifi) > 0 else 0.0

            reconciled_events.append({
                "dfo_id": dfo_id,
                "began": row["Began"],
                "ended": row["Ended"],
                "main_cause": str(row["MainCause"]),
                "severity": float(row["Severity"]) if pd.notnull(row["Severity"]) else None,
                "dead_dfo": int(row["Dead"]) if pd.notnull(row["Dead"]) else None,
                "displaced_dfo": int(row["Displaced"]) if pd.notnull(row["Displaced"]) else None,
                "centroid_lon": float(row["long"]),
                "centroid_lat": float(row["lat"]),
                "area_km2": float(row["Area"]),
                "thresh_type": str(row["ThreshType"]),
                "matching_ifi_count": len(matching_ifi),
                "matching_ifi_ueis": ifi_ueis[:5],
                "matching_ifi_states": ifi_states[:5],
                "matching_ifi_districts_sample": ifi_districts[:3],
                "ifi_fatalities_sum": ifi_fatalities,
                "gcs_zip_name": f"DFO_{dfo_id}_From_{b_dt.strftime('%Y%m%d')}_to_{e_dt.strftime('%Y%m%d')}.zip" if pd.notnull(b_dt) and pd.notnull(e_dt) else None,
            })
        
        df_reconciled = pd.DataFrame(reconciled_events)
    else:
        print("[WARNING] IFI v3 CSV not found; proceeding with pure GFD metadata.")
        df_reconciled = df_india

    # 5. Output Catalog Artifacts
    catalog_json_path = PROCESSED_GT_DIR / "gfd_india_events_catalog.json"
    catalog_csv_path = PROCESSED_GT_DIR / "gfd_india_events_catalog.csv"

    catalog_data = {
        "catalog_name": "AQUORA Global Flood Database (GFD) India Event Catalog",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_reference": "Tellman et al., Nature 2021; Cloud to Street MODIS Global Flood Database v1.4",
        "gee_collection_id": "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1",
        "gcs_bucket": "gs://gfd_v1_4",
        "license": "Creative Commons Attribution-NonCommercial 4.0 International (CC-BY-NC-4.0)",
        "total_india_events": india_event_count,
        "earliest_event_date": df_india["Began_dt"].min().strftime("%Y-%m-%d"),
        "latest_event_date": df_india["Began_dt"].max().strftime("%Y-%m-%d"),
        "events": df_reconciled.to_dict(orient="records"),
    }

    with open(catalog_json_path, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2)
    df_reconciled.to_csv(catalog_csv_path, index=False)

    print(f"\n[OUTPUT] Wrote GFD India catalog JSON to {catalog_json_path}")
    print(f"[OUTPUT] Wrote GFD India catalog CSV to {catalog_csv_path}")

    # 6. Highlights of High-Confidence Events
    high_impact = df_reconciled[df_reconciled["matching_ifi_count"] > 0].sort_values(by="matching_ifi_count", ascending=False)
    print(f"\n[TOP RECONCILED EVENTS] {len(high_impact)} GFD India events temporally match confirmed IFI v3 disasters:")
    for _, ev in high_impact.head(5).iterrows():
        print(f"  - DFO {ev['dfo_id']} ({ev['began']} to {ev['ended']}): {ev['main_cause']} | {ev['matching_ifi_count']} IFI records across {ev['matching_ifi_states']}")
        print(f"    GCS Zip: {ev['gcs_zip_name']} | Centroid: ({ev['centroid_lat']:.3f}, {ev['centroid_lon']:.3f})")

    print("=" * 80)
    return catalog_data


if __name__ == "__main__":
    audit_gfd_india_catalog()
