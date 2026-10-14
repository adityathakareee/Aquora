"""
AQUORA Phase 2E — National Flood Feature Pipeline API Endpoints.

Exposes REST endpoints for:
1. Schema inspection: GET /api/v1/features/schema
2. Single-point feature extraction: POST /api/v1/features/extract/point
3. Bounded batch grid extraction: POST /api/v1/features/extract/batch
"""

import base64
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.features import (
    BatchGridFeatureExtractionRequest,
    BatchGridFeatureExtractionResponse,
    FeatureSchemaMetadataResponse,
    PointFeatureExtractionRequest,
    PointFeatureExtractionResponse,
)
from app.services.india_feature_pipeline import IndiaFeaturePipelineService

router = APIRouter(prefix="/features", tags=["Flood Feature Pipeline (Phase 2E)"])
feature_pipeline_service = IndiaFeaturePipelineService()


@router.get(
    "/schema",
    response_model=FeatureSchemaMetadataResponse,
    summary="Inspect Multiscale Feature Pipeline Schema",
    description="Returns the authoritative aquora_ml_feature_schema_v1 metadata, tier breakdown, and field definitions.",
)
async def get_feature_schema():
    raw_schema = feature_pipeline_service._load_schema()
    tiers = raw_schema.get("tiers", {})
    return FeatureSchemaMetadataResponse(
        schema_name=raw_schema.get("schema_name", "aquora_ml_feature_schema_v1"),
        schema_version=raw_schema.get("schema_version", "1.0.0"),
        created_at=raw_schema.get("created_at", "2026-10-07T00:00:00Z"),
        governance=raw_schema.get("governance", {}),
        tiers=tiers,
        total_features=len(feature_pipeline_service.ALL_20_FEATURES),
    )


@router.post(
    "/extract/point",
    response_model=PointFeatureExtractionResponse,
    summary="Extract Multiscale Features for a Point",
    description="Extracts the 20-feature predictor vector for given coordinates adhering strictly to tier gating and missing-data invariants.",
)
async def extract_point_features(request: PointFeatureExtractionRequest):
    try:
        response = feature_pipeline_service.extract_point_features(
            latitude=request.latitude,
            longitude=request.longitude,
            timestamp=request.timestamp,
            allow_benchmark_rainfall=request.allow_benchmark_rainfall,
            include_candidate_target=request.include_candidate_target,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature extraction failed: {str(e)}",
        )


@router.post(
    "/extract/batch",
    response_model=BatchGridFeatureExtractionResponse,
    summary="Extract Bounded Batch Grid Features",
    description="Samples features across a bounding box with bounded points and exports as structured JSON or Parquet buffer.",
)
async def extract_batch_features(request: BatchGridFeatureExtractionRequest):
    try:
        records = feature_pipeline_service.extract_batch_grid(
            min_lat=request.min_lat,
            max_lat=request.max_lat,
            min_lon=request.min_lon,
            max_lon=request.max_lon,
            grid_resolution_deg=request.grid_resolution_deg,
            timestamp=request.timestamp,
            allow_benchmark_rainfall=request.allow_benchmark_rainfall,
        )

        bbox_dict = {
            "min_lat": request.min_lat,
            "max_lat": request.max_lat,
            "min_lon": request.min_lon,
            "max_lon": request.max_lon,
        }

        if request.export_format == "parquet_base64":
            df = feature_pipeline_service.export_records_to_dataframe(records)
            parquet_bytes = feature_pipeline_service.export_dataframe_to_parquet_bytes(df)
            b64_str = base64.b64encode(parquet_bytes).decode("ascii")
            return BatchGridFeatureExtractionResponse(
                point_count=len(records),
                bounding_box=bbox_dict,
                grid_resolution_deg=request.grid_resolution_deg,
                records=None,
                parquet_base64=b64_str,
                parquet_byte_size=len(parquet_bytes),
                schema_version="1.0.0",
            )

        return BatchGridFeatureExtractionResponse(
            point_count=len(records),
            bounding_box=bbox_dict,
            grid_resolution_deg=request.grid_resolution_deg,
            records=records,
            parquet_base64=None,
            parquet_byte_size=None,
            schema_version="1.0.0",
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch feature extraction failed: {str(e)}",
        )
