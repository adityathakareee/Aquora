"""
AQUORA 2.0 — Sentinel-1 SAR Schemas.

Defines vendor-neutral schemas for:
- SAR scene discovery and metadata
- Safe acquisition jobs
- SAR preprocessing and bitemporal backscatter delta extraction
- Flood candidate evidence tracking with strict non-fabrication
- Geographic domain coverage and status
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class SARAcquisitionStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    VERIFIED_TARGET = "VERIFIED_TARGET"
    ACQUIRED = "ACQUIRED"
    PROCESSING_PENDING = "PROCESSING_PENDING"
    PROCESSED = "PROCESSED"
    DOWNLOAD_BLOCKED = "DOWNLOAD_BLOCKED"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class SAREvidenceClassification(str, Enum):
    CANDIDATE_EVIDENCE = "CANDIDATE_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"
    BENCHMARK_ONLY = "BENCHMARK_ONLY"


class SARJobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class SARSceneMetadata(BaseModel):
    """Normalized metadata for a single Sentinel-1 GRD IW scene."""
    scene_id: str = Field(..., description="Unique Sentinel-1 SAFE scene identifier")
    event_id: Optional[str] = Field(None, description="Associated disaster or benchmark event ID (e.g. E02, E03)")
    domain_id: Optional[str] = Field(None, description="Pilot river domain or deep zone ID")
    role: str = Field("OBSERVATION", description="Scene role (PRE_EVENT_BASELINE, CO_EVENT, POST_EVENT, OBSERVATION)")
    platform: str = Field("Sentinel-1A", description="Satellite platform (Sentinel-1A, Sentinel-1B)")
    product_type: str = Field("GRD", description="Product type (GRD_HD, GRD)")
    sensor_mode: str = Field("IW", description="Sensor acquisition mode (IW, EW, SM)")
    polarizations: List[str] = Field(default_factory=lambda: ["VV", "VH"], description="Available polarizations")
    orbit_direction: str = Field(..., description="Pass direction: DESCENDING or ASCENDING")
    relative_orbit: Optional[int] = Field(None, description="Relative orbit / track number")
    start_time_utc: datetime = Field(..., description="Scene acquisition start timestamp UTC")
    stop_time_utc: datetime = Field(..., description="Scene acquisition stop timestamp UTC")
    bbox: Tuple[float, float, float, float] = Field(..., description="WGS84 bounding box (min_lon, min_lat, max_lon, max_lat)")
    download_url: Optional[str] = Field(None, description="Direct download endpoint (e.g. ASF Datapool or CDSE)")
    file_size_bytes: Optional[int] = Field(None, description="Expected or actual archive size in bytes")
    sha256: Optional[str] = Field(None, description="Cryptographic SHA-256 hash")
    acquisition_status: SARAcquisitionStatus = Field(SARAcquisitionStatus.DISCOVERED, description="Current acquisition lifecycle state")
    local_path: Optional[str] = Field(None, description="Local storage path if acquired")


class SARDiscoveryRequest(BaseModel):
    """Request query parameters for SAR scene catalog discovery."""
    domain_id: Optional[str] = Field(None, description="Target pilot domain (ganga_patna, brahmaputra_guwahati, etc.)")
    bbox: Optional[List[float]] = Field(None, description="Custom WGS84 bounding box [min_lon, min_lat, max_lon, max_lat]")
    start_time: Optional[datetime] = Field(None, description="Start time UTC")
    end_time: Optional[datetime] = Field(None, description="End time UTC")
    orbit_direction: Optional[str] = Field(None, description="Filter by orbit direction (DESCENDING, ASCENDING)")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of scenes to return")


class SARDiscoveryResponse(BaseModel):
    """Response containing discovered SAR scenes matching criteria."""
    total_discovered: int = Field(..., description="Total matching scenes found")
    domain_id: Optional[str] = Field(None, description="Queried pilot domain ID if specified")
    scenes: List[SARSceneMetadata] = Field(default_factory=list, description="List of discovered scene metadata")
    coverage_status: str = Field(..., description="Spatial/temporal coverage status")
    auth_status: str = Field(..., description="Provider authentication status")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Discovery audit provenance")


class SARAcquisitionRequest(BaseModel):
    """Request to initiate bounded acquisition for selected scenes."""
    scene_ids: List[str] = Field(..., min_length=1, max_length=10, description="List of scene IDs to acquire")
    dry_run: bool = Field(True, description="When true, validates targets and credentials without executing binary downloads")
    max_bytes_per_scene: int = Field(1_500_000_000, description="Maximum allowed size per scene in bytes (safety guard)")


class SARJobResponse(BaseModel):
    """Asynchronous job execution status record."""
    job_id: str = Field(..., description="Unique job execution identifier")
    job_type: str = Field(..., description="Job type: ACQUISITION or PROCESSING")
    status: SARJobStatus = Field(..., description="Overall job status")
    scene_statuses: Dict[str, str] = Field(default_factory=dict, description="Per-scene execution state")
    message: str = Field(..., description="Human-readable status summary")
    created_at: datetime = Field(..., description="Job submission timestamp UTC")
    updated_at: datetime = Field(..., description="Last status update timestamp UTC")
    errors: List[str] = Field(default_factory=list, description="List of execution errors or blockers")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Execution provenance metadata")


class SARProcessingRequest(BaseModel):
    """Request to process a bitemporal SAR pair into flood candidate evidence."""
    domain_id: str = Field(..., description="Target river domain or deep zone identifier")
    pre_event_scene_id: str = Field(..., description="Pre-event baseline Sentinel-1 scene ID")
    co_event_scene_id: str = Field(..., description="Co-event Sentinel-1 scene ID")
    resolution_m: float = Field(30.0, description="Target modeling grid cell resolution in meters")
    apply_water_mask: bool = Field(True, description="Mask permanent water bodies via ESA WorldCover")
    apply_terrain_mask: bool = Field(True, description="Mask steep slopes > 5 deg subject to radar layover")


class SAREvidenceResponse(BaseModel):
    """Derived bitemporal backscatter delta and candidate flood evidence."""
    evidence_id: str = Field(..., description="Unique evidence record ID")
    domain_id: str = Field(..., description="Pilot domain or deep zone ID")
    pre_event_scene_id: str = Field(..., description="Baseline scene ID")
    co_event_scene_id: str = Field(..., description="Co-event scene ID")
    orbit_direction: str = Field(..., description="Orbit direction (must match)")
    relative_orbit: Optional[str] = Field(None, description="Relative orbit number")
    delta_threshold_db: float = Field(-3.0, description="Candidate backscatter change threshold in dB")
    mean_delta_vv_db: Optional[float] = Field(None, description="Domain spatial mean backscatter delta in dB")
    min_delta_vv_db: Optional[float] = Field(None, description="Maximum backscatter drop (most negative delta)")
    candidate_flood_pixels: Optional[int] = Field(None, description="Count of candidate flooded 30m cells (delta < threshold)")
    permanent_water_pixels_masked: Optional[int] = Field(None, description="Count of permanent water pixels excluded")
    evidence_classification: SAREvidenceClassification = Field(..., description="Classification category")
    validation_status: str = Field("UNVALIDATED_CANDIDATE", description="Strict distinction: UNVALIDATED_CANDIDATE vs VALIDATED_EXTENT")
    is_synthetic_benchmark: bool = Field(False, description="Whether evidence is from a synthetic benchmark fixture")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Lineage and processing parameters")


class SARCoverageResponse(BaseModel):
    """India-wide SAR spatial and temporal coverage overview."""
    supported_domains: List[str] = Field(default_factory=list, description="List of recognized pilot river domains")
    domain_catalog: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Domain details, bounds, and scene inventory")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Audit provenance metadata")
