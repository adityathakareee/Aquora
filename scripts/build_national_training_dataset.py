"""
AQUORA Phase 3 — National Training Dataset Generation CLI Script.

Extracts multiscale features for sample coordinates across Indian pilot domains,
applies strict label filtering, isolates unknown (-1) labels, and generates
the Parquet datasets and provenance manifest.
"""

import sys
from pathlib import Path

# Add project root and backend to python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

from ml.dataset_generator import NationalDatasetGenerator


def main():
    print("=" * 60)
    print("AQUORA PHASE 3: NATIONAL SCREENING DATASET GENERATION")
    print("=" * 60)

    # Multi-basin pilot sample points (Ganga, Brahmaputra, Godavari, Narmada, Mithi)
    sample_definitions = [
        {"sample_id": "pt_ganga_01", "latitude": 25.60, "longitude": 85.15, "flood_label": -1, "label_source": "NO_COINCIDENT_SAR_PASS"},
        {"sample_id": "pt_ganga_02", "latitude": 25.62, "longitude": 85.18, "flood_label": -1, "label_source": "NO_COINCIDENT_SAR_PASS"},
        {"sample_id": "pt_brahma_01", "latitude": 26.15, "longitude": 91.75, "flood_label": -1, "label_source": "NO_COINCIDENT_SAR_PASS"},
        {"sample_id": "pt_brahma_02", "latitude": 26.18, "longitude": 91.78, "flood_label": -1, "label_source": "NO_COINCIDENT_SAR_PASS"},
        {"sample_id": "pt_godavari_01", "latitude": 19.98, "longitude": 73.80, "flood_label": -1, "label_source": "NO_COINCIDENT_SAR_PASS"},
        {"sample_id": "pt_godavari_02", "latitude": 20.00, "longitude": 73.82, "flood_label": -1, "label_source": "NO_COINCIDENT_SAR_PASS"},
        {"sample_id": "pt_narmada_01", "latitude": 21.70, "longitude": 73.00, "flood_label": -1, "label_source": "NO_COINCIDENT_SAR_PASS"},
        {"sample_id": "pt_narmada_02", "latitude": 21.72, "longitude": 73.03, "flood_label": -1, "label_source": "NO_COINCIDENT_SAR_PASS"},
        {"sample_id": "pt_mithi_01", "latitude": 19.076, "longitude": 72.877, "flood_label": -1, "label_source": "INSUFFICIENT_EVIDENCE"},
        {"sample_id": "pt_mithi_02", "latitude": 19.080, "longitude": 72.880, "flood_label": -1, "label_source": "INSUFFICIENT_EVIDENCE"},
    ]

    generator = NationalDatasetGenerator()
    df_master, df_supervised, manifest = generator.build_dataset_from_samples(
        samples=sample_definitions,
        dataset_name="national_screening_pilot",
        allow_benchmark_rainfall=True,
    )

    print(f"\n[SUMMARY] Master dataset rows extracted: {len(df_master)}")
    print(f"[SUMMARY] Supervised dataset rows: {len(df_supervised)}")
    print(f"[SUMMARY] Unknown (-1) labels excluded: {manifest['sample_accounting']['label_breakdown']['unknown_unobserved_minus1']}")
    print(f"[STATUS] Supervised data ready for training: {manifest['authenticity_declaration']['supervised_data_ready']}")
    print(f"[OUTPUT] Master Parquet: {manifest['output_files']['master_parquet']}")
    print(f"[OUTPUT] Supervised Parquet: {manifest['output_files']['supervised_parquet']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
