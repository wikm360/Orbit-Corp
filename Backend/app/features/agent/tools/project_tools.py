import json
from typing import Any

from app.features.agent.schemas import ToolExecutionResult
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
