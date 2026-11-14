"""dollar quota: role plans, per-user overrides and the enforcement switch

Revision ID: 0027_quota_plans
Revises: 0026_usage_cost
Create Date: 2026-11-15

Additive. `quota_config.enforced` starts false (shadow mode): plans exist but nobody is blocked until a super admin turns it on.
Seed (micro-USD): user 0.45 / 1.5 / 4.5 USD (5h / week / month), admin 1.5 / 5 / 15 USD.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_quota_plans"
down_revision: Union[str, None] = "0026_usage_cost"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quota_plans",
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("five_hour_micro", sa.BigInteger(), nullable=False),
        sa.Column("weekly_micro", sa.BigInteger(), nullable=False),
        sa.Column("monthly_micro", sa.BigInteger(), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("role"),
    )
    op.execute(
        "INSERT INTO quota_plans (role, five_hour_micro, weekly_micro, monthly_micro) VALUES "
        "('user', 450000, 1500000, 4500000), ('admin', 1500000, 5000000, 15000000)"
    )
    op.create_table(
        "quota_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enforced", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_quota_config_single_row"),
    )
    op.execute("INSERT INTO quota_config (id, enforced) VALUES (1, false)")
    for name in ("quota_five_hour_override", "quota_weekly_override", "quota_monthly_override"):
        op.add_column("users", sa.Column(name, sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("quota_unlimited", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    for name in ("quota_unlimited", "quota_monthly_override", "quota_weekly_override", "quota_five_hour_override"):
        op.drop_column("users", name)
    op.drop_table("quota_config")
    op.drop_table("quota_plans")
