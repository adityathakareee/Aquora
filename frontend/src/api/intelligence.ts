import { apiFetch } from './client';

export interface LocationSummary {
  entity_code: string;
  name: string;
  entity_type: string;
  parent_code: string | null;
  intelligence_level: string;
  centroid_lat: number;
  centroid_lon: number;
  default_zoom: number;
  has_children: boolean;
}

export interface LocationDetail extends LocationSummary {
  child_codes: string[];
  metadata: Record<string, any>;
}

export interface IntelligenceZone {
  zone_id: string;
  name: string;
  entity_code: string;
  level: string;
  status: string;
  spatial_bounds: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
  };
  capabilities: {
    national_screening: string;
    regional_intelligence: string;
    deep_intelligence: string;
    physical_flood_solver: boolean;
    high_resolution_dem: boolean;
    real_radar_corroboration: boolean;
    critical_facility_routing: boolean;
    drainage_loss_proxy: boolean;
    verified_facilities_count: number;
  };
  governance_note: string;
}

export interface LocationCapabilities {
  entity_code: string;
  name: string;
  intelligence_level: string;
  capabilities: Record<string, string>;
  deep_zone_ids: string[];
  active_zone_id: string | null;
}

export interface NationalScreeningRequest {
  latitude: number;
  longitude: number;
  timestamp?: string;
  allow_benchmark_rainfall?: boolean;
}

export interface NationalScreeningResponse {
  status: string;
  is_ready: boolean;
  model_id: string;
  model_version: string;
  resolved_zone: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  features_used: string[] | null;
  feature_values: Record<string, number | null> | null;
  susceptibility_probability: number | null;
  susceptibility_grade: string | null;
  calibration_status: string;
  provenance: Record<string, any>;
  message?: string;
}

export interface RegionalIntelligenceRequest {
  latitude: number;
  longitude: number;
  timestamp?: string;
  allow_benchmark_rainfall?: boolean;
}

export interface RegionalIntelligenceResponse {
  status: string;
  is_ready: boolean;
  model_id: string;
  model_version: string;
  intelligence_level: string;
  basin_id: string | null;
  basin_name: string | null;
  resolved_zone: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  features_used: string[] | null;
  feature_values: Record<string, number | null> | null;
  watershed_exposure_index: number | null;
  exposure_grade: string;
  calibration_status: string;
  critical_facilities_count: number | null;
  provenance: Record<string, any>;
  message?: string;
}

export interface BasinSummaryResponse {
  basin_id: string;
  basin_name: string;
  pfaf_code?: string;
  pfafstetter_level?: number;
  drainage_area_km2?: number;
  major_states: string[];
  centroid: { latitude: number; longitude: number };
  bounds: { min_lon: number; min_lat: number; max_lon: number; max_lat: number };
  operational_status: string;
  capabilities: Record<string, any>;
  governance_note: string;
}

export interface DeepIntelligenceRequest {
  latitude: number;
  longitude: number;
  timestamp?: string;
  allow_benchmark_rainfall?: boolean;
  execute_simulation?: boolean;
  simulation_horizon_minutes?: number;
}

export interface DeepIntelligenceResponse {
  status: string;
  intelligence_level: string;
  zone_id: string | null;
  zone_name: string | null;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  point_in_zone: boolean;
  raster_sampled: boolean;
  elevation_m: number | null;
  slope_degrees: number | null;
  aspect_degrees: number | null;
  flow_accumulation_cells: number | null;
  drainage_proxy_score: number | null;
  built_up_fraction: number | null;
  distance_to_road_m: number | null;
  distance_to_waterway_m: number | null;
  tide_level_m: number | null;
  modeled_water_depth_m: number | null;
  physical_severity: string | null;
  ml_susceptibility_score: number | null;
  calibration_status: string;
  sar_corroboration: Record<string, any>;
  critical_facilities_count: number | null;
  simulation?: any;
  facility_impacts?: any;
  provenance: Record<string, any>;
  limitations: string[];
  message: string;
}

export async function fetchLocations(params?: {
  parent_code?: string;
  entity_type?: string;
  intelligence_level?: string;
}): Promise<LocationSummary[]> {
  const query = new URLSearchParams();
  if (params?.parent_code) query.set('parent_code', params.parent_code);
  if (params?.entity_type) query.set('entity_type', params.entity_type);
  if (params?.intelligence_level) query.set('intelligence_level', params.intelligence_level);
  const qStr = query.toString();
  return apiFetch<LocationSummary[]>(`/api/v1/locations${qStr ? `?${qStr}` : ''}`);
}

export async function fetchLocationDetail(entityCode: string): Promise<LocationDetail> {
  return apiFetch<LocationDetail>(`/api/v1/locations/${entityCode}`);
}

export async function fetchIntelligenceZones(params?: {
  level?: string;
  status?: string;
}): Promise<IntelligenceZone[]> {
  const query = new URLSearchParams();
  if (params?.level) query.set('level', params.level);
  if (params?.status) query.set('status', params.status);
  const qStr = query.toString();
  return apiFetch<IntelligenceZone[]>(`/api/v1/intelligence/zones${qStr ? `?${qStr}` : ''}`);
}

export async function fetchLocationCapabilities(locationCode: string): Promise<LocationCapabilities> {
  return apiFetch<LocationCapabilities>(`/api/v1/intelligence/capabilities?location_code=${encodeURIComponent(locationCode)}`);
}

export async function screenNationalPoint(payload: NationalScreeningRequest): Promise<NationalScreeningResponse> {
  return apiFetch<NationalScreeningResponse>('/api/v1/intelligence/screening/national', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function getRegionalIntelligence(payload: RegionalIntelligenceRequest): Promise<RegionalIntelligenceResponse> {
  return apiFetch<RegionalIntelligenceResponse>('/api/v1/intelligence/regional', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function getBasinSummary(basinId: string): Promise<BasinSummaryResponse> {
  return apiFetch<BasinSummaryResponse>(`/api/v1/intelligence/regional/basins/${encodeURIComponent(basinId)}`);
}

export async function inspectDeepPoint(payload: DeepIntelligenceRequest): Promise<DeepIntelligenceResponse> {
  return apiFetch<DeepIntelligenceResponse>('/api/v1/intelligence/deep', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export interface MahanadiExperimentMetrics {
  event_id: string;
  basin_id: string;
  basin_name: string;
  governance_status: string;
  calibration_status: string;
  alert_eligibility: string;
  primary_flood_authority: string;
  scientific_conclusion: string;
  metrics: Record<string, any>;
  ablation_comparison: Array<Record<string, any>>;
  spatial_independence_audit: Record<string, any>;
  feature_importance: Array<Record<string, any>>;
}

export interface MahanadiSubbasinsResponse {
  type: string;
  total_subbasins: number;
  partitions: {
    train_count: number;
    val_count: number;
    test_count: number;
  };
  spatial_independence: string;
  features: Array<any>;
}

export interface MahanadiLayerItem {
  id: string;
  name: string;
  type: string;
  visible_default?: boolean;
  description: string;
  color?: string;
  color_map?: Record<string, string>;
  url?: string;
}

export interface MahanadiLayersResponse {
  basin_id: string;
  basin_name: string;
  governance: {
    status: string;
    calibration: string;
    alerts: string;
    primary_authority: string;
    banner_text: string;
  };
  layers: MahanadiLayerItem[];
}

export async function fetchMahanadiExperiments(): Promise<MahanadiExperimentMetrics> {
  return apiFetch<MahanadiExperimentMetrics>('/api/v1/intelligence/regional/mahanadi/experiments');
}

export async function fetchMahanadiSubbasins(): Promise<MahanadiSubbasinsResponse> {
  return apiFetch<MahanadiSubbasinsResponse>('/api/v1/intelligence/regional/mahanadi/subbasins');
}

export async function fetchMahanadiLayers(): Promise<MahanadiLayersResponse> {
  return apiFetch<MahanadiLayersResponse>('/api/v1/intelligence/regional/mahanadi/layers');
}

