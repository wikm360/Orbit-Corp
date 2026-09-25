import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import UserContext
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.features.agent.schemas import ToolExecutionResult
from app.features.agent.tools.base import BaseTool
from app.features.agent.tools.document_tools import (
    GetDocumentOutlineTool,
    ReadDocumentPagesTool,
    ReadEntireDocumentTool,
    SearchKnowledgeBaseTool,
)
from app.features.agent.tools.memory_tools import RecallProjectInsightsTool, RememberProjectInsightTool
from app.features.agent.tools.project_tools import (
    GetCurrentChatAttachmentsTool,
    ListProjectDocumentsTool,
    ListUserProjectsTool,
)
from app.features.chat.models import Conversation

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Holds every tool the agent may call and dispatches by name.

    A tool failure - a permission error, a bad argument, an unexpected
    exception - is always turned into a plain-text result here rather than
    propagated, so one bad tool call can't kill the turn or drop the
    websocket/SSE connection; the model just sees why it failed and can try
    something else.
    """

    def __init__(self, tools: list[BaseTool]):
        self._tools: dict[str, BaseTool] = {tool.name: tool for tool in tools}

    def to_openai_tools(self) -> list[dict]:
        return [tool.to_openai_tool() for tool in self._tools.values()]

    async def dispatch(
        self,
        name: str,
        arguments_json: str,
        *,
        db: AsyncSession,
        context: UserContext,
        conversation: Conversation,
    ) -> ToolExecutionResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolExecutionResult(text=f"Unknown tool: '{name}'")

        try:
            arguments = json.loads(arguments_json) if arguments_json else {}
        except (json.JSONDecodeError, TypeError):
            return ToolExecutionResult(text=f"Invalid arguments for tool '{name}': not valid JSON")

        try:
            return await tool.execute(db=db, context=context, conversation=conversation, **arguments)
        except ForbiddenError:
            return ToolExecutionResult(text="Permission Denied")
        except NotFoundError as exc:
            return ToolExecutionResult(text=exc.detail)
        except BadRequestError as exc:
            return ToolExecutionResult(text=f"Invalid request: {exc.detail}")
        except TypeError as exc:
            # Most often the model passing an argument (or missing a
            # required one) that this tool's `execute` doesn't accept - a
            # schema mismatch, not a system failure.
            return ToolExecutionResult(text=f"Invalid arguments for tool '{name}': {exc}")
        except Exception:
            logger.exception("Tool '%s' failed", name)
            return ToolExecutionResult(text=f"Tool '{name}' failed unexpectedly. Try a different approach.")


def build_default_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            GetDocumentOutlineTool(),
            ReadDocumentPagesTool(),
            ReadEntireDocumentTool(),
            SearchKnowledgeBaseTool(),
            ListUserProjectsTool(),
            ListProjectDocumentsTool(),
            GetCurrentChatAttachmentsTool(),
            RecallProjectInsightsTool(),
            RememberProjectInsightTool(),
        ]
    )
