import uuid

from sqlalchemy import ColumnElement, or_

from app.features.documents.models import Document, DocumentStatus


def accessible_documents_filter(
    project_id: uuid.UUID | None, conversation_id: uuid.UUID
) -> ColumnElement[bool]:
    """SQLAlchemy filter expression: only documents visible from the current chat.

    Applied directly inside the pgvector similarity query (not as a
    post-filter on already-fetched rows), so access control is enforced at
    the database level. Scope is always the current conversation's own
    ad hoc uploads, plus (for project group chats, or personal chats with a
    project linked) that project's shared knowledge base.
    """
    conditions = [Document.conversation_id == conversation_id]
    if project_id is not None:
        conditions.append(Document.project_id == project_id)
    return (Document.status == DocumentStatus.READY) & or_(*conditions)
