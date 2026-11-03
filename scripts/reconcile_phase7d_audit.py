import pandas as pd
import yaml
import hashlib
from pathlib import Path
import rasterio
from rasterio.windows import from_bounds
import numpy as np

def sha256(fname):
    h = hashlib.sha256()
    with open(fname, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

# 1. Check raw raster windows
events = [
    ('DFO_4499', 'data/raw/phase7/ground_truth/gfd/DFO_4499/DFO_4499_From_20170727_to_20170810.tif', 88.0, 89.0, 22.0, 23.0),
    ('DFO_2935', 'data/raw/phase7/ground_truth/gfd/DFO_2935/DFO_2935_From_20060728_to_20060912.tif', 73.0, 74.0, 20.0, 21.0),
    ('DFO_3372', 'data/raw/phase7/ground_truth/gfd/DFO_3372/DFO_3372_From_20080830_to_20080908.tif', 94.0, 95.0, 27.0, 28.0),
    ('DFO_2507', 'data/raw/phase7/ground_truth/gfd/DFO_2507/DFO_2507_From_20040620_to_20041007.tif', 85.0, 86.0, 25.0, 26.0),
]

print('=' * 80)
print('1. RAW RASTER COUNTS IN 1-DEGREE BOUNDING WINDOWS:')
print('=' * 80)
for name, p, min_lon, max_lon, min_lat, max_lat in events:
    with rasterio.open(p) as src:
        win = from_bounds(min_lon, min_lat, max_lon, max_lat, transform=src.transform)
        fl = src.read(1, window=win)
        cp = src.read(4, window=win)
        perm = src.read(5, window=win)
        total_cells = fl.size
        nodata = np.isnan(fl)
        valid = ~nodata
        cloud = valid & (cp < 0.70)
        perm_cells = valid & (perm == 1.0)
        flood_cells = valid & (fl == 1.0) & (perm == 0.0) & (cp >= 0.70)
        dry_cells = valid & (fl == 0.0) & (perm == 0.0) & (cp >= 0.70)
        print(f'{name:8s}: Total={total_cells:7,d} | NoData={nodata.sum():5,d} | Cloud(<0.70)={cloud.sum():5,d} | Perm={perm_cells.sum():5,d} | Flood={flood_cells.sum():6,d} | Dry={dry_cells.sum():7,d}')

# 2. Check Master and Binary Datasets
df_mst = pd.read_parquet('data/processed/phase7/ml/phase7c_multievent_dataset.parquet')
df_bin = pd.read_parquet('data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet')
df_mst_csv = pd.read_csv('data/processed/phase7/ml/phase7c_multievent_dataset.csv')
df_bin_csv = pd.read_csv('data/processed/phase7/ml/phase7c_multievent_binary_dataset.csv')

print('\n' + '=' * 80)
print(f'2. MASTER DATASET (Parquet: {len(df_mst):,d} rows | CSV: {len(df_mst_csv):,d} rows)')
print('=' * 80)
print(df_mst.groupby(['split', 'event_id', 'flood_label']).size().unstack(fill_value=0))

print('\n' + '=' * 80)
print(f'3. BINARY DATASET (Parquet: {len(df_bin):,d} rows | CSV: {len(df_bin_csv):,d} rows)')
print('=' * 80)
print(df_bin.groupby(['split', 'event_id', 'flood_label']).size().unstack(fill_value=0))

# 3. Check Packaged files
pkg_dir = Path('data/packages/phase7d_kaggle_dataset')
df_pkg_bin = pd.read_parquet(pkg_dir / 'phase7c_multievent_binary_dataset.parquet')
df_pkg_mst = pd.read_parquet(pkg_dir / 'phase7c_multievent_dataset.parquet')
df_pkg_bin_csv = pd.read_csv(pkg_dir / 'phase7c_multievent_binary_dataset.csv')
df_pkg_mst_csv = pd.read_csv(pkg_dir / 'phase7c_multievent_dataset.csv')

print('\n' + '=' * 80)
print('4. PACKAGED FILES VERIFICATION:')
print('=' * 80)
print(f'Package Binary Parquet: {len(df_pkg_bin):,d} rows | CSV: {len(df_pkg_bin_csv):,d} rows')
print(f'Package Master Parquet: {len(df_pkg_mst):,d} rows | CSV: {len(df_pkg_mst_csv):,d} rows')
assert len(df_pkg_bin) == len(df_bin) == len(df_bin_csv) == len(df_pkg_bin_csv) == 207205
assert len(df_pkg_mst) == len(df_mst) == len(df_mst_csv) == len(df_pkg_mst_csv) == 209116
print('>>> Packaged datasets match prepared datasets row-for-row.')

# 4. Check Manifests
with open('data/manifests/phase7c_multievent_dataset_manifest.yaml') as f:
    m_7c = yaml.safe_load(f)
with open('data/manifests/phase7d_kaggle_dataset_manifest.yaml') as f:
    m_7d = yaml.safe_load(f)

print('\n' + '=' * 80)
print('5. MANIFEST RECONCILIATION:')
print('=' * 80)
print(f"Manifest 7C Master samples: {m_7c['master_dataset']['total_rows']:,d}")
print(f"Manifest 7C Binary samples: {m_7c['binary_dataset']['total_rows']:,d}")
print(f"Manifest 7D Master samples: {m_7d['dataset_structure']['master_dataset_rows']:,d}")
print(f"Manifest 7D Binary samples: {m_7d['dataset_structure']['binary_dataset_rows']:,d}")
print(f"Manifest 7D Test Binary samples: {m_7d['split_summary']['test']['binary_samples']:,d}")
print(f"Manifest 7D Test Flood: {m_7d['split_summary']['test']['flood_samples']:,d}")
print(f"Manifest 7D Test Dry: {m_7d['split_summary']['test']['dry_samples']:,d}")

# 5. Checksum Reconciliation
print('\n' + '=' * 80)
print('6. CHECKSUM RECONCILIATION:')
print('=' * 80)
files_to_hash = [
    ('Prepared Binary Parquet', 'data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet'),
    ('Packaged Binary Parquet', 'data/packages/phase7d_kaggle_dataset/phase7c_multievent_binary_dataset.parquet'),
    ('Prepared Master Parquet', 'data/processed/phase7/ml/phase7c_multievent_dataset.parquet'),
    ('Packaged Master Parquet', 'data/packages/phase7d_kaggle_dataset/phase7c_multievent_dataset.parquet'),
    ('Prepared Binary CSV', 'data/processed/phase7/ml/phase7c_multievent_binary_dataset.csv'),
    ('Packaged Binary CSV', 'data/packages/phase7d_kaggle_dataset/phase7c_multievent_binary_dataset.csv'),
    ('Prepared Master CSV', 'data/processed/phase7/ml/phase7c_multievent_dataset.csv'),
    ('Packaged Master CSV', 'data/packages/phase7d_kaggle_dataset/phase7c_multievent_dataset.csv'),
]

for label, p in files_to_hash:
    sz = Path(p).stat().st_size
    h = sha256(p)
    print(f'{label:24s}: {sz:10,d} bytes | SHA256: {h}')

# Assert packaged and prepared hashes match exactly
assert sha256('data/processed/phase7/ml/phase7c_multievent_binary_dataset.parquet') == sha256('data/packages/phase7d_kaggle_dataset/phase7c_multievent_binary_dataset.parquet')
assert sha256('data/processed/phase7/ml/phase7c_multievent_dataset.parquet') == sha256('data/packages/phase7d_kaggle_dataset/phase7c_multievent_dataset.parquet')
assert sha256('data/processed/phase7/ml/phase7c_multievent_binary_dataset.csv') == sha256('data/packages/phase7d_kaggle_dataset/phase7c_multievent_binary_dataset.csv')
assert sha256('data/processed/phase7/ml/phase7c_multievent_dataset.csv') == sha256('data/packages/phase7d_kaggle_dataset/phase7c_multievent_dataset.csv')
print('\n>>> All prepared and packaged file hashes match with 100% cryptographic parity.')
