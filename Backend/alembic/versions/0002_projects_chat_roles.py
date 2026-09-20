"""projects, group chat, super_admin role, refresh tokens

Revision ID: 0002_projects_chat_roles
Revises: 0001_init
Create Date: 2026-09-20

Upgrades the team/document-only schema from 0001 to the role/team/project/chat
model, keeping existing data:

- users.role gains `super_admin`; the oldest existing admin is promoted.
- teams gain description/created_by; team_memberships gain role/added_by/created_at
  (everyone becomes a plain `member`).
- new tables: refresh_tokens, projects, project_memberships.
- documents move from team scope to project scope. Every team that owned
  documents gets a "General" project holding them, and all of that team's
  members become members of it. `document_permissions` (cross-team sharing)
  has no equivalent in the project model and is dropped.
- conversations.user_id becomes created_by, plus type/project_id/linked_project_id.
- messages.role becomes sender_type (+ sender_id, reply_to_message_id).

Not reversible: the old shape can't be reconstructed from the new one.
"""
import hashlib
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0002_projects_chat_roles"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

team_role_enum = pg.ENUM("leader", "member", name="team_role", create_type=False)
conversation_type_enum = pg.ENUM(
    "personal", "project_group", name="conversation_type", create_type=False
)
sender_type_enum = pg.ENUM("user", "assistant", name="sender_type", create_type=False)


def _uuid_fk(column: str, target: str, ondelete: str, nullable: bool):
    return sa.Column(
        column, pg.UUID(as_uuid=True), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable
    )


def upgrade() -> None:
    bind = op.get_bind()

    # ALTER TYPE ... ADD VALUE can't be used in the same transaction that adds it.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'super_admin'")

    team_role_enum.create(bind, checkfirst=True)
    conversation_type_enum.create(bind, checkfirst=True)
    sender_type_enum.create(bind, checkfirst=True)

    op.execute(
        "UPDATE users SET role = 'super_admin' "
        "WHERE id = (SELECT id FROM users WHERE role = 'admin' ORDER BY created_at LIMIT 1)"
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("user_id", "users.id", "CASCADE", nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.add_column("teams", sa.Column("description", sa.Text, nullable=True))
    op.add_column("teams", _uuid_fk("created_by", "users.id", "SET NULL", nullable=True))

    op.add_column(
        "team_memberships",
        sa.Column("role", team_role_enum, nullable=False, server_default="member"),
    )
    op.add_column("team_memberships", _uuid_fk("added_by", "users.id", "SET NULL", nullable=True))
    op.add_column(
        "team_memberships",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "projects",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("team_id", "teams.id", "CASCADE", nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        _uuid_fk("created_by", "users.id", "SET NULL", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("team_id", "name", name="uq_project_team_name"),
    )
    op.create_index("ix_projects_team_id", "projects", ["team_id"])

    op.create_table(
        "project_memberships",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        _uuid_fk("project_id", "projects.id", "CASCADE", nullable=False),
        _uuid_fk("user_id", "users.id", "CASCADE", nullable=False),
        _uuid_fk("added_by", "users.id", "SET NULL", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )
    op.create_index("ix_project_memberships_project_id", "project_memberships", ["project_id"])
    op.create_index("ix_project_memberships_user_id", "project_memberships", ["user_id"])

    # --- conversations: user_id -> created_by, + type / project scope -------
    op.drop_constraint("conversations_user_id_fkey", "conversations", type_="foreignkey")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.alter_column("conversations", "user_id", new_column_name="created_by", nullable=True)
    op.create_foreign_key(
        "conversations_created_by_fkey",
        "conversations",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_conversations_created_by", "conversations", ["created_by"])
    op.add_column(
        "conversations",
        sa.Column("type", conversation_type_enum, nullable=False, server_default="personal"),
    )
    op.alter_column("conversations", "type", server_default=None)
    op.add_column("conversations", _uuid_fk("project_id", "projects.id", "CASCADE", nullable=True))
    op.add_column(
        "conversations", _uuid_fk("linked_project_id", "projects.id", "SET NULL", nullable=True)
    )
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"])

    # --- messages: role -> sender_type ---------------------------------------
    op.add_column("messages", sa.Column("sender_type", sender_type_enum, nullable=True))
    op.execute("UPDATE messages SET sender_type = role::text::sender_type")
    op.alter_column("messages", "sender_type", nullable=False)
    op.add_column("messages", _uuid_fk("sender_id", "users.id", "SET NULL", nullable=True))
    op.execute(
        "UPDATE messages m SET sender_id = c.created_by "
        "FROM conversations c WHERE c.id = m.conversation_id AND m.sender_type = 'user'"
    )
    op.add_column(
        "messages", _uuid_fk("reply_to_message_id", "messages.id", "SET NULL", nullable=True)
    )
    op.drop_column("messages", "role")
    op.execute("DROP TYPE message_role")

    # --- documents: team scope -> project scope ------------------------------
    op.add_column("documents", sa.Column("content_hash", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("embedding_model", sa.String(255), nullable=True))
    op.add_column("documents", _uuid_fk("project_id", "projects.id", "CASCADE", nullable=True))
    op.add_column(
        "documents", _uuid_fk("conversation_id", "conversations.id", "CASCADE", nullable=True)
    )

    op.execute(
        "INSERT INTO projects (id, team_id, name, description) "
        "SELECT gen_random_uuid(), t.id, 'General', "
        "'Documents migrated from the previous team-scoped model' "
        "FROM teams t WHERE EXISTS (SELECT 1 FROM documents d WHERE d.team_id = t.id)"
    )
    op.execute(
        "INSERT INTO project_memberships (id, project_id, user_id) "
        "SELECT gen_random_uuid(), p.id, tm.user_id "
        "FROM projects p JOIN team_memberships tm ON tm.team_id = p.team_id "
        "WHERE p.name = 'General'"
    )
    op.execute(
        "UPDATE documents d SET project_id = p.id "
        "FROM projects p WHERE p.team_id = d.team_id AND p.name = 'General'"
    )

    for doc_id, file_path in bind.execute(sa.text("SELECT id, file_path FROM documents")).all():
        path = Path(file_path)
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            # Missing file: a unique placeholder so it never matches (and thus
            # never gets reused as) another upload's content.
            digest = hashlib.sha256(str(doc_id).encode()).hexdigest()
        bind.execute(
            sa.text("UPDATE documents SET content_hash = :h WHERE id = :id"),
            {"h": digest, "id": doc_id},
        )

    op.alter_column("documents", "content_hash", nullable=False)
    op.drop_table("document_permissions")
    op.drop_column("documents", "team_id")
    op.create_check_constraint(
        "ck_document_single_scope",
        "documents",
        "(project_id IS NOT NULL AND conversation_id IS NULL) OR "
        "(project_id IS NULL AND conversation_id IS NOT NULL)",
    )
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_conversation_id", "documents", ["conversation_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])


def downgrade() -> None:
    raise NotImplementedError(
        "0002_projects_chat_roles can't be reversed: the previous team-scoped "
        "document permissions can't be reconstructed from the project model."
    )
