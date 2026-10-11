import pytest

from app.features.db_connector.models import DbQueryLog, QueryStatus


async def _register_admin(client, email: str = "admin@example.com") -> dict:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_accounting_db_router_endpoints(client, db_session, monkeypatch):
    headers = await _register_admin(client)

    # 1. Seed a query log
    log = DbQueryLog(
        question="تست وضعیت حساب",
        hint_keys=["view:vouchers:1"],
        sql_text="SELECT TOP 5 * FROM ai.vouchers",
        attempts=1,
        status=QueryStatus.OK,
        row_count=5,
        duration_ms=40,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    # 2. Submit feedback
    resp = await client.post(
        f"/api/v1/accounting-db/queries/{log.id}/feedback",
        json={"feedback": 1, "note": "پاسخ صحیح بود"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["feedback"] == 1
    assert data["feedback_note"] == "پاسخ صحیح بود"

    # 3. List queries (admin)
    list_resp = await client.get("/api/v1/accounting-db/queries", headers=headers)
    assert list_resp.status_code == 200
    queries = list_resp.json()
    assert len(queries) >= 1
    assert queries[0]["id"] == str(log.id)

    # 4. Get stats (admin)
    stats_resp = await client.get("/api/v1/accounting-db/queries/stats", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_queries"] >= 1
    assert stats["positive_feedback"] >= 1

    # 5. Freshness endpoint
    fresh_resp = await client.get("/api/v1/accounting-db/freshness", headers=headers)
    assert fresh_resp.status_code == 200

