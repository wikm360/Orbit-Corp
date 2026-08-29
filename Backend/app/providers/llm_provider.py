from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import TypedDict

from openai import AsyncOpenAI

from app.core.config import get_settings


class ChatMessage(TypedDict):
    role: str
    content: str


class LLMProvider(ABC):
    """Abstract interface every chat/completion backend must implement.

    Callers never talk to the OpenAI SDK (or any vendor SDK) directly, so the
    model/vendor can be swapped, or a fallback provider added, purely via config.
    """

    @abstractmethod
    def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield response text deltas as they arrive from the model."""


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

    async def _raw_stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        extra_body = {"enable_thinking": False} if self._disable_thinking else None
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            stream=True,
            extra_body=extra_body,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        return _strip_tag_blocks(self._raw_stream(messages), self._strip_tags)


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
