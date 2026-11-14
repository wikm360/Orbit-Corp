"""Cost in micro-USD: price table, recording, unknown models, and the super-admin-only price endpoints."""

import uuid
from decimal import Decimal

from sqlalchemy import select

from app.core.database import async_session_factory
from app.features.usage import pricing
from app.features.usage.models import LlmUsage
from app.features.usage.service import record_usage, usage_scope
from tests.features.usage.test_token_quota import API, _world

PRICES = {"gemini": (Decimal("0.30"), Decimal("2.50")), "qwen": (Decimal("0.15"), Decimal("0.47"))}


def test_cost_is_tokens_times_price_per_million_rounded_up():
    assert pricing.cost_micro_usd(PRICES, "gemini", 100_000, 20_000) == 80_000  # $0.03 + $0.05 = $0.08
    assert pricing.cost_micro_usd(PRICES, "qwen", 1, 0) == 1  # 0.15 micro-USD rounds up, never free
    assert pricing.cost_micro_usd(PRICES, "Google/Gemini", 1_000_000, 0) == 300_000  # vendor prefix + case ignored


def test_unknown_model_is_charged_at_the_most_expensive_price_and_empty_table_is_zero():
    assert pricing.cost_micro_usd(PRICES, "mystery", 1_000_000, 1_000_000) == 300_000 + 2_500_000
    assert pricing.cost_micro_usd({}, "mystery", 1_000_000, 1_000_000) == 0


async def test_record_usage_stores_the_cost_and_keeps_old_rows_when_the_price_changes(client):
    superadmin, _, _, _, _, user_id, *_ = await _world(client)
    url = f"{API}/admin/model-prices/test-model-x"
    pricing.invalidate_cache()
    assert (await client.put(url, json={"input_per_m": 1.0, "output_per_m": 2.0}, headers=superadmin)).status_code == 200
    uid = uuid.UUID(user_id)
    with usage_scope(uid, "chat"):
        await record_usage("test-model-x", 1000, 500)
    assert (await client.put(url, json={"input_per_m": 10.0, "output_per_m": 20.0}, headers=superadmin)).status_code == 200
    with usage_scope(uid, "ocr"):
        await record_usage("test-model-x", 1000, 500, purpose="ocr")
    async with async_session_factory() as db:
        rows = (await db.execute(select(LlmUsage).where(LlmUsage.user_id == uid).order_by(LlmUsage.id))).scalars().all()
    assert [r.cost_micro_usd for r in rows] == [2000, 20000]
    assert [r.billed_to for r in rows] == ["user", "user"]


async def test_only_super_admin_edits_prices_admin_reads_and_reports_show_cost(client):
    superadmin, _, admin, _, user, user_id, *_ = await _world(client)
    url = f"{API}/admin/model-prices/vendor/test-model-y"
    body = {"input_per_m": 0.5, "output_per_m": 1.5}
    assert (await client.put(url, json=body, headers=admin)).status_code == 403
    assert (await client.put(url, json=body, headers=user)).status_code == 403
    assert (await client.put(url, json=body, headers=superadmin)).status_code == 200
    assert (await client.put(url, json={"input_per_m": -1, "output_per_m": 1}, headers=superadmin)).status_code == 400
    listed = (await client.get(f"{API}/admin/model-prices", headers=admin)).json()
    assert {"model": "vendor/test-model-y", "input_per_m": 0.5, "output_per_m": 1.5} == {k: listed_row[k] for listed_row in listed if listed_row["model"] == "vendor/test-model-y" for k in ("model", "input_per_m", "output_per_m")}

    uid = uuid.UUID(user_id)
    pricing.invalidate_cache()
    with usage_scope(uid, "chat"):
        await record_usage("vendor/test-model-y", 2_000_000, 1_000_000)  # $1.00 + $1.50
    report = (await client.get(f"{API}/admin/users/{user_id}/token-usage", headers=admin)).json()
    assert report["cost_usd"] == 2.5 and report["by_model"][0]["model"] == "vendor/test-model-y"
    assert report["by_purpose"][0]["cost_usd"] == 2.5
    summary = (await client.get(f"{API}/admin/usage/cost-summary", headers=admin)).json()
    assert any(u["user_id"] == user_id and u["cost_usd"] == 2.5 for u in summary["by_user"])
    assert (await client.get(f"{API}/admin/usage/cost-summary", headers=user)).status_code == 403

    assert (await client.delete(url, headers=admin)).status_code == 403
    assert (await client.delete(url, headers=superadmin)).status_code == 204
    assert (await client.delete(url, headers=superadmin)).status_code == 404
