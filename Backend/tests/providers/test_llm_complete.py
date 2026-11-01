from app.providers.llm_provider import LLMProvider


class _Streamer(LLMProvider):
    async def _events(self):
        yield {"type": "content", "delta": "he"}
        yield {"type": "content", "delta": "llo"}
        yield {"type": "tool_calls", "calls": [{"id": "1", "name": "t", "arguments": "{}"}]}

    def stream_chat(self, messages, tools=None, tool_choice="auto"):
        return self._events()


async def test_default_complete_drains_the_stream():
    result = await _Streamer().complete([{"role": "user", "content": "x"}])
    assert result["content"] == "hello"
    assert result["tool_calls"] == [{"id": "1", "name": "t", "arguments": "{}"}]
    assert result["usage"] == {"prompt_tokens": 0, "completion_tokens": 0}
