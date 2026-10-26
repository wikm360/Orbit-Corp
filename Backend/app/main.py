import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core import model_registry  # noqa: F401 - registers all models on Base.metadata
from app.core.config import get_settings
from app.core.request_logging import RequestResponseLoggingMiddleware, configure_request_logger
from app.features.access_control.router import router as teams_router
from app.features.admin.panel import setup_admin_panel
from app.features.admin.router import inspector_router, router as admin_router
from app.features.auth.router import router as auth_router
from app.features.chat.router import router as chat_router
from app.features.db_connector.router import router as accounting_db_router
from app.features.documents.router import router as documents_router
from app.features.memory.router import router as memory_router
from app.features.projects.router import router as projects_router

logger = logging.getLogger(__name__)
settings = get_settings()


async def _auto_sync_schema_hints() -> None:
    try:
        from app.core.database import async_session_factory
        from app.features.db_connector.hints import ingest_hints

        logger.info("Checking schema hints status...")
        async with async_session_factory() as session:
            stats = await ingest_hints(session)
            logger.info("Schema hints sync completed: %s", stats)
    except Exception as exc:
        logger.warning("Automatic schema hints sync skipped or failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.rahkaran_db_enabled:
        asyncio.create_task(_auto_sync_schema_hints())
    yield


docs_url = "/docs" if settings.environment != "production" else None
redoc_url = "/redoc" if settings.environment != "production" else None
openapi_url = f"{settings.api_prefix}/openapi.json" if settings.environment != "production" else None

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def handle_proxy_headers_and_redirects(request: Request, call_next):
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto:
        request.scope["scheme"] = forwarded_proto.lower()

    response: Response = await call_next(request)

    if response.status_code in (301, 302, 303, 307, 308):
        location = response.headers.get("location")
        if location and location.startswith("http://") and (
            forwarded_proto == "https" or request.scope.get("scheme") == "https"
        ):
            response.headers["location"] = "https://" + location[7:]

    return response

if settings.request_logging_enabled:
    configure_request_logger()
    app.add_middleware(
        RequestResponseLoggingMiddleware,
        max_body_bytes=settings.request_log_body_limit_bytes,
    )

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(teams_router, prefix=settings.api_prefix)
app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(documents_router, prefix=settings.api_prefix)
app.include_router(memory_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(accounting_db_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(inspector_router, prefix=settings.api_prefix)
app.include_router(inspector_router)

setup_admin_panel(app)


@app.get("/health")
async def health():
    return {"status": "ok"}
