"""
AQUORA Phase 2C — India Rainfall & Hydrometeorological Ingestion Test Suite.

Verifies:
1. Earthdata authentication handling, safety, and failure behavior.
2. Scientific normalization (mm/hr -> mm, nodata sentinels, negative rejection).
3. Temporal aggregation across canonical horizons (1h to 72h) & missing interval detection.
4. Spatial resolution preservation (~0.1 deg native grid, NO false 30m claim).
5. Representative 5-basin pilot validation (Ganga, Brahmaputra, Godavari, Narmada, Mumbai).
6. Strict separation of historical observations from operational forecasts.
7. Zero fabrication & no silent fallback outside verified pilot coverage.
8. National & Regional Data Contract hydrometeorological integration.
9. REST API endpoints (/auth-status, /basin, /sample, /forecast).
10. Mumbai regression & backward compatibility protection.
"""

from datetime import datetime, timedelta, timezone
import math
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.providers.forecast import OpenMeteoForecastProvider
from app.providers.rainfall import IMERGRainfallProvider
from app.schemas.rainfall import QualityStatus, RainfallQuantityType
from app.services.india_rainfall_service import (
    AuthenticationStatus,
    EarthdataAuthManager,
    IndiaRainfallService,
    PILOT_BASIN_BENCHMARKS,
    PrecipitationNormalizer,
    RainfallProductType,
    SpatialRainfallExtractor,
    TemporalRainfallAggregator,
)
from app.services.india_spatial_service import IndiaSpatialService
from app.schemas.intelligence_contracts import (
    NationalDataContract,
    RegionalDataContract,
    DeepDataContract,
)


client = TestClient(app)


# ==============================================================================
# 1. EARTHDATA AUTHENTICATION SAFETY & FAILURE BEHAVIOR
# ==============================================================================

def test_earthdata_auth_missing_credentials_fails_safely():
    """Verify that unconfigured credentials report UNAUTHENTICATED without crashing."""
    manager = EarthdataAuthManager(username=None, password=None, bearer_token=None)
    assert manager.get_status() == AuthenticationStatus.UNAUTHENTICATED
    assert not manager.has_credentials()

    # Calling get_auth_headers without credentials must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        manager.get_auth_headers()
    assert "NASA Earthdata credentials missing" in str(exc_info.value)
    assert "Zero Fabrication" in str(exc_info.value)


def test_earthdata_auth_masking_never_leaks_secrets():
    """Verify that credentials masking strictly hides raw secrets."""
    manager = EarthdataAuthManager(
        username="test_user",
        password="super_secret_password_12345",
        bearer_token="secret_token_abcdef"
    )
    masked = manager.mask_credentials()
    assert masked["auth_configured"] is True
    assert masked["username_configured"] is True
    assert masked["password_configured"] is True
    assert "super_secret_password_12345" not in str(masked)
    assert "secret_token_abcdef" not in str(masked)


def test_service_check_earthdata_authentication():
    """Verify service level auth status inspection."""
    service = IndiaRainfallService()
    auth_check = service.check_earthdata_authentication()
    assert "status" in auth_check
    assert "can_download_raw_imerg" in auth_check
    assert "auth_details" in auth_check
    assert auth_check["provider"] == "NASA GES DISC / Earthdata"
    assert auth_check["product"] == "GPM_3IMERGDF V07B Final"


# ==============================================================================
# 2. PRECIPITATION NORMALIZATION & UNIT CONVERSION
# ==============================================================================

def test_precipitation_normalizer_rate_to_accumulation():
    """Verify conversion of mm/hr rate to mm accumulation for 30-min window."""
    # 20.0 mm/hr over 30 min = 10.0 mm
    accum = PrecipitationNormalizer.rate_to_accumulation(20.0, duration_minutes=30.0)
    assert accum == 10.0

    # 0.0 mm/hr over 30 min = 0.0 mm
    assert PrecipitationNormalizer.rate_to_accumulation(0.0, duration_minutes=30.0) == 0.0

    # Negative rate must raise ValueError
    with pytest.raises(ValueError):
        PrecipitationNormalizer.rate_to_accumulation(-5.0, duration_minutes=30.0)


def test_precipitation_normalizer_accumulation_to_rate():
    """Verify conversion of mm accumulation to mm/hr rate for 30-min window."""
    # 15.0 mm over 30 min = 30.0 mm/hr
    rate = PrecipitationNormalizer.accumulation_to_rate(15.0, duration_minutes=30.0)
    assert rate == 30.0

    with pytest.raises(ValueError):
        PrecipitationNormalizer.accumulation_to_rate(-1.0, duration_minutes=30.0)


def test_precipitation_normalizer_sanitize_values():
    """Verify classification of valid 0.0 vs sentinels vs invalid negative values."""
    normalizer = PrecipitationNormalizer()

    # Valid observed dry zero
    val, status = normalizer.sanitize_value(0.0)
    assert val == 0.0
    assert status == QualityStatus.VALID

    # Valid positive precipitation
    val, status = normalizer.sanitize_value(12.4)
    assert val == 12.4
    assert status == QualityStatus.VALID

    # NASA nodata sentinel (-9999.0)
    val, status = normalizer.sanitize_value(-9999.0)
    assert val is None
    assert status == QualityStatus.NODATA

    # NaN nodata
    val, status = normalizer.sanitize_value(float("nan"))
    assert val is None
    assert status == QualityStatus.NODATA

    # Negative invalid value (e.g. -0.5)
    val, status = normalizer.sanitize_value(-0.5)
    assert val is None
    assert status == QualityStatus.INVALID


# ==============================================================================
# 3. TEMPORAL RAINFALL AGGREGATION
# ==============================================================================

def test_temporal_aggregation_continuous_series():
    """Verify exact multi-horizon temporal accumulation over continuous 30-min steps."""
    anchor = datetime(2023, 7, 12, 12, 0, tzinfo=timezone.utc)
    # Generate 144 contiguous 30-minute steps ending at anchor (72 hours total)
    series = []
    for i in range(144):
        # 1.0 mm per 30-min step
        t = anchor - timedelta(minutes=30 * (143 - i))
        series.append({
            "timestamp": t,
            "accumulation_mm": 1.0,
            "status": QualityStatus.VALID.value,
        })

    # 1-hour accumulation = 2 steps * 1.0 mm = 2.0 mm
    res_1h = TemporalRainfallAggregator.aggregate_window(series, anchor, "1h")
    assert res_1h["status"] == QualityStatus.VALID.value
    assert res_1h["accumulation_mm"] == 2.0
    assert res_1h["steps_available"] == 2

    # 3-hour accumulation = 6 steps * 1.0 mm = 6.0 mm
    res_3h = TemporalRainfallAggregator.aggregate_window(series, anchor, "3h")
    assert res_3h["accumulation_mm"] == 6.0

    # 6-hour accumulation = 12 steps = 12.0 mm
    res_6h = TemporalRainfallAggregator.aggregate_window(series, anchor, "6h")
    assert res_6h["accumulation_mm"] == 12.0

    # 12-hour accumulation = 24 steps = 24.0 mm
    res_12h = TemporalRainfallAggregator.aggregate_window(series, anchor, "12h")
    assert res_12h["accumulation_mm"] == 24.0

    # 24-hour accumulation = 48 steps = 48.0 mm
    res_24h = TemporalRainfallAggregator.aggregate_window(series, anchor, "24h")
    assert res_24h["accumulation_mm"] == 48.0

    # 48-hour accumulation = 96 steps = 96.0 mm
    res_48h = TemporalRainfallAggregator.aggregate_window(series, anchor, "48h")
    assert res_48h["accumulation_mm"] == 96.0

    # 72-hour accumulation = 144 steps = 144.0 mm
    res_72h = TemporalRainfallAggregator.aggregate_window(series, anchor, "72h")
    assert res_72h["accumulation_mm"] == 144.0


@pytest.mark.parametrize("horizon,required_steps", [
    ("1h", 2),
    ("3h", 6),
    ("6h", 12),
    ("12h", 24),
    ("24h", 48),
    ("48h", 96),
    ("72h", 144),
])
def test_temporal_aggregation_partial_window_rejection(horizon, required_steps):
    """
    CRITICAL ZERO FABRICATION TEST:
    Partial windows (e.g. required_steps - 1) must return None with QualityStatus.MISSING.
    Must NEVER falsely report partial windows as complete accumulations or fill missing steps.
    """
    anchor = datetime(2023, 7, 12, 12, 0, tzinfo=timezone.utc)
    # Supply exactly 1 fewer step than required
    partial_steps = required_steps - 1
    partial_series = []
    for i in range(partial_steps):
        t = anchor - timedelta(minutes=30 * (partial_steps - 1 - i))
        partial_series.append({
            "timestamp": t,
            "accumulation_mm": 1.5,
            "status": QualityStatus.VALID.value,
        })

    res = TemporalRainfallAggregator.aggregate_window(partial_series, anchor, horizon)
    assert res["accumulation_mm"] is None
    assert res["status"] == QualityStatus.MISSING.value
    assert res["steps_available"] == partial_steps
    assert res["steps_required"] == required_steps


def test_temporal_aggregation_missing_intervals_returns_missing_status():
    """
    CRITICAL ZERO FABRICATION TEST:
    If intervals are missing, aggregation must return None with QualityStatus.MISSING.
    Must NEVER fill missing intervals with synthetic zeroes.
    """
    anchor = datetime(2023, 7, 12, 12, 0, tzinfo=timezone.utc)
    # Only supply 20 steps for a 24-hour window (requires 48)
    incomplete_series = []
    for i in range(20):
        t = anchor - timedelta(minutes=30 * (19 - i))
        incomplete_series.append({
            "timestamp": t,
            "accumulation_mm": 2.0,
            "status": QualityStatus.VALID.value,
        })

    res_24h = TemporalRainfallAggregator.aggregate_window(incomplete_series, anchor, "24h")
    assert res_24h["accumulation_mm"] is None
    assert res_24h["status"] == QualityStatus.MISSING.value
    assert res_24h["steps_available"] == 20
    assert res_24h["steps_required"] == 48


def test_temporal_aggregation_duplicate_timestamps_rejected():
    """Verify that duplicate timestamps in time series raise ValueError."""
    anchor = datetime(2023, 7, 12, 12, 0, tzinfo=timezone.utc)
    t1 = anchor - timedelta(minutes=30)
    series_with_dups = [
        {"timestamp": t1, "accumulation_mm": 1.0, "status": "VALID"},
        {"timestamp": t1, "accumulation_mm": 2.0, "status": "VALID"},  # Duplicate!
        {"timestamp": anchor, "accumulation_mm": 1.0, "status": "VALID"},
    ]
    with pytest.raises(ValueError) as exc:
        TemporalRainfallAggregator.aggregate_window(series_with_dups, anchor, "1h")
    assert "Duplicate timestamp detected" in str(exc.value)


def test_temporal_aggregation_anomaly_index():
    """Verify standardized rainfall anomaly calculation and explicit unavailable handling."""
    # Baseline mean 20.0, std 10.0; Observed 40.0 -> z = (40 - 20) / 10 = +2.0
    z = TemporalRainfallAggregator.calculate_anomaly_index(
        rainfall_24h_mm=40.0,
        climatological_mean_24h_mm=20.0,
        climatological_std_24h_mm=10.0,
    )
    assert z == 2.0

    # When std is 0 or negative, returns None (explicit unavailable status)
    assert TemporalRainfallAggregator.calculate_anomaly_index(40.0, 20.0, 0.0) is None
    assert TemporalRainfallAggregator.calculate_anomaly_index(40.0, 20.0, -5.0) is None

    # When baseline mean or std is None, returns None
    assert TemporalRainfallAggregator.calculate_anomaly_index(40.0, None, 10.0) is None
    assert TemporalRainfallAggregator.calculate_anomaly_index(40.0, 20.0, None) is None

    # When rainfall is None, returns None
    assert TemporalRainfallAggregator.calculate_anomaly_index(None, 20.0, 10.0) is None


# ==============================================================================
# 4. SPATIAL NORMALIZATION & RESOLUTION PRESERVATION
# ==============================================================================

def test_spatial_extractor_preserves_native_resolution():
    """
    Verify IMERG native ~0.1 deg spatial resolution is preserved.
    NEVER claims 30m resolution for macro-scale satellite precipitation.
    """
    extractor = SpatialRainfallExtractor()
    meta = extractor.get_source_resolution_metadata()
    assert meta["native_spatial_resolution"] == "0.1 degree x 0.1 degree (~10 km x ~10 km at equator)"
    assert meta["resampling_applied_to_30m"] is False
    assert meta["crs"] == "EPSG:4326 (WGS 84)"


def test_spatial_extractor_grid_cell_id_mapping():
    """Verify coordinate mapping to canonical 0.1-degree cell identifier."""
    # Patna coordinates (25.60N, 85.15E) -> IMERG_010DEG_25.60N_85.10E or 85.20E
    cell_id = SpatialRainfallExtractor.coordinate_to_grid_cell_id(25.60, 85.15)
    assert cell_id.startswith("IMERG_010DEG_")
    assert "25.60N" in cell_id


# ==============================================================================
# 5. REPRESENTATIVE 5-BASIN PILOT VALIDATION
# ==============================================================================

@pytest.mark.parametrize("domain_id,expected_basin_name,min_24h_mm", [
    ("ganga_patna", "Ganga River Basin", 100.0),
    ("brahmaputra_guwahati", "Brahmaputra River Basin", 200.0),
    ("godavari_nashik", "Godavari River Basin", 100.0),
    ("narmada_bharuch", "Narmada River Basin", 150.0),
    ("deep_mumbai_mithi", "Mithi Coastal Catchment (Mumbai)", 250.0),
])
def test_pilot_basin_historical_rainfall_benchmarks(domain_id, expected_basin_name, min_24h_mm):
    """Verify that all 5 pilot basins contain valid historical rainfall benchmarks."""
    service = IndiaRainfallService()
    res = service.get_basin_rainfall(domain_id)

    assert res is not None
    assert res["domain_id"] == domain_id
    assert res["basin_name"] == expected_basin_name
    assert res["rainfall_24h_mm"] >= min_24h_mm
    assert res["rainfall_1h_mm"] > 0.0
    assert res["rainfall_72h_mm"] >= res["rainfall_24h_mm"]
    assert res["product_type"] == RainfallProductType.LITERATURE_DERIVED_BENCHMARK.value
    assert res["is_benchmark"] is True
    assert res["is_operational"] is False
    assert res["is_forecast"] is False
    assert res["quality_status"] == QualityStatus.VALID.value
    assert res["provenance"]["zero_fabrication_enforced"] is True


# ==============================================================================
# 6. ZERO FABRICATION OUTSIDE PILOT COVERAGE
# ==============================================================================

def test_zero_fabrication_outside_pilot_coverage():
    """
    Verify coordinates outside pilot domains return None.
    NEVER silently falls back to Mumbai or generates synthetic rainfall.
    """
    service = IndiaRainfallService()

    # Query coordinate in Thar Desert (unregistered domain)
    res_desert = service.sample_rainfall_at_location(27.0, 71.0)
    assert res_desert is None, "Unverified desert point must return None (Zero Fabrication)"

    # Query coordinate in Arabian Sea
    res_sea = service.sample_rainfall_at_location(15.0, 65.0)
    assert res_sea is None, "Ocean point must return None"

    # Query non-existent basin domain ID
    res_unknown = service.get_basin_rainfall("unregistered_basin_xyz")
    assert res_unknown is None


# ==============================================================================
# 7. OBSERVATION VS FORECAST SEPARATION
# ==============================================================================

@pytest.mark.asyncio
async def test_forecast_observation_strict_separation(monkeypatch):
    """Verify operational NWP forecast is strictly labeled as FORECAST, never observation."""
    service = IndiaRainfallService()

    # Historical observation / benchmark
    obs = service.get_basin_rainfall("ganga_patna")
    assert obs["is_forecast"] is False
    assert obs["product_type"] == RainfallProductType.LITERATURE_DERIVED_BENCHMARK.value
    assert obs["is_benchmark"] is True

    # Deterministic mock for operational forecast
    now_dt = datetime.now(timezone.utc)
    async def mock_fetch_raw(self, latitude: float, longitude: float, forecast_days: int = 1):
        return {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "hourly": {
                "time": [(now_dt + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00") for h in range(24)],
                "precipitation": [0.5 for _ in range(24)],
            },
        }

    monkeypatch.setattr(OpenMeteoForecastProvider, "_fetch_raw_ecmwf_payload", mock_fetch_raw)

    # Operational forecast
    fcst = await service.get_precipitation_forecast(latitude=25.6, longitude=85.15, lead_time_minutes=60)
    assert fcst.provenance.get("data_class") == RainfallProductType.OPERATIONAL_FORECAST.value
    assert fcst.provenance.get("is_historical_observation") is False


@pytest.mark.asyncio
async def test_forecast_no_silent_fallback_on_upstream_failure(monkeypatch):
    """
    CRITICAL NO SILENT FALLBACK TEST:
    Verify that if the live NWP forecast provider fails in operational mode (allow_synthetic_fallback=False),
    it raises an explicit RuntimeError rather than silently substituting synthetic or Mumbai forecast.
    """
    service = IndiaRainfallService()

    async def mock_failing_fetch(*args, **kwargs):
        raise ConnectionError("Upstream ECMWF API connection timeout")

    monkeypatch.setattr(service.forecast_provider, "fetch_forecast", mock_failing_fetch)

    # In operational mode (allow_synthetic_fallback=False), must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        await service.get_precipitation_forecast(
            latitude=25.6,
            longitude=85.15,
            lead_time_minutes=60,
            allow_synthetic_fallback=False,
        )
    assert "No silent synthetic fallback is permitted in operational mode" in str(exc_info.value)

    # When explicit fallback is enabled (for test environments), it must explicitly tag the payload
    synth_fcst = await service.get_precipitation_forecast(
        latitude=25.6,
        longitude=85.15,
        lead_time_minutes=60,
        allow_synthetic_fallback=True,
    )
    assert synth_fcst.provenance.get("is_synthetic_fallback") is True
    assert "Live upstream provider unreachable" in synth_fcst.provenance.get("fallback_reason", "")


# ==============================================================================
# 8. DATA CONTRACT INTEGRATION & BENCHMARK ISOLATION
# ==============================================================================

def test_contract_genuine_measured_zero_remains_valid():
    """
    Regression Test 1: A genuine measured zero-rainfall observation remains valid (0.0).
    Verifies that observed zero precipitation is preserved and not confused with unavailable data.
    """
    # 1. National Data Contract with genuine zero observation
    nat_contract = IndiaSpatialService.build_national_data_contract(
        latitude=25.60,
        longitude=85.15,
        rainfall_1h_mm=0.0,
        rainfall_24h_mm=0.0,
        rainfall_anomaly_index=0.0,
    )
    assert isinstance(nat_contract, NationalDataContract)
    assert nat_contract.rainfall_1h_mm == 0.0
    assert nat_contract.rainfall_24h_mm == 0.0
    assert nat_contract.rainfall_anomaly_index == 0.0
    assert nat_contract.rainfall_available is True
    assert nat_contract.rainfall_operational_status == "OPERATIONAL_OBSERVATION_AVAILABLE"
    assert nat_contract.rainfall_provenance == "AUTHENTIC_OBSERVATION"

    # 2. Regional Data Contract with genuine zero observation
    reg_contract = IndiaSpatialService.build_regional_data_contract(
        latitude=25.60,
        longitude=85.15,
        rainfall_24h_mm=0.0,
    )
    assert isinstance(reg_contract, RegionalDataContract)
    assert reg_contract.rainfall_24h_mm == 0.0
    assert reg_contract.rainfall_available is True
    assert reg_contract.rainfall_operational_status == "OPERATIONAL_OBSERVATION_AVAILABLE"
    assert reg_contract.rainfall_provenance == "AUTHENTIC_OBSERVATION"


def test_contract_missing_rainfall_remains_unavailable_not_zero():
    """
    Regression Test 2: Missing or unavailable rainfall remains explicitly unavailable (None).
    Guarantees that missing operational observations are NEVER silently converted to 0.0.
    """
    # 1. National Data Contract in operational mode with omitted rainfall
    nat_contract = IndiaSpatialService.build_national_data_contract(
        latitude=25.60,
        longitude=85.15,
        allow_benchmark_rainfall=False,
    )
    assert isinstance(nat_contract, NationalDataContract)
    assert nat_contract.rainfall_1h_mm is None, "Missing rainfall must be None, NOT defaulted to 0.0"
    assert nat_contract.rainfall_3h_mm is None, "Missing rainfall must be None, NOT defaulted to 0.0"
    assert nat_contract.rainfall_6h_mm is None, "Missing rainfall must be None, NOT defaulted to 0.0"
    assert nat_contract.rainfall_24h_mm is None, "Missing rainfall must be None, NOT defaulted to 0.0"
    assert nat_contract.rainfall_72h_mm is None, "Missing rainfall must be None, NOT defaulted to 0.0"
    assert nat_contract.rainfall_anomaly_index is None, "Missing anomaly must be None, NOT defaulted to 0.0"
    assert nat_contract.rainfall_available is False, "Operational rainfall must be marked unavailable"
    assert nat_contract.rainfall_operational_status == "OPERATIONAL_OBSERVATION_UNAVAILABLE"
    assert nat_contract.rainfall_provenance == "UNAVAILABLE"

    # Crucial assertion: unavailable rainfall is not 0.0
    assert nat_contract.rainfall_24h_mm != 0.0, "Zero-fabrication violation: missing data represented as 0.0"

    # 2. Regional Data Contract in operational mode with omitted rainfall
    reg_contract = IndiaSpatialService.build_regional_data_contract(
        latitude=25.60,
        longitude=85.15,
        allow_benchmark_rainfall=False,
    )
    assert isinstance(reg_contract, RegionalDataContract)
    assert reg_contract.rainfall_24h_mm is None
    assert reg_contract.rainfall_available is False
    assert reg_contract.rainfall_operational_status == "OPERATIONAL_OBSERVATION_UNAVAILABLE"
    assert reg_contract.rainfall_provenance == "UNAVAILABLE"


def test_contract_benchmark_isolation_by_default():
    """
    Regression Test 3: Benchmark data cannot enter operational contracts by default.
    Ensures that calling build_national_data_contract without explicit benchmark flag
    never injects synthetic benchmark deluge data.
    """
    contract_op = IndiaSpatialService.build_national_data_contract(
        latitude=25.60,
        longitude=85.15,
    )
    assert isinstance(contract_op, NationalDataContract)
    # The Ganga Patna benchmark has 184.6 mm 24h peak; ensure it is NOT injected
    assert contract_op.rainfall_24h_mm is None
    assert contract_op.rainfall_24h_mm != 184.6
    assert contract_op.rainfall_available is False
    assert contract_op.rainfall_provenance != "LITERATURE_DERIVED_BENCHMARK"
    assert contract_op.rainfall_provenance == "UNAVAILABLE"


def test_contract_explicit_benchmark_retains_non_operational_provenance():
    """
    Regression Test 4: Explicit benchmark mode retains clear non-operational provenance.
    """
    contract_dev = IndiaSpatialService.build_national_data_contract(
        latitude=25.60,
        longitude=85.15,
        allow_benchmark_rainfall=True,
    )
    assert isinstance(contract_dev, NationalDataContract)
    assert contract_dev.rainfall_24h_mm == 184.6
    assert contract_dev.rainfall_available is True
    assert contract_dev.rainfall_operational_status == "NON_OPERATIONAL_TEST_FIXTURE"
    assert contract_dev.rainfall_provenance == "LITERATURE_DERIVED_BENCHMARK"


def test_existing_contract_consumers_backward_compatibility():
    """
    Regression Test 5: Existing contract consumers and regression tests remain functional.
    - Explicit non-zero values override defaults cleanly.
    - Direct NationalDataContract instantiation works with and without rainfall fields.
    """
    # 1. Explicit override with non-zero values
    contract = IndiaSpatialService.build_national_data_contract(
        latitude=25.60,
        longitude=85.15,
        rainfall_1h_mm=15.0,
        rainfall_24h_mm=95.0,
    )
    assert isinstance(contract, NationalDataContract)
    assert contract.rainfall_1h_mm == 15.0
    assert contract.rainfall_24h_mm == 95.0
    assert contract.rainfall_available is True
    assert contract.rainfall_operational_status == "OPERATIONAL_OBSERVATION_AVAILABLE"
    assert contract.rainfall_provenance == "AUTHENTIC_OBSERVATION"

    # 2. Direct Pydantic model instantiation with omitted optional rainfall
    direct_contract = NationalDataContract(
        latitude=25.60,
        longitude=85.15,
        elevation_m=53.0,
        slope_deg=1.2,
        distance_to_river_m=120.0,
        historical_flood_frequency_score=0.45,
        landcover_class=10,
    )
    assert direct_contract.rainfall_24h_mm is None
    assert direct_contract.elevation_m == 53.0


def test_downstream_deep_data_contract_missing_rainfall_unavailable():
    """
    Downstream Audit Test: DeepDataContract in operational mode without rainfall.
    Ensures Deep Intelligence Level 3 contracts do NOT convert None to 0.0,
    and explicitly declare operational observations unavailable.
    """
    deep_contract = IndiaSpatialService.build_deep_data_contract(
        latitude=19.076,
        longitude=72.8777,
        flow_accumulation_cells=1500,
        modeled_depth_m=1.2,
        allow_benchmark_rainfall=False,
    )
    assert isinstance(deep_contract, DeepDataContract)
    assert deep_contract.rainfall_1h_mm is None
    assert deep_contract.rainfall_24h_mm is None
    assert deep_contract.rainfall_available is False
    assert deep_contract.rainfall_operational_status == "OPERATIONAL_OBSERVATION_UNAVAILABLE"
    assert deep_contract.rainfall_provenance == "UNAVAILABLE"
    assert deep_contract.flow_accumulation_cells == 1500
    assert deep_contract.modeled_depth_m == 1.2

    # Invariant: missing rainfall must never evaluate to 0.0
    assert deep_contract.rainfall_24h_mm != 0.0


def test_downstream_deep_data_contract_genuine_zero_preserved():
    """
    Downstream Audit Test: DeepDataContract with genuine measured zero rainfall.
    Ensures measured zero is preserved without confusion with unavailable data.
    """
    deep_contract = IndiaSpatialService.build_deep_data_contract(
        latitude=19.076,
        longitude=72.8777,
        rainfall_1h_mm=0.0,
        rainfall_24h_mm=0.0,
        rainfall_anomaly_index=0.0,
        flow_accumulation_cells=500,
    )
    assert isinstance(deep_contract, DeepDataContract)
    assert deep_contract.rainfall_1h_mm == 0.0
    assert deep_contract.rainfall_24h_mm == 0.0
    assert deep_contract.rainfall_available is True
    assert deep_contract.rainfall_operational_status == "OPERATIONAL_OBSERVATION_AVAILABLE"
    assert deep_contract.rainfall_provenance == "AUTHENTIC_OBSERVATION"


def test_downstream_anomaly_calculation_safely_handles_none_vs_zero():
    """
    Downstream Audit Test: Climatological anomaly estimation safely handles None vs 0.0.
    - If rainfall_24h_mm is None: returns None (unavailable, does not crash or assume float).
    - If rainfall_24h_mm is 0.0: returns valid negative z-score ((0 - 32) / 25 = -1.28).
    """
    from app.services.india_rainfall_service import TemporalRainfallAggregator

    # 1. Unavailable rainfall -> None
    z_none = TemporalRainfallAggregator.calculate_anomaly_index(None, 32.0, 25.0)
    assert z_none is None, "Missing rainfall must return None anomaly, not a fabricated number"

    # 2. Measured zero rainfall -> valid calculation
    z_zero = TemporalRainfallAggregator.calculate_anomaly_index(0.0, 32.0, 25.0)
    assert z_zero == -1.28, "Measured zero rainfall must calculate valid climatological deviation"



def test_populate_national_rainfall_isolation():
    """Verify populate_national_rainfall isolates benchmarks and requires explicit opt-in."""
    service = IndiaRainfallService()

    # 1. Operational default: unavailable
    rain_op = service.populate_national_rainfall(25.60, 85.15, allow_benchmark=False)
    assert rain_op["rainfall_available"] is False
    assert rain_op["rainfall_24h_mm"] is None
    assert rain_op["is_benchmark"] is False
    assert rain_op["operational_status"] == "OPERATIONAL_OBSERVATION_UNAVAILABLE"

    # 2. Benchmark opt-in for testing
    rain_dev = service.populate_national_rainfall(25.60, 85.15, allow_benchmark=True)
    assert rain_dev["rainfall_available"] is True
    assert rain_dev["rainfall_24h_mm"] > 0.0
    assert rain_dev["is_benchmark"] is True
    assert rain_dev["operational_claim"] == "NON_OPERATIONAL_TEST_FIXTURE"
    assert rain_dev["rainfall_product_type"] == RainfallProductType.LITERATURE_DERIVED_BENCHMARK.value


# ==============================================================================
# 9. REST API ENDPOINTS & BENCHMARK ISOLATION
# ==============================================================================

def test_api_rainfall_auth_status():
    """Verify /rainfall/auth-status endpoint returns safe inspection dictionary."""
    resp = client.get("/api/v1/rainfall/auth-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "can_download_raw_imerg" in data
    assert "auth_details" in data


def test_api_rainfall_basin_endpoint():
    """Verify /rainfall/basin/{domain_id} endpoint returns explicit non-operational benchmark."""
    resp = client.get("/api/v1/rainfall/basin/ganga_patna")
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain_id"] == "ganga_patna"
    assert data["rainfall_24h_mm"] > 0.0
    assert data["product_type"] == RainfallProductType.LITERATURE_DERIVED_BENCHMARK.value
    assert data["is_benchmark"] is True
    assert data["is_operational"] is False
    assert data["provenance"]["operational_claim"] == "NON_OPERATIONAL_TEST_FIXTURE"

    # Unregistered basin domain returns 404 (Zero Fabrication)
    resp_404 = client.get("/api/v1/rainfall/basin/nonexistent_basin")
    assert resp_404.status_code == 404
    assert "Zero Fabrication" in resp_404.json()["detail"]


def test_api_rainfall_sample_endpoint_benchmark_isolation():
    """Verify /rainfall/sample endpoint enforces benchmark isolation."""
    # 1. Operational query without allow_benchmark returns 404
    resp_op = client.get("/api/v1/rainfall/sample?lat=25.60&lon=85.15")
    assert resp_op.status_code == 404
    assert "Operational gridded precipitation observations unavailable" in resp_op.json()["detail"]
    assert "pass allow_benchmark=true" in resp_op.json()["detail"]

    # 2. Explicit benchmark query returns 200 with non-operational fixture
    resp_dev = client.get("/api/v1/rainfall/sample?lat=25.60&lon=85.15&allow_benchmark=true")
    assert resp_dev.status_code == 200
    data = resp_dev.json()
    assert data["rainfall_24h_mm"] > 0.0
    assert data["is_benchmark"] is True
    assert data["is_operational"] is False
    assert data["product_type"] == RainfallProductType.LITERATURE_DERIVED_BENCHMARK.value

    # 3. Outside pilot domains returns 404
    resp_outside = client.get("/api/v1/rainfall/sample?lat=15.0&lon=65.0&allow_benchmark=true")
    assert resp_outside.status_code == 404


def test_api_rainfall_forecast_endpoint_deterministic(monkeypatch):
    """Verify /rainfall/forecast endpoint returns operational forecast with deterministic mock."""
    from app.schemas.rainfall import RainfallForecastSchema, QualityStatus

    now = datetime.now(timezone.utc)
    mock_fcst = RainfallForecastSchema(
        dataset_identifier="FCST_ECMWF_MOCK_001",
        provider="OPEN_METEO_ECMWF",
        model_name="ECMWF_IFS",
        model_version="Cycle 48r1",
        initialization_time=now,
        valid_time=now + timedelta(minutes=60),
        lead_time_minutes=60,
        resolution_deg=(0.1, 0.1),
        units="mm",
        quality_status=QualityStatus.VALID,
        bounds=(85.10, 25.55, 85.20, 25.65),
        provenance={
            "provider": "OPEN_METEO_ECMWF",
            "data_mode": "MOCK_DETERMINISTIC",
            "is_historical_observation": False,
            "data_class": RainfallProductType.OPERATIONAL_FORECAST.value,
        },
    )

    async def mock_fetch(*args, **kwargs):
        return mock_fcst

    from app.services.india_rainfall_service import IndiaRainfallService
    monkeypatch.setattr(IndiaRainfallService, "get_precipitation_forecast", lambda self, *args, **kwargs: mock_fetch())

    resp = client.get("/api/v1/rainfall/forecast?lat=25.60&lon=85.15&lead_time_minutes=60")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provenance"]["data_class"] == RainfallProductType.OPERATIONAL_FORECAST.value
    assert data["provenance"]["is_historical_observation"] is False


def test_api_rainfall_forecast_upstream_failure_returns_503(monkeypatch):
    """
    Verify /rainfall/forecast returns HTTP 503 Service Unavailable when upstream provider fails.
    Confirms NO synthetic forecast is silently substituted in production.
    """
    async def mock_failing_forecast(*args, **kwargs):
        raise RuntimeError("ECMWF IFS upstream provider connection timeout")

    from app.services.india_rainfall_service import IndiaRainfallService
    monkeypatch.setattr(IndiaRainfallService, "get_precipitation_forecast", mock_failing_forecast)

    resp = client.get("/api/v1/rainfall/forecast?lat=25.60&lon=85.15&lead_time_minutes=60")
    assert resp.status_code == 503
    detail = resp.json()["detail"]
    assert "Operational forecast upstream unavailable" in detail
    assert "No silent synthetic fallback permitted" in detail


# ==============================================================================
# 10. MUMBAI REGRESSION & BACKWARD COMPATIBILITY
# ==============================================================================

def test_mumbai_event_rainfall_raster_backward_compatibility():
    """Verify existing Mumbai event raster loader behavior and zero fabrication on missing files."""
    provider = IMERGRainfallProvider()
    assert provider.provider_id == "NASA_GPM_IMERG"
    assert provider.version == "V07B"

    # Non-existent event safely raises FileNotFoundError (Zero Fabrication, no synthetic fallback)
    with pytest.raises(FileNotFoundError):
        provider.load_event_rainfall_raster(event_id="NON_EXISTENT_EVENT_XYZ")


# ==============================================================================
# 11. DATA PROVENANCE TRANSPARENCY, RECONCILIATION & MANIFEST VERIFICATION
# ==============================================================================

def test_basin_rainfall_provenance_transparency():
    """
    Verify get_basin_rainfall provenance explicitly discloses that current pilot datasets
    are LITERATURE_DERIVED_BENCHMARK fixtures and NOT authentic live satellite downloads.
    """
    service = IndiaRainfallService()
    res = service.get_basin_rainfall("ganga_patna")
    assert res is not None
    prov = res["provenance"]
    assert prov["dataset_classification"] == "LITERATURE_DERIVED_BENCHMARK"
    assert prov["operational_claim"] == "NON_OPERATIONAL_TEST_FIXTURE"
    assert prov["is_authentic_satellite_download"] is False
    assert prov["zero_fabrication_enforced"] is True
    assert res["is_benchmark"] is True
    assert res["is_operational"] is False


def test_mithi_benchmark_reconciliation():
    """
    Verify deep_mumbai_mithi benchmark reconciliation:
    - Literature peak 24h deluge: 322.0 mm (August 5, 2020 IMD Santacruz)
    - Fixture sequence: 48 half-hourly steps (24 hours total)
    - Stored fixture accumulation sum: 415.01 mm (scaled by generator to literature multi-day storm total)
    - Sequence-end 24h accumulation: 415.01 mm (z = +15.32)
    - Confirms both quantities are explicitly documented and non-operational.
    """
    service = IndiaRainfallService()
    res = service.get_basin_rainfall("deep_mumbai_mithi")
    assert res is not None
    assert res["domain_id"] == "deep_mumbai_mithi"
    assert res["rainfall_24h_mm"] == 322.0  # Literature peak 24h target
    assert res["rainfall_anomaly_index"] == 11.60

    recon = res["fixture_reconciliation"]
    assert recon["stored_intervals_count"] == 48
    assert recon["stored_duration_hours"] == 24.0
    assert recon["stored_intervals_sum_mm"] == 415.01
    assert recon["sequence_end_24h_mm"] == 415.01
    assert recon["sequence_end_24h_anomaly_index"] == 15.32
    assert recon["literature_peak_24h_mm"] == 322.0
    assert recon["literature_72h_total_mm"] == 415.0
    assert "reconciliation_note" in recon
    assert "Neither value is independently verified against primary IMD" in recon["reconciliation_note"]
    assert "benchmark test fixtures" in recon["reconciliation_note"]



def test_parquet_datasets_provenance_and_non_operational_status():
    """
    Verify all 5 normalized Parquet files exist on disk and are governed by
    explicit literature-derived benchmark status in the manifest.
    """
    import yaml
    from pathlib import Path
    import pandas as pd

    repo_root = Path(__file__).resolve().parents[2]
    manifest_file = repo_root / "data" / "manifests" / "phase2c_rainfall_manifest.yaml"
    assert manifest_file.exists(), "Phase 2C YAML manifest must exist"

    with open(manifest_file, "r") as f:
        manifest = yaml.safe_load(f)

    assert manifest["live_authenticated_acquisition_status"] == "PIPELINE_IMPLEMENTED_LIVE_ACQUISITION_NOT_VERIFIED"
    for ds in manifest["datasets"]:
        if ds["dataset_id"].startswith("P2C-RAIN-"):
            assert ds["status"] == "LITERATURE_DERIVED_BENCHMARK"
            assert "NON_OPERATIONAL_TEST_FIXTURE" in ds["operational_claim"]
            assert ds["source_authenticity"] == "UNVERIFIED_NO_RAW_IMERG_GRANULES"
            pq_path = repo_root / ds["processed_path"]
            assert pq_path.exists(), f"Normalized Parquet file {pq_path} must exist"
            df = pd.read_parquet(pq_path)
            assert len(df) > 0


@pytest.mark.asyncio
async def test_ecmwf_forecast_unit_deterministic_mock(monkeypatch):
    """
    Deterministic unit test for OpenMeteoForecastProvider without external network access.
    Validates parsing, schema conformance, and fail-safe policy.
    """
    service = IndiaRainfallService()

    now_dt = datetime.now(timezone.utc)
    async def mock_fetch_raw(self, latitude: float, longitude: float, forecast_days: int = 1):
        return {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "hourly": {
                "time": [(now_dt + timedelta(hours=h)).strftime("%Y-%m-%dT%H:00") for h in range(24)],
                "precipitation": [round(float(h) * 0.2, 2) for h in range(24)],
            },
        }

    monkeypatch.setattr(OpenMeteoForecastProvider, "_fetch_raw_ecmwf_payload", mock_fetch_raw)

    fcst = await service.get_precipitation_forecast(
        latitude=25.60,
        longitude=85.15,
        lead_time_minutes=60,
        allow_synthetic_fallback=False,
    )
    assert fcst is not None
    assert fcst.lead_time_minutes == 60
    assert fcst.units == "mm"
    assert fcst.provenance.get("provider") == "OPEN_METEO_ECMWF"
    assert fcst.provenance.get("is_historical_observation") is False
    assert fcst.provenance.get("data_class") == RainfallProductType.OPERATIONAL_FORECAST.value


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_NWP_TESTS"),
    reason="Opt-in live network test; set RUN_LIVE_NWP_TESTS=1 to run against live Open-Meteo ECMWF API",
)
@pytest.mark.asyncio
async def test_live_ecmwf_forecast_verified_operational():
    """
    Opt-in live query against ECMWF IFS Open Data via Open-Meteo.
    Validates real NWP payload, UTC valid times, and fail-safe policy over network.
    """
    service = IndiaRainfallService()
    fcst = await service.get_precipitation_forecast(
        latitude=25.60,
        longitude=85.15,
        lead_time_minutes=60,
        allow_synthetic_fallback=False,
    )
    assert fcst is not None
    assert fcst.lead_time_minutes == 60
    assert fcst.units == "mm"
    assert fcst.provenance.get("provider") == "OPEN_METEO_ECMWF"
    assert fcst.provenance.get("data_mode") == "REAL_DATA"
    assert fcst.provenance.get("is_historical_observation") is False
    assert fcst.provenance.get("data_class") == RainfallProductType.OPERATIONAL_FORECAST.value

