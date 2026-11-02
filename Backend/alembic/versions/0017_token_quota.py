"""token quota: users.token_* columns and llm_usage

Revision ID: 0017_token_quota
Revises: 0016_project_member_permissions
Create Date: 2026-11-02

Additive: NULL limit = unlimited, so nobody is restricted until an admin sets a limit.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_token_quota"
down_revision: Union[str, None] = "0016_project_member_permissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("token_limit", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("tokens_used", sa.BigInteger(), server_default=sa.text("0"), nullable=False))
    op.add_column("users", sa.Column("token_period_start", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.add_column("users", sa.Column("token_limit_set_by", sa.UUID(), nullable=True))
    op.add_column("users", sa.Column("token_limit_set_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_users_token_limit_set_by", "users", "users", ["token_limit_set_by"], ["id"], ondelete="SET NULL")

    op.create_table(
        "llm_usage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_tokens", sa.Integer(), nullable=False),
        sa.Column("counts_toward_quota", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_usage_user_created", "llm_usage", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_llm_usage_user_created", table_name="llm_usage")
    op.drop_table("llm_usage")
    op.drop_constraint("fk_users_token_limit_set_by", "users", type_="foreignkey")
    for column in ("token_limit_set_at", "token_limit_set_by", "token_period_start", "tokens_used", "token_limit"):
        op.drop_column("users", column)
