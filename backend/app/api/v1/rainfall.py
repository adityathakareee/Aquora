"""
Developer Verification Endpoints for Rainfall & Forecast Data Pipeline.

FOR INFRASTRUCTURE VERIFICATION ONLY.
DOES NOT EXPOSE FLOOD PREDICTIONS, RUNOFF, OR FLOOD DEPTH.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from app.providers.forecast import SyntheticForecastProvider
from app.providers.rainfall import IMERGRainfallProvider
from app.schemas.geospatial import BoundingBox
from app.schemas.rainfall import (
    IngestionRunSchema,
    RainfallForecastSchema,
    RainfallObservationSchema,
)
from app.services.ingestion.rain_service import (
    ForecastIngestionService,
    RainfallIngestionService,
)

router = APIRouter(prefix="/rainfall", tags=["Rainfall Pipeline"])


@router.get(
    "/observations/latest",
    response_model=RainfallObservationSchema,
    summary="Get Latest Rainfall Observation Grid Metadata (IMERG)"
)
async def get_latest_observation(
    variant: str = Query("Final", description="IMERG Product Variant: Final, Late, Early")
) -> RainfallObservationSchema:
    """
    Developer verification endpoint for latest NASA GPM IMERG rainfall observation record.
    """
    provider = IMERGRainfallProvider()
    service = RainfallIngestionService()
    bbox = BoundingBox(minx=12.4, miny=41.8, maxx=12.6, maxy=42.0)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=30)

    obs, _ = await service.ingest_observation(
        provider=provider,
        bbox=bbox,
        start_time=start_time,
        end_time=end_time,
        product_variant=variant
    )
    return obs


@router.get(
    "/forecasts/latest",
    response_model=list[RainfallForecastSchema],
    summary="Get Latest 0-3 Hour Horizon Forecast Grids"
)
async def get_latest_forecasts() -> list[RainfallForecastSchema]:
    """
    Developer verification endpoint for 0-3 hour precipitation forecast horizons (+0m to +180m).
    """
    provider = SyntheticForecastProvider()
    service = ForecastIngestionService()
    bbox = BoundingBox(minx=12.4, miny=41.8, maxx=12.6, maxy=42.0)
    init_time = datetime.utcnow()

    forecasts, _ = await service.ingest_0_3h_horizon(
        provider=provider,
        bbox=bbox,
        initialization_time=init_time
    )
    return forecasts


@router.get(
    "/ingestion-runs",
    response_model=list[IngestionRunSchema],
    summary="Get Recent Data Ingestion Audit Execution Logs"
)
async def get_ingestion_runs() -> list[IngestionRunSchema]:
    """
    Developer verification endpoint for recent ingestion run audit records.
    """
    provider_rain = IMERGRainfallProvider()
    service_rain = RainfallIngestionService()
    bbox = BoundingBox(minx=12.4, miny=41.8, maxx=12.6, maxy=42.0)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=30)

    _, run_obs = await service_rain.ingest_observation(
        provider=provider_rain,
        bbox=bbox,
        start_time=start_time,
        end_time=end_time
    )

    provider_fcst = SyntheticForecastProvider()
    service_fcst = ForecastIngestionService()
    _, run_fcst = await service_fcst.ingest_0_3h_horizon(
        provider=provider_fcst,
        bbox=bbox,
        initialization_time=end_time
    )

    return [run_obs, run_fcst]


# ==============================================================================
# PHASE 2C: INDIA HYDROMETEOROLOGICAL INGESTION ENDPOINTS
# ==============================================================================

@router.get(
    "/auth-status",
    summary="Inspect NASA Earthdata Authentication Status"
)
async def get_earthdata_auth_status() -> dict:
    """
    Check NASA Earthdata Login authentication status.
    Fails safely and reports explicit status without leaking credentials.
    """
    from app.services.india_rainfall_service import IndiaRainfallService
    service = IndiaRainfallService()
    return service.check_earthdata_authentication()


@router.get(
    "/basin/{domain_id}",
    summary="Get Verified Non-Operational Precipitation Benchmark for Pilot Basin"
)
async def get_basin_rainfall(domain_id: str) -> dict:
    """
    Retrieve non-operational precipitation benchmark fixture for a verified pilot basin domain:
    - ganga_patna
    - brahmaputra_guwahati
    - godavari_nashik
    - narmada_bharuch
    - deep_mumbai_mithi

    Benchmark Isolation: Returns 404 if domain is unverified. Output is strictly marked
    as LITERATURE_DERIVED_BENCHMARK / NON_OPERATIONAL_TEST_FIXTURE.
    """
    from fastapi import HTTPException
    from app.services.india_rainfall_service import IndiaRainfallService
    service = IndiaRainfallService()
    res = service.get_basin_rainfall(domain_id)
    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"Pilot domain '{domain_id}' not found in verified benchmarks. Zero Fabrication prohibits synthesis."
        )
    return res


@router.get(
    "/sample",
    summary="Sample Precipitation Observations at Coordinates"
)
async def sample_precipitation_at_location(
    lat: float = Query(..., ge=-90.0, le=90.0, description="WGS84 Latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="WGS84 Longitude"),
    allow_benchmark: bool = Query(False, description="Explicitly allow non-operational benchmark test fixtures for development/testing"),
) -> dict:
    """
    Sample precipitation observations for coordinates within verified pilot domains.

    Benchmark Isolation:
    - If allow_benchmark=False (operational default): returns 404 because authentic
      operational NASA IMERG granules are not yet ingested (PIPELINE_IMPLEMENTED_LIVE_ACQUISITION_NOT_VERIFIED)
      and synthetic benchmarks are isolated.
    - If allow_benchmark=True: returns literature-derived benchmark fixture explicitly tagged as
      NON_OPERATIONAL_TEST_FIXTURE.
    """
    from fastapi import HTTPException
    from app.services.india_rainfall_service import IndiaRainfallService
    if not allow_benchmark:
        raise HTTPException(
            status_code=404,
            detail=(
                "Operational gridded precipitation observations unavailable: authentic NASA IMERG granules not ingested. "
                "Zero Fabrication prohibits silent substitution of synthetic benchmarks. "
                "To inspect non-operational literature-derived benchmark fixtures for development, pass allow_benchmark=true."
            ),
        )
    service = IndiaRainfallService()
    res = service.sample_rainfall_at_location(lat, lon, allow_benchmark=True)
    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"Coordinates ({lat}, {lon}) are outside verified pilot domains. Zero Fabrication prohibits synthetic rainfall."
        )
    return res


@router.get(
    "/forecast",
    summary="Get Operational Numerical Weather Prediction Forecast (ECMWF IFS via Open-Meteo)"
)
async def get_operational_forecast(
    lat: float = Query(..., ge=-90.0, le=90.0, description="WGS84 Latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="WGS84 Longitude"),
    lead_time_minutes: int = Query(60, ge=15, le=360, description="Forecast horizon lead time in minutes"),
) -> dict:
    """
    Fetch operational precipitation forecast.
    STRICTLY MARKED AS FORECAST. Never mixed with historical observations.
    """
    from fastapi import HTTPException
    from app.services.india_rainfall_service import IndiaRainfallService
    service = IndiaRainfallService()
    try:
        fcst = await service.get_precipitation_forecast(
            latitude=lat,
            longitude=lon,
            lead_time_minutes=lead_time_minutes,
            allow_synthetic_fallback=False,
        )
        return fcst.model_dump()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Operational forecast upstream unavailable: {str(e)}. No silent synthetic fallback permitted under Zero Fabrication principles."
        )
