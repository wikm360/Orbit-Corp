from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import UserContext
from app.features.agent.schemas import ToolExecutionResult
from app.features.chat.models import Conversation


class BaseTool(ABC):
    """A capability the agent can call via the LLM's native tool-calling
    protocol.

    Every tool re-validates access itself using `context`/`conversation`
    rather than trusting the model's arguments - the model picks *which*
    document/project to touch, but a tool must never let it reach outside
    the current project or conversation just because it asked to.
    """

    name: str
    description: str
    parameters: dict  # JSON Schema for the tool's "arguments" object

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def is_available_for(
        self,
        context: UserContext | None = None,
        conversation: Conversation | None = None,
    ) -> bool:
        """Determines whether this tool should be offered in the LLM's prompt.

        By default, tools are available to all authenticated callers unless
        overridden by subclass logic.
        """
        return True

    @abstractmethod
    async def execute(
        self,
        *,
        db: AsyncSession,
        context: UserContext,
        conversation: Conversation,
        **arguments: Any,
    ) -> ToolExecutionResult: ...
