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


class NationalScreeningModelPlaceholder:
    """
    Architectural slot for future Phase 2/3 India National Screening Model.
    Explicitly flags status as PLANNED. NEVER fabricates fake predictions.
    """
    model_id: str = "aquora_india_national_screening_placeholder"
    intelligence_level: IntelligenceLevel = IntelligenceLevel.NATIONAL
    model_version: str = "none"
    status: str = "PLANNED"
    supported_zones: List[str] = ["national_india", "IN"]

    def predict_risk(self, features: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "National Screening Model is scheduled for Phase 2/3 Kaggle training. "
            "No synthetic or fabricated inference is permitted."
        )


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

        # 2. Register National placeholder
        cls.register(NationalScreeningModelPlaceholder())

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
