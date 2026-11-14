"""setup pool, organisation monthly cap and per-page prices (Mistral OCR)

Revision ID: 0028_setup_pool_org_cap
Revises: 0027_quota_plans
Create Date: 2026-11-16

Additive. The pool starts disabled and the org cap unset, so nothing changes until a super admin sets them.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_setup_pool_org_cap"
down_revision: Union[str, None] = "0027_quota_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quota_config", sa.Column("setup_pool_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("quota_config", sa.Column("setup_pool_micro", sa.BigInteger(), server_default=sa.text("0"), nullable=False))
    op.add_column("quota_config", sa.Column("org_monthly_cap_micro", sa.BigInteger(), nullable=True))
    op.add_column("model_prices", sa.Column("per_page_usd", sa.Numeric(12, 6), nullable=True))
    op.add_column("llm_usage", sa.Column("pages", sa.Integer(), server_default=sa.text("0"), nullable=False))


def downgrade() -> None:
    op.drop_column("llm_usage", "pages")
    op.drop_column("model_prices", "per_page_usd")
    op.drop_column("quota_config", "org_monthly_cap_micro")
    op.drop_column("quota_config", "setup_pool_micro")
    op.drop_column("quota_config", "setup_pool_enabled")
