"""usage cost in micro-USD and the model price table

Revision ID: 0026_usage_cost
Revises: 0025_vr_pv_manual
Create Date: 2026-11-14

Additive. Monitoring only: nothing is blocked by cost yet. Seeds the three prices in use; history is back-filled for models
that match a price row exactly (others stay 0 until a price is added and re-priced by hand).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_usage_cost"
down_revision: Union[str, None] = "0025_vr_pv_manual"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "model_prices",
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("input_per_m", sa.Numeric(12, 6), nullable=False),
        sa.Column("output_per_m", sa.Numeric(12, 6), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("model"),
    )
    op.execute(
        "INSERT INTO model_prices (model, input_per_m, output_per_m) VALUES "
        "('gemini-3.5-flash-lite', 0.30, 2.50), ('qwen3.8-flash', 0.15, 0.47), ('text-embedding-3-large', 0.13, 0.13)"
    )
    op.add_column("llm_usage", sa.Column("cost_micro_usd", sa.BigInteger(), server_default=sa.text("0"), nullable=False))
    op.add_column("llm_usage", sa.Column("billed_to", sa.String(length=12), server_default=sa.text("'user'"), nullable=False))
    op.execute(
        "UPDATE llm_usage u SET cost_micro_usd = ceil(u.prompt_tokens * p.input_per_m + u.completion_tokens * p.output_per_m) "
        "FROM model_prices p WHERE lower(p.model) = lower(u.model)"
    )


def downgrade() -> None:
    op.drop_column("llm_usage", "billed_to")
    op.drop_column("llm_usage", "cost_micro_usd")
    op.drop_table("model_prices")
