import uuid

import jwt as pyjwt
from fastapi import APIRouter, Depends, File, Query, UploadFile, WebSocket, WebSocketDisconnect, status as ws_status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory, get_db
from app.core.dependencies import UserContext, get_current_user_context
from app.core.exceptions import BadRequestError
from app.core.security import decode_access_token
from app.features.access_control.service import get_user_led_team_ids, get_user_team_ids
from app.features.auth.models import User
from app.features.chat import service
from app.features.chat.dependencies import require_conversation_access
from app.features.chat.models import Conversation, ConversationType
from app.features.chat.schemas import (
    ChatRequest,
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
    ConversationUpdate,
    GroupMessageCreate,
    MessageRead,
)
from app.features.chat.ws import manager as ws_manager
from app.features.documents import service as documents_service
from app.features.documents.schemas import DocumentUploadResponse
from app.features.projects.models import Project
from app.features.projects.service import get_user_project_ids

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


@router.post("")
async def chat(
    payload: ChatRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Personal AI chat: creates/continues a private conversation and streams
    the assistant's answer over SSE."""
    return StreamingResponse(
        service.stream_chat_response(db, context, payload.conversation_id, payload.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/conversations", response_model=ConversationRead)
async def create_conversation(
    payload: ConversationCreate,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_conversation(db, context, payload)


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_user_conversations(db, context)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation: Conversation = Depends(require_conversation_access),
    db: AsyncSession = Depends(get_db),
):
    await db.refresh(conversation, attribute_names=["messages"])
    return conversation


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    after: uuid.UUID | None = None,
    conversation: Conversation = Depends(require_conversation_access),
    db: AsyncSession = Depends(get_db),
):
    """Catch-up fetch for a client reconnecting to the websocket: messages
    strictly newer than `after` (or the full history if omitted)."""
    return await service.list_messages_after(db, conversation.id, after)


@router.patch("/conversations/{conversation_id}", response_model=ConversationRead)
async def update_conversation(
    payload: ConversationUpdate,
    context: UserContext = Depends(get_current_user_context),
    conversation: Conversation = Depends(require_conversation_access),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_conversation(db, context, conversation, payload.linked_project_id)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageRead)
async def post_group_message(
    payload: GroupMessageCreate,
    context: UserContext = Depends(get_current_user_context),
    conversation: Conversation = Depends(require_conversation_access),
    db: AsyncSession = Depends(get_db),
):
    if conversation.type != ConversationType.PROJECT_GROUP:
        raise BadRequestError("Only project group chats accept plain posted messages")
    return await service.post_group_message(db, context, conversation, payload.content)


@router.post("/conversations/{conversation_id}/documents", response_model=DocumentUploadResponse)
async def upload_conversation_document(
    file: UploadFile = File(...),
    context: UserContext = Depends(get_current_user_context),
    conversation: Conversation = Depends(require_conversation_access),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise BadRequestError("File exceeds the maximum allowed upload size")

    document = await documents_service.upload_conversation_document(
        db,
        conversation_id=conversation.id,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
        uploaded_by=context.id,
    )
    return DocumentUploadResponse(document=document)


async def _authenticate_websocket(db: AsyncSession, token: str) -> UserContext | None:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except pyjwt.PyJWTError:
        return None
    if user_id is None:
        return None

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        return None

    team_ids = await get_user_team_ids(db, user.id)
    led_team_ids = await get_user_led_team_ids(db, user.id)
    project_ids = await get_user_project_ids(db, user.id)
    return UserContext(user=user, team_ids=team_ids, led_team_ids=led_team_ids, project_ids=project_ids)


@router.websocket("/conversations/{conversation_id}/ws")
async def conversation_websocket(
    websocket: WebSocket,
    conversation_id: uuid.UUID,
    token: str = Query(...),
):
    # Browsers can't set an Authorization header on a WebSocket handshake, so
    # the access token travels as a query param instead.
    async with async_session_factory() as db:
        context = await _authenticate_websocket(db, token)
        if context is None:
            await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
            return

        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
            return

        if conversation.type == ConversationType.PERSONAL:
            allowed = conversation.created_by == context.id or context.is_admin
        else:
            allowed = context.is_project_member(conversation.project_id)
            if not allowed:
                project = await db.get(Project, conversation.project_id)
                allowed = project is not None and context.leads_team(project.team_id)

        if not allowed:
            await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
            return

    await ws_manager.connect(conversation_id, websocket)
    try:
        while True:
            # Sending happens over REST (so every message is persisted before
            # it's broadcast); this loop just keeps the connection open and
            # detects the client going away.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(conversation_id, websocket)
