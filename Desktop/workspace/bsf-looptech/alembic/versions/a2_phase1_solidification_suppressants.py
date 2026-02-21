"""Phase 1 Migration 2: solidification_materials + leaching_suppressants

Revision ID: a2_phase1_ss
Revises: a1_phase1_sm
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a2_phase1_ss"
down_revision = "a1_phase1_sm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Solidification material master --
    op.create_table(
        "solidification_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("material_type", sa.String(50), nullable=False, index=True),
        sa.Column("base_material", sa.String(200), nullable=True),
        sa.Column("effective_components", sa.JSON(), nullable=True),
        sa.Column("applicable_soil_types", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("min_addition_rate", sa.Float(), nullable=True),
        sa.Column("max_addition_rate", sa.Float(), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True, server_default="'kg'"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # -- Leaching suppressant master --
    op.create_table(
        "leaching_suppressants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True, index=True),
        sa.Column("suppressant_type", sa.String(100), nullable=False, index=True),
        sa.Column("target_metals", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("min_addition_rate", sa.Float(), nullable=True),
        sa.Column("max_addition_rate", sa.Float(), nullable=True),
        sa.Column("ph_range_min", sa.Float(), nullable=True),
        sa.Column("ph_range_max", sa.Float(), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True, server_default="'kg'"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("leaching_suppressants")
    op.drop_table("solidification_materials")
