import uuid

from sqlalchemy import ColumnElement, or_

from app.features.documents.models import Document, DocumentStatus


def accessible_documents_filter(
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
) -> ColumnElement[bool]:
    """SQLAlchemy filter expression: only documents visible from the current chat.

    Includes:
    - Ad hoc uploads made inside this conversation
    - The linked/group project knowledge base (if any)
    - The user's own personal documents library
    """
    conditions = [Document.conversation_id == conversation_id]
    if project_id is not None:
        conditions.append(Document.project_id == project_id)
    if user_id is not None:
        conditions.append((Document.uploaded_by == user_id) & Document.project_id.is_(None))
    return (Document.status == DocumentStatus.READY) & or_(*conditions)
