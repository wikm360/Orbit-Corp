import httpx
import pytest

from app.providers import embedding_provider as module
from app.providers.embedding_provider import BGEM3EmbeddingProvider


def _provider(handler) -> BGEM3EmbeddingProvider:
    return BGEM3EmbeddingProvider(
        base_url="http://embeddings.test/v1",
        api_key="k",
        model="m",
        dimensions=2,
        transport=httpx.MockTransport(handler),
    )


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(module.asyncio, "sleep", fake_sleep)
    return slept


def _ok(texts):
    return httpx.Response(
        200, json={"data": [{"index": i, "embedding": [float(i), 0.0]} for i in range(len(texts))]}
    )


async def test_rate_limited_requests_are_retried_then_succeed(_no_real_sleep):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return _ok(["a", "b"])

    result = await _provider(handler).embed(["a", "b"])

    assert result == [[0.0, 0.0], [1.0, 0.0]]
    assert calls["n"] == 3
    assert _no_real_sleep == [2.0, 2.0]  # honored Retry-After


async def test_a_non_retryable_error_fails_immediately(_no_real_sleep):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(401)

    with pytest.raises(httpx.HTTPStatusError):
        await _provider(handler).embed(["a"])

    assert calls["n"] == 1
    assert _no_real_sleep == []


async def test_gives_up_after_the_max_attempts(_no_real_sleep):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    with pytest.raises(httpx.HTTPStatusError):
        await _provider(handler).embed(["a"])

    assert calls["n"] == BGEM3EmbeddingProvider._MAX_ATTEMPTS
    assert _no_real_sleep == [1.0, 2.0, 4.0, 8.0]


async def test_dimensions_are_only_sent_when_enabled():
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen.append(json.loads(request.content))
        return _ok(["a"])

    plain = _provider(handler)
    await plain.embed(["a"])
    shortened = BGEM3EmbeddingProvider(
        base_url="http://embeddings.test/v1",
        api_key="k",
        model="m",
        dimensions=2,
        transport=httpx.MockTransport(handler),
        send_dimensions=True,
    )
    await shortened.embed(["a"])

    assert "dimensions" not in seen[0]
    assert seen[1]["dimensions"] == 2


async def test_session_reuses_one_client_for_all_calls(monkeypatch):
    created = {"n": 0}
    real = httpx.AsyncClient

    def counting_client(*args, **kwargs):
        created["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(module.httpx, "AsyncClient", counting_client)
    provider = _provider(lambda request: _ok(["a"]))

    async with provider.session():
        await provider.embed(["a"])
        await provider.embed(["a"])
        await provider.embed(["a"])
    assert created["n"] == 1

    await provider.embed(["a"])  # outside a session: a temporary client per call, as before
    assert created["n"] == 2
