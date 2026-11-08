"""volume report: planned (forecast) lines and results

Revision ID: 0019_vr_plan_basis
Revises: 0018_vr_item_rules
Create Date: 2026-11-08

Additive: `basis` ('actual' | 'planned') on vr_lines and vr_results (existing rows are actual); the unique result cell
now includes it so a forecast and an actual can share a (scope, company, site, item) cell.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_vr_plan_basis"
down_revision: Union[str, None] = "0018_vr_item_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NIL = "'00000000-0000-0000-0000-000000000000'::uuid"


def upgrade() -> None:
    op.add_column("vr_lines", sa.Column("basis", sa.String(length=10), nullable=False, server_default="actual"))
    op.add_column("vr_results", sa.Column("basis", sa.String(length=10), nullable=False, server_default="actual"))
    op.drop_index("uq_vr_results_cell", table_name="vr_results")
    op.create_index(
        "uq_vr_results_cell", "vr_results",
        ["report_id", "scope", "basis", sa.text(f"coalesce(company_id, {_NIL})"), sa.text(f"coalesce(site_id, {_NIL})"), "item_id"],
        unique=True,
    )


def downgrade() -> None:
    op.execute("DELETE FROM vr_results WHERE basis <> 'actual'")
    op.execute("DELETE FROM vr_lines WHERE basis <> 'actual'")
    op.drop_index("uq_vr_results_cell", table_name="vr_results")
    op.create_index(
        "uq_vr_results_cell", "vr_results",
        ["report_id", "scope", sa.text(f"coalesce(company_id, {_NIL})"), sa.text(f"coalesce(site_id, {_NIL})"), "item_id"],
        unique=True,
    )
    op.drop_column("vr_results", "basis")
    op.drop_column("vr_lines", "basis")
