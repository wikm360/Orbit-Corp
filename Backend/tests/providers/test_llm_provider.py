from app.providers.llm_provider import OpenAICompatibleLLMProvider


class _FakeFunctionDelta:
    def __init__(self, name: str | None = None, arguments: str | None = None):
        self.name = name
        self.arguments = arguments


class _FakeToolCallDelta:
    def __init__(self, index: int, id: str | None = None, function: _FakeFunctionDelta | None = None):
        self.index = index
        self.id = id
        self.function = function


class _FakeDelta:
    def __init__(self, content: str | None = None, tool_calls: list[_FakeToolCallDelta] | None = None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeChoice:
    def __init__(self, delta: _FakeDelta, finish_reason: str | None = None):
        self.delta = delta
        self.finish_reason = finish_reason


class _FakeChunk:
    def __init__(self, choices: list[_FakeChoice]):
        self.choices = choices


def _fake_stream(chunks: list[_FakeChunk]):
    async def _gen():
        for chunk in chunks:
            yield chunk

    return _gen()


def _provider(chunks: list[_FakeChunk], strip_tags: list[str] | None = None) -> OpenAICompatibleLLMProvider:
    provider = OpenAICompatibleLLMProvider(
        base_url="http://unused", api_key="unused", model="test-model", strip_tags=strip_tags
    )

    async def _fake_create(**kwargs):
        return _fake_stream(chunks)

    provider._client.chat.completions.create = _fake_create  # type: ignore[method-assign]
    return provider


async def test_stream_chat_yields_content_only_when_no_tool_call_is_made():
    chunks = [
        _FakeChunk([_FakeChoice(_FakeDelta(content="Hello"))]),
        _FakeChunk([_FakeChoice(_FakeDelta(content=", world!"))]),
        _FakeChunk([_FakeChoice(_FakeDelta(), finish_reason="stop")]),
    ]
    provider = _provider(chunks)

    events = [event async for event in provider.stream_chat([{"role": "user", "content": "hi"}])]

    assert events == [
        {"type": "content", "delta": "Hello"},
        {"type": "content", "delta": ", world!"},
    ]


async def test_stream_chat_accumulates_fragmented_tool_call_deltas():
    """OpenAI streams a tool call's id/name/arguments split across many
    chunks, keyed by `index` - this must be reassembled into one ToolCall,
    emitted only once the stream confirms it's complete."""
    chunks = [
        _FakeChunk(
            [
                _FakeChoice(
                    _FakeDelta(
                        tool_calls=[
                            _FakeToolCallDelta(
                                index=0, id="call_123", function=_FakeFunctionDelta(name="get_w")
                            )
                        ]
                    )
                )
            ]
        ),
        _FakeChunk(
            [
                _FakeChoice(
                    _FakeDelta(
                        tool_calls=[_FakeToolCallDelta(index=0, function=_FakeFunctionDelta(name="eather"))]
                    )
                )
            ]
        ),
        _FakeChunk(
            [
                _FakeChoice(
                    _FakeDelta(
                        tool_calls=[
                            _FakeToolCallDelta(index=0, function=_FakeFunctionDelta(arguments='{"city":'))
                        ]
                    )
                )
            ]
        ),
        _FakeChunk(
            [
                _FakeChoice(
                    _FakeDelta(
                        tool_calls=[
                            _FakeToolCallDelta(index=0, function=_FakeFunctionDelta(arguments='"Tehran"}'))
                        ]
                    )
                )
            ]
        ),
        _FakeChunk([_FakeChoice(_FakeDelta(), finish_reason="tool_calls")]),
    ]
    provider = _provider(chunks)

    events = [event async for event in provider.stream_chat([{"role": "user", "content": "weather?"}])]

    assert events == [
        {
            "type": "tool_calls",
            "calls": [{"id": "call_123", "name": "get_weather", "arguments": '{"city":"Tehran"}'}],
        }
    ]


async def test_stream_chat_assembles_parallel_tool_calls_in_index_order():
    chunks = [
        _FakeChunk(
            [
                _FakeChoice(
                    _FakeDelta(
                        tool_calls=[
                            _FakeToolCallDelta(
                                index=1, id="call_b", function=_FakeFunctionDelta(name="tool_b", arguments="{}")
                            ),
                            _FakeToolCallDelta(
                                index=0, id="call_a", function=_FakeFunctionDelta(name="tool_a", arguments="{}")
                            ),
                        ]
                    )
                )
            ]
        ),
        _FakeChunk([_FakeChoice(_FakeDelta(), finish_reason="tool_calls")]),
    ]
    provider = _provider(chunks)

    events = [event async for event in provider.stream_chat([{"role": "user", "content": "do both"}])]

    assert events == [
        {
            "type": "tool_calls",
            "calls": [
                {"id": "call_a", "name": "tool_a", "arguments": "{}"},
                {"id": "call_b", "name": "tool_b", "arguments": "{}"},
            ],
        }
    ]


async def test_stream_chat_still_strips_configured_content_tags():
    chunks = [
        _FakeChunk([_FakeChoice(_FakeDelta(content="<thought>hidden reasoning</thought>answer"))]),
        _FakeChunk([_FakeChoice(_FakeDelta(), finish_reason="stop")]),
    ]
    provider = _provider(chunks, strip_tags=["thought"])

    events = [event async for event in provider.stream_chat([{"role": "user", "content": "hi"}])]

    joined = "".join(e["delta"] for e in events if e["type"] == "content")
    assert joined == "answer"
