import uuid

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse, HTMLResponse

from app.core.database import async_session_factory, get_db
from app.core.dependencies import (
    get_current_user_context,
    require_admin,
    require_super_admin,
    UserContext,
)
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.features.admin import service
from app.features.admin.ocr_inspector_template import OCR_INSPECTOR_HTML
from app.features.auth.models import User, UserRole
from app.features.usage import quota as quota_module, service as usage_service
from app.features.auth.schemas import UserRead
from app.features.documents import service as documents_service
from app.features.documents.ingestion.parser import IMAGE_EXTENSIONS, render_pdf_page
from app.features.documents.ingestion.ocr_debugger import (
    get_debug_document_trace,
    get_debug_image_path,
    list_debug_documents,
)
from app.features.documents.models import Document, DocumentChunk, OcrCache
from app.features.documents.schemas import DocumentRead
from app.features.projects.models import Project

# Org-wide oversight only. Team/project creation and membership management
# live under /teams and /projects, with their own per-team/per-project
# permission checks (team leaders can manage their own team/projects without
# being global admins).
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole = UserRole.USER
    accounting_access: bool = False


class AccountingAccessUpdate(BaseModel):
    enabled: bool


class UserManagementAccessUpdate(BaseModel):
    enabled: bool


class WorkspaceAccessUpdate(BaseModel):
    enabled: bool


class TokenLimitUpdate(BaseModel):
    limit: int | None  # None = unlimited


class TokenLimitExtend(BaseModel):
    add: int


@router.put("/users/{user_id}/token-limit", response_model=UserRead, dependencies=[Depends(require_super_admin)])
async def set_token_limit(user_id: uuid.UUID, payload: TokenLimitUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    """Set (or, with `limit: null`, remove) a user's token limit. Super admins are never limited; only super admins manage an admin's."""
    return await usage_service.set_limit(db, context.user, user_id, payload.limit)


@router.post("/users/{user_id}/token-limit/extend", response_model=UserRead, dependencies=[Depends(require_super_admin)])
async def extend_token_limit(user_id: uuid.UUID, payload: TokenLimitExtend, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    """Raise the limit by `add` tokens; the usage counter is untouched."""
    return await usage_service.extend_limit(db, context.user, user_id, payload.add)


@router.post("/users/{user_id}/token-limit/reset", response_model=UserRead, dependencies=[Depends(require_super_admin)])
async def reset_token_usage(user_id: uuid.UUID, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    """Zero the counter and start a new period; the usage history is kept."""
    return await usage_service.reset_usage(db, context.user, user_id)


@router.get("/users/{user_id}/token-usage")
async def token_usage(user_id: uuid.UUID, days: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return await usage_service.usage_report(db, user, days)


class QuotaEnforcedUpdate(BaseModel):
    enforced: bool


class SetupPoolUpdate(BaseModel):
    enabled: bool | None = None      # null = leave as is
    budget_usd: float | None = None  # total budget (all-time used is subtracted); raise it to top up


class OrgCapUpdate(BaseModel):
    monthly_cap_usd: float | None  # null = no organisation cap


class QuotaPlanUpdate(BaseModel):
    five_hour_usd: float
    weekly_usd: float
    monthly_usd: float


class UserQuotaUpdate(BaseModel):
    """null cap = follow the role's plan; unlimited = no cap at all."""
    five_hour_usd: float | None = None
    weekly_usd: float | None = None
    monthly_usd: float | None = None
    unlimited: bool = False


@router.get("/quota")
async def quota_overview(db: AsyncSession = Depends(get_db)):
    """Plans per role, whether the dollar quota is enforced, and the current Jalali month's bounds."""
    return await usage_service.quota_overview(db)


@router.put("/quota/enforced", dependencies=[Depends(require_super_admin)])
async def set_quota_enforced(payload: QuotaEnforcedUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    """Off = shadow mode (cost recorded, nobody blocked by it). Super admins only."""
    return await usage_service.set_enforced(db, context.user, payload.enforced)


@router.put("/quota/setup-pool", dependencies=[Depends(require_super_admin)])
async def set_setup_pool(payload: SetupPoolUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    """The shared pool that pays OCR/embedding of project uploads instead of the uploader's quota. Super admins only."""
    return await usage_service.set_setup_pool(db, context.user, payload.enabled, payload.budget_usd)


@router.put("/quota/org-cap", dependencies=[Depends(require_super_admin)])
async def set_org_cap(payload: OrgCapUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    """Cap on the whole organisation's spend per Jalali month (everyone but super admins is blocked once it is reached)."""
    return await usage_service.set_org_cap(db, context.user, payload.monthly_cap_usd)


@router.put("/quota/plans/{role}", dependencies=[Depends(require_super_admin)])
async def set_quota_plan(role: str, payload: QuotaPlanUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    return await usage_service.set_plan(db, context.user, role, payload.five_hour_usd, payload.weekly_usd, payload.monthly_usd)


@router.get("/users/{user_id}/quota")
async def user_quota(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return await quota_module.user_quota(db, user)


@router.put("/users/{user_id}/quota", dependencies=[Depends(require_super_admin)])
async def set_user_quota(user_id: uuid.UUID, payload: UserQuotaUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    user = await usage_service.set_user_quota(db, context.user, user_id, payload.five_hour_usd, payload.weekly_usd, payload.monthly_usd, payload.unlimited)
    return await quota_module.user_quota(db, user)


class ModelPriceUpdate(BaseModel):
    input_per_m: float = 0.0   # USD per 1M input tokens
    output_per_m: float = 0.0  # USD per 1M output tokens
    per_page_usd: float | None = None  # USD per page, for per-page priced models (Mistral OCR)


def _price_out(row) -> dict:
    return {"model": row.model, "input_per_m": float(row.input_per_m), "output_per_m": float(row.output_per_m),
            "per_page_usd": None if row.per_page_usd is None else float(row.per_page_usd),
            "updated_by": str(row.updated_by) if row.updated_by else None, "updated_at": row.updated_at}


@router.get("/model-prices")
async def list_model_prices(db: AsyncSession = Depends(get_db)):
    return [_price_out(r) for r in await usage_service.list_prices(db)]


@router.put("/model-prices/{model:path}", dependencies=[Depends(require_super_admin)])
async def set_model_price(model: str, payload: ModelPriceUpdate, context: UserContext = Depends(get_current_user_context), db: AsyncSession = Depends(get_db)):
    """Super admins only. Applies to calls recorded from now on; recorded history keeps its cost."""
    return _price_out(await usage_service.set_price(db, context.user, model, payload.input_per_m, payload.output_per_m, payload.per_page_usd))


@router.delete("/model-prices/{model:path}", status_code=204, dependencies=[Depends(require_super_admin)])
async def delete_model_price(model: str, db: AsyncSession = Depends(get_db)):
    await usage_service.delete_price(db, model)
    return Response(status_code=204)


@router.get("/usage/cost-summary")
async def cost_summary(days: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db)):
    """Org-wide cost per purpose / model / user (monitoring; nothing is blocked by cost yet)."""
    return await usage_service.cost_summary(db, days)


@router.get("/users", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db)):
    return await service.list_users(db)


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    if payload.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN) and not context.is_super_admin:
        raise ForbiddenError("Only super admins can create admin users")
    if payload.accounting_access and not context.is_super_admin:
        raise ForbiddenError("Only super admins can grant accounting access")
    return await service.create_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=payload.role,
        accounting_access_granted_by=context.id if payload.accounting_access else None,
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=UserRead,
    dependencies=[Depends(require_super_admin)],
)
async def set_user_role(user_id: uuid.UUID, payload: UserRoleUpdate, db: AsyncSession = Depends(get_db)):
    """Granting ADMIN/SUPER_ADMIN is reserved for super admins, to avoid a
    plain admin escalating themselves or others."""
    return await service.set_user_role(db, user_id, payload.role)


@router.put(
    "/users/{user_id}/accounting-access",
    response_model=UserRead,
    dependencies=[Depends(require_super_admin)],
)
async def set_accounting_access(
    user_id: uuid.UUID,
    payload: AccountingAccessUpdate,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Super admins grant or revoke the Rahkaran accounting tools for any user (admin or not). A super admin always has
    access and cannot be changed here, so the organisation can never lock itself out."""
    return await service.set_accounting_access(db, user_id, enabled=payload.enabled, granted_by=context.id)


@router.put(
    "/users/{user_id}/user-management-access",
    response_model=UserRead,
    dependencies=[Depends(require_super_admin)],
)
async def set_user_management_access(
    user_id: uuid.UUID,
    payload: UserManagementAccessUpdate,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Super admins delegate (or take back) account management (`/user-management`) to any user."""
    from app.features.user_management import service as user_management_service

    return await user_management_service.set_access(db, user_id, enabled=payload.enabled, granted_by=context.id)


@router.put(
    "/users/{user_id}/workspace-access",
    response_model=UserRead,
    dependencies=[Depends(require_super_admin)],
)
async def set_workspace_access(
    user_id: uuid.UUID,
    payload: WorkspaceAccessUpdate,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Super admins delegate (or take back) team/project administration to any non-admin user."""
    return await service.set_workspace_access(db, user_id, enabled=payload.enabled, granted_by=context.id)


@router.get("/documents", response_model=list[DocumentRead])
async def list_all_documents(db: AsyncSession = Depends(get_db)):
    return await service.list_all_documents(db)


# Inspector router without strict header bearer requirements so browser tabs & img tags render cleanly
inspector_router = APIRouter(prefix="/admin", tags=["admin-inspector"])


@inspector_router.get("/ocr-inspector", response_class=HTMLResponse)
async def ocr_inspector_page():
    """Serves the interactive visual OCR and layout inspector dashboard."""
    return HTMLResponse(content=OCR_INSPECTOR_HTML)


@inspector_router.get("/ocr-debug/list")
async def get_ocr_debug_list():
    """Lists all documents with recorded OCR debug traces."""
    return list_debug_documents()


@inspector_router.get("/ocr-debug/{document_id}")
async def get_ocr_debug_detail(document_id: str):
    """Retrieves the full OCR debug trace for a document."""
    trace = get_debug_document_trace(document_id)
    if not trace:
        raise NotFoundError("Debug trace not found for document")
    return trace


@inspector_router.get("/ocr-debug/{document_id}/image/{filename}")
async def get_ocr_debug_image(document_id: str, filename: str):
    """Serves annotated page images or cropped block images."""
    image_path = get_debug_image_path(document_id, filename)
    if not image_path:
        raise NotFoundError("Image not found")
    media_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    return FileResponse(image_path, media_type=media_type)


@inspector_router.get("/documents-inspect/list")
async def list_inspectable_documents():
    """Lists all documents with their project, page counts, and ingestion status."""
    async with async_session_factory() as db:
        stmt = (
            select(Document, Project.name.label("project_name"))
            .outerjoin(Project, Document.project_id == Project.id)
            .order_by(Document.created_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {
                "id": str(doc.id),
                "filename": doc.filename,
                "status": doc.status.value,
                "content_type": doc.content_type,
                "project_id": str(doc.project_id) if doc.project_id else None,
                "project_name": proj_name or ("گفتگوی شخصی" if doc.conversation_id else "بدون پروژه"),
                "conversation_id": str(doc.conversation_id) if doc.conversation_id else None,
                "error_message": doc.error_message,
                "created_at": doc.created_at.isoformat() if doc.created_at else "",
            }
            for doc, proj_name in rows
        ]


@inspector_router.get("/documents-inspect/{document_id}")
async def get_document_inspect_detail(document_id: str):
    """Retrieves full document page texts, reconstruction data, and chunk counts."""
    doc_uuid = uuid.UUID(document_id)
    async with async_session_factory() as db:
        doc = await db.get(Document, doc_uuid)
        if doc is None:
            raise NotFoundError("Document not found")

        chunk_count = await db.scalar(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_uuid)
        )

        ocr_cache_count = await db.scalar(
            select(func.count(OcrCache.cache_key)).where(OcrCache.document_id == doc_uuid)
        )

        project_name = None
        if doc.project_id:
            project = await db.get(Project, doc.project_id)
            if project:
                project_name = project.name

    # Load reconstructed json if available
    recon = documents_service.load_reconstructed_document(doc.file_path)
    pages = []
    if recon and "pages" in recon:
        for p in recon["pages"]:
            text = (p.get("text") or "").strip()
            pages.append(
                {
                    "page": p.get("page", 1),
                    "text": text,
                    "text_len": len(text),
                    "has_images": bool(p.get("has_images")),
                    "metadata": p.get("metadata") or {},
                }
            )
    elif chunk_count and chunk_count > 0:
        # Fallback to chunks grouped by page
        async with async_session_factory() as db:
            chunks = (
                await db.scalars(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == doc_uuid)
                    .order_by(DocumentChunk.chunk_index)
                )
            ).all()
        grouped: dict[int, list[str]] = {}
        for c in chunks:
            page_num = c.page_number or 1
            grouped.setdefault(page_num, []).append(c.content)
        for page_num in sorted(grouped.keys()):
            combined = "\n\n".join(grouped[page_num])
            pages.append(
                {
                    "page": page_num,
                    "text": combined,
                    "text_len": len(combined),
                    "has_images": False,
                    "metadata": {"source": "chunks"},
                }
            )

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status.value,
        "content_type": doc.content_type,
        "error_message": doc.error_message,
        "project_name": project_name or ("گفتگوی شخصی" if doc.conversation_id else "بدون پروژه"),
        "total_pages": len(pages),
        "chunk_count": chunk_count or 0,
        "ocr_cache_count": ocr_cache_count or 0,
        "pages": pages,
    }


@inspector_router.get("/documents-inspect/{document_id}/page-image/{page_number}")
async def get_document_inspect_page_image(document_id: str, page_number: int):
    """Renders a PDF page to PNG or returns the original image file for visual inspection."""
    doc_uuid = uuid.UUID(document_id)
    async with async_session_factory() as db:
        doc = await db.get(Document, doc_uuid)
        if doc is None:
            raise NotFoundError("Document not found")

    import asyncio
    from pathlib import Path

    suffix = Path(doc.file_path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        if page_number != 1:
            raise BadRequestError("Single image document only has page 1")
        data = Path(doc.file_path).read_bytes()
        media_type = "image/png" if suffix == ".png" else "image/jpeg"
        return Response(content=data, media_type=media_type)

    if suffix != ".pdf":
        raise BadRequestError(f"Page images not supported for '{suffix}'")

    rendered = await asyncio.to_thread(render_pdf_page, doc.file_path, page_number)
    if rendered is None:
        raise NotFoundError("Page image could not be rendered")

    return Response(content=rendered.data, media_type="image/png")


@inspector_router.post("/documents-inspect/{document_id}/reprocess")
async def reprocess_document_inspect(document_id: str):
    """Re-enqueues the document for full ingestion and OCR."""
    doc_uuid = uuid.UUID(document_id)
    async with async_session_factory() as db:
        doc = await documents_service.reprocess_document(db, doc_uuid)
        return {"status": "ok", "message": f"Document '{doc.filename}' re-queued for processing"}


@inspector_router.post("/documents-inspect/{document_id}/purge-ocr-cache")
async def purge_document_ocr_cache_endpoint(document_id: str):
    """Purges all cached OCR readings for this document."""
    from app.features.documents.ingestion.ocr_cache import purge_document_ocr_cache

    doc_uuid = uuid.UUID(document_id)
    async with async_session_factory() as db:
        doc = await db.get(Document, doc_uuid)
        if doc is None:
            raise NotFoundError("Document not found")
        count = await purge_document_ocr_cache(db, doc_uuid)
        return {
            "status": "ok",
            "deleted_count": count,
            "message": f"کش OCR مربوط به {count} صفحه از فایل '{doc.filename}' با موفقیت حذف شد.",
        }


@inspector_router.post("/documents-inspect/{document_id}/reprocess-fresh")
async def reprocess_fresh_document_inspect(document_id: str):
    """Purges cached OCR readings first, then re-enqueues document for a fresh OCR run."""
    from app.features.documents.ingestion.ocr_cache import purge_document_ocr_cache

    doc_uuid = uuid.UUID(document_id)
    async with async_session_factory() as db:
        doc = await db.get(Document, doc_uuid)
        if doc is None:
            raise NotFoundError("Document not found")
        deleted_count = await purge_document_ocr_cache(db, doc_uuid)
        doc = await documents_service.reprocess_document(db, doc_uuid)
        return {
            "status": "ok",
            "deleted_cache_count": deleted_count,
            "message": f"کش قدیمی ({deleted_count} صفحه) حذف شد و پردازش مجدد بدون کش برای فایل '{doc.filename}' آغاز گردید.",
        }

