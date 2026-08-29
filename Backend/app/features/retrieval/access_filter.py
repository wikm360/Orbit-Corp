from sqlalchemy import ColumnElement, or_, select

from app.core.dependencies import UserContext
from app.features.access_control.models import DocumentPermission
from app.features.documents.models import Document, DocumentStatus


def accessible_documents_filter(context: UserContext) -> ColumnElement[bool]:
    """SQLAlchemy filter expression: only documents the user's teams may see.

    Applied directly inside the pgvector similarity query (not as a
    post-filter on already-fetched rows), so access control is enforced at
    the database level and never leaks chunk content through pagination.
    """
    shared_document_ids = select(DocumentPermission.document_id).where(
        DocumentPermission.team_id.in_(context.team_ids)
    )
    return (
        Document.status == DocumentStatus.READY
    ) & or_(
        Document.team_id.in_(context.team_ids),
        Document.id.in_(shared_document_ids),
    )
