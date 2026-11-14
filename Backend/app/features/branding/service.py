"""Organisation branding: read (public), update and logo (super admin)."""

import io
import logging
import uuid
from datetime import datetime, timezone

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.features.auth.models import User
from app.features.branding import palette
from app.features.branding.models import OrgBranding

logger = logging.getLogger(__name__)

# What a fresh deployment (and the first customer's existing one) shows until a super admin changes it.
DEFAULTS = {
    "name": "شرکت محور گستر نصر",
    "short_name": "محور گستر",
    "app_title": "دستیار هوشمند محور گستر",
    "description": "دستیار داخلی شرکت محور گستر نصر، متصل به اسناد و قراردادهای سازمان",
    "tagline": "دستیار هوشمند سازمانی",
    "product_label": "ORBIT WORKSPACE",
    "login_headline": "هر سؤالی درباره‌ی اسناد شرکت داری، همین‌جا بپرس.",
    "login_footer": "ابزار داخلی کارکنان محور گستر • دسترسی فقط با حساب سازمانی",
    "color_brand": "#3446b8",
    "color_accent": "#e8c523",
    "color_highlight": "#25b8b4",
}
TEXT_LIMITS = {"name": 120, "short_name": 60, "app_title": 120, "description": 300, "tagline": 120, "product_label": 40, "login_headline": 200, "login_footer": 200}
COLOR_FIELDS = ("color_brand", "color_accent", "color_highlight")
MAX_LOGO_BYTES = 512 * 1024
MAX_LOGO_PIXELS = 2048
_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def _logo_url(version: int, has_logo: bool) -> str | None:
    return f"{get_settings().api_prefix}/branding/logo?v={version}" if has_logo else None


async def _row(db: AsyncSession, *, with_logo: bool = False) -> OrgBranding | None:
    stmt = select(OrgBranding).where(OrgBranding.id == 1)
    if with_logo:
        from sqlalchemy.orm import undefer

        stmt = stmt.options(undefer(OrgBranding.logo_data))
    return (await db.execute(stmt.execution_options(populate_existing=True))).scalar_one_or_none()


def _public(values: dict, logo_version: int, has_logo: bool, updated_at: datetime | None) -> dict:
    colors = {"brand": values["color_brand"], "accent": values["color_accent"], "highlight": values["color_highlight"]}
    return {
        **{k: values[k] for k in TEXT_LIMITS},
        "colors": colors,
        "palette": {"brand": palette.css_scale(colors["brand"]), "accent": palette.css_scale(colors["accent"]), "teal": palette.css_scale(colors["highlight"]),
                    "ground": palette.ground(colors["brand"])},
        "logo_url": _logo_url(logo_version, has_logo),
        "updated_at": updated_at,
    }


async def read(db: AsyncSession) -> dict:
    row = await _row(db)
    if row is None:
        return _public(DEFAULTS, 0, False, None)
    values = {k: getattr(row, k) for k in DEFAULTS}
    return _public(values, row.logo_version, row.logo_content_type is not None, row.updated_at)


async def _ensure_row(db: AsyncSession) -> OrgBranding:
    row = await _row(db)
    if row is None:
        row = OrgBranding(id=1, **DEFAULTS)
        db.add(row)
        await db.flush()
    return row


def _clean(field: str, value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise BadRequestError(f"{field} must not be empty")
    if len(value) > TEXT_LIMITS[field]:
        raise BadRequestError(f"{field} is too long (max {TEXT_LIMITS[field]} characters)")
    return value


def _check_color(field: str, value: str) -> str:
    if not palette.HEX.match(value):
        raise BadRequestError(f"{field} must be a colour like #3446b8")
    value = value.lower()
    if field in ("color_brand", "color_highlight") and not palette.button_contrast_ok(value):
        raise BadRequestError(f"{field} is too light: white text on it would be hard to read. Pick a darker colour")
    return value


async def update(db: AsyncSession, actor: User, changes: dict) -> dict:
    """Apply the given fields (None = unchanged). Validates texts, colours (hex + readable with white text) and lengths."""
    row = await _ensure_row(db)
    for field, value in changes.items():
        if value is None:
            continue
        if field in TEXT_LIMITS:
            setattr(row, field, _clean(field, value))
        elif field in COLOR_FIELDS:
            setattr(row, field, _check_color(field, value))
    row.updated_by, row.updated_at = actor.id, datetime.now(timezone.utc)
    await db.commit()
    logger.info("Branding updated by %s (%s)", actor.id, ", ".join(k for k, v in changes.items() if v is not None))
    return await read(db)


def validate_logo(data: bytes) -> str:
    """The real content decides the type (not the client's header): PNG / JPEG / WebP, decodable, at most 2048px a side."""
    if not data:
        raise BadRequestError("The file is empty")
    if len(data) > MAX_LOGO_BYTES:
        raise BadRequestError(f"The logo must be at most {MAX_LOGO_BYTES // 1024} KB")
    try:
        with Image.open(io.BytesIO(data)) as image:
            fmt, size = image.format, image.size
            image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise BadRequestError("The logo must be a PNG, JPEG or WebP image") from None
    if fmt not in _FORMATS:
        raise BadRequestError("The logo must be a PNG, JPEG or WebP image")
    if max(size) > MAX_LOGO_PIXELS:
        raise BadRequestError(f"The logo must be at most {MAX_LOGO_PIXELS}px on each side")
    return _FORMATS[fmt]


async def set_logo(db: AsyncSession, actor: User, data: bytes) -> dict:
    content_type = validate_logo(data)
    row = await _ensure_row(db)
    row.logo_data, row.logo_content_type = data, content_type
    row.logo_version += 1
    row.updated_by, row.updated_at = actor.id, datetime.now(timezone.utc)
    await db.commit()
    logger.info("Branding logo replaced by %s (v%s, %s bytes)", actor.id, row.logo_version, len(data))
    return await read(db)


async def delete_logo(db: AsyncSession, actor: User) -> dict:
    row = await _row(db)
    if row is None or row.logo_content_type is None:
        raise NotFoundError("No logo is set")
    row.logo_data, row.logo_content_type = None, None
    row.logo_version += 1
    row.updated_by, row.updated_at = actor.id, datetime.now(timezone.utc)
    await db.commit()
    return await read(db)


async def logo(db: AsyncSession) -> tuple[bytes, str, int]:
    row = await _row(db, with_logo=True)
    if row is None or row.logo_data is None or row.logo_content_type is None:
        raise NotFoundError("No logo is set")
    return row.logo_data, row.logo_content_type, row.logo_version
