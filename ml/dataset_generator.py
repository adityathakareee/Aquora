"""
AQUORA Phase 3 — National Flood Screening Dataset Generator.

Generates reproducible, provenance-aware tabular Parquet datasets for
national flood screening model training using the Phase 2E IndiaFeaturePipelineService.

GOVERNANCE RULES:
1. Exactly the 11 CORE_NATIONAL features in governed order.
2. Regional and Deep-Zone exclusive features are strictly excluded from the predictor matrix.
3. Labels and label metadata are isolated in separate columns, NEVER in features.
4. Unknown labels (flood_label == -1) are excluded from the supervised training split.
5. Never silently converts missing values to zero.
6. Generates full audit provenance tracking total rows, class breakdown, and exclusions.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import structlog

from app.services.india_feature_pipeline import IndiaFeaturePipelineService
from app.services.india_spatial_service import IndiaSpatialService

logger = structlog.get_logger("aquora.ml.dataset_generator")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DATA_DIR = PROJECT_ROOT / "data" / "processed" / "ml" / "national_screening"


class NationalDatasetGenerator:
    """
    Builds training and evaluation Parquet datasets for the National Screening Model.
    """

    CORE_11_PREDICTORS: List[str] = [
        "rainfall_1h_mm",
        "rainfall_3h_mm",
        "rainfall_6h_mm",
        "rainfall_24h_mm",
        "rainfall_72h_mm",
        "rainfall_anomaly_index",
        "elevation_m",
        "slope_deg",
        "distance_to_river_m",
        "historical_flood_frequency",
        "landcover_class",
    ]

    METADATA_COLUMNS: List[str] = [
        "sample_id",
        "latitude",
        "longitude",
        "basin_id",
        "basin_name",
        "state_code",
        "zone_tier",
        "observation_timestamp",
        "extraction_timestamp",
    ]

    LABEL_COLUMNS: List[str] = [
        "flood_label",  # 1 = positive flood, 0 = defensible dry, -1 = unobserved/unknown
        "label_source",
        "label_confidence",
        "sar_scene_id",
        "sar_delta_vv_db",
    ]

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DATA_DIR
        self.pipeline_service = IndiaFeaturePipelineService()

    def extract_sample_row(
        self,
        sample_id: str,
        latitude: float,
        longitude: float,
        timestamp: Optional[datetime] = None,
        flood_label: int = -1,
        label_source: str = "UNOBSERVED",
        label_confidence: Optional[float] = None,
        sar_scene_id: Optional[str] = None,
        sar_delta_vv_db: Optional[float] = None,
        allow_benchmark_rainfall: bool = False,
        feature_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract a single fully governed row adhering to the 11-feature core schema.
        """
        pt_res = self.pipeline_service.extract_point_features(
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            allow_benchmark_rainfall=allow_benchmark_rainfall,
            include_candidate_target=False,
        )

        # Resolve hydrographic basin for spatial grouping
        basin_info = IndiaSpatialService.get_river_basin(latitude, longitude)
        basin_id = basin_info.get("basin_id", "UNKNOWN_BASIN") if basin_info else "UNKNOWN_BASIN"
        basin_name = basin_info.get("basin_name", "Unknown Basin") if basin_info else "Unknown Basin"

        # Resolve administrative state
        admin_info = IndiaSpatialService.get_administrative_entity(latitude, longitude)
        state_code = admin_info.get("state_code", "UNKNOWN_STATE") if admin_info else "UNKNOWN_STATE"

        row: Dict[str, Any] = {
            "sample_id": sample_id,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "basin_id": basin_id,
            "basin_name": basin_name,
            "state_code": state_code,
            "zone_tier": pt_res.zone_tier,
            "observation_timestamp": timestamp.isoformat() if timestamp else None,
            "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 11 Core predictors only
        for col in self.CORE_11_PREDICTORS:
            row[col] = pt_res.features.get(col)

        # Apply feature overrides if explicitly provided (e.g. for testing / fixtures)
        if feature_overrides is not None:
            for col in self.CORE_11_PREDICTORS:
                if col in feature_overrides:
                    row[col] = feature_overrides[col]

        # Isolated label boundary
        row["flood_label"] = int(flood_label)
        row["label_source"] = str(label_source)
        row["label_confidence"] = float(label_confidence) if label_confidence is not None else None
        row["sar_scene_id"] = sar_scene_id
        row["sar_delta_vv_db"] = float(sar_delta_vv_db) if sar_delta_vv_db is not None else None

        return row

    def build_dataset_from_samples(
        self,
        samples: List[Dict[str, Any]],
        dataset_name: str = "national_screening_pilot",
        allow_benchmark_rainfall: bool = False,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """
        Process a list of sample definitions into:
        1. Master dataset (all samples including -1 unobserved)
        2. Supervised dataset (strictly filtered to flood_label in (0, 1))
        3. Comprehensive audit manifest with exclusion accounting
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: List[Dict[str, Any]] = []

        total_requested = len(samples)
        excluded_missing_coords = 0

        for i, s in enumerate(samples):
            lat = s.get("latitude")
            lon = s.get("longitude")
            if lat is None or lon is None:
                excluded_missing_coords += 1
                continue

            sample_id = s.get("sample_id", f"sample_{i:06d}")
            ts = s.get("timestamp")
            fl = s.get("flood_label", -1)
            ls = s.get("label_source", "UNOBSERVED")
            lc = s.get("label_confidence")
            sid = s.get("sar_scene_id")
            sdelta = s.get("sar_delta_vv_db")
            feat_ov = s.get("features")

            row = self.extract_sample_row(
                sample_id=sample_id,
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                flood_label=fl,
                label_source=ls,
                label_confidence=lc,
                sar_scene_id=sid,
                sar_delta_vv_db=sdelta,
                allow_benchmark_rainfall=allow_benchmark_rainfall,
                feature_overrides=feat_ov,
            )
            rows.append(row)

        df_master = pd.DataFrame(rows)

        # Enforce column order and nullable dtypes
        ordered_cols = self.METADATA_COLUMNS + self.CORE_11_PREDICTORS + self.LABEL_COLUMNS
        for col in ordered_cols:
            if col not in df_master.columns:
                df_master[col] = None
        df_master = df_master[ordered_cols]

        # Explicit nullable types
        df_master["landcover_class"] = pd.to_numeric(df_master["landcover_class"], errors="coerce").round().astype("Int32")
        df_master["flood_label"] = pd.to_numeric(df_master["flood_label"], errors="coerce").fillna(-1).astype("int32")
        float_cols = [c for c in self.CORE_11_PREDICTORS if c != "landcover_class"]
        for c in float_cols:
            df_master[c] = pd.to_numeric(df_master[c], errors="coerce").astype("float64")

        # Supervised Split: STRICTLY EXCLUDE flood_label == -1
        df_supervised = df_master[df_master["flood_label"].isin([0, 1])].copy()

        # Audit and label counts
        total_rows = len(df_master)
        positive_count = int((df_master["flood_label"] == 1).sum())
        negative_count = int((df_master["flood_label"] == 0).sum())
        unknown_count = int((df_master["flood_label"] == -1).sum())
        other_excluded = int((~df_master["flood_label"].isin([-1, 0, 1])).sum())

        supervised_rows = len(df_supervised)
        unique_basins = list(df_supervised["basin_id"].unique()) if supervised_rows > 0 else []

        # Save files
        master_path = self.output_dir / f"{dataset_name}_master.parquet"
        supervised_path = self.output_dir / f"{dataset_name}_supervised.parquet"
        manifest_path = self.output_dir / f"{dataset_name}_manifest.json"

        df_master.to_parquet(master_path, engine="pyarrow", compression="snappy", index=False)
        df_supervised.to_parquet(supervised_path, engine="pyarrow", compression="snappy", index=False)

        manifest = {
            "dataset_name": dataset_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0.0",
            "feature_count": len(self.CORE_11_PREDICTORS),
            "predictor_features": self.CORE_11_PREDICTORS,
            "sample_accounting": {
                "total_requested": total_requested,
                "total_extracted": total_rows,
                "excluded_invalid_coords": excluded_missing_coords,
                "label_breakdown": {
                    "flood_positive_1": positive_count,
                    "flood_negative_0": negative_count,
                    "unknown_unobserved_minus1": unknown_count,
                    "invalid_labels_excluded": other_excluded,
                },
                "supervised_training_rows": supervised_rows,
                "pct_unknown_excluded": round((unknown_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0,
            },
            "spatial_groups": {
                "supervised_basin_count": len(unique_basins),
                "supervised_basins": unique_basins,
            },
            "authenticity_declaration": {
                "benchmark_rainfall_used": allow_benchmark_rainfall,
                "zero_fabrication_policy": "Unknown labels (-1) strictly excluded from supervised training. Stable SAR is never converted to non-flood.",
                "supervised_data_ready": (supervised_rows > 0 and positive_count > 0 and negative_count > 0 and len(unique_basins) >= 2),
            },
            "output_files": {
                "master_parquet": str(master_path),
                "supervised_parquet": str(supervised_path),
            },
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return df_master, df_supervised, manifest

    def build_dataset_dataframe(
        self,
        samples: List[Dict[str, Any]],
        dataset_name: str = "test_dataset",
        allow_benchmark_rainfall: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Convenience method returning (df_supervised, audit_summary)."""
        _, df_supervised, manifest = self.build_dataset_from_samples(
            samples, dataset_name=dataset_name, allow_benchmark_rainfall=allow_benchmark_rainfall
        )
        accounting = manifest.get("sample_accounting", {})
        summary = {
            "excluded_unknown_labels": accounting.get("label_breakdown", {}).get("unknown_unobserved_minus1", 0),
            "positive_label_count": accounting.get("label_breakdown", {}).get("flood_positive_1", 0),
            "negative_label_count": accounting.get("label_breakdown", {}).get("flood_negative_0", 0),
            "total_supervised_rows": accounting.get("supervised_training_rows", 0),
        }
        return df_supervised, summary


# Governed alias
NationalScreeningDatasetGenerator = NationalDatasetGenerator
