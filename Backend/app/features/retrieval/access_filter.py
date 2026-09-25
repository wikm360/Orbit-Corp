import uuid

from sqlalchemy import ColumnElement, or_

from app.features.documents.models import Document, DocumentStatus


def accessible_documents_filter(
    project_id: uuid.UUID | None,
    conversation_id: uuid.UUID,
) -> ColumnElement[bool]:
    """SQLAlchemy filter expression: only documents visible from the current chat.

    Every document belongs to exactly one scope, so visibility is exactly:
    - files uploaded into *this* conversation, or
    - the project knowledge base of the conversation's project (if any).

    Nothing else - in particular, files uploaded to a different conversation
    are never visible here, even to the same user.
    """
    conditions = [Document.conversation_id == conversation_id]
    if project_id is not None:
        conditions.append(Document.project_id == project_id)
    return (Document.status == DocumentStatus.READY) & or_(*conditions)
