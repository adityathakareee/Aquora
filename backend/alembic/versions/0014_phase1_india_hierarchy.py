"""Phase 1 India Geographic Hierarchy and Intelligence Zones.

Revision ID: 0014_phase1_india_hierarchy
Revises: 0013_phase15_alerts
Create Date: 2026-10-07
"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0014_phase1_india_hierarchy"
down_revision: str | None = "0013_phase15_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create geographic_entities table
    op.create_table(
        "geographic_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("entity_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("intelligence_level", sa.String(length=32), nullable=False, server_default="NATIONAL"),
        sa.Column("geom", Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False), nullable=True),
        sa.Column("srid", sa.Integer(), nullable=False, server_default="4326"),
        sa.Column("centroid_lat", sa.Float(), nullable=True),
        sa.Column("centroid_lon", sa.Float(), nullable=True),
        sa.Column("default_zoom", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("metadata_properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["geographic_entities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_geographic_entities_entity_code"), "geographic_entities", ["entity_code"], unique=True)
    op.create_index(op.f("ix_geographic_entities_name"), "geographic_entities", ["name"], unique=False)
    op.create_index(op.f("ix_geographic_entities_entity_type"), "geographic_entities", ["entity_type"], unique=False)
    op.create_index(op.f("ix_geographic_entities_parent_id"), "geographic_entities", ["parent_id"], unique=False)
    op.create_index(op.f("ix_geographic_entities_intelligence_level"), "geographic_entities", ["intelligence_level"], unique=False)
    op.create_index("idx_geographic_entities_geom", "geographic_entities", ["geom"], postgresql_using="gist")

    # 2. Create intelligence_zones table
    op.create_table(
        "intelligence_zones",
        sa.Column("zone_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("spatial_bounds", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["geographic_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("zone_id"),
    )
    op.create_index(op.f("ix_intelligence_zones_entity_id"), "intelligence_zones", ["entity_id"], unique=False)
    op.create_index(op.f("ix_intelligence_zones_level"), "intelligence_zones", ["level"], unique=False)
    op.create_index(op.f("ix_intelligence_zones_status"), "intelligence_zones", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_intelligence_zones_status"), table_name="intelligence_zones")
    op.drop_index(op.f("ix_intelligence_zones_level"), table_name="intelligence_zones")
    op.drop_index(op.f("ix_intelligence_zones_entity_id"), table_name="intelligence_zones")
    op.drop_table("intelligence_zones")

    op.drop_index("idx_geographic_entities_geom", table_name="geographic_entities", postgresql_using="gist")
    op.drop_index(op.f("ix_geographic_entities_intelligence_level"), table_name="geographic_entities")
    op.drop_index(op.f("ix_geographic_entities_parent_id"), table_name="geographic_entities")
    op.drop_index(op.f("ix_geographic_entities_entity_type"), table_name="geographic_entities")
    op.drop_index(op.f("ix_geographic_entities_name"), table_name="geographic_entities")
    op.drop_index(op.f("ix_geographic_entities_entity_code"), table_name="geographic_entities")
    op.drop_table("geographic_entities")
