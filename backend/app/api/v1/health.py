from pathlib import Path
import redis.asyncio as redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import logger
from app.db.init_db import verify_production_schema
from app.db.session import AsyncSessionLocal
from app.schemas.health import LivenessResponse, ReadinessResponse, ServicesHealth

router = APIRouter(prefix="/health", tags=["Health"])

@router.api_route("", methods=["GET", "HEAD"], response_model=ReadinessResponse, summary="Health Readiness Alias", include_in_schema=False)
async def health_index(response: Response) -> ReadinessResponse:
    """Alias for /api/v1/health/ready."""
    return await health_ready(response)

@router.api_route("/live", methods=["GET", "HEAD"], response_model=LivenessResponse, summary="Application Process Liveness Check")
async def health_live() -> LivenessResponse:
    """
    Liveness check to verify if the application process is running.
    Does NOT require database or Redis connectivity.
    """
    return LivenessResponse(status="ok")

@router.api_route("/ready", methods=["GET", "HEAD"], response_model=ReadinessResponse, summary="Dependency Infrastructure Readiness Check")
async def health_ready(response: Response) -> ReadinessResponse:
    """
    Readiness check to verify PostgreSQL database, Redis, migration schema head, and terrain assets.
    Returns HTTP 200 when all dependencies are healthy, or HTTP 503 when degraded.
    """
    db_status = "ok"
    redis_status = "ok"
    schema_status = "ok"
    terrain_status = "ok"

    # 1. PostgreSQL Connectivity Check
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            if result.scalar() != 1:
                db_status = "error"
    except Exception as e:  # noqa: BLE001
        logger.error("Database readiness check failed", error=str(e))
        db_status = "error"

    # 2. Schema Verification Check (All 14 Required Tables)
    if db_status == "ok":
        try:
            missing_tables = await verify_production_schema()
            if missing_tables:
                logger.error("Database readiness check failed: missing tables", missing=missing_tables)
                schema_status = f"missing_{len(missing_tables)}_tables"
        except Exception as e:  # noqa: BLE001
            logger.error("Schema readiness check error", error=str(e))
            schema_status = "error"
    else:
        schema_status = "db_unavailable"

    # 3. Redis Connectivity Check
    try:
        r = redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        ping_ok = await r.ping()
        await r.aclose()
        if not ping_ok:
            redis_status = "error"
    except Exception as e:  # noqa: BLE001
        logger.error("Redis readiness check failed", error=str(e))
        redis_status = "error"

    # 4. Required Runtime Terrain Assets Check
    try:
        file_path = Path(__file__).resolve()
        # Find project root containing data/ or backend/
        repo_root = file_path.parents[4] if len(file_path.parents) > 4 else file_path.parents[-1]
        dem_path = repo_root / settings.DEM_GEOTIFF_PATH
        if not dem_path.exists():
            dem_path = Path(settings.DEM_GEOTIFF_PATH).resolve()
        if not dem_path.exists():
            # Try relative to cwd
            dem_path = Path.cwd() / settings.DEM_GEOTIFF_PATH
        if not dem_path.exists():
            logger.warning("Terrain asset check failed: file missing", path=str(dem_path))
            terrain_status = "missing_asset"
    except Exception as e:  # noqa: BLE001
        logger.error("Terrain asset check error", error=str(e))
        terrain_status = "error"

    is_healthy = (
        db_status == "ok"
        and redis_status == "ok"
        and schema_status == "ok"
        and terrain_status == "ok"
    )

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ok" if is_healthy else "degraded",
        environment=settings.ENVIRONMENT,
        services=ServicesHealth(
            database=db_status,
            redis=redis_status,
            schema_migration=schema_status,
            terrain_assets=terrain_status,
        )
    )

