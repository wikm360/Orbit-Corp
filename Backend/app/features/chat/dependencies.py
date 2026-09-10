import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import UserContext, get_current_user_context
from app.core.exceptions import ForbiddenError, NotFoundError
from app.features.chat.models import Conversation, ConversationType
from app.features.projects.models import Project


async def require_conversation_access(
    conversation_id: uuid.UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    """A personal conversation's owner, any member of a group chat's project,
    that project's team leader(s), or an org admin."""
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation not found")

    if conversation.type == ConversationType.PERSONAL:
        if conversation.created_by != context.id and not context.is_admin:
            raise ForbiddenError("This is another user's personal conversation")
        return conversation

    if context.is_project_member(conversation.project_id):
        return conversation
    project = await db.get(Project, conversation.project_id)
    if project is not None and context.leads_team(project.team_id):
        return conversation
    raise ForbiddenError("You are not a member of this project")
