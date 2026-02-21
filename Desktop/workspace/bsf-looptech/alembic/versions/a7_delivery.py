"""Delivery tables: incoming_materials + delivery_schedules

Revision ID: a7_delivery
Revises: a6_phase5_batch
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a7_delivery"
down_revision = "a6_phase26_vec_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # incoming_materials (搬入物マスター)
    op.create_table(
        "incoming_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suppliers.id"),
            nullable=False,
        ),
        sa.Column("material_category", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("default_weight_unit", sa.String(10), nullable=False, server_default="t"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_incoming_materials_material_category", "incoming_materials", ["material_category"])
    op.create_index("ix_incoming_materials_name", "incoming_materials", ["name"])
    op.create_index(
        "ix_incoming_materials_supplier_category",
        "incoming_materials",
        ["supplier_id", "material_category"],
    )

    # delivery_schedules (搬入予定)
    op.create_table(
        "delivery_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incoming_material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incoming_materials.id"),
            nullable=False,
        ),
        sa.Column("scheduled_date", sa.DateTime, nullable=False),
        sa.Column("estimated_weight", sa.Float, nullable=True),
        sa.Column("actual_weight", sa.Float, nullable=True),
        sa.Column("weight_unit", sa.String(10), nullable=False, server_default="t"),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column(
            "waste_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("waste_records.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_delivery_schedules_scheduled_date", "delivery_schedules", ["scheduled_date"])
    op.create_index(
        "ix_delivery_schedules_status_date",
        "delivery_schedules",
        ["status", "scheduled_date"],
    )


def downgrade() -> None:
    op.drop_table("delivery_schedules")
    op.drop_table("incoming_materials")
