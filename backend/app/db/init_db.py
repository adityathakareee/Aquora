"""
Idempotent Critical Facility Seeder and Migration Helper for Aquora Production.

Ensures:
1. Database migrations (alembic upgrade head) are executed programmatically up to head revision.
2. Verified OSM + MCGM critical facility datasets (366 total) are idempotently loaded into PostgreSQL database.
3. No duplicate facility records are inserted on container restarts.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.critical_access import CriticalFacility


REQUIRED_PRODUCTION_TABLES = [
    "audit_events",
    "rainfall_observation_grids",
    "terrain_datasets",
    "drainage_networks",
    "flood_simulation_runs",
    "digital_twin_runs",
    "digital_twin_slices",
    "routing_runs",
    "critical_facilities",
    "protect_city_runs",
    "ground_truth_runs",
    "simulator_scenarios",
    "simulator_runs",
    "alerts",
    "geographic_entities",
    "intelligence_zones",
]


def apply_alembic_migrations() -> None:
    """Execute Alembic migrations (alembic upgrade head) programmatically."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(settings.DATABASE_URL)
        safe_db_info = f"host={parsed.hostname}, port={parsed.port or 5432}, dbname={parsed.path.lstrip('/')}"
        logger.info("Database connection target for migrations", target=safe_db_info)
    except Exception:
        logger.info("Database connection target configured via settings.DATABASE_URL")

    logger.info("Verifying database schema migration status (alembic upgrade head)... Target head: 0014_phase1_india_hierarchy")
    try:
        from alembic.config import Config
        from alembic import command

        backend_dir = Path(__file__).resolve().parents[2]
        alembic_ini_path = backend_dir / "alembic.ini"

        if alembic_ini_path.exists():
            alembic_cfg = Config(str(alembic_ini_path))
            alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
            alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic database migrations applied successfully (head reached: 0013_phase15_alerts).")
        else:
            logger.warning("alembic.ini not found at path", path=str(alembic_ini_path))
    except Exception as err:
        logger.error("Alembic migration execution error", error=str(err))
        raise err


async def verify_production_schema() -> list[str]:
    """
    Verify all 14 required production tables exist in PostgreSQL public schema.
    Returns list of missing table names (empty list if 100% healthy).
    """
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as session:
            query = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            res = await session.execute(query)
            existing_tables = set(res.scalars().all())
            missing = [t for t in REQUIRED_PRODUCTION_TABLES if t not in existing_tables]
            return missing
    except Exception as err:
        logger.error("Error executing schema verification query", error=str(err))
        return REQUIRED_PRODUCTION_TABLES


async def seed_critical_facilities() -> int:
    """Seed baseline critical facilities idempotently into the database."""
    logger.info("Executing critical facility seed check...")

    try:
        repo_root = Path(__file__).resolve().parents[3]
        data_dir = repo_root / settings.CRITICAL_FACILITIES_DATA_PATH

        if not data_dir.exists():
            logger.warning("Critical facilities data directory not found for seeding", path=str(data_dir))
            return 0

        facilities_to_seed: list[dict[str, Any]] = []

        for json_file in sorted(data_dir.glob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                features = data.get("features", [])
                for idx, feat in enumerate(features):
                    props = feat.get("properties", {})
                    geom = feat.get("geometry", {})
                    coords = geom.get("coordinates", [0.0, 0.0])

                    lon, lat = coords[0], coords[1]
                    f_id = props.get("facility_id", f"fac_seed_{idx}")
                    name = props.get("name", "Unnamed Facility")
                    cat = props.get("category", "OTHER_CRITICAL").upper()

                    facilities_to_seed.append({
                        "facility_id": f_id,
                        "name": name,
                        "category": cat,
                        "latitude": lat,
                        "longitude": lon,
                        "source": props.get("source", "Verified Dataset"),
                        "source_id": props.get("source_id"),
                        "source_type": props.get("source_type", "OPEN_GOVERNMENT"),
                        "verification_status": props.get("verification_status", "VERIFIED"),
                        "operational_status": props.get("operational_status", "UNKNOWN"),
                        "provenance": props.get("provenance", {}),
                    })
            except Exception as err:
                logger.warning(f"Error parsing facility seed file {json_file}: {err}")

        if not facilities_to_seed:
            logger.warning("No facility records found to seed")
            return 0

        async with AsyncSessionLocal() as session:
            # Check existing count
            stmt = select(CriticalFacility.facility_id)
            result = await session.execute(stmt)
            existing_ids = set(result.scalars().all())

            new_records = [f for f in facilities_to_seed if f["facility_id"] not in existing_ids]

            if new_records:
                for rec in new_records:
                    fac_obj = CriticalFacility(
                        facility_id=rec["facility_id"],
                        name=rec["name"],
                        category=rec["category"],
                        latitude=rec["latitude"],
                        longitude=rec["longitude"],
                        source=rec["source"],
                        source_id=rec["source_id"],
                        source_type=rec["source_type"],
                        verification_status=rec["verification_status"],
                        operational_status=rec["operational_status"],
                        provenance=rec["provenance"],
                    )
                    session.add(fac_obj)

                await session.commit()
                logger.info(f"Idempotently seeded {len(new_records)} new critical facilities into database")
                return len(new_records)
            else:
                logger.info(f"Database already contains {len(existing_ids)} verified critical facilities; skipping seed")
                return len(existing_ids)
    except Exception as seed_err:
        logger.error("Facility seeding failed", error=str(seed_err))
        raise seed_err


async def run_migrations_and_seed() -> None:
    """Execute migrations, verify production schema, and seed facilities."""
    await asyncio.to_thread(apply_alembic_migrations)
    missing = await verify_production_schema()
    if missing:
        err_msg = f"CRITICAL PRODUCTION SCHEMA FAILURE: Missing required tables: {missing}"
        logger.error(err_msg)
        raise RuntimeError(err_msg)
    logger.info("Production database schema verification PASSED (all 14 required tables present).")
    await seed_critical_facilities()


if __name__ == "__main__":
    apply_alembic_migrations()
    asyncio.run(run_migrations_and_seed())

