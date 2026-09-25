import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context, require_project_manager
from app.core.exceptions import BadRequestError
from app.features.memory import service
from app.features.memory.schemas import ProjectMemoryCreate, ProjectMemoryRead, ProjectMemoryUpdate
from app.features.projects.models import Project

router = APIRouter(tags=["memory"])


@router.get("/projects/{project_id}/memories", response_model=list[ProjectMemoryRead])
async def list_project_memories(
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_project_memories(db, project.id)


@router.post("/projects/{project_id}/memories", response_model=ProjectMemoryRead)
async def create_project_memory(
    payload: ProjectMemoryCreate,
    project: Project = Depends(require_project_manager),
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await service.remember(db, project.id, context.id, payload.fact_text, payload.category)


@router.patch("/projects/{project_id}/memories/{memory_id}", response_model=ProjectMemoryRead)
async def update_project_memory(
    memory_id: uuid.UUID,
    payload: ProjectMemoryUpdate,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    memory = await service.get_memory(db, memory_id)
    if memory.project_id != project.id:
        raise BadRequestError("This memory does not belong to the given project")
    return await service.update_memory(
        db,
        memory,
        fact_text=payload.fact_text,
        category=payload.category,
        is_verified=payload.is_verified,
    )


@router.delete("/projects/{project_id}/memories/{memory_id}", status_code=204)
async def delete_project_memory(
    memory_id: uuid.UUID,
    project: Project = Depends(require_project_manager),
    db: AsyncSession = Depends(get_db),
):
    memory = await service.get_memory(db, memory_id)
    if memory.project_id != project.id:
        raise BadRequestError("This memory does not belong to the given project")
    await service.delete_memory(db, memory_id)
