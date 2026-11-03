"""
Flood Processing Service for Phase 6 API & Workflow Orchestration.

Orchestrates input cross-validation, hash computation, engine execution,
file-backed artifact writing, mass balance auditing, and database persistence.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.geospatial.flood import (
    DrainageCouplingPolicy,
    RainfallSourceType,
    RunoffParameters,
    run_flood_simulation_loop,
)
from app.models.flood import (
    FloodSimulationArtifact,
    FloodSimulationDiagnostic,
    FloodSimulationRun,
)
from app.providers.drainage import SyntheticDrainageProvider
from app.providers.forecast import OpenMeteoForecastProvider, SyntheticForecastProvider
from app.providers.rainfall import IMERGRainfallProvider
from app.providers.terrain import LocalDEMTerrainProvider, SyntheticTerrainProvider
from app.schemas.flood import (
    FloodSimulationRequestSchema,
    FloodSimulationRunResponseSchema,
)
from app.schemas.geospatial import BoundingBox
from app.services.spatial_resolver import SpatialZoneResolver, UnsupportedZoneError


class FloodProcessingService:
    """
    Orchestration service for physical flood simulation execution,
    file-backed output management, and PostGIS audit logging.
    """

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.synthetic_terrain_provider = SyntheticTerrainProvider()
        self.local_dem_provider = LocalDEMTerrainProvider()
        self.imerg_rainfall_provider = IMERGRainfallProvider()
        self.open_meteo_forecast_provider = OpenMeteoForecastProvider()
        self.synthetic_forecast_provider = SyntheticForecastProvider()
        self.drainage_provider = SyntheticDrainageProvider()

    async def execute_simulation(
        self,
        request: FloodSimulationRequestSchema
    ) -> FloodSimulationRunResponseSchema:
        """
        Execute end-to-end mass-conserving physical flood simulation based on request configuration.
        """
        resp, _sim_res, _dem_array, _dem_meta = await self.execute_simulation_raw(request)
        return resp

    async def execute_simulation_raw(
        self,
        request: FloodSimulationRequestSchema
    ) -> tuple[FloodSimulationRunResponseSchema, dict[str, Any], np.ndarray, dict[str, Any]]:
        """
        Execute end-to-end physical flood simulation and return response schema,
        raw simulation payload (including per-timestep spatial depth grids), DEM array, and DEM metadata.
        """
        sim_id = f"sim_{uuid.uuid4().hex[:12]}"
        provider_mode = (request.provider_mode or "REAL_DATA").upper()
        if request.terrain_dataset_id and "elevation_30m" in str(request.terrain_dataset_id):
            provider_mode = "REAL_DATA"

        logger.info(
            "Starting physical flood simulation",
            simulation_id=sim_id,
            provider_mode=provider_mode,
            horizon_minutes=request.horizon_minutes,
            timestep_minutes=request.timestep_minutes
        )

        project_root = Path(__file__).resolve().parents[3]
        use_forecast = (
            request.use_forecast_provider
            or request.rainfall_source_type == RainfallSourceType.FORECAST
            or (request.forecast_dataset_id is not None and len(str(request.forecast_dataset_id).strip()) > 0)
        )

        if provider_mode == "REAL_DATA":
            # 1. Resolve Real DEM Inputs (LocalDEMTerrainProvider)
            if request.terrain_dataset_id and request.terrain_dataset_id != "elevation_30m":
                dem_target = request.terrain_dataset_id
            else:
                dem_target = str(project_root / "data" / "processed" / "phase7" / "terrain" / "elevation_30m.tif")

            dem_array, dem_meta = self.local_dem_provider.load_dem_raster(dem_target)
            terrain_fixture = f"REAL_DEM_{Path(dem_meta.get('dataset_id', 'elevation_30m.tif')).name}"

            if use_forecast:
                # 2A. Resolve Real Open-Meteo ECMWF Rainfall Forecast Inputs
                init_time_str = request.start_time or datetime.now(timezone.utc).isoformat()
                try:
                    init_dt = datetime.fromisoformat(init_time_str.replace("Z", "+00:00"))
                except ValueError:
                    init_dt = datetime.now(timezone.utc)
                if init_dt.tzinfo is None:
                    init_dt = init_dt.replace(tzinfo=timezone.utc)

                # Resolve intelligence zone bounding box and validate solver capability
                zone_id = getattr(request, "zone_id", None)
                if zone_id:
                    SpatialZoneResolver.validate_capability(zone_id, "physical_flood_solver")
                bbox = SpatialZoneResolver.get_zone_bbox(zone_id)

                # Fetch real forecast; raises explicit exception on error (NO synthetic fallback in REAL_DATA mode)
                forecast_schemas = await self.open_meteo_forecast_provider.fetch_0_3h_horizon_forecasts(
                    bbox=bbox, initialization_time=init_dt
                )

                num_rain_steps = (request.horizon_minutes // 30) + 1
                rainfall_series = []
                for i in range(num_rain_steps):
                    elapsed_min = i * 30
                    fcst_idx = min(elapsed_min // 60, len(forecast_schemas) - 1)
                    fcst_item = forecast_schemas[fcst_idx]
                    precip_val_mm = float(fcst_item.provenance.get("precipitation_value_mm", 0.0))
                    rainfall_series.append({
                        "offset_minutes": elapsed_min,
                        "rainfall_intensity_mm_hr": precip_val_mm,
                        "source_type": "OPEN_METEO_ECMWF_ECMWF_IFS_GLOBAL",
                    })

                mean_rain_intensity = float(np.mean([r["rainfall_intensity_mm_hr"] for r in rainfall_series]))
                max_rain_intensity = float(np.max([r["rainfall_intensity_mm_hr"] for r in rainfall_series]))

                provenance_data = {
                    "provider_mode": "REAL_DATA",
                    "provider": "OPEN_METEO_ECMWF",
                    "model_name": "ECMWF_IFS_GLOBAL",
                    "source": "Open-Meteo ECMWF",
                    "data_mode": "REAL_DATA",
                    "forecast_temporal_resolution": "1 hour (60 minutes)",
                    "forecast_spatial_resolution": "approximately 9 km (0.09 deg)",
                    "forecast_initialization_time": init_dt.isoformat(),
                    "forecast_valid_times": [f.valid_time.isoformat() for f in forecast_schemas],
                    "forecast_lead_times_minutes": [f.lead_time_minutes for f in forecast_schemas],
                    "precipitation_units": "mm accumulation (converted to mm/hr rate for Phase 6 30-min substeps preserving mass)",
                    "mass_conservation": "PRESERVED_PIECEWISE_CONSTANT_30MIN_SUBSTEPS",
                    "spatial_forcing": "UNIFORM_MACRO_SCALE_9KM",
                    "dem_source": dem_meta.get("source", str(dem_target)),
                    "dem_crs": str(dem_meta["crs"]),
                    "dem_resolution_m": list(dem_meta["resolution"]),
                    "dem_dimensions": list(dem_array.shape),
                    "rainfall_source": "Open-Meteo ECMWF IFS Global Forecast",
                    "rainfall_intensity_mean_mm_hr": mean_rain_intensity,
                    "rainfall_intensity_max_mm_hr": max_rain_intensity,
                    "drainage_status": "REAL municipal drainage network data UNAVAILABLE; surface drainage proxy active.",
                    "tide_status": "REAL tide data AVAILABLE (UHSLC Station 846A), but backwater boundary conditions NOT CONSUMED by Phase 6 D8 solver engine.",
                    "is_synthetic_fallback": False,
                }
            else:
                # 2B. Resolve Real NASA IMERG Observation Inputs
                event_id = request.event_id or "E02"
                rain_path = project_root / "data" / "processed" / "phase7" / "rainfall" / f"{event_id}_rainfall_30m.tif"
                if not rain_path.exists():
                    raise FileNotFoundError(f"REAL_DATA mode requires real NASA IMERG rainfall file for event {event_id} at {rain_path}, but file was not found")

                rain_array, rain_meta = self.imerg_rainfall_provider.load_event_rainfall_raster(event_id=event_id, custom_path=str(rain_path))

                if dem_array.shape != rain_array.shape or str(dem_meta["crs"]) != rain_meta["crs"]:
                    raise ValueError(
                        f"Grid compatibility mismatch: DEM shape {dem_array.shape}, CRS {dem_meta['crs']} "
                        f"vs Rainfall shape {rain_array.shape}, CRS {rain_meta['crs']}"
                    )

                mean_rain_intensity = float(np.mean(rain_array))
                max_rain_intensity = float(np.max(rain_array))
                num_rain_steps = (request.horizon_minutes // 30) + 1
                rainfall_series = [
                    {
                        "offset_minutes": i * 30,
                        "rainfall_intensity_mm_hr": mean_rain_intensity,
                        "source_type": f"REAL_NASA_IMERG_V07B_{event_id}",
                    }
                    for i in range(num_rain_steps)
                ]

                provenance_data = {
                    "provider_mode": "REAL_DATA",
                    "dem_source": dem_meta.get("source", str(dem_target)),
                    "dem_crs": str(dem_meta["crs"]),
                    "dem_resolution_m": list(dem_meta["resolution"]),
                    "dem_dimensions": list(dem_array.shape),
                    "rainfall_source": rain_meta.get("source_file", str(rain_path)),
                    "rainfall_event_id": event_id,
                    "rainfall_intensity_mean_mm_hr": mean_rain_intensity,
                    "rainfall_intensity_max_mm_hr": max_rain_intensity,
                    "drainage_status": "REAL municipal drainage network data UNAVAILABLE; surface drainage proxy active.",
                    "tide_status": "REAL tide data AVAILABLE (UHSLC Station 846A), but backwater boundary conditions NOT CONSUMED by Phase 6 D8 solver engine.",
                    "is_synthetic_fallback": False,
                }

            # 4. Drainage Status (Real municipal network unavailable)
            drainage_fixture = "UNAVAILABLE_REAL_MUNICIPAL_DRAINAGE_PROXY_ONLY"
            raw_nodes, raw_links = [], []
            drainage_graph = {"nodes": {}, "links": {}, "adj": {}, "rev_adj": {}, "outfalls": set()}
            cell_inlet_assoc = {}

        else:
            provider_mode = "TEST"
            # 1. Resolve Synthetic Terrain Inputs
            terrain_fixture = request.terrain_dataset_id or "synthetic_v_valley"
            if "inclined" in terrain_fixture:
                dem_array, dem_meta = self.synthetic_terrain_provider.generate_synthetic_dem(fixture_type="inclined_plane")
            elif "flat" in terrain_fixture:
                dem_array, dem_meta = self.synthetic_terrain_provider.generate_synthetic_dem(fixture_type="flat_plane")
            else:
                dem_array, dem_meta = self.synthetic_terrain_provider.generate_synthetic_dem(fixture_type="v_valley")

            # 2. Resolve Synthetic Drainage Inputs
            drainage_fixture = request.drainage_dataset_id or "synthetic_simple_chain"
            if "branching" in drainage_fixture:
                raw_nodes, raw_links, _raw_meta = self.drainage_provider.generate_synthetic_network(fixture_type="branching_network")
            else:
                raw_nodes, raw_links, _raw_meta = self.drainage_provider.generate_synthetic_network(fixture_type="simple_chain")

            def _get_nid(n):
                return str(n.get("node_id") or n.get("id") or "")

            def _get_lid(l):
                return str(l.get("link_id") or l.get("id") or "")

            drainage_graph = {
                "nodes": {_get_nid(n): n for n in raw_nodes},
                "links": {_get_lid(l): l for l in raw_links},
                "adj": {_get_nid(n): [l["to_node_id"] for l in raw_links if l["from_node_id"] == _get_nid(n)] for n in raw_nodes},
                "rev_adj": {_get_nid(n): [l["from_node_id"] for l in raw_links if l["to_node_id"] == _get_nid(n)] for n in raw_nodes},
                "outfalls": {_get_nid(n) for n in raw_nodes if str(n.get("node_type", "")).upper() == "OUTFALL"}
            }

            cell_inlet_assoc = {
                (0, 0): [raw_nodes[0]] if raw_nodes else [],
            }

            # 3. Resolve Synthetic Rainfall Inputs (Observation or Synthetic Forecast)
            if use_forecast:
                init_time_str = request.start_time or datetime.now(timezone.utc).isoformat()
                try:
                    init_dt = datetime.fromisoformat(init_time_str.replace("Z", "+00:00"))
                except ValueError:
                    init_dt = datetime.now(timezone.utc)
                if init_dt.tzinfo is None:
                    init_dt = init_dt.replace(tzinfo=timezone.utc)
                zone_id = getattr(request, "zone_id", None)
                if zone_id:
                    SpatialZoneResolver.validate_capability(zone_id, "physical_flood_solver")
                bbox = SpatialZoneResolver.get_zone_bbox(zone_id)
                forecast_schemas = await self.synthetic_forecast_provider.fetch_0_3h_horizon_forecasts(
                    bbox=bbox, initialization_time=init_dt
                )
                num_rain_steps = (request.horizon_minutes // 30) + 1
                rainfall_series = [
                    {
                        "offset_minutes": i * 30,
                        "rainfall_intensity_mm_hr": request.synthetic_rainfall_mm_hr if request.synthetic_rainfall_mm_hr is not None else 30.0,
                        "source_type": "SYNTHETIC_FORECAST_PROVIDER",
                    }
                    for i in range(num_rain_steps)
                ]
            else:
                rainfall_intensity = request.synthetic_rainfall_mm_hr if request.synthetic_rainfall_mm_hr is not None else 30.0
                num_rain_steps = (request.horizon_minutes // 30) + 1
                rainfall_series = [
                    {
                        "offset_minutes": i * 30,
                        "rainfall_intensity_mm_hr": rainfall_intensity,
                        "source_type": request.rainfall_source_type.value,
                    }
                    for i in range(num_rain_steps)
                ]

            provenance_data = {
                "provider_mode": "TEST",
                "dem_source": "TEST FIXTURE ONLY — Synthetic Terrain Generator",
                "rainfall_source": "SYNTHETIC_RAINFALL",
                "drainage_status": "TEST FIXTURE ONLY — Synthetic Drainage Generator",
                "tide_status": "NOT CONSUMED",
                "is_synthetic_fallback": False,
            }

        # Calculate D8 Surface Flow Direction
        from app.geospatial.terrain import calculate_d8_flow_direction
        flow_dir_array = calculate_d8_flow_direction(dem_array, dem_meta["transform"])

        # Hydrologic Parameters
        runoff_params = RunoffParameters(
            model=request.runoff_parameters.model,
            runoff_coefficient=request.runoff_parameters.runoff_coefficient,
            infiltration_rate_mm_hr=request.runoff_parameters.infiltration_rate_mm_hr,
            initial_loss_mm=request.runoff_parameters.initial_loss_mm,
            depression_storage_m3_per_m2=request.runoff_parameters.depression_storage_m3_per_m2,
        )

        coupling_policy = DrainageCouplingPolicy(
            unknown_capacity_policy=request.coupling_policy.unknown_capacity_policy,
            unknown_direction_policy=request.coupling_policy.unknown_direction_policy,
            unknown_association_policy=request.coupling_policy.unknown_association_policy,
            max_association_distance_m=request.coupling_policy.max_association_distance_m,
        )

        # Compute Reproducibility Hash
        config_payload = {
            "provider_mode": provider_mode,
            "terrain": terrain_fixture,
            "drainage": drainage_fixture,
            "horizon": request.horizon_minutes,
            "timestep": request.timestep_minutes,
            "rainfall_series": rainfall_series,
            "runoff": runoff_params.__dict__,
            "coupling": coupling_policy.__dict__,
            "crs": request.analysis_crs,
        }
        config_hash = hashlib.sha256(json.dumps(config_payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]

        # Execute Physical Solver Loop
        sim_res = run_flood_simulation_loop(
            dem_metadata=dem_meta,
            elevation_array=dem_array,
            flow_dir_array=flow_dir_array,
            rainfall_series=rainfall_series,
            drainage_network=drainage_graph,
            cell_inlet_associations=cell_inlet_assoc,
            runoff_params=runoff_params,
            coupling_policy=coupling_policy,
            timestep_minutes=request.timestep_minutes,
            horizon_minutes=request.horizon_minutes,
            start_time_iso=request.start_time,
            resampling_method=request.rainfall_resampling_method.value,
            mass_balance_tolerance=settings.MASS_BALANCE_TOLERANCE
        )

        # Write File-Backed Output Artifacts
        output_dir = Path(settings.FLOOD_PROCESSED_DATA_PATH) / sim_id
        output_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = output_dir / "manifest.json"
        manifest_data = {
            "simulation_id": sim_id,
            "provider_mode": provider_mode,
            "configuration_hash": config_hash,
            "engine_version": settings.VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "provenance": provenance_data,
            "totals": sim_res["totals"],
            "input_completeness": sim_res["input_completeness"],
            "warnings": sim_res["warnings"],
            "timestep_summaries": sim_res["timestep_summaries"],
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # Persist Record to PostGIS DB if Session Available
        now_utc = datetime.now(timezone.utc)
        if self.db:
            try:
                sim_run_db = FloodSimulationRun(
                    simulation_identifier=sim_id,
                    study_area_id=request.study_area_id,
                    status="COMPLETED",
                    started_at=now_utc,
                    completed_at=now_utc,
                    start_time=datetime.fromisoformat(sim_res["start_time_iso"].replace("Z", "+00:00")),
                    horizon_minutes=request.horizon_minutes,
                    timestep_minutes=request.timestep_minutes,
                    total_timesteps=sim_res["total_timesteps"],
                    rainfall_source_id=f"RAIN_{request.rainfall_source_type.value}",
                    terrain_dataset_id=terrain_fixture,
                    drainage_dataset_id=drainage_fixture,
                    configuration_hash=config_hash,
                    engine_version=settings.VERSION,
                    analysis_crs=request.analysis_crs,
                    input_completeness=sim_res["input_completeness"],
                    mass_balance_totals=sim_res["totals"],
                    overall_mass_balance_error_m3=sim_res["totals"]["overall_mass_balance_error_m3"],
                    is_mass_balance_valid=sim_res["totals"]["overall_mass_balance_error_m3"] <= settings.MASS_BALANCE_TOLERANCE,
                    output_manifest_path=str(manifest_path),
                    warnings=sim_res["warnings"],
                    error_message=None,
                )
                self.db.add(sim_run_db)

                artifact_db = FloodSimulationArtifact(
                    simulation_id=sim_id,
                    artifact_type="MANIFEST",
                    relative_path=str(manifest_path.relative_to(Path(settings.FLOOD_PROCESSED_DATA_PATH).parent.parent)),
                    format="JSON",
                    checksum=config_hash,
                    created_at=now_utc,
                )
                self.db.add(artifact_db)

                for diag_dict in sim_res["diagnostics"]:
                    diag_db = FloodSimulationDiagnostic(
                        simulation_id=sim_id,
                        timestep_index=diag_dict["timestep_index"],
                        timestamp_iso=diag_dict["timestamp_iso"],
                        previous_storage_m3=diag_dict["previous_storage_m3"],
                        rainfall_input_m3=diag_dict["rainfall_input_m3"],
                        runoff_generated_m3=diag_dict["runoff_generated_m3"],
                        surface_inflow_m3=diag_dict["surface_inflow_m3"],
                        surface_outflow_m3=diag_dict["surface_outflow_m3"],
                        drainage_inflow_m3=diag_dict["drainage_inflow_m3"],
                        drainage_outflow_m3=diag_dict["drainage_outflow_m3"],
                        infiltration_losses_m3=diag_dict["infiltration_losses_m3"],
                        current_storage_m3=diag_dict["current_storage_m3"],
                        mass_balance_error_m3=diag_dict["mass_balance_error_m3"],
                        is_valid=diag_dict["is_valid"],
                    )
                    self.db.add(diag_db)

                await self.db.commit()
            except Exception as db_err:
                logger.warning("Database persistence skipped or failed (PostgreSQL offline)", error=str(db_err))
                await self.db.rollback()

        logger.info(
            "Completed physical flood simulation",
            simulation_id=sim_id,
            provider_mode=provider_mode,
            overall_mass_balance_error_m3=sim_res["totals"]["overall_mass_balance_error_m3"]
        )

        response_schema = FloodSimulationRunResponseSchema(
            simulation_id=sim_id,
            study_area_id=request.study_area_id,
            provider_mode=provider_mode,
            status="COMPLETED",
            started_at=now_utc.isoformat(),
            completed_at=now_utc.isoformat(),
            start_time=sim_res["start_time_iso"],
            horizon_minutes=request.horizon_minutes,
            timestep_minutes=request.timestep_minutes,
            total_timesteps=sim_res["total_timesteps"],
            rainfall_source_id=f"RAIN_{request.rainfall_source_type.value}",
            terrain_dataset_id=terrain_fixture,
            drainage_dataset_id=drainage_fixture,
            configuration_hash=config_hash,
            engine_version=settings.VERSION,
            input_completeness=sim_res["input_completeness"],
            mass_balance_totals=sim_res["totals"],
            overall_mass_balance_error_m3=sim_res["totals"]["overall_mass_balance_error_m3"],
            is_mass_balance_valid=sim_res["totals"]["overall_mass_balance_error_m3"] <= settings.MASS_BALANCE_TOLERANCE,
            output_manifest_path=str(manifest_path),
            provenance=provenance_data,
            warnings=sim_res["warnings"],
            error_message=None,
        )
        return response_schema, sim_res, dem_array, dem_meta

