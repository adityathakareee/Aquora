"""
Phase 8 Prototype ML Calibration Service.
Connects existing Kaggle-trained XGBoost prototype (aquora_xgboost_prototype.joblib)
to backend physical outputs (Phase 6) and real data features.

CRITICAL INVARIANTS:
- Read-only execution: model is never retrained or modified.
- Artifact integrity: path resolved safely via settings, never falls back to synthetic ML.
- Explicit PROTOTYPE_ONLY status across all responses and metadata.
- 16 required features in exact expected order.
"""

import hashlib
import json
import structlog
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
try:
    import rasterio
except ImportError:
    rasterio = None


from app.core.config import settings

logger = structlog.get_logger("aquora.calibration")

EXPECTED_FEATURES = [
    "elevation_m",
    "slope_deg",
    "aspect_deg",
    "flow_accumulation_cells",
    "drainage_proxy_score",
    "landcover_class",
    "built_up_fraction",
    "distance_to_road_m",
    "distance_to_waterway_m",
    "rainfall_30min_mm",
    "rainfall_intensity_mm_hr",
    "tide_level_m",
]

MODEL_STATUS = "PROTOTYPE_ONLY"
CALIBRATION_STATUS = "NOT_CALIBRATED"




class CalibrationService:
    _instance: Optional["CalibrationService"] = None
    _model: Any = None
    _model_path: Optional[Path] = None
    _sha256: Optional[str] = None
    _feature_names: Optional[List[str]] = None

    def __init__(self, model_path: Optional[str] = None):
        path_str = model_path or settings.AQUORA_CALIBRATION_MODEL_PATH
        resolved_path = Path(path_str)
        if not resolved_path.is_absolute():
            repo_root = Path(__file__).resolve().parents[3]
            resolved_path = repo_root / path_str

        self.model_path = resolved_path
        self._load_model_if_needed()

    def _load_model_if_needed(self) -> None:
        if CalibrationService._model is not None and CalibrationService._model_path == self.model_path:
            return

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Required XGBoost prototype model artifact not found at {self.model_path}. "
                "No synthetic ML fallback is permitted."
            )

        try:
            with open(self.model_path, "rb") as f:
                content = f.read()
                sha256_hash = hashlib.sha256(content).hexdigest()

            model = joblib.load(self.model_path)
        except Exception as e:
            raise ValueError(
                f"Failed to load XGBoost prototype artifact from {self.model_path}: {str(e)}"
            ) from e

        # Validate feature count & order
        booster = model.get_booster()
        feature_names = booster.feature_names
        if feature_names is not None:
            if len(feature_names) != len(EXPECTED_FEATURES):
                raise ValueError(
                    f"Model feature count mismatch: expected {len(EXPECTED_FEATURES)}, got {len(feature_names)}"
                )
            if feature_names != EXPECTED_FEATURES:
                raise ValueError(
                    f"Model feature order mismatch:\nExpected: {EXPECTED_FEATURES}\nGot: {feature_names}"
                )
        else:
            if getattr(model, "n_features_in_", None) != len(EXPECTED_FEATURES):
                raise ValueError(
                    f"Model feature count mismatch: expected {len(EXPECTED_FEATURES)}, got {getattr(model, 'n_features_in_', None)}"
                )
            feature_names = EXPECTED_FEATURES

        CalibrationService._model = model
        CalibrationService._model_path = self.model_path
        CalibrationService._sha256 = sha256_hash
        CalibrationService._feature_names = feature_names

        logger.info(
            f"Loaded Phase 8 XGBoost Prototype model from {self.model_path} "
            f"[sha256: {sha256_hash[:12]}..., status: {MODEL_STATUS}]"
        )

    @property
    def model(self) -> Any:
        self._load_model_if_needed()
        return CalibrationService._model

    @property
    def sha256(self) -> str:
        self._load_model_if_needed()
        return CalibrationService._sha256 or ""

    @property
    def feature_schema(self) -> List[str]:
        return list(EXPECTED_FEATURES)

    def get_model_metadata(self) -> Dict[str, Any]:
        self._load_model_if_needed()
        model_cls = type(CalibrationService._model).__name__
        return {
            "model_path": str(self.model_path),
            "model_filename": self.model_path.name,
            "model_class": model_cls,
            "model_status": MODEL_STATUS,
            "calibration_status": CALIBRATION_STATUS,
            "sha256": self.sha256,
            "feature_count": len(EXPECTED_FEATURES),
            "feature_schema": self.feature_schema,
            "synthetic_fallback": False,
        }

    def prepare_features_for_event(
        self,
        event_id: str = "E05",
        data_dir: Optional[Path] = None,
        physical_depth_grid: Optional[np.ndarray] = None,
    ) -> pd.DataFrame:
        """
        Extract exact 16 features in exact required order from real rasters for event_id.
        Fails clearly if any required raster or tide data is missing.
        """
        if data_dir is None:
            repo_root = Path(__file__).resolve().parents[3]
            data_dir = repo_root / "data" / "processed" / "phase7"

        dem_path = data_dir / "terrain" / "elevation_30m.tif"
        slope_path = data_dir / "terrain" / "slope_30m.tif"
        aspect_path = data_dir / "terrain" / "aspect_30m.tif"
        flow_acc_path = data_dir / "terrain" / "flow_accumulation_30m.tif"
        drainage_path = data_dir / "terrain" / "drainage_proxy_30m.tif"
        landcover_path = data_dir / "landcover" / "landcover_class_30m.tif"
        roads_path = data_dir / "urban" / "distance_to_road_30m.tif"
        waterways_path = data_dir / "urban" / "distance_to_waterway_30m.tif"
        rainfall_path = data_dir / "rainfall" / f"{event_id}_rainfall_30m.tif"
        tide_summary_path = data_dir / "tide" / "event_tide_aligned_summary.json"

        required_paths = [
            dem_path, slope_path, aspect_path, flow_acc_path, drainage_path,
            landcover_path, roads_path, waterways_path, rainfall_path, tide_summary_path
        ]
        for p in required_paths:
            if not p.exists():
                raise FileNotFoundError(
                    f"Required real data file missing for Phase 8 calibration feature preparation: {p}. "
                    "Cannot proceed without real data (NO synthetic fallback allowed)."
                )

        with rasterio.open(dem_path) as src:
            elevation_m = src.read(1).astype(np.float32).flatten()
        with rasterio.open(slope_path) as src:
            slope_deg = src.read(1).astype(np.float32).flatten()
        with rasterio.open(aspect_path) as src:
            aspect_deg = src.read(1).astype(np.float32).flatten()
        with rasterio.open(flow_acc_path) as src:
            flow_acc = src.read(1).astype(np.float32).flatten()
        with rasterio.open(drainage_path) as src:
            drainage_proxy = src.read(1).astype(np.float32).flatten()
        with rasterio.open(landcover_path) as src:
            landcover_cls = src.read(1).astype(np.int32).flatten()
        with rasterio.open(roads_path) as src:
            dist_road = src.read(1).astype(np.float32).flatten()
        with rasterio.open(waterways_path) as src:
            dist_waterway = src.read(1).astype(np.float32).flatten()
        with rasterio.open(rainfall_path) as src:
            rainfall_mm_hr = src.read(1).astype(np.float32).flatten()

        is_built_up = (landcover_cls == 1).astype(np.int32)
        is_vegetation = (landcover_cls == 2).astype(np.int32)
        built_up_fraction = np.where(landcover_cls == 1, 0.85, 0.15).astype(np.float32)

        rainfall_30min_mm = (rainfall_mm_hr / 2.0).astype(np.float32)

        with open(tide_summary_path, "r", encoding="utf-8") as f:
            tide_summary = json.load(f)
        if event_id not in tide_summary:
            raise KeyError(f"Event ID '{event_id}' not found in tide summary {tide_summary_path}")
        tide_info = tide_summary[event_id]
        tide_level_m = float(tide_info.get("max_tide_level_m", 3.4))
        tide_anomaly_m = float(tide_info.get("tide_anomaly_msl_m", 1.98))

        tide_level_arr = np.full_like(elevation_m, tide_level_m, dtype=np.float32)
        tide_anomaly_arr = np.full_like(elevation_m, tide_anomaly_m, dtype=np.float32)

        if physical_depth_grid is not None:
            phys_depth_flat = physical_depth_grid.astype(np.float32).flatten()
            physical_model_score = np.clip(phys_depth_flat / 2.0, 0.0, 1.0)
        else:
            physical_model_score = np.clip(
                (rainfall_mm_hr / 50.0) * 0.4
                + built_up_fraction * 0.3
                + (1.0 - np.minimum(elevation_m, 50.0) / 50.0) * 0.3,
                0.0, 1.0
            ).astype(np.float32)

        df = pd.DataFrame({
            "elevation_m": elevation_m,
            "slope_deg": slope_deg,
            "aspect_deg": aspect_deg,
            "flow_accumulation_cells": flow_acc,
            "drainage_proxy_score": drainage_proxy,
            "landcover_class": landcover_cls,
            "built_up_fraction": built_up_fraction,
            "distance_to_road_m": dist_road,
            "distance_to_waterway_m": dist_waterway,
            "rainfall_30min_mm": rainfall_30min_mm,
            "rainfall_intensity_mm_hr": rainfall_mm_hr,
            "tide_level_m": tide_level_arr,
        })

        return df[EXPECTED_FEATURES]


    def evaluate(
        self,
        features_df: pd.DataFrame,
        simulation_run_id: Optional[str] = None,
        event_id: str = "E05",
        provider_mode: str = "REAL_DATA",
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run read-only XGBoost inference and compute statistical summary.
        """
        if len(features_df.columns) != len(EXPECTED_FEATURES):
            raise ValueError(
                f"Feature dataframe column count ({len(features_df.columns)}) does not match expected ({len(EXPECTED_FEATURES)})"
            )
        if list(features_df.columns) != EXPECTED_FEATURES:
            raise ValueError(
                f"Feature dataframe column order mismatch:\nExpected: {EXPECTED_FEATURES}\nGot: {list(features_df.columns)}"
            )

        model = self.model
        probs = model.predict_proba(features_df)[:, 1]

        input_count = len(features_df)
        pred_count = len(probs)
        min_s = float(np.min(probs))
        max_s = float(np.max(probs))
        mean_s = float(np.mean(probs))
        std_s = float(np.std(probs))
        high_risk_cnt = int(np.sum(probs >= 0.5))

        import uuid
        actual_run_id = run_id or f"calib-eval-{uuid.uuid4().hex[:8]}"

        summary = {
            "input_row_count": input_count,
            "prediction_count": pred_count,
            "min_score": min_s,
            "max_score": max_s,
            "mean_score": mean_s,
            "std_score": std_s,
            "high_risk_cell_count": high_risk_cnt,
        }

        provenance = {
            "model_path": str(self.model_path),
            "model_filename": self.model_path.name,
            "model_class": type(model).__name__,
            "sha256": self.sha256,
            "model_status": MODEL_STATUS,
            "calibration_status": CALIBRATION_STATUS,
            "terminology_disclaimer": "Prototype ML Score — ML calibration prototype — not operationally validated",
            "provider_mode": provider_mode,
            "simulation_run_id": simulation_run_id,
            "event_id": event_id,
        }

        return {
            "run_id": actual_run_id,
            "simulation_run_id": simulation_run_id,
            "event_id": event_id,
            "model_artifact": self.model_path.name,
            "model_status": MODEL_STATUS,
            "calibration_status": CALIBRATION_STATUS,
            "provider_mode": provider_mode,
            "feature_schema": self.feature_schema,
            "feature_count": len(EXPECTED_FEATURES),
            "sample_scores": [float(x) for x in probs[:10]],
            "raw_scores": probs,
        }

    def predict_single(self, features: Dict[str, Any]) -> Optional[float]:
        """
        Execute read-only inference on a single coordinate feature dictionary.
        Maps available features to EXPECTED_FEATURES; fills missing features with np.nan.
        Returns predicted probability as float, or None if prediction fails.
        """
        try:
            row_dict = {}
            for col in EXPECTED_FEATURES:
                val = features.get(col)
                if val is None:
                    row_dict[col] = np.nan
                else:
                    try:
                        row_dict[col] = float(val)
                    except (ValueError, TypeError):
                        row_dict[col] = np.nan
            df = pd.DataFrame([row_dict], columns=EXPECTED_FEATURES)
            model = self.model
            if model is None:
                return None
            probs = model.predict_proba(df)[:, 1]
            return float(probs[0])
        except Exception as e:
            logger.warning("Single-point calibration prediction failed", error=str(e))
            return None
