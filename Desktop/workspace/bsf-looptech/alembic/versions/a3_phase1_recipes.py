"""Phase 1 Migration 3: recipes + recipe_details

Revision ID: a3_phase1_rc
Revises: a2_phase1_ss
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a3_phase1_rc"
down_revision = "a2_phase1_ss"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Recipe header --
    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("waste_type", sa.String(100), nullable=False, index=True),
        sa.Column("target_strength", sa.Float(), nullable=True),
        sa.Column("target_elution", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="'draft'"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], name="fk_recipes_supplier_id"),
    )

    # -- Recipe detail lines --
    op.create_table(
        "recipe_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_type", sa.String(30), nullable=False),
        sa.Column("addition_rate", sa.Float(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["recipe_id"], ["recipes.id"],
            name="fk_recipe_details_recipe_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_recipe_details_recipe_id", "recipe_details", ["recipe_id"])


def downgrade() -> None:
    op.drop_index("ix_recipe_details_recipe_id", table_name="recipe_details")
    op.drop_table("recipe_details")
    op.drop_table("recipes")
