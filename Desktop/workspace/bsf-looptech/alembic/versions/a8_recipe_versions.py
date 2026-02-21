"""Recipe version management tables

Revision ID: a8_recipe_versions
Revises: a7_delivery
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "a8_recipe_versions"
down_revision = "a7_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add current_version column to recipes
    op.add_column(
        "recipes",
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
    )

    # Create recipe_versions table
    op.create_table(
        "recipe_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("recipe_id", UUID(as_uuid=True), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("supplier_id", UUID(as_uuid=True), nullable=True),
        sa.Column("waste_type", sa.String(100), nullable=False),
        sa.Column("target_strength", sa.Float(), nullable=True),
        sa.Column("target_elution", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_recipe_versions_recipe_id", "recipe_versions", ["recipe_id"])
    op.create_index(
        "uq_recipe_versions_recipe_version",
        "recipe_versions",
        ["recipe_id", "version"],
        unique=True,
    )

    # Create recipe_version_details table
    op.create_table(
        "recipe_version_details",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", UUID(as_uuid=True), sa.ForeignKey("recipe_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", UUID(as_uuid=True), nullable=False),
        sa.Column("material_type", sa.String(30), nullable=False),
        sa.Column("addition_rate", sa.Float(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_recipe_version_details_version_id", "recipe_version_details", ["version_id"])


def downgrade() -> None:
    op.drop_table("recipe_version_details")
    op.drop_table("recipe_versions")
    op.drop_column("recipes", "current_version")
