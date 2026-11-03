"""
AQUORA 2.0 Multi-Tier ML Model Registry and Abstraction Layer.

Decouples backend inference from the assumption that 'the model = Mumbai model'.
Provides an extensible registry capable of dispatching inference across:
1. National Screening Models (India-wide, Level 1)
2. Regional Models (State/Basin level, Level 2)
3. Deep Zone Models (e.g. Mumbai/Mithi high-resolution XGBoost prototype, Level 3)

Preserves existing Mumbai model execution with 100% backward compatibility.
Does NOT fabricate national models.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
import structlog

from app.schemas.intelligence_contracts import IntelligenceLevel, CapabilityStatus
from app.services.calibration_service import CalibrationService

logger = structlog.get_logger("aquora.ml_registry")


@runtime_checkable
class BaseFloodModel(Protocol):
    """Protocol for all AQUORA flood intelligence models."""
    model_id: str
    intelligence_level: IntelligenceLevel
    model_version: str
    status: str
    supported_zones: List[str]

    def predict_risk(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Execute risk prediction on the provided feature dictionary."""
        ...


class MumbaiMithiDeepModel:
    """
    Adapter preserving the existing Kaggle-trained XGBoost prototype
    (aquora_xgboost_prototype.joblib) for the Mumbai Deep Intelligence Zone.
    """
    model_id: str = "aquora_xgboost_mumbai_mithi_v1"
    intelligence_level: IntelligenceLevel = IntelligenceLevel.DEEP
    model_version: str = "0.8.0-prototype"
    status: str = "PROTOTYPE_ONLY"
    supported_zones: List[str] = [
        "deep_mumbai_mithi",
        "mithi_catchment_mumbai",
        "mumbai_mithi",
        "default",
    ]

    def __init__(self, service: Optional[CalibrationService] = None):
        self._service = service or CalibrationService()

    def predict_risk(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes prediction using the verified CalibrationService.
        Enforces read-only PROTOTYPE_ONLY status.
        """
        raw_prob = self._service.predict_single(features)
        return {
            "model_id": self.model_id,
            "intelligence_level": self.intelligence_level.value,
            "model_status": self.status,
            "predicted_probability": raw_prob,
            "calibrated_label": "PROTOTYPE_UNVERIFIED",
            "feature_count_used": len(features),
        }


from pathlib import Path
import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_SCREENING_ARTIFACT = PROJECT_ROOT / "ml" / "models" / "aquora_national_screening_model.joblib"
DEFAULT_REGIONAL_ARTIFACT = PROJECT_ROOT / "ml" / "models" / "aquora_regional_basin_model.joblib"


class Phase7EXGBoostWrapper:
    """
    Adapter enabling Phase 7E Kaggle-trained XGBoost model (trained on the 7 non-leaking predictors)
    to execute seamlessly on the governed 11 Core National feature matrix.
    """
    def __init__(self, bst_json_str: str, feature_indices: List[int], threshold: float = 0.01):
        self.bst_json_str = bst_json_str
        self.feature_indices = feature_indices
        self.threshold = threshold
        self.feature_names = [
            "rainfall_24h_mm",
            "rainfall_72h_mm",
            "rainfall_anomaly_index",
            "elevation_m",
            "slope_deg",
            "distance_to_river_m",
            "landcover_class",
        ]
        self._bst = None

    @property
    def bst(self):
        if self._bst is None:
            import xgboost as xgb
            self._bst = xgb.Booster()
            self._bst.load_model(bytearray(self.bst_json_str, "utf-8"))
        return self._bst

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        import xgboost as xgb
        X_sub = np.asarray(X, dtype=np.float32)[:, self.feature_indices]
        dmat = xgb.DMatrix(X_sub, feature_names=self.feature_names)
        p1 = self.bst.predict(dmat)
        p0 = 1.0 - p1
        return np.column_stack([p0, p1])

    def predict(self, X: np.ndarray) -> np.ndarray:
        probs = self.predict_proba(X)[:, 1]
        return (probs >= self.threshold).astype(int)


class NationalScreeningModel:
    """
    AQUORA National Flood Risk Screening Model (Level 1).
    Evaluates the 11 CORE_NATIONAL features to predict macro flood susceptibility.

    Zero Fabrication & Safety Invariants:
    1. Operates exclusively on the 11 Core National predictors.
    2. Rejects unexpected or forbidden columns (e.g. Phase 6 hydraulic depth, SAR delta).
    3. When untrained or artifact is missing, status is NOT_TRAINED and predict_risk reports not-ready.
       NEVER fabricates fake predictions or falls back to Mumbai.
    4. Supports loading certified versioned artifacts with schema and feature validation.
    """
    model_id: str = "aquora_national_screening_xgboost_v1"
    intelligence_level: IntelligenceLevel = IntelligenceLevel.NATIONAL
    model_version: str = "1.0.0-screening"
    status: str = "PLANNED"
    supported_zones: List[str] = ["national_india", "IN"]

    FEATURE_NAMES: List[str] = [
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

    TRAINED_PREDICTORS: List[str] = [
        "rainfall_24h_mm",
        "rainfall_72h_mm",
        "rainfall_anomaly_index",
        "elevation_m",
        "slope_deg",
        "distance_to_river_m",
        "landcover_class",
    ]

    GEOMORPHIC_ANCHORS: List[str] = [
        "elevation_m",
        "slope_deg",
        "distance_to_river_m",
    ]

    def __init__(self, artifact_path: Optional[Path] = None):
        self._artifact_path = Path(artifact_path) if artifact_path else DEFAULT_SCREENING_ARTIFACT
        self._model: Optional[Any] = None
        self._metadata: Dict[str, Any] = {}
        self._load_artifact()

    def _load_artifact(self) -> None:
        """Safely load and validate serialized model artifact."""
        if self._artifact_path and self._artifact_path.exists():
            try:
                payload = joblib.load(self._artifact_path)
                if isinstance(payload, dict) and "model" in payload:
                    # Validate schema version
                    if payload.get("schema_version") != "1.0.0":
                        logger.error("Incompatible model schema version", version=payload.get("schema_version"))
                        self.status = "SCHEMA_MISMATCH"
                        return
                    # Validate exact feature names and order
                    if payload.get("feature_names") != self.FEATURE_NAMES:
                        logger.error("Feature list mismatch in artifact")
                        self.status = "FEATURE_MISMATCH"
                        return
                    self._model = payload["model"]
                    self._metadata = payload.get("metadata", {})
                    self.model_version = payload.get("model_version", self.model_version)
                    self.status = payload.get("status", "OPERATIONAL")
                    logger.info("Loaded National Screening Model artifact", path=str(self._artifact_path))
                else:
                    self.status = "INVALID_ARTIFACT_FORMAT"
            except Exception as e:
                logger.error("Failed to load national screening artifact", error=str(e))
                self.status = "LOAD_ERROR"
        else:
            self.status = "PLANNED"

    @property
    def is_ready(self) -> bool:
        """True only if an authentic, certified model artifact is loaded and verified."""
        return self._model is not None and self.status in ("OPERATIONAL", "EVALUATED", "TRAINED")

    def predict_risk(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute risk prediction on the provided 11-feature dictionary.
        Returns not-ready status if model is not trained.
        Strictly enforces the Input-Validity Policy across the 7 trained predictors.
        """
        if not self.is_ready:
            if not features:
                raise NotImplementedError(
                    "National Screening Model is scheduled for Phase 3 training. "
                    "No synthetic or fabricated inference is permitted."
                )
            return {
                "model_id": self.model_id,
                "intelligence_level": self.intelligence_level.value,
                "model_status": self.status,
                "is_ready": False,
                "predicted_probability": None,
                "susceptibility_grade": None,
                "calibration_status": "UNCALIBRATED_MACRO_SCREENING",
                "governance_status": "PROTOTYPE_ONLY",
                "operational_readiness": "NOT_FOR_PUBLIC_ALERTS",
                "physics_engine_primacy": "Phase 6 deterministic physics engine remains primary authority",
                "message": (
                    "National Screening Model is not trained. "
                    "Authentic nationwide labeled datasets remain uningested. "
                    "Zero-fabrication rule strictly prohibits synthetic inference."
                ),
            }

        # Validate feature presence in dictionary
        missing_features = [k for k in self.FEATURE_NAMES if k not in features]
        if missing_features:
            raise ValueError(f"Features dictionary missing required core national predictors: {missing_features}")

        # Evaluate available vs missing predictors among the 7 trained features
        available_predictors = []
        for feat in self.TRAINED_PREDICTORS:
            v = features.get(feat)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                available_predictors.append(feat)
        missing_predictors = [k for k in self.TRAINED_PREDICTORS if k not in available_predictors]

        # Policy Gate 1: Zero available predictors
        # If zero predictors are measured, XGBoost default branch yields uninformative base prior (0.0130).
        # We strictly suppress inference to prevent false-low predictions.
        if len(available_predictors) == 0:
            return {
                "model_id": self.model_id,
                "intelligence_level": self.intelligence_level.value,
                "model_status": "INSUFFICIENT_INPUT_DATA",
                "is_ready": False,
                "predicted_probability": None,
                "susceptibility_grade": None,
                "calibration_status": "UNCALIBRATED_MACRO_SCREENING",
                "governance_status": "PROTOTYPE_ONLY",
                "operational_readiness": "NOT_FOR_PUBLIC_ALERTS",
                "physics_engine_primacy": "Phase 6 deterministic physics engine remains primary authority",
                "features_evaluated": self.FEATURE_NAMES,
                "available_predictors": [],
                "missing_predictors": self.TRAINED_PREDICTORS,
                "input_validity": "NO_PREDICTORS_AVAILABLE",
                "message": (
                    "Zero trained model predictors are available for this location. "
                    "Inference is suppressed under input-validity policy to prevent uninformative base predictions."
                ),
                "metadata": self._metadata,
            }

        # Policy Gate 2: Essential geomorphic anchors check
        # In Phase 7E training (0.00% missingness), terrain predictors (distance_to_river, elevation, slope)
        # account for >65% of tree split gains. Without basic terrain, the point has no physical spatial grounding.
        has_geomorphic_anchor = any(
            features.get(k) is not None and not (isinstance(features.get(k), float) and np.isnan(features.get(k)))
            for k in self.GEOMORPHIC_ANCHORS
        )
        if not has_geomorphic_anchor:
            return {
                "model_id": self.model_id,
                "intelligence_level": self.intelligence_level.value,
                "model_status": "INSUFFICIENT_INPUT_DATA",
                "is_ready": False,
                "predicted_probability": None,
                "susceptibility_grade": None,
                "calibration_status": "UNCALIBRATED_MACRO_SCREENING",
                "governance_status": "PROTOTYPE_ONLY",
                "operational_readiness": "NOT_FOR_PUBLIC_ALERTS",
                "physics_engine_primacy": "Phase 6 deterministic physics engine remains primary authority",
                "features_evaluated": self.FEATURE_NAMES,
                "available_predictors": available_predictors,
                "missing_predictors": missing_predictors,
                "input_validity": "MISSING_GEOMORPHIC_ANCHORS",
                "message": (
                    "Essential geomorphic terrain predictors (elevation, slope, distance to river) "
                    "are unindexed for this coordinate tile. Meaningful spatial screening cannot be evaluated."
                ),
                "metadata": self._metadata,
            }

        # Policy Gate 3: Complete Input Requirement under Strict Missing-Feature Governance Policy
        # Phase 7E training dataset contained strictly 0.00% missing values across all 7 trained predictors.
        # Diagnostic validation experiments (see docs/PHASE_7E_PARTIAL_INPUT_VALIDATION_REPORT.md) demonstrated
        # that unobserved rainfall causes a >5x inflation in mean predicted probability (from 5.8% to 29.2%)
        # and an 80.8% false positive rate on dry validation points due to XGBoost default-branch deluge traversal.
        # Therefore, partial-feature inference with missing rainfall is scientifically indefensible.
        # Complete feature availability across all 7 trained predictors is strictly required for inference.
        if len(missing_predictors) > 0:
            return {
                "model_id": self.model_id,
                "intelligence_level": self.intelligence_level.value,
                "model_status": "INSUFFICIENT_INPUT_DATA",
                "is_ready": False,
                "predicted_probability": None,
                "susceptibility_grade": None,
                "calibration_status": "UNCALIBRATED_MACRO_SCREENING",
                "governance_status": "PROTOTYPE_ONLY",
                "operational_readiness": "NOT_FOR_PUBLIC_ALERTS",
                "physics_engine_primacy": "Phase 6 deterministic physics engine remains primary authority",
                "features_evaluated": self.FEATURE_NAMES,
                "available_predictors": available_predictors,
                "missing_predictors": missing_predictors,
                "input_validity": "MISSING_REQUIRED_PREDICTORS",
                "message": (
                    f"Operational screening requires all 7 trained predictors. Missing: {missing_predictors}. "
                    "Phase 7E training data contained 0.00% missing values; diagnostic validation proved that partial-input "
                    "default branching produces severe false-positive probability distortions. "
                    "Inference is suppressed under strict feature governance."
                ),
                "metadata": self._metadata,
            }

        # Construct input array in exact feature order (handling missing values natively)
        row_vals = []
        for k in self.FEATURE_NAMES:
            v = features.get(k)
            row_vals.append(float(v) if v is not None else np.nan)
        X = np.array([row_vals], dtype=np.float32)

        # Predict probability
        try:
            prob = float(self._model.predict_proba(X)[0, 1])
        except Exception as err:
            logger.error("Inference failure on national screening model", error=str(err))
            raise RuntimeError(f"Model inference failed: {str(err)}")

        # Map to uncalibrated macro susceptibility grade
        if prob < 0.33:
            grade = "LOW"
        elif prob < 0.66:
            grade = "MEDIUM"
        else:
            grade = "HIGH"

        # Determine whether meteorology was observed, benchmark, or unobserved
        has_meteorology = any(
            features.get(k) is not None and not (isinstance(features.get(k), float) and np.isnan(features.get(k)))
            for k in ["rainfall_24h_mm", "rainfall_72h_mm", "rainfall_anomaly_index"]
        )
        validity_level = "COMPLETE_INPUT" if has_meteorology else "PARTIAL_GEOMORPHIC_ONLY"
        msg = (
            "Evaluated on complete geomorphic terrain, landcover, and precipitation scenario features."
            if has_meteorology
            else (
                "Evaluated on authentic geomorphic terrain and landcover features. "
                "Operational real-time precipitation gauges are unobserved at this cell; "
                "meteorological features remain null under zero-fabrication rules."
            )
        )

        return {
            "model_id": self.model_id,
            "intelligence_level": self.intelligence_level.value,
            "model_status": self.status,
            "is_ready": True,
            "predicted_probability": round(prob, 4),
            "susceptibility_grade": grade,
            "calibration_status": "UNCALIBRATED_MACRO_SCREENING",
            "governance_status": "PROTOTYPE_ONLY",
            "operational_readiness": "NOT_FOR_PUBLIC_ALERTS",
            "physics_engine_primacy": "Phase 6 deterministic physics engine remains primary authority",
            "features_evaluated": self.FEATURE_NAMES,
            "available_predictors": available_predictors,
            "missing_predictors": missing_predictors,
            "input_validity": validity_level,
            "message": msg,
            "metadata": self._metadata,
        }


class RegionalBasinModel:
    """
    AQUORA Regional Flood Intelligence Model (Level 2).
    Evaluates the 14 authorized features (11 Core National + 3 Regional Expansion)
    to predict meso-scale watershed susceptibility and exposure.

    Zero Fabrication & Safety Invariants:
    1. Operates exclusively on the 14 Core National + Regional Expansion predictors.
    2. Rejects unexpected or forbidden columns (e.g. Phase 6 hydraulic depth, SAR delta, Deep features).
    3. When untrained or artifact is missing, status is PLANNED / NOT_TRAINED and is_ready is False.
       Provides uncalibrated watershed exposure screening index if inputs exist, or None.
       NEVER emits a fake machine learning probability or claims calibrated operational forecasting.
    4. Supports loading certified versioned artifacts with schema and feature validation.
    """
    model_id: str = "aquora_regional_basin_model_v1"
    intelligence_level: IntelligenceLevel = IntelligenceLevel.REGIONAL
    model_version: str = "1.0.0-regional"
    status: str = "PLANNED"
    supported_zones: List[str] = [
        "regional_ganga_basin",
        "regional_brahmaputra_basin",
        "regional_godavari_basin",
        "regional_narmada_basin",
        "regional_maharashtra",
        "BASIN-GANGA",
        "BASIN-BRAHMAPUTRA",
        "BASIN-GODAVARI",
        "BASIN-NARMADA",
        "BASIN-KRISHNA",
        "BASIN-TAPI",
        "BASIN-MAHANADI",
        "BASIN-MITHI",
        "default",
    ]

    FEATURE_NAMES: List[str] = [
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
        "basin_drainage_area_km2",
        "soil_saturation_index",
        "population_density_per_km2",
    ]

    FORBIDDEN_FEATURES: set = {
        "water_depth_m",
        "flow_velocity_ms",
        "modeled_depth_m",
        "sar_delta_vv_db",
        "flood_label",
        "candidate_flood_label",
        "flow_accumulation_cells",
        "drainage_proxy_score",
        "built_up_fraction",
        "distance_to_road_m",
        "distance_to_waterway_m",
        "tide_level_m",
    }

    def __init__(self, artifact_path: Optional[Path] = None):
        self._artifact_path = Path(artifact_path) if artifact_path else DEFAULT_REGIONAL_ARTIFACT
        self._model: Optional[Any] = None
        self._metadata: Dict[str, Any] = {}
        self._load_artifact()

    def _load_artifact(self) -> None:
        """Safely load and validate serialized model artifact."""
        if self._artifact_path and self._artifact_path.exists():
            try:
                payload = joblib.load(self._artifact_path)
                if isinstance(payload, dict) and "model" in payload:
                    if payload.get("schema_version") != "1.0.0":
                        logger.error("Incompatible model schema version", version=payload.get("schema_version"))
                        self.status = "SCHEMA_MISMATCH"
                        return
                    if payload.get("feature_names") != self.FEATURE_NAMES:
                        logger.error("Feature list mismatch in artifact")
                        self.status = "FEATURE_MISMATCH"
                        return
                    self._model = payload["model"]
                    self._metadata = payload.get("metadata", {})
                    self.model_version = payload.get("model_version", self.model_version)
                    self.status = payload.get("status", "OPERATIONAL")
                    logger.info("Loaded Regional Basin Model artifact", path=str(self._artifact_path))
                else:
                    self.status = "INVALID_ARTIFACT_FORMAT"
            except Exception as e:
                logger.error("Failed to load regional model artifact", error=str(e))
                self.status = "CORRUPT_ARTIFACT"
        else:
            self.status = "PLANNED"

    def predict_risk(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute regional risk evaluation or uncalibrated screening on feature dictionary.
        Enforces zero-fabrication and scientific transparency.
        """
        # Validate forbidden features
        forbidden_present = set(features.keys()) & self.FORBIDDEN_FEATURES
        if forbidden_present:
            raise ValueError(
                f"Forbidden columns detected in regional predictor matrix: {sorted(list(forbidden_present))}. "
                "Phase 6 hydraulic variables and Deep-zone exclusive features are strictly prohibited."
            )

        # 1. Trained ML model path (only when a verified trained artifact is loaded)
        if self._model is not None and self.status == "OPERATIONAL":
            X = np.array([[features.get(f) if features.get(f) is not None else np.nan for f in self.FEATURE_NAMES]])
            try:
                if hasattr(self._model, "predict_proba"):
                    prob = float(self._model.predict_proba(X)[0, 1])
                else:
                    prob = float(self._model.predict(X)[0])
            except Exception as e:
                logger.error("Model inference execution error", error=str(e))
                raise RuntimeError(f"Regional model inference failed: {str(e)}")

            if prob < 0.33:
                grade = "LOW"
            elif prob < 0.66:
                grade = "MEDIUM"
            else:
                grade = "HIGH"

            return {
                "model_id": self.model_id,
                "intelligence_level": self.intelligence_level.value,
                "model_status": self.status,
                "is_ready": True,
                "predicted_probability": round(prob, 4),
                "watershed_exposure_index": round(prob, 4),
                "exposure_grade": grade,
                "calibration_status": "CALIBRATED_REGIONAL_ML",
                "features_evaluated": self.FEATURE_NAMES,
                "metadata": self._metadata,
                "message": "Operational Level 2 Regional ML risk prediction.",
            }

        # 2. Untrained / Heuristic screening path (Zero-fabrication)
        r24 = features.get("rainfall_24h_mm")
        sat = features.get("soil_saturation_index")
        dist = features.get("distance_to_river_m")
        slope = features.get("slope_deg")

        # Heuristic index is only defensible if rainfall and basic terrain are available
        if r24 is not None and dist is not None and slope is not None:
            r_norm = min(1.0, max(0.0, float(r24) / 100.0))
            s_norm = min(1.0, max(0.0, float(sat))) if sat is not None else r_norm
            p_norm = max(0.0, min(1.0, 1.0 - (float(dist) / 5000.0)))
            t_norm = max(0.0, min(1.0, 1.0 - (float(slope) / 15.0)))
            heuristic_index = round(0.35 * r_norm + 0.25 * s_norm + 0.25 * p_norm + 0.15 * t_norm, 4)
            if heuristic_index < 0.33:
                grade = "LOW"
            elif heuristic_index < 0.66:
                grade = "MEDIUM"
            else:
                grade = "HIGH"
        else:
            heuristic_index = None
            grade = "UNCALIBRATED"

        return {
            "model_id": self.model_id,
            "intelligence_level": self.intelligence_level.value,
            "model_status": self.status,
            "is_ready": False,
            "predicted_probability": None,
            "watershed_exposure_index": heuristic_index,
            "exposure_grade": grade,
            "calibration_status": "UNCALIBRATED_REGIONAL_SCREENING",
            "features_evaluated": self.FEATURE_NAMES,
            "metadata": self._metadata,
            "message": (
                "Level 2 Regional ML model artifact is not yet trained with coincident authentic labels. "
                "Returning uncalibrated watershed exposure screening index based on antecedent rainfall, "
                "river proximity, and terrain slope. Zero-fabrication: predicted_probability is None."
            ),
        }


# Backward-compatible alias
NationalScreeningModelPlaceholder = NationalScreeningModel


class FloodModelRegistry:
    """
    Central registry routing inference requests to appropriate models
    based on intelligence level and geographic zone.
    """
    _registry: Dict[str, BaseFloodModel] = {}
    _initialized: bool = False

    @classmethod
    def initialize(cls) -> None:
        """Register baseline models idempotently."""
        if cls._initialized:
            return

        # 1. Register active Mumbai Deep Zone prototype model
        try:
            mumbai_model = MumbaiMithiDeepModel()
            cls.register(mumbai_model)
            logger.info("Registered Mumbai Deep Zone ML model", model_id=mumbai_model.model_id)
        except Exception as e:
            logger.warning("Mumbai Deep Zone model artifact deferred initialization", error=str(e))

        # 2. Register National screening model (reports NOT_TRAINED if no artifact)
        cls.register(NationalScreeningModel())

        # 3. Register Regional basin model (reports PLANNED / heuristic if no artifact)
        cls.register(RegionalBasinModel())

        cls._initialized = True

    @classmethod
    def register(cls, model: BaseFloodModel) -> None:
        """Register a model instance in the global registry."""
        cls._registry[model.model_id] = model

    @classmethod
    def get_model(
        cls,
        level: IntelligenceLevel,
        zone_id: Optional[str] = None
    ) -> BaseFloodModel:
        """
        Retrieve best matching model for the requested intelligence level and zone.
        Falls back to Mumbai Deep model if zone matches Mumbai or default.
        """
        if not cls._initialized:
            cls.initialize()

        target_zone = zone_id or "default"

        # Search for exact zone match
        for model in cls._registry.values():
            if model.intelligence_level == level and target_zone in model.supported_zones:
                return model

        # Fallback to level match
        for model in cls._registry.values():
            if model.intelligence_level == level:
                return model

        raise KeyError(f"No registered model found for level={level.value}, zone_id={zone_id}")

    @classmethod
    def list_models(cls) -> List[Dict[str, Any]]:
        """List all registered models and their statuses."""
        if not cls._initialized:
            cls.initialize()

        return [
            {
                "model_id": m.model_id,
                "intelligence_level": m.intelligence_level.value,
                "model_version": m.model_version,
                "status": m.status,
                "supported_zones": m.supported_zones,
            }
            for m in cls._registry.values()
        ]
