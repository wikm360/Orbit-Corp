from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context, require_super_admin
from app.features.branding import service

# Public: the login page needs the brand before anyone is signed in. Nothing sensitive is exposed (names, colours, logo).
public_router = APIRouter(prefix="/branding", tags=["branding"])
# Writes: super admins only.
admin_router = APIRouter(prefix="/admin/branding", tags=["branding"], dependencies=[Depends(require_super_admin)])


class BrandingUpdate(BaseModel):
    """Every field optional: only the ones sent change."""
    name: str | None = None
    short_name: str | None = None
    app_title: str | None = None
    description: str | None = None
    tagline: str | None = None
    product_label: str | None = None
    login_headline: str | None = None
    login_footer: str | None = None
    color_brand: str | None = None
    color_accent: str | None = None
    color_highlight: str | None = None


@public_router.get("")
async def get_branding(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-cache"
    return await service.read(db)


@public_router.get("/logo")
async def get_logo(db: AsyncSession = Depends(get_db)):
    data, content_type, version = await service.logo(db)
    # The URL carries ?v=<version>, so a replaced logo is a new URL and the old one may be cached for long.
    return Response(content=data, media_type=content_type, headers={
        "Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff", "ETag": f'"logo-{version}"',
    })


@admin_router.put("")
async def update_branding(payload: BrandingUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await service.update(db, context.user, payload.model_dump())


@admin_router.post("/logo")
async def upload_logo(file: UploadFile = File(...), context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    data = await file.read(service.MAX_LOGO_BYTES + 1)
    return await service.set_logo(db, context.user, data)


@admin_router.delete("/logo")
async def remove_logo(context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await service.delete_logo(db, context.user)
