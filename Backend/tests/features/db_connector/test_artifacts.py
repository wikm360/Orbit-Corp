"""Reference artifacts: the exact SQL + rows of a database answer travel with the assistant message to the client."""
import json
import uuid

import pytest

from app.core.config import get_settings
from app.core.dependencies import UserContext
from app.features.agent import engine as agent_engine_module
from app.features.agent.engine import AgentEngine
from app.features.auth.models import User, UserRole
from app.features.chat import service as chat_service
from app.features.chat.models import Conversation, ConversationType, Message, SenderType
from app.features.db_connector import router as db_router
from app.features.db_connector.artifacts import build_sql_result_artifact, column_kind
from app.features.db_connector.executor import QueryResult
from app.features.db_connector.models import DbQueryLog, QueryStatus
from app.features.db_connector.service import AccountingAnswer

ARTIFACT = {"type": "sql_result", "version": 1, "query_id": "q-1", "sql": "SELECT 1 AS x FROM ai.accounts",
            "columns": [{"name": "x", "kind": "number"}], "rows": [[1]], "row_count": 1, "rows_shown": 1, "truncated": False}


# ------------------------------------------------------------------ column kinds / artifact


@pytest.mark.parametrize(
    "name,values,expected",
    [
        ("net_pay", [2048558901], "money"),
        ("total_benefits", [1, 2], "money"),
        ("opening_net", [5], "money"),
        ("monthly_wage", [341088264], "money"),
        ("margin_ratio", [0.3], "ratio"),
        ("employee_count", [517], "number"),
        ("issue_year_month", [140505], "text"),
        ("fiscal_year", [1404], "text"),
        ("sl_code", [111302], "text"),
        ("employee_name", ["علی"], "text"),
        ("voucher_date", ["2026-07-22"], "date"),
        ("jalali_date", ["1405/04/31"], "date"),  # shown as-is by the client (only ISO dates are converted)
        ("حقوق_ناخالص_میلیارد_ریال", [2.31], "number"),  # LLM alias already scaled: must not be shown as Rials
        ("مبلغ_ریال", [1000000], "money"),
        ("تعداد_کارکنان", [10], "number"),
        ("x", [None, None], "text"),
    ],
)
def test_column_kind(name, values, expected):
    assert column_kind(name, values) == expected


def test_build_artifact_caps_shown_rows_but_keeps_total_count():
    rows = [[i, f"n{i}"] for i in range(250)]
    art = build_sql_result_artifact(query_id="q", question="؟", sql="SELECT 1", columns=["code_no", "name"], rows=rows, truncated=False,
                                    duration_ms=5, data_as_of={"k": "v"}, max_rows=100)
    assert art["type"] == "sql_result" and art["row_count"] == 250 and art["rows_shown"] == 100 and len(art["rows"]) == 100
    assert art["columns"][0]["name"] == "code_no" and art["currency"] == "IRR" and art["data_as_of"] == {"k": "v"}


# ------------------------------------------------------------------ engine


class _Scripted:
    def __init__(self, steps):
        self._steps, self.calls = steps, 0

    def stream_chat(self, messages, tools=None):
        events = self._steps[self.calls]
        self.calls += 1
        return self._gen(events)

    async def _gen(self, events):
        for e in events:
            yield e


async def _seed(db_session):
    user = User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.com", hashed_password="pw", role=UserRole.USER)
    db_session.add(user)
    await db_session.flush()
    conv = Conversation(id=uuid.uuid4(), type=ConversationType.PERSONAL, created_by=user.id, title="t")
    db_session.add(conv)
    await db_session.flush()
    db_session.add(Message(conversation_id=conv.id, sender_type=SenderType.USER, sender_id=user.id, content="q", sources=[]))
    await db_session.commit()
    return user, conv


@pytest.mark.asyncio
async def test_engine_runs_identical_tool_calls_once_and_collects_artifacts(db_session, monkeypatch):
    monkeypatch.setattr(get_settings(), "rahkaran_db_enabled", True)
    calls = []

    async def fake_run(db, *, question, user_id, conversation_id, **kwargs):
        calls.append(question)
        return AccountingAnswer(text="جدول", artifact=dict(ARTIFACT))

    monkeypatch.setattr("app.features.db_connector.service.run_accounting_query", fake_run)
    same = json.dumps({"question": "حقوق؟"}, ensure_ascii=False)
    reordered = json.dumps({"question": "حقوق؟"})  # same arguments, different JSON spelling
    provider = _Scripted([
        [{"type": "tool_calls", "calls": [{"id": "c1", "name": "ask_accounting_db", "arguments": same},
                                          {"id": "c2", "name": "ask_accounting_db", "arguments": reordered}]}],
        [{"type": "content", "delta": "پاسخ"}],
    ])
    monkeypatch.setattr(agent_engine_module, "get_llm_provider", lambda: provider)
    user, conv = await _seed(db_session)
    statuses = []

    async def cb(event, data):
        if event == "agent_activity":
            statuses.append(data["status"])

    result = await AgentEngine().run_agent_loop(db_session, conv, UserContext(user=user), cb)
    assert calls == ["حقوق؟"]  # executed once
    assert statuses.count("querying_database") == 1  # and announced once
    assert len(result.artifacts) == 1 and result.artifacts[0]["type"] == "sql_result"
    assert result.content == "پاسخ"


@pytest.mark.asyncio
async def test_chat_stream_done_event_and_history_carry_the_artifact(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rahkaran_db_enabled", True)

    async def fake_run(db, *, question, user_id, conversation_id, **kwargs):
        return AccountingAnswer(text="جدول", artifact=dict(ARTIFACT))

    monkeypatch.setattr("app.features.db_connector.service.run_accounting_query", fake_run)
    provider = _Scripted([
        [{"type": "tool_calls", "calls": [{"id": "c1", "name": "ask_accounting_db", "arguments": json.dumps({"question": "x"})}]}],
        [{"type": "content", "delta": "پاسخ نهایی"}],
    ])
    monkeypatch.setattr(agent_engine_module, "get_llm_provider", lambda: provider)
    monkeypatch.setattr(chat_service, "_agent_engine", AgentEngine())

    reg = await client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "supersecret"})
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    resp = await client.post("/api/v1/chat", json={"message": "حقوق؟"}, headers=headers)
    assert resp.status_code == 200
    done = [blk for blk in resp.text.split("\n\n") if blk.startswith("event: done")][0]
    payload = json.loads(done.split("data: ", 1)[1])
    assert payload["artifacts"][0]["sql"] == ARTIFACT["sql"]

    conv_id = json.loads([b for b in resp.text.split("\n\n") if b.startswith("event: start")][0].split("data: ", 1)[1])["conversation_id"]
    detail = (await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers)).json()
    assistant = [m for m in detail["messages"] if m["sender_type"] == "assistant"][0]
    assert assistant["artifacts"][0]["type"] == "sql_result" and assistant["artifacts"][0]["rows"] == [[1]]
    user_msg = [m for m in detail["messages"] if m["sender_type"] == "user"][0]
    assert user_msg["artifacts"] == []


# ------------------------------------------------------------------ router: ownership, freshness auth, export


async def _register(client, email):
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret"})
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, uuid.UUID(body["user"]["id"])


async def _log_for(db_session, user_id, sql="SELECT TOP 5 sl_code FROM ai.accounts"):
    log = DbQueryLog(user_id=user_id, question="q", hint_keys=[], sql_text=sql, attempts=1, status=QueryStatus.OK, row_count=1, duration_ms=1)
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


@pytest.mark.asyncio
async def test_feedback_and_export_are_limited_to_the_owner_or_admin(client, db_session, monkeypatch):
    admin_headers, _ = await _register(client, "admin@example.com")  # first user = super admin
    owner_headers, owner_id = await _register(client, "owner@example.com")
    other_headers, _ = await _register(client, "other@example.com")
    log = await _log_for(db_session, owner_id)

    async def fake_exec(sql, max_rows=None):
        return QueryResult(columns=["sl_code", "note"], rows=[["111302", "=HYPERLINK(\"x\")"], ["111005", "ok"]], truncated=False, duration_ms=3)

    monkeypatch.setattr(db_router, "execute_query", fake_exec)
    fb = f"/api/v1/accounting-db/queries/{log.id}/feedback"
    assert (await client.post(fb, json={"feedback": -1}, headers=other_headers)).status_code == 403
    assert (await client.post(fb, json={"feedback": 1}, headers=owner_headers)).status_code == 200
    assert (await client.post(fb, json={"feedback": 1}, headers=admin_headers)).status_code == 200

    ex = f"/api/v1/accounting-db/queries/{log.id}/export"
    assert (await client.get(ex, headers=other_headers)).status_code == 403
    csv_resp = await client.get(ex + "?format=csv", headers=owner_headers)
    assert csv_resp.status_code == 200 and "attachment" in csv_resp.headers["content-disposition"]
    text = csv_resp.content.decode("utf-8-sig")
    assert "sl_code,note" in text and "'=HYPERLINK" in text  # formula injection neutralised
    xlsx_resp = await client.get(ex + "?format=xlsx", headers=owner_headers)
    assert xlsx_resp.status_code == 200 and xlsx_resp.content[:2] == b"PK"  # zip container


@pytest.mark.asyncio
async def test_export_revalidates_stored_sql_and_freshness_needs_login(client, db_session, monkeypatch):
    headers, uid = await _register(client, "admin@example.com")
    bad = await _log_for(db_session, uid, sql="SELECT * FROM FIN3.Voucher")
    monkeypatch.setattr(db_router, "execute_query", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run")))
    resp = await client.get(f"/api/v1/accounting-db/queries/{bad.id}/export", headers=headers)
    assert resp.status_code == 400
    assert (await client.get("/api/v1/accounting-db/freshness")).status_code in (401, 403)
    assert (await client.get("/api/v1/accounting-db/freshness", headers=headers)).status_code == 200


# ------------------------------------------------------------------ resilience: the LLM gateway drops the stream


class _FailsOnSecondCall(_Scripted):
    """First call returns a tool call; the second raises mid-stream (what 'incomplete chunked read' looks like to the engine)."""

    def stream_chat(self, messages, tools=None):
        self.calls += 1
        return self._first() if self.calls == 1 else self._boom()

    async def _first(self):
        yield {"type": "tool_calls", "calls": [{"id": "c1", "name": "ask_accounting_db", "arguments": json.dumps({"question": "x"})}]}

    async def _boom(self):
        import httpx
        raise httpx.RemoteProtocolError("peer closed connection without sending complete message body (incomplete chunked read)")
        yield  # pragma: no cover


@pytest.mark.asyncio
async def test_model_stream_failure_still_delivers_the_database_result(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rahkaran_db_enabled", True)

    async def fake_run(db, *, question, user_id, conversation_id, **kwargs):
        return AccountingAnswer(text="جدول", artifact=dict(ARTIFACT))

    monkeypatch.setattr("app.features.db_connector.service.run_accounting_query", fake_run)
    monkeypatch.setattr(agent_engine_module, "get_llm_provider", lambda: _FailsOnSecondCall([]))
    monkeypatch.setattr(chat_service, "_agent_engine", AgentEngine())

    reg = await client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "supersecret"})
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    resp = await client.post("/api/v1/chat", json={"message": "حقوق؟"}, headers=headers)
    assert resp.status_code == 200
    blocks = resp.text.split("\n\n")
    events = [b.split("\n", 1)[0] for b in blocks if b.startswith("event:")]
    assert "event: artifact" in events  # shown as soon as the tool finished
    assert events[-1] == "event: done"  # the HTTP response ends cleanly instead of aborting
    done = json.loads([b for b in blocks if b.startswith("event: done")][0].split("data: ", 1)[1])
    assert done["artifacts"][0]["sql"] == ARTIFACT["sql"]

    conv_id = json.loads([b for b in blocks if b.startswith("event: start")][0].split("data: ", 1)[1])["conversation_id"]
    detail = (await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers)).json()
    assistant = [m for m in detail["messages"] if m["sender_type"] == "assistant"][0]
    assert "قطع شد" in assistant["content"] and assistant["artifacts"][0]["type"] == "sql_result"


@pytest.mark.asyncio
async def test_provider_retries_a_stream_dropped_before_any_output_but_not_after(monkeypatch):
    import httpx
    from app.providers import llm_provider as lp

    monkeypatch.setattr(lp.asyncio, "sleep", lambda *_: _noop())
    provider = lp.OpenAICompatibleLLMProvider(base_url="http://x/v1", api_key="k", model="m")
    attempts = {"n": 0}

    async def flaky(messages, tools, tool_calls_out):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise httpx.RemoteProtocolError("incomplete chunked read")
        yield "سلام"

    provider._raw_content_stream = flaky
    events = [e async for e in provider.stream_chat([{"role": "user", "content": "hi"}])]
    assert events == [{"type": "content", "delta": "سلام"}] and attempts["n"] == 3

    attempts["n"] = 0

    async def dies_midway(messages, tools, tool_calls_out):
        attempts["n"] += 1
        yield "نیمه"
        raise httpx.RemoteProtocolError("incomplete chunked read")

    provider._raw_content_stream = dies_midway
    got = []
    with pytest.raises(httpx.RemoteProtocolError):
        async for e in provider.stream_chat([{"role": "user", "content": "hi"}]):
            got.append(e)
    assert got == [{"type": "content", "delta": "نیمه"}] and attempts["n"] == 1  # delivered text cannot be replayed


async def _noop():
    return None
