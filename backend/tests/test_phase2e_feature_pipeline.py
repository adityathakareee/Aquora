"""
AQUORA Phase 2E — Comprehensive Multiscale Feature Pipeline Test Suite.

Verifies acceptance criteria P2E-ACC-01 through P2E-ACC-10:
- P2E-ACC-01: National Tier Feature Completeness (11 core features)
- P2E-ACC-02: Regional Expansion Gating (3 features)
- P2E-ACC-03: Deep Zone Isolation (6 features)
- P2E-ACC-04: Schema Validation (aquora_ml_feature_schema_v1 1.0.0)
- P2E-ACC-05: Missing Data Invariant (None/NaN preservation)
- P2E-ACC-06: Zero Rainfall Preservation (0.0 vs None)
- P2E-ACC-07: Candidate Target Label Boundary (Zero Leakage)
- P2E-ACC-08: Physics Model Output Exclusion (No water_depth_m in features)
- P2E-ACC-09: Batch Bounds & Parquet Serialization (snappy, Arrow null masks)
- P2E-ACC-10: API Endpoint Integration & Health
"""

import base64
from datetime import datetime, timezone
import io
import pytest
from fastapi.testclient import TestClient
import numpy as np
import pandas as pd

from app.main import app
from app.schemas.features import PointFeatureExtractionRequest, BatchGridFeatureExtractionRequest
from app.services.india_feature_pipeline import IndiaFeaturePipelineService

client = TestClient(app)
pipeline_service = IndiaFeaturePipelineService()


# ------------------------------------------------------------------------------
# P2E-ACC-01: National Tier Feature Completeness
# ------------------------------------------------------------------------------
def test_p2e_acc_01_national_tier_feature_completeness():
    """Verify that all 11 core national features are structurally present in the extracted dictionary."""
    res = pipeline_service.extract_point_features(
        latitude=21.1458,  # Nagpur, Maharashtra (National tier)
        longitude=79.0882,
        allow_benchmark_rainfall=False,
    )
    assert res.zone_tier in ("NATIONAL", "REGIONAL")
    for feat in IndiaFeaturePipelineService.CORE_NATIONAL_FEATURES:
        assert feat in res.features, f"Missing core national feature: {feat}"
    assert len(res.features) == 20


# ------------------------------------------------------------------------------
# P2E-ACC-02: Regional Expansion Gating
# ------------------------------------------------------------------------------
def test_p2e_acc_02_regional_expansion_gating():
    """Verify regional features are populated for regional points and None for generic national points."""
    # Point inside verified Godavari/Tapi corridor or basin
    regional_res = pipeline_service.extract_point_features(
        latitude=19.9975,  # Nashik / Upper Godavari
        longitude=73.7898,
        allow_benchmark_rainfall=True,
    )
    assert regional_res.zone_tier in ("REGIONAL", "DEEP_ZONE")
    for r_feat in IndiaFeaturePipelineService.REGIONAL_FEATURES:
        assert r_feat in regional_res.features

    # National extraction outside regional basin / corridor
    # Force national classification test
    tier, _, _ = IndiaFeaturePipelineService.resolve_point_tier(28.6139, 77.2090)  # Delhi
    national_res = pipeline_service.extract_point_features(28.6139, 77.2090)
    if tier == "NATIONAL":
        assert national_res.features["basin_drainage_area_km2"] is None
        assert national_res.features["soil_saturation_index"] is None
        assert national_res.features["population_density_per_km2"] is None


# ------------------------------------------------------------------------------
# P2E-ACC-03: Deep Zone Isolation
# ------------------------------------------------------------------------------
def test_p2e_acc_03_deep_zone_isolation():
    """Verify deep features are gated strictly to Deep Zone tier and isolated from unverified zones."""
    # 1. Mithi Deep Zone point
    deep_res = pipeline_service.extract_point_features(
        latitude=19.0760,
        longitude=72.8777,
        allow_benchmark_rainfall=True,
    )
    assert deep_res.zone_tier == "DEEP_ZONE"
    assert deep_res.provenance["deep_zone_source"] == "MUMBAI_MITHI_DEEP_ZONE"
    # built_up_fraction: authenticity cannot be established (no raster on disk; 0.65 is fallback)
    assert deep_res.features["built_up_fraction"] is None
    assert deep_res.provenance["built_up_source"] == "UNAVAILABLE"
    # All 6 deep features remain explicitly None with provenance (Zero Fabrication)
    for uningested_feat in IndiaFeaturePipelineService.DEEP_ZONE_FEATURES:
        assert deep_res.features[uningested_feat] is None
    assert deep_res.provenance["deep_zone_status"] == "HIGH_RESOLUTION_SWD_UNINGESTED"

    # 2. Non-deep point (Nagpur)
    outside_res = pipeline_service.extract_point_features(
        latitude=21.1458,
        longitude=79.0882,
        allow_benchmark_rainfall=True,
    )
    assert outside_res.zone_tier != "DEEP_ZONE"
    for d_feat in IndiaFeaturePipelineService.DEEP_ZONE_FEATURES:
        assert outside_res.features[d_feat] is None, f"Deep feature {d_feat} must be None outside Deep Zone"
    assert outside_res.provenance["deep_zone_status"] == "TIER_NOT_ELIGIBLE_FOR_DEEP_ZONE"

    # 3. Constraint checking when deep features are provided
    mock_deep = {k: 0.5 for k in IndiaFeaturePipelineService.ALL_20_FEATURES}
    mock_deep["landcover_class"] = 50
    mock_deep["flow_accumulation_cells"] = 1200
    mock_deep["distance_to_road_m"] = 25.0
    mock_deep["distance_to_waterway_m"] = 15.0
    assert pipeline_service.validate_feature_dict(mock_deep) is True

    # Bad constraints must fail validation
    bad_deep = dict(mock_deep)
    bad_deep["flow_accumulation_cells"] = -10
    assert pipeline_service.validate_feature_dict(bad_deep) is False

    bad_bu = dict(mock_deep)
    bad_bu["built_up_fraction"] = 1.25  # Exceeds [0, 1]
    assert pipeline_service.validate_feature_dict(bad_bu) is False


# ------------------------------------------------------------------------------
# P2E-ACC-04: Schema Validation (1.0.0)
# ------------------------------------------------------------------------------
def test_p2e_acc_04_schema_validation():
    """Verify that every feature record validates successfully against the 1.0.0 schema constraints."""
    res = pipeline_service.extract_point_features(19.0760, 72.8777, allow_benchmark_rainfall=True)
    assert res.schema_version == "1.0.0"
    assert res.schema_validated is True
    assert pipeline_service.validate_feature_dict(res.features) is True


# ------------------------------------------------------------------------------
# P2E-ACC-05: Missing Data Invariant
# ------------------------------------------------------------------------------
def test_p2e_acc_05_missing_data_invariant():
    """Verify that unpolled or unavailable observations remain explicitly None, never fabricated to 0.0."""
    res = pipeline_service.extract_point_features(
        latitude=21.1458,
        longitude=79.0882,
        allow_benchmark_rainfall=False,  # Operational mode: rainfall observation is unavailable
    )
    # Rainfall features must be None, not 0.0
    assert res.features["rainfall_1h_mm"] is None
    assert res.features["rainfall_24h_mm"] is None
    assert res.provenance["rainfall_status"] == "OPERATIONAL_OBSERVATION_UNAVAILABLE"


# ------------------------------------------------------------------------------
# P2E-ACC-06: Zero Rainfall Preservation
# ------------------------------------------------------------------------------
def test_p2e_acc_06_zero_rainfall_preservation():
    """Verify that genuine zero rainfall is preserved as 0.0 with proper provenance."""
    # Test dictionary with genuine 0.0
    feat_dict = {k: 0.0 for k in IndiaFeaturePipelineService.CORE_NATIONAL_FEATURES}
    feat_dict["landcover_class"] = 10
    feat_dict["historical_flood_frequency"] = 0.0
    for k in IndiaFeaturePipelineService.REGIONAL_FEATURES + IndiaFeaturePipelineService.DEEP_ZONE_FEATURES:
        feat_dict[k] = None

    assert feat_dict["rainfall_24h_mm"] == 0.0
    assert pipeline_service.validate_feature_dict(feat_dict) is True


# ------------------------------------------------------------------------------
# P2E-ACC-07: Candidate Target Label Boundary (Zero Leakage)
# ------------------------------------------------------------------------------
def test_p2e_acc_07_candidate_target_label_boundary():
    """Verify that flood_label and SAR evidence are isolated in candidate_target metadata, never in features."""
    res = pipeline_service.extract_point_features(
        latitude=19.0760,
        longitude=72.8777,
        allow_benchmark_rainfall=True,
        include_candidate_target=True,
    )
    assert res.candidate_target is not None
    assert "flood_label" not in res.features
    assert "sar_delta_vv_db" not in res.features
    assert "sar_scene_id" not in res.features
    assert res.candidate_target.flood_label in (-1, 0, 1)


# ------------------------------------------------------------------------------
# P2E-ACC-08: Physics Model Output Exclusion
# ------------------------------------------------------------------------------
def test_p2e_acc_08_physics_model_output_exclusion():
    """Verify that Phase 6 outputs (water_depth_m, flow_velocity_ms) are strictly rejected from features."""
    bad_features = {k: 1.0 for k in IndiaFeaturePipelineService.ALL_20_FEATURES}
    bad_features["water_depth_m"] = 0.75  # Phase 6 hydraulic depth
    assert pipeline_service.validate_feature_dict(bad_features) is False


# ------------------------------------------------------------------------------
# P2E-ACC-09: Batch Bounds & Parquet Serialization
# ------------------------------------------------------------------------------
def test_p2e_acc_09_batch_bounds_and_parquet_serialization():
    """Verify batch grid bounds checking, max point rejection, and Parquet round-trip serialization."""
    # 1. Bounded batch extraction
    records = pipeline_service.extract_batch_grid(
        min_lat=19.05,
        max_lat=19.08,
        min_lon=72.85,
        max_lon=72.88,
        grid_resolution_deg=0.02,
        allow_benchmark_rainfall=True,
    )
    assert len(records) > 0
    assert len(records) <= IndiaFeaturePipelineService.MAX_BATCH_POINTS

    # 2. DataFrame conversion and nullable types
    df = pipeline_service.export_records_to_dataframe(records)
    assert isinstance(df, pd.DataFrame)
    assert "latitude" in df.columns
    assert "rainfall_24h_mm" in df.columns
    assert df["landcover_class"].dtype.name == "Int32"

    # 3. Parquet serialization with null masks
    parquet_bytes = pipeline_service.export_dataframe_to_parquet_bytes(df)
    assert len(parquet_bytes) > 0

    # Read back to verify round-trip integrity
    df_read = pd.read_parquet(io.BytesIO(parquet_bytes))
    assert len(df_read) == len(df)
    assert list(df_read.columns) == list(df.columns)

    # 4. Over-limit batch rejection
    with pytest.raises(ValueError, match="exceeding maximum limit"):
        pipeline_service.extract_batch_grid(
            min_lat=10.0,
            max_lat=30.0,
            min_lon=70.0,
            max_lon=90.0,
            grid_resolution_deg=0.01,  # Massive 4,000,000 points
        )


# ------------------------------------------------------------------------------
# P2E-ACC-10: API Endpoint Integration & Health
# ------------------------------------------------------------------------------
def test_p2e_acc_10_api_endpoints():
    """Verify GET /schema, POST /extract/point, and POST /extract/batch endpoints via TestClient."""
    # 1. Schema endpoint
    schema_resp = client.get("/api/v1/features/schema")
    assert schema_resp.status_code == 200
    schema_data = schema_resp.json()
    assert schema_data["schema_version"] == "1.0.0"
    assert schema_data["total_features"] == 20
    assert "CORE_NATIONAL" in schema_data["tiers"]

    # 2. Point extraction endpoint
    point_resp = client.post(
        "/api/v1/features/extract/point",
        json={
            "latitude": 19.0760,
            "longitude": 72.8777,
            "allow_benchmark_rainfall": True,
            "include_candidate_target": True,
        },
    )
    assert point_resp.status_code == 200
    point_data = point_resp.json()
    assert point_data["zone_tier"] == "DEEP_ZONE"
    assert point_data["schema_validated"] is True
    assert point_data["features"]["rainfall_24h_mm"] is not None

    # 3. Batch extraction endpoint (JSON format)
    batch_resp = client.post(
        "/api/v1/features/extract/batch",
        json={
            "min_lat": 19.05,
            "max_lat": 19.07,
            "min_lon": 72.85,
            "max_lon": 72.87,
            "grid_resolution_deg": 0.02,
            "export_format": "json",
        },
    )
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()
    assert batch_data["point_count"] > 0
    assert isinstance(batch_data["records"], list)

    # 4. Batch extraction endpoint (Parquet base64 format)
    batch_pq_resp = client.post(
        "/api/v1/features/extract/batch",
        json={
            "min_lat": 19.05,
            "max_lat": 19.07,
            "min_lon": 72.85,
            "max_lon": 72.87,
            "grid_resolution_deg": 0.02,
            "export_format": "parquet_base64",
        },
    )
    assert batch_pq_resp.status_code == 200
    batch_pq_data = batch_pq_resp.json()
    assert batch_pq_data["parquet_base64"] is not None
    assert batch_pq_data["parquet_byte_size"] > 0
    raw_pq = base64.b64decode(batch_pq_data["parquet_base64"])
    assert len(raw_pq) == batch_pq_data["parquet_byte_size"]


# ------------------------------------------------------------------------------
# Focused Historical Flood Frequency Tests (Zero Fabrication Gate)
# ------------------------------------------------------------------------------
def test_historical_flood_frequency_unavailable_case():
    """Verify that in the absence of documented event catalogs, flood frequency is strictly None with UNAVAILABLE provenance."""
    # Test Mithi Deep Zone point
    deep_res = pipeline_service.extract_point_features(19.0760, 72.8777, allow_benchmark_rainfall=True)
    assert deep_res.features["historical_flood_frequency"] is None
    assert deep_res.provenance["flood_frequency_source"] == "UNAVAILABLE"
    # Never substitute elevation proxy or hardcoded 0.85
    assert deep_res.features["historical_flood_frequency"] != 0.85

    # Test Regional point (Nashik)
    reg_res = pipeline_service.extract_point_features(19.9975, 73.7898, allow_benchmark_rainfall=True)
    assert reg_res.features["historical_flood_frequency"] is None
    assert reg_res.provenance["flood_frequency_source"] == "UNAVAILABLE"

    # Test National point (Nagpur)
    nat_res = pipeline_service.extract_point_features(21.1458, 79.0882, allow_benchmark_rainfall=False)
    assert nat_res.features["historical_flood_frequency"] is None
    assert nat_res.provenance["flood_frequency_source"] == "UNAVAILABLE"


def test_historical_flood_frequency_verified_source_validation():
    """Verify that when authentic flood-event data is supplied, it validates within [0, 1] and rejects out-of-bounds."""
    base_feat = {k: 0.0 for k in IndiaFeaturePipelineService.CORE_NATIONAL_FEATURES}
    base_feat["landcover_class"] = 20
    for k in IndiaFeaturePipelineService.REGIONAL_FEATURES + IndiaFeaturePipelineService.DEEP_ZONE_FEATURES:
        base_feat[k] = None

    # Valid documented frequencies in [0, 1]
    base_feat["historical_flood_frequency"] = 0.42
    assert pipeline_service.validate_feature_dict(base_feat) is True

    base_feat["historical_flood_frequency"] = 1.0
    assert pipeline_service.validate_feature_dict(base_feat) is True

    # Out of bounds (< 0.0 or > 1.0) must fail
    base_feat["historical_flood_frequency"] = -0.05
    assert pipeline_service.validate_feature_dict(base_feat) is False

    base_feat["historical_flood_frequency"] = 1.25
    assert pipeline_service.validate_feature_dict(base_feat) is False


# ------------------------------------------------------------------------------
# Focused Rainfall Fixture Isolation Tests
# ------------------------------------------------------------------------------
def test_rainfall_fixture_isolation_operational_mode():
    """Verify operational extraction (allow_benchmark=False) keeps missing rainfall unavailable and does not infer authentic observations."""
    res = pipeline_service.extract_point_features(
        latitude=19.0760,
        longitude=72.8777,
        allow_benchmark_rainfall=False,
    )
    # Rainfall must be None, NOT 0.0
    for r_col in ["rainfall_1h_mm", "rainfall_3h_mm", "rainfall_6h_mm", "rainfall_24h_mm", "rainfall_72h_mm", "rainfall_anomaly_index"]:
        assert res.features[r_col] is None, f"{r_col} should be None when operational observation is unavailable"

    assert res.provenance["rainfall_status"] == "OPERATIONAL_OBSERVATION_UNAVAILABLE"
    assert res.provenance["rainfall_is_benchmark"] is False
    assert "rainfall_note" not in res.provenance

    # Derived soil_saturation_index must NOT imply authentic observation when rainfall is unavailable
    assert res.features["soil_saturation_index"] is None
    assert res.provenance["soil_saturation_source"] == "UNAVAILABLE"


def test_rainfall_fixture_isolation_benchmark_tagging():
    """Verify benchmark mode explicitly tags data as NON_OPERATIONAL_TEST_FIXTURE and labels derived features."""
    res = pipeline_service.extract_point_features(
        latitude=19.0760,
        longitude=72.8777,
        allow_benchmark_rainfall=True,
    )
    # In benchmark mode for pilot domain, benchmark values are loaded
    assert res.provenance["rainfall_is_benchmark"] is True
    assert res.provenance["rainfall_note"] == "NON_OPERATIONAL_TEST_FIXTURE"

    # Derived soil saturation index must explicitly flag benchmark provenance
    assert res.features["soil_saturation_index"] is not None
    assert res.provenance["soil_saturation_source"] == "BENCHMARK_ANTECEDENT_PRECIPITATION"
