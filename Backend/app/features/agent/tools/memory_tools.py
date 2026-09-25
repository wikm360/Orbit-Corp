import json
from typing import Any

from app.features.agent.schemas import ToolExecutionResult
from app.features.agent.scope import resolve_retrieval_scope
from app.features.agent.tools.base import BaseTool
from app.features.memory import service as memory_service
from app.features.memory.models import MemoryCategory

_CATEGORY_VALUES = [category.value for category in MemoryCategory]


class RecallProjectInsightsTool(BaseTool):
    name = "recall_project_insights"
    description = (
        "Semantically search this project's shared memory - facts, decisions, and "
        "conventions the team has previously told the assistant to remember. Only "
        "available in a project-linked conversation."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to recall"},
            "category": {
                "type": "string",
                "enum": _CATEGORY_VALUES,
                "description": "Optionally restrict to one category of memory",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self, *, db, context, conversation, query: str, category: str | None = None, **_: Any
    ) -> ToolExecutionResult:
        project_id = resolve_retrieval_scope(context, conversation)
        if project_id is None:
            return ToolExecutionResult(text="This conversation isn't linked to any project.")

        parsed_category = MemoryCategory(category) if category else None
        memories = await memory_service.recall(db, project_id, query, category=parsed_category)
        if not memories:
            return ToolExecutionResult(text="No relevant project memory found.")

        payload = [
            {"fact": memory.fact_text, "category": memory.category.value, "is_verified": memory.is_verified}
            for memory in memories
        ]
        return ToolExecutionResult(text=json.dumps(payload, ensure_ascii=False))


class RememberProjectInsightTool(BaseTool):
    name = "remember_project_insight"
    description = (
        "Save a fact or decision to this project's shared memory, so it can be "
        "recalled in future conversations by anyone on the project. Only call "
        "this when the user explicitly asks you to remember something - never "
        "on your own initiative. Only available in a project-linked conversation."
    )
    parameters = {
        "type": "object",
        "properties": {
            "fact": {"type": "string", "description": "The fact or decision to remember"},
            "category": {"type": "string", "enum": _CATEGORY_VALUES},
        },
        "required": ["fact", "category"],
    }

    async def execute(
        self, *, db, context, conversation, fact: str, category: str, **_: Any
    ) -> ToolExecutionResult:
        project_id = resolve_retrieval_scope(context, conversation)
        if project_id is None:
            return ToolExecutionResult(text="This conversation isn't linked to any project.")

        try:
            parsed_category = MemoryCategory(category)
        except ValueError:
            return ToolExecutionResult(
                text=f"'{category}' is not a valid category. Use one of: {', '.join(_CATEGORY_VALUES)}"
            )

        await memory_service.remember(db, project_id, context.id, fact, parsed_category)
        return ToolExecutionResult(text="Saved to project memory.")
