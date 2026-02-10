"""Phase 1 Migration 1: suppliers table + material_types expansion

Revision ID: a1_phase1_sm
Revises: 7b4fa5afc037
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1_phase1_sm"
down_revision = "7b4fa5afc037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Supplier master --
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("contact_person", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("waste_types", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # -- Expand material_types with physical/chemical properties --
    op.add_column("material_types", sa.Column("specific_gravity", sa.Float(), nullable=True))
    op.add_column("material_types", sa.Column("particle_size", sa.Float(), nullable=True))
    op.add_column("material_types", sa.Column("ph", sa.Float(), nullable=True))
    op.add_column("material_types", sa.Column("moisture_content", sa.Float(), nullable=True))

    # -- Add supplier FK to waste_records --
    op.add_column(
        "waste_records",
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_waste_records_supplier_id",
        "waste_records",
        "suppliers",
        ["supplier_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_waste_records_supplier_id", "waste_records", type_="foreignkey")
    op.drop_column("waste_records", "supplier_id")
    op.drop_column("material_types", "moisture_content")
    op.drop_column("material_types", "ph")
    op.drop_column("material_types", "particle_size")
    op.drop_column("material_types", "specific_gravity")
    op.drop_table("suppliers")
