"""
AQUORA Phase 3 — National Flood Screening Model Training CLI.

Orchestrates supervised model training using NationalScreeningTrainingPipeline.
Enforces zero-fabrication: halts training honestly if labeled data is insufficient.
"""

import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT))

from ml.training_pipeline import NationalScreeningTrainingPipeline, DataSufficiencyError


def main():
    print("=" * 60)
    print("AQUORA PHASE 3: NATIONAL SCREENING MODEL TRAINING")
    print("=" * 60)

    dataset_path = PROJECT_ROOT / "data" / "processed" / "ml" / "national_screening" / "national_screening_pilot_master.parquet"

    if not dataset_path.exists():
        print(f"[ERROR] Dataset not found at {dataset_path}. Please run scripts/build_national_training_dataset.py first.")
        sys.exit(1)

    df = pd.read_parquet(dataset_path)
    print(f"[INPUT] Loaded {len(df)} samples from {dataset_path}")

    pipeline = NationalScreeningTrainingPipeline()

    try:
        result = pipeline.train_and_evaluate(df)
        print("\n[SUCCESS] Model training and spatial cross-validation complete!")
        print(f"[ARTIFACT] Saved model to: {result['artifact_file']}")
        print(f"[METRICS] Out-of-Fold PR-AUC: {result['metadata']['aggregate_oof_metrics']['pr_auc']}")
    except DataSufficiencyError as dse:
        print("\n[DATA QUALITY GATE BLOCKED — HONEST AUDIT]")
        print(f"[REASON] {str(dse)}")
        print("[POLICY] Model remains in 'NOT_TRAINED' status. Zero-fabrication prohibits synthetic labeling.")
        print("=" * 60)


if __name__ == "__main__":
    main()
