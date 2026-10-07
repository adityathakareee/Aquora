from fastapi import APIRouter

from app.api.v1.alerts import router as alerts_router
from app.api.v1.calibration import router as calibration_router
from app.api.v1.critical_access import router as critical_access_router
from app.api.v1.digital_twin import router as digital_twin_router
from app.api.v1.drainage import router as drainage_router
from app.api.v1.flood import router as flood_router
from app.api.v1.ground_truth import router as ground_truth_router
from app.api.v1.health import router as health_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.locations import router as locations_router
from app.api.v1.protect_city import router as protect_city_router
from app.api.v1.rainfall import router as rainfall_router
from app.api.v1.routing import router as routing_router
from app.api.v1.simulator import router as simulator_router
from app.api.v1.terrain import router as terrain_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(locations_router)
v1_router.include_router(intelligence_router)
v1_router.include_router(rainfall_router)
v1_router.include_router(terrain_router)
v1_router.include_router(drainage_router)
v1_router.include_router(flood_router)
v1_router.include_router(calibration_router)
v1_router.include_router(digital_twin_router)
v1_router.include_router(routing_router)
v1_router.include_router(critical_access_router)
v1_router.include_router(protect_city_router)
v1_router.include_router(ground_truth_router)
v1_router.include_router(simulator_router)
v1_router.include_router(alerts_router)

__all__ = ["v1_router"]


