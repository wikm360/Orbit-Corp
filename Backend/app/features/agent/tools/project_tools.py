import json
from typing import Any

from app.features.agent.schemas import ToolExecutionResult
from app.features.agent.scope import resolve_retrieval_scope
from app.features.agent.tools.base import BaseTool
from app.features.documents import service as documents_service
from app.features.projects import service as projects_service


class ListUserProjectsTool(BaseTool):
    name = "list_user_projects"
    description = "List the projects the current user is a member of."
    parameters = {"type": "object", "properties": {}}

    async def execute(self, *, db, context, conversation, **_: Any) -> ToolExecutionResult:
        projects = await projects_service.list_user_projects(db, context.id)
        payload = [{"id": str(project.id), "name": project.name} for project in projects]
        return ToolExecutionResult(text=json.dumps(payload, ensure_ascii=False))


class ListProjectDocumentsTool(BaseTool):
    name = "list_project_documents"
    description = (
        "List documents in the current conversation's project knowledge base "
        "(not ad hoc chat attachments - use get_current_chat_attachments for "
        "those). Only available in a project group chat, or a personal chat "
        "linked to a project."
    )
    parameters = {"type": "object", "properties": {}}

    async def execute(self, *, db, context, conversation, **_: Any) -> ToolExecutionResult:
        project_id = resolve_retrieval_scope(context, conversation)
        if project_id is None:
            return ToolExecutionResult(text="This conversation isn't linked to any project.")

        documents = await documents_service.list_project_documents(db, project_id)
        payload = [
            {"id": str(document.id), "filename": document.filename, "status": document.status.value}
            for document in documents
        ]
        return ToolExecutionResult(text=json.dumps(payload, ensure_ascii=False))


class GetCurrentChatAttachmentsTool(BaseTool):
    name = "get_current_chat_attachments"
    description = "List files uploaded directly into the current conversation."
    parameters = {"type": "object", "properties": {}}

    async def execute(self, *, db, context, conversation, **_: Any) -> ToolExecutionResult:
        documents = await documents_service.list_conversation_documents(db, conversation.id)
        payload = [
            {"id": str(document.id), "filename": document.filename, "status": document.status.value}
            for document in documents
        ]
        return ToolExecutionResult(text=json.dumps(payload, ensure_ascii=False))
