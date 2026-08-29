import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context
from app.core.exceptions import NotFoundError
from app.features.chat import service
from app.features.chat.models import Conversation
from app.features.chat.schemas import ChatRequest, ConversationDetail, ConversationRead

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(
    payload: ChatRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        service.stream_chat_response(db, context, payload.conversation_id, payload.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_conversations(db, context)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != context.id:
        raise NotFoundError("Conversation not found")
    await db.refresh(conversation, attribute_names=["messages"])
    return conversation
