from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Literal, TypedDict

import asyncio
import logging

import httpx
import openai
from openai import AsyncOpenAI

from app.core.config import get_settings


logger = logging.getLogger(__name__)

_STREAM_ATTEMPTS = 3
_TRANSIENT_STREAM_ERRORS = (
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.ReadTimeout,
    httpx.ConnectError,
    httpx.ConnectTimeout,
    openai.APIConnectionError,
    openai.APITimeoutError,
)


class ToolCall(TypedDict):
    id: str
    name: str
    arguments: str  # raw JSON string, not yet parsed - the caller decides how


# The OpenAI function-tool schema: {"type": "function", "function": {"name":
# ..., "description": ..., "parameters": <JSON Schema>}}. Left as a plain
# dict (not modeled field-by-field) since providers only ever pass it through
# to the vendor SDK verbatim.
ToolSpec = dict


class ChatMessage(TypedDict, total=False):
    role: str
    # A plain string, or a list of OpenAI content parts ({"type": "text"|"image_url", ...}) for a message with images.
    content: str | list[dict] | None
    # Set on an assistant message that called tools instead of (or before)
    # answering, so it can be replayed back into history on the next turn.
    # This is the OpenAI wire format (not the flat `ToolCall` shape `stream_chat`
    # reports in a `tool_calls` event): a list of
    # {"id": ..., "type": "function", "function": {"name": ..., "arguments": ...}}
    # - callers building this from a `ToolCall` need to re-nest it.
    tool_calls: list[dict]
    # Set on a `role: "tool"` message: which call this is the result of.
    tool_call_id: str


class ContentEvent(TypedDict):
    type: Literal["content"]
    delta: str


class ToolCallsEvent(TypedDict):
    type: Literal["tool_calls"]
    calls: list[ToolCall]


StreamEvent = ContentEvent | ToolCallsEvent


class LLMProvider(ABC):
    """Abstract interface every chat/completion backend must implement.

    Callers never talk to the OpenAI SDK (or any vendor SDK) directly, so the
    model/vendor can be swapped, or a fallback provider added, purely via config.
    """

    @abstractmethod
    def stream_chat(
        self, messages: list[ChatMessage], tools: list[ToolSpec] | None = None, tool_choice: str = "auto"
    ) -> AsyncIterator[StreamEvent]:
        """Streams the model's turn as it arrives.

        Yields zero or more `content` events (text deltas, in order), then -
        only if the model chose to call one or more tools instead of (or
        before) finishing its answer - a single trailing `tool_calls` event
        once the call(s) are fully accumulated. A turn never mixes further
        content after a `tool_calls` event; the caller runs the tools and
        starts a new `stream_chat` turn with the results appended to history.
        """


async def _strip_tag_blocks(
    stream: AsyncIterator[str], tag_names: list[str]
) -> AsyncIterator[str]:
    """Filters out `<tag>...</tag>` blocks (for the given tag names) from a
    stream of text deltas, yielding everything else as-is.

    Some reasoning models (observed with Qwen3.x on at least one gateway)
    stream their chain-of-thought directly inside the answer's `content`
    field wrapped in tags like `<thought>`, and don't reliably honor the
    `enable_thinking` request flag that's supposed to suppress this. Since
    the tag can't be trusted to arrive as a single delta (it may be split
    across many small streamed chunks), this buffers only while a match is
    ambiguous or a stripped tag is open, and otherwise passes deltas
    straight through so real streaming is preserved outside of the (usually
    front-loaded) thinking blocks.

    Content hidden inside an open tag is held, not discarded, until the
    matching close tag actually shows up. If the stream ends first (a
    truncated response, or a tag name that doesn't behave the way this was
    written for), the held text is flushed instead of silently dropped -
    returning an unexpected block is better than returning a blank answer.
    """
    if not tag_names:
        async for delta in stream:
            yield delta
        return

    open_tags = tuple(f"<{name}>" for name in tag_names)
    longest_marker = max(len(m) for m in open_tags)

    buffer = ""
    suppressed = ""
    inside_tag_close_marker: str | None = None

    async for delta in stream:
        buffer += delta

        while True:
            if inside_tag_close_marker is not None:
                idx = buffer.find(inside_tag_close_marker)
                if idx == -1:
                    suppressed += buffer
                    buffer = ""
                    break
                suppressed = ""  # close tag confirmed: safe to discard for real
                buffer = buffer[idx + len(inside_tag_close_marker) :]
                inside_tag_close_marker = None
                continue

            earliest_idx: int | None = None
            matched_open: str | None = None
            for marker in open_tags:
                idx = buffer.find(marker)
                if idx != -1 and (earliest_idx is None or idx < earliest_idx):
                    earliest_idx = idx
                    matched_open = marker

            if earliest_idx is None:
                # No open tag found. Hold back a tail that could be the start
                # of one (e.g. buffer ends with "<thou"), emit the rest.
                safe_len = max(0, len(buffer) - (longest_marker - 1))
                if safe_len > 0:
                    yield buffer[:safe_len]
                    buffer = buffer[safe_len:]
                break

            if earliest_idx > 0:
                yield buffer[:earliest_idx]
            tag_name = matched_open[1:-1]
            inside_tag_close_marker = f"</{tag_name}>"
            buffer = buffer[earliest_idx + len(matched_open) :]

    if inside_tag_close_marker is not None and suppressed:
        yield suppressed
    if buffer:
        yield buffer


def _log_usage(model: str, usage) -> None:
    """One line per call: how much of the prompt was served from the provider's prefix cache (cached_tokens)."""
    details = getattr(usage, "prompt_tokens_details", None)
    logger.info(
        "[LLM:USAGE] model=%s prompt=%s cached=%s completion=%s",
        model,
        getattr(usage, "prompt_tokens", None),
        getattr(details, "cached_tokens", None) if details is not None else None,
        getattr(usage, "completion_tokens", None),
    )


class OpenAICompatibleLLMProvider(LLMProvider):
    """Works with OpenAI itself or any OpenAI-compatible chat completions API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        disable_thinking: bool = False,
        strip_tags: list[str] | None = None,
    ):
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        # `enable_thinking` is a vendor extension (not a standard OpenAI
        # param), only sent via extra_body when this flag is on - real
        # OpenAI models never see it.
        self._disable_thinking = disable_thinking
        self._strip_tags = strip_tags or []

    async def _raw_content_stream(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        tool_calls_out: list[ToolCall],
        tool_choice: str = "auto",
    ) -> AsyncIterator[str]:
        """Yields content deltas only (for `_strip_tag_blocks` to filter).

        Tool-call fragments are accumulated as a side effect instead of
        yielded, since the OpenAI streaming API splits one logical call's
        `id`/`function.name`/`function.arguments` across many chunks, keyed
        by an `index` that identifies which (possibly parallel) call a
        fragment belongs to. Once a chunk's `finish_reason` confirms the
        model is done (`"tool_calls"`), the fully-assembled calls are
        appended to `tool_calls_out` for the caller to pick up after this
        generator is exhausted.
        """
        extra_body = {"enable_thinking": False} if self._disable_thinking else None
        kwargs: dict = {}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            stream=True,
            stream_options={"include_usage": True},
            extra_body=extra_body,
            **kwargs,
        )

        accumulated: dict[int, dict[str, str]] = {}
        async for chunk in stream:
            if getattr(chunk, "usage", None) is not None:
                _log_usage(self._model, chunk.usage)
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if delta.content:
                yield delta.content

            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    entry = accumulated.setdefault(
                        tc_delta.index, {"id": "", "name": "", "arguments": ""}
                    )
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    if tc_delta.function is not None:
                        if tc_delta.function.name:
                            entry["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            entry["arguments"] += tc_delta.function.arguments

            if choice.finish_reason == "tool_calls":
                for _, entry in sorted(accumulated.items()):
                    tool_calls_out.append(
                        {"id": entry["id"], "name": entry["name"], "arguments": entry["arguments"]}
                    )

    async def _stream_events(
        self, messages: list[ChatMessage], tools: list[ToolSpec] | None, tool_choice: str = "auto"
    ) -> AsyncIterator[StreamEvent]:
        # Gateways sometimes drop a connection ("incomplete chunked read"). If that happens before a single token was delivered
        # to the caller, nothing is lost by asking again; once content has been yielded it cannot be replayed, so the error is raised.
        for attempt in range(1, _STREAM_ATTEMPTS + 1):
            tool_calls: list[ToolCall] = []
            delivered = False
            try:
                content_stream = self._raw_content_stream(messages, tools, tool_calls, tool_choice)
                async for stripped in _strip_tag_blocks(content_stream, self._strip_tags):
                    delivered = True
                    yield {"type": "content", "delta": stripped}
                # `content_stream` is now fully drained, so `tool_calls` (populated
                # as a side effect while draining it) is final.
                if tool_calls:
                    yield {"type": "tool_calls", "calls": tool_calls}
                return
            except _TRANSIENT_STREAM_ERRORS as exc:
                if delivered or attempt == _STREAM_ATTEMPTS:
                    raise
                logger.warning("LLM stream interrupted before any output (attempt %d/%d): %s", attempt, _STREAM_ATTEMPTS, exc)
                await asyncio.sleep(1.5 * attempt)

    def stream_chat(
        self, messages: list[ChatMessage], tools: list[ToolSpec] | None = None, tool_choice: str = "auto"
    ) -> AsyncIterator[StreamEvent]:
        return self._stream_events(messages, tools, tool_choice)


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    return OpenAICompatibleLLMProvider(
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        disable_thinking=settings.llm_disable_thinking,
        strip_tags=settings.llm_strip_content_tags,
    )


def get_rerank_llm_provider() -> LLMProvider:
    """Provider for re-ranking search results: `llm_rerank_model` when set, otherwise the default chat model."""
    settings = get_settings()
    return OpenAICompatibleLLMProvider(
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_rerank_model or settings.llm_model,
        disable_thinking=settings.llm_disable_thinking,
        strip_tags=settings.llm_strip_content_tags,
    )


def get_sql_llm_provider() -> LLMProvider:
    """Provider for writing SQL: `llm_sql_model` when set, otherwise the default chat model."""
    settings = get_settings()
    return OpenAICompatibleLLMProvider(
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_sql_model or settings.llm_model,
        disable_thinking=settings.llm_disable_thinking,
        strip_tags=settings.llm_strip_content_tags,
    )
