import uuid

from app.core.dependencies import UserContext
from app.features.chat.models import Conversation, ConversationType


def resolve_retrieval_scope(context: UserContext, conversation: Conversation) -> uuid.UUID | None:
    """Which project's knowledge base (if any) this conversation may search,
    on top of its own ad hoc uploads and the user's personal library.

    A project group chat is always scoped to its own project. A personal
    chat is scoped only to a project it has explicitly linked, and only for
    as long as the user is still a member of that project - membership is
    re-checked here rather than trusted from when the link was made.
    """
    if conversation.type == ConversationType.PROJECT_GROUP:
        return conversation.project_id
    if conversation.linked_project_id is not None and context.is_project_member(
        conversation.linked_project_id
    ):
        return conversation.linked_project_id
    return None
