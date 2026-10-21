import logging
from typing import Any

from fastapi import FastAPI
from starlette.requests import Request
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import engine, async_session_factory
from app.core.security import hash_password, verify_password

logger = logging.getLogger(__name__)


def setup_admin_panel(app: FastAPI) -> None:
    """Mounts SQLAdmin at /db-admin with session-based authentication."""
    try:
        from sqladmin import Admin, ModelView
        from sqladmin.authentication import AuthenticationBackend
    except ImportError:
        logger.warning("sqladmin not installed, skipping admin panel setup.")
        return

    from app.features.access_control.models import Team, TeamMembership
    from app.features.auth.models import RefreshToken, User, UserRole
    from app.features.chat.models import Conversation, Message
    from app.features.db_connector.models import DbQueryLog, SchemaHint
    from app.features.documents.models import Document, DocumentChunk
    from app.features.memory.models import ProjectMemory
    from app.features.projects.models import Project, ProjectMembership

    settings = get_settings()

    class AdminAuth(AuthenticationBackend):
        async def login(self, request: Request) -> bool:
            form = await request.form()
            email = str(form.get("username", "")).strip()
            password = str(form.get("password", "")).strip()

            if not email or not password:
                return False

            async with async_session_factory() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user is None:
                    return False
                if not verify_password(password, user.hashed_password):
                    return False
                if user.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
                    return False

                request.session.update({
                    "user_id": str(user.id),
                    "user_email": user.email,
                    "user_role": user.role.value,
                })
                return True

        async def logout(self, request: Request) -> bool:
            request.session.clear()
            return True

        async def authenticate(self, request: Request) -> bool:
            user_id = request.session.get("user_id")
            user_role = request.session.get("user_role")
            if not user_id or not user_role:
                return False
            return user_role in (UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value)

    authentication_backend = AdminAuth(secret_key=settings.jwt_secret_key)

    admin = Admin(
        app,
        engine,
        base_url="/db-admin",
        title="Orbit Database Admin",
        authentication_backend=authentication_backend,
    )

    # -------------------------------------------------------------------------
    # Model Views (using only verified attributes on each model)
    # -------------------------------------------------------------------------
    class UserAdmin(ModelView, model=User):
        name = "User"
        name_plural = "Users"
        icon = "fa-solid fa-users"
        column_list = [User.id, User.email, User.full_name, User.role, User.created_at]
        column_searchable_list = [User.email, User.full_name]
        column_sortable_list = [User.email, User.role, User.created_at]
        column_details_exclude_list = [User.hashed_password]
        form_excluded_columns = [User.team_memberships, User.created_at]

        async def on_model_change(self, data: dict, model: Any, is_created: bool, request: Request) -> None:
            if "hashed_password" in data and data["hashed_password"]:
                val = str(data["hashed_password"])
                if not (val.startswith("$2b$") or val.startswith("$2a$")):
                    data["hashed_password"] = hash_password(val)

    class RefreshTokenAdmin(ModelView, model=RefreshToken):
        name = "Refresh Token"
        name_plural = "Refresh Tokens"
        icon = "fa-solid fa-key"
        can_create = False
        can_edit = False
        column_list = [RefreshToken.id, RefreshToken.user_id, RefreshToken.expires_at, RefreshToken.created_at, RefreshToken.revoked_at]
        column_sortable_list = [RefreshToken.created_at, RefreshToken.expires_at]

    class TeamAdmin(ModelView, model=Team):
        name = "Team"
        name_plural = "Teams"
        icon = "fa-solid fa-people-group"
        column_list = [Team.id, Team.name, Team.created_by, Team.created_at]
        column_searchable_list = [Team.name]
        column_sortable_list = [Team.name, Team.created_at]
        form_excluded_columns = [Team.memberships, Team.created_at]

    class TeamMembershipAdmin(ModelView, model=TeamMembership):
        name = "Team Membership"
        name_plural = "Team Memberships"
        icon = "fa-solid fa-id-badge"
        column_list = [TeamMembership.id, TeamMembership.team_id, TeamMembership.user_id, TeamMembership.role, TeamMembership.created_at]
        column_sortable_list = [TeamMembership.role, TeamMembership.created_at]
        form_excluded_columns = [TeamMembership.created_at]

    class ProjectAdmin(ModelView, model=Project):
        name = "Project"
        name_plural = "Projects"
        icon = "fa-solid fa-diagram-project"
        column_list = [Project.id, Project.name, Project.team_id, Project.created_by, Project.created_at]
        column_searchable_list = [Project.name]
        column_sortable_list = [Project.name, Project.created_at]
        form_excluded_columns = [Project.memberships, Project.created_at]

    class ProjectMembershipAdmin(ModelView, model=ProjectMembership):
        name = "Project Membership"
        name_plural = "Project Memberships"
        icon = "fa-solid fa-user-check"
        column_list = [ProjectMembership.id, ProjectMembership.project_id, ProjectMembership.user_id, ProjectMembership.created_at]
        column_sortable_list = [ProjectMembership.created_at]
        form_excluded_columns = [ProjectMembership.created_at]

    class DocumentAdmin(ModelView, model=Document):
        name = "Document"
        name_plural = "Documents"
        icon = "fa-solid fa-file"
        column_list = [Document.id, Document.filename, Document.content_type, Document.status, Document.project_id, Document.created_at]
        column_searchable_list = [Document.filename]
        column_sortable_list = [Document.status, Document.created_at]
        form_excluded_columns = [Document.chunks, Document.created_at]

    class DocumentChunkAdmin(ModelView, model=DocumentChunk):
        name = "Document Chunk"
        name_plural = "Document Chunks"
        icon = "fa-solid fa-file-lines"
        column_list = [DocumentChunk.id, DocumentChunk.document_id, DocumentChunk.chunk_index]
        column_details_exclude_list = [DocumentChunk.embedding, DocumentChunk.search_tsv]
        can_create = False
        form_excluded_columns = [DocumentChunk.embedding, DocumentChunk.search_tsv]

    class ProjectMemoryAdmin(ModelView, model=ProjectMemory):
        name = "Project Memory"
        name_plural = "Project Memories"
        icon = "fa-solid fa-brain"
        column_list = [ProjectMemory.id, ProjectMemory.project_id, ProjectMemory.created_by_user_id, ProjectMemory.category, ProjectMemory.created_at]
        column_details_exclude_list = [ProjectMemory.embedding]
        form_excluded_columns = [ProjectMemory.embedding, ProjectMemory.created_at, ProjectMemory.updated_at]

    class ConversationAdmin(ModelView, model=Conversation):
        name = "Conversation"
        name_plural = "Conversations"
        icon = "fa-solid fa-comments"
        column_list = [Conversation.id, Conversation.type, Conversation.title, Conversation.project_id, Conversation.created_by, Conversation.created_at]
        column_searchable_list = [Conversation.title]
        column_sortable_list = [Conversation.type, Conversation.created_at]
        form_excluded_columns = [Conversation.messages, Conversation.created_at]

    class MessageAdmin(ModelView, model=Message):
        name = "Message"
        name_plural = "Messages"
        icon = "fa-solid fa-message"
        column_list = [Message.id, Message.conversation_id, Message.sender_type, Message.sender_id, Message.created_at]
        column_sortable_list = [Message.created_at]
        can_create = False
        form_excluded_columns = [Message.conversation, Message.created_at]

    class DbQueryLogAdmin(ModelView, model=DbQueryLog):
        name = "Query Log"
        name_plural = "Query Logs"
        icon = "fa-solid fa-database"
        column_list = [DbQueryLog.id, DbQueryLog.user_id, DbQueryLog.status, DbQueryLog.duration_ms, DbQueryLog.row_count, DbQueryLog.created_at]
        column_searchable_list = [DbQueryLog.question]
        column_sortable_list = [DbQueryLog.status, DbQueryLog.created_at, DbQueryLog.duration_ms]
        can_create = False

    class SchemaHintAdmin(ModelView, model=SchemaHint):
        name = "Schema Hint"
        name_plural = "Schema Hints"
        icon = "fa-solid fa-lightbulb"
        column_list = [SchemaHint.id, SchemaHint.hint_key, SchemaHint.kind, SchemaHint.title]
        column_searchable_list = [SchemaHint.hint_key, SchemaHint.title]
        column_details_exclude_list = [SchemaHint.embedding]
        form_excluded_columns = [SchemaHint.embedding, SchemaHint.updated_at]

    admin.add_view(UserAdmin)
    admin.add_view(RefreshTokenAdmin)
    admin.add_view(TeamAdmin)
    admin.add_view(TeamMembershipAdmin)
    admin.add_view(ProjectAdmin)
    admin.add_view(ProjectMembershipAdmin)
    admin.add_view(DocumentAdmin)
    admin.add_view(DocumentChunkAdmin)
    admin.add_view(ProjectMemoryAdmin)
    admin.add_view(ConversationAdmin)
    admin.add_view(MessageAdmin)
    admin.add_view(DbQueryLogAdmin)
    admin.add_view(SchemaHintAdmin)

    logger.info("SQLAdmin panel mounted at /db-admin")
