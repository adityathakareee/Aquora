"""
AQUORA 2.0 Geographic Hierarchy and Intelligence Zone SQLAlchemy Models.

Defines the multi-tiered spatial architecture:
    COUNTRY -> STATE -> DISTRICT -> BASIN -> CITY -> CATCHMENT -> GRID_CELL

Supports PostGIS spatial indexing and the three core intelligence levels:
    NATIONAL, REGIONAL, DEEP
"""

import datetime
import uuid
from typing import Any, Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class GeographicEntity(Base):
    """
    Represents an administrative, hydrological, or operational spatial entity
    in the multi-tier Indian geographic hierarchy.
    """
    __tablename__ = "geographic_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    entity_code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    entity_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True
    )  # COUNTRY, STATE, DISTRICT, BASIN, CITY, CATCHMENT, GRID_CELL
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geographic_entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    intelligence_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NATIONAL",
        index=True
    )  # NATIONAL, REGIONAL, DEEP
    geom: Mapped[Any] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=True),
        nullable=True
    )
    srid: Mapped[int] = mapped_column(
        Integer,
        default=4326,
        nullable=False
    )
    centroid_lat: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    centroid_lon: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    default_zoom: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False
    )
    metadata_properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Self-referential hierarchy relationships
    parent: Mapped[Optional["GeographicEntity"]] = relationship(
        "GeographicEntity",
        remote_side=[id],
        back_populates="children"
    )
    children: Mapped[list["GeographicEntity"]] = relationship(
        "GeographicEntity",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    intelligence_zones: Mapped[list["IntelligenceZone"]] = relationship(
        "IntelligenceZone",
        back_populates="entity",
        cascade="all, delete-orphan"
    )


class IntelligenceZone(Base):
    """
    Represents an operational AQUORA intelligence zone, capturing its tier,
    capabilities, coverage bounds, and validation status.
    """
    __tablename__ = "intelligence_zones"

    zone_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geographic_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True
    )  # NATIONAL, REGIONAL, DEEP
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="ACTIVE",
        index=True
    )  # ACTIVE, PROTOTYPE, PLANNED
    capabilities: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    spatial_bounds: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    entity: Mapped["GeographicEntity"] = relationship(
        "GeographicEntity",
        back_populates="intelligence_zones"
    )
