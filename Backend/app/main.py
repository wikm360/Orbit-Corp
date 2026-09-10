from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import model_registry  # noqa: F401 - registers all models on Base.metadata
from app.core.config import get_settings
from app.features.access_control.router import router as teams_router
from app.features.admin.router import router as admin_router
from app.features.auth.router import router as auth_router
from app.features.chat.router import router as chat_router
from app.features.documents.router import router as documents_router
from app.features.projects.router import router as projects_router

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(teams_router, prefix=settings.api_prefix)
app.include_router(projects_router, prefix=settings.api_prefix)
app.include_router(documents_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)


@app.get("/health")
async def health():
    return {"status": "ok"}
