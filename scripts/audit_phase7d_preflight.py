import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

master_p = REPO_ROOT / 'data/processed/phase7/ml/phase7c_multievent_dataset.parquet'
binary_p = REPO_ROOT / 'data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet'
pilot_p = REPO_ROOT / 'data/processed/phase7/ml/phase7_gfd_pilot_dataset.parquet'
manifest_p = REPO_ROOT / 'data/manifests/phase7c_multievent_dataset_manifest.yaml'
schema_p = REPO_ROOT / 'ml/aquora_ml_feature_schema_v1.json'

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

print("=" * 70)
print("PHASE 7D PREFLIGHT DATASET AUDIT")
print("=" * 70)

# 1. File checks & Hashes
print(f"Master Parquet: {master_p.name} ({master_p.stat().st_size:,} bytes | SHA-256: {compute_sha256(master_p)})")
print(f"Binary Parquet: {binary_p.name} ({binary_p.stat().st_size:,} bytes | SHA-256: {compute_sha256(binary_p)})")
print(f"Pilot Parquet preserved: {pilot_p.name} ({pilot_p.stat().st_size:,} bytes | SHA-256: {compute_sha256(pilot_p)})")

df_master = pd.read_parquet(master_p)
df_binary = pd.read_parquet(binary_p)

print("\n--- MASTER DATASET SUMMARY ---")
print(f"Total Rows: {len(df_master)}, Columns: {len(df_master.columns)}")
print("Events:")
print(df_master["event_id"].value_counts())
print("\nLabels:")
print(df_master["flood_label"].value_counts())
print("\nEvent x Label:")
print(pd.crosstab(df_master["event_id"], df_master["flood_label"]))
print("\nSplit x Event:")
print(pd.crosstab(df_master["split"], df_master["event_id"]))

print("\n--- BINARY DATASET SUMMARY ---")
print(f"Total Rows: {len(df_binary)}, Columns: {len(df_binary.columns)}")
print("Labels:")
print(df_binary["flood_label"].value_counts())
print("\nSplit x Label:")
print(pd.crosstab(df_binary["split"], df_binary["flood_label"]))
print("\nEvent x Label:")
print(pd.crosstab(df_binary["event_id"], df_binary["flood_label"]))

print("\n--- FEATURE INTEGRITY & SCHEMA COMPLIANCE ---")
with open(schema_p) as f:
    schema = json.load(f)
core_features = schema["tiers"]["CORE_NATIONAL"]["features"]

for feat in core_features:
    n_null = df_binary[feat].isnull().sum()
    n_inf = np.isinf(df_binary[feat].dropna()).sum()
    dtype = df_binary[feat].dtype
    val_min = df_binary[feat].min()
    val_max = df_binary[feat].max()
    val_std = df_binary[feat].std()
    print(f"  {feat:<28} | dtype: {str(dtype):<8} | nulls: {n_null:<5} | infs: {n_inf:<2} | min: {val_min:8.2f} | max: {val_max:8.2f} | std: {val_std:8.2f}")

print("\n--- DUPLICATES & COORDINATE LEAKAGE CHECK ---")
dup_coords_master = df_master.duplicated(subset=["latitude", "longitude"]).sum()
dup_coords_binary = df_binary.duplicated(subset=["latitude", "longitude"]).sum()
print(f"Duplicate coordinates in master: {dup_coords_master}")
print(f"Duplicate coordinates in binary: {dup_coords_binary}")

# Check cross-split coordinate overlap
train_coords = set(zip(df_binary[df_binary["split"] == "train"]["latitude"], df_binary[df_binary["split"] == "train"]["longitude"]))
val_coords = set(zip(df_binary[df_binary["split"] == "validation"]["latitude"], df_binary[df_binary["split"] == "validation"]["longitude"]))
test_coords = set(zip(df_binary[df_binary["split"] == "test"]["latitude"], df_binary[df_binary["split"] == "test"]["longitude"]))

print(f"Train / Val coordinate overlap: {len(train_coords.intersection(val_coords))}")
print(f"Train / Test coordinate overlap: {len(train_coords.intersection(test_coords))}")
print(f"Val / Test coordinate overlap: {len(val_coords.intersection(test_coords))}")

# Check event separation
train_events = set(df_binary[df_binary["split"] == "train"]["event_id"])
val_events = set(df_binary[df_binary["split"] == "validation"]["event_id"])
test_events = set(df_binary[df_binary["split"] == "test"]["event_id"])
print(f"Train Events: {train_events}")
print(f"Val Events: {val_events}")
print(f"Test Events: {test_events}")
print(f"Disjoint splits check: {len(train_events.intersection(val_events)) == 0 and len(train_events.intersection(test_events)) == 0 and len(val_events.intersection(test_events)) == 0}")
