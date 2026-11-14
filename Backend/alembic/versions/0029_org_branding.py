"""organisation branding (name, texts, colours, logo)

Revision ID: 0029_org_branding
Revises: 0028_setup_pool_org_cap
Create Date: 2026-11-17

Additive. One row per deployment, seeded with the first customer's identity so an existing installation looks exactly as before
(no logo stored: upload it once in the admin panel). A new organisation edits the row from the panel.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_org_branding"
down_revision: Union[str, None] = "0028_setup_pool_org_cap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_branding",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("short_name", sa.String(length=60), nullable=False),
        sa.Column("app_title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=False),
        sa.Column("tagline", sa.String(length=120), nullable=False),
        sa.Column("product_label", sa.String(length=40), nullable=False),
        sa.Column("login_headline", sa.String(length=200), nullable=False),
        sa.Column("login_footer", sa.String(length=200), nullable=False),
        sa.Column("color_brand", sa.String(length=7), nullable=False),
        sa.Column("color_accent", sa.String(length=7), nullable=False),
        sa.Column("color_highlight", sa.String(length=7), nullable=False),
        sa.Column("logo_data", sa.LargeBinary(), nullable=True),
        sa.Column("logo_content_type", sa.String(length=40), nullable=True),
        sa.Column("logo_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="ck_org_branding_single_row"),
    )
    op.execute(sa.text(
        "INSERT INTO org_branding (id, name, short_name, app_title, description, tagline, product_label, login_headline, login_footer, "
        "color_brand, color_accent, color_highlight) VALUES (1, :name, :short, :title, :descr, :tagline, :label, :headline, :footer, "
        "'#3446b8', '#e8c523', '#25b8b4')"
    ).bindparams(
        name="شرکت محور گستر نصر", short="محور گستر", title="دستیار هوشمند محور گستر",
        descr="دستیار داخلی شرکت محور گستر نصر، متصل به اسناد و قراردادهای سازمان", tagline="دستیار هوشمند سازمانی", label="ORBIT WORKSPACE",
        headline="هر سؤالی درباره‌ی اسناد شرکت داری، همین‌جا بپرس.", footer="ابزار داخلی کارکنان محور گستر • دسترسی فقط با حساب سازمانی",
    ))


def downgrade() -> None:
    op.drop_table("org_branding")
