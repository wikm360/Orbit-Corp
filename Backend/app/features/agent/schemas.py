from dataclasses import dataclass, field

from pydantic import BaseModel


class SourceCitation(BaseModel):
    document_id: str
    document_filename: str
    chunk_index: int
    snippet: str
    score: float


class AgentActivityEvent(BaseModel):
    """Shape of the `agent_activity` event sent to the client (over SSE or
    the group chat's websocket broadcast) while a turn is in progress."""

    status: str
    tool: str | None = None
    args: dict | None = None


@dataclass
class ToolExecutionResult:
    """What one tool call produces: `text` is what goes back to the model as
    the `role: tool` message content; `citations` is auxiliary structured
    data the engine collects for the turn's final `sources` list - kept
    separate so a tool never needs shared mutable state to report both."""

    text: str
    citations: list[SourceCitation] = field(default_factory=list)


@dataclass
class AgentTurnResult:
    content: str
    citations: list[SourceCitation] = field(default_factory=list)
