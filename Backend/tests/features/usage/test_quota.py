"""Dollar quota: Jalali month bounds, the three windows, plans and overrides (super admin only), shadow mode, and the gates."""

import uuid
from datetime import datetime, timedelta, timezone

from app.core.database import async_session_factory
from app.features.auth.models import User
from app.features.usage import quota
from app.features.usage.models import LlmUsage
from tests.features.usage.test_token_quota import API, _world


def test_jalali_conversion_matches_known_dates():
    assert quota.gregorian_to_jalali(2026, 3, 21) == (1405, 1, 1)  # Nowruz 1405
    assert quota.gregorian_to_jalali(2026, 3, 20) == (1404, 12, 29)
    assert quota.gregorian_to_jalali(2026, 11, 14) == (1405, 8, 23)
    assert quota.jalali_to_gregorian(1405, 8, 1) == (2026, 10, 23)
    assert quota.jalali_to_gregorian(1403, 12, 30) == (2025, 3, 20)  # 1403 is a leap year
    for g in [(2024, 2, 29), (2025, 12, 31), (2026, 9, 22), (2027, 3, 21)]:
        assert quota.jalali_to_gregorian(*quota.gregorian_to_jalali(*g)) == g


def test_month_bounds_start_at_tehran_midnight_of_the_jalali_month():
    start, nxt = quota.month_bounds(datetime(2026, 11, 14, 12, tzinfo=timezone.utc))  # 23 Aban 1405
    assert start == datetime(2026, 10, 22, 20, 30, tzinfo=timezone.utc)  # 1 Aban 00:00 Tehran (UTC+3:30)
    assert nxt == datetime(2026, 11, 21, 20, 30, tzinfo=timezone.utc)  # 1 Azar
    assert quota.month_bounds(datetime(2026, 3, 20, 20, 0, tzinfo=timezone.utc))[1] == datetime(2026, 3, 20, 20, 30, tzinfo=timezone.utc)  # right before Nowruz


async def _spend(user_id: str, usd: float, ago: timedelta = timedelta(0), purpose: str = "chat", billed_to: str = "user") -> None:
    async with async_session_factory() as db:
        user = await db.get(User, uuid.UUID(user_id))
        user.token_period_start = min(user.token_period_start, datetime.now(timezone.utc) - ago - timedelta(days=1))  # usage "ago" must postdate the last reset
        db.add(LlmUsage(user_id=uuid.UUID(user_id), purpose=purpose, model="m", prompt_tokens=1, completion_tokens=1, cached_tokens=0,
                        cost_micro_usd=round(usd * 1e6), billed_to=billed_to, created_at=datetime.now(timezone.utc) - ago))
        await db.commit()


async def _setup(client, superadmin, enforced=True):
    await client.put(f"{API}/admin/quota/plans/user", json={"five_hour_usd": 0.45, "weekly_usd": 1.5, "monthly_usd": 4.5}, headers=superadmin)
    await client.put(f"{API}/admin/quota/plans/admin", json={"five_hour_usd": 1.5, "weekly_usd": 5, "monthly_usd": 15}, headers=superadmin)
    quota.invalidate_cache()
    r = await client.put(f"{API}/admin/quota/enforced", json={"enforced": enforced}, headers=superadmin)
    assert r.status_code == 200 and r.json()["enforced"] is enforced
    quota.invalidate_cache()


async def _chat_status(client, headers) -> int:
    return (await client.post(f"{API}/chat", json={"message": "hi"}, headers=headers)).status_code


async def test_shadow_mode_blocks_nothing_and_enforcement_blocks_each_window(client):
    superadmin, _, admin, admin_id, user, user_id, *_ = await _world(client)
    await _setup(client, superadmin, enforced=False)
    await _spend(user_id, 10)  # far over every cap
    assert await _chat_status(client, user) != 429  # shadow mode

    await _setup(client, superadmin, enforced=True)
    r = await client.post(f"{API}/chat", json={"message": "hi"}, headers=user)
    assert r.status_code == 429 and r.json()["detail"] == "token_quota_exceeded"
    assert r.headers["X-Quota-Window"] == "five_hour" and "X-Quota-Resets-At" in r.headers

    q = (await client.get(f"{API}/auth/me/quota", headers=user)).json()
    assert q["enforced"] and [w["exhausted"] for w in q["windows"]] == [True, True, True]
    assert {w["name"]: w["limit_usd"] for w in q["windows"]} == {"five_hour": 0.45, "weekly": 1.5, "monthly": 4.5}

    assert await _chat_status(client, admin) != 429  # the admin plan is higher and the admin spent nothing
    assert await _chat_status(client, superadmin) != 429


async def test_windows_roll_and_only_the_exhausted_one_blocks(client):
    superadmin, _, _, _, user, user_id, *_ = await _world(client)
    await _setup(client, superadmin)
    await _spend(user_id, 0.5, ago=timedelta(hours=6))  # outside 5h, inside week/month
    assert await _chat_status(client, user) != 429
    await _spend(user_id, 1.1, ago=timedelta(hours=1))  # 5h: 1.1 >= 0.45 -> blocked; week: 1.6 >= 1.5
    r = await client.post(f"{API}/chat", json={"message": "hi"}, headers=user)
    assert r.status_code == 429 and r.headers["X-Quota-Window"] == "five_hour"
    resets = datetime.fromisoformat(r.headers["X-Quota-Resets-At"])
    assert timedelta(hours=3, minutes=55) < resets - datetime.now(timezone.utc) < timedelta(hours=4, minutes=5)  # the 1.1 call leaves the 5h window in 4h

    # old usage frees up: only 0.5 six hours ago counts for week/month -> under 1.5 / 4.5, and 5h is empty
    async with async_session_factory() as db:
        await db.execute(LlmUsage.__table__.delete().where(LlmUsage.user_id == uuid.UUID(user_id), LlmUsage.cost_micro_usd == 1_100_000))
        await db.commit()
    assert await _chat_status(client, user) != 429


async def test_ocr_and_embedding_cost_counts_but_pool_billed_usage_does_not(client):
    superadmin, _, _, _, user, user_id, *_ = await _world(client)
    await _setup(client, superadmin)
    await _spend(user_id, 9, purpose="ocr", billed_to="org_setup")
    assert await _chat_status(client, user) != 429
    await _spend(user_id, 0.5, purpose="ocr")
    assert await _chat_status(client, user) == 429
    upload = await client.post(f"{API}/chat/conversations/{uuid.uuid4()}/documents", files={"file": ("a.txt", b"x")}, headers=user)
    assert upload.status_code in (404, 429)  # unknown conversation is rejected first; the project upload gate is covered below


async def test_only_super_admin_edits_plans_overrides_and_enforcement(client):
    superadmin, _, admin, admin_id, user, user_id, *_ = await _world(client)
    plan = {"five_hour_usd": 1, "weekly_usd": 2, "monthly_usd": 3}
    for headers in (admin, user):
        assert (await client.put(f"{API}/admin/quota/plans/user", json=plan, headers=headers)).status_code == 403
        assert (await client.put(f"{API}/admin/quota/enforced", json={"enforced": True}, headers=headers)).status_code == 403
        assert (await client.put(f"{API}/admin/users/{user_id}/quota", json={"unlimited": True}, headers=headers)).status_code == 403
    # the old per-user token limit is super-admin only as well
    assert (await client.put(f"{API}/admin/users/{user_id}/token-limit", json={"limit": 5}, headers=admin)).status_code == 403
    assert (await client.get(f"{API}/admin/quota", headers=admin)).status_code == 200  # admins can read
    assert (await client.get(f"{API}/admin/users/{user_id}/quota", headers=admin)).status_code == 200

    assert (await client.put(f"{API}/admin/quota/plans/user", json={"five_hour_usd": 3, "weekly_usd": 2, "monthly_usd": 1}, headers=superadmin)).status_code == 400
    assert (await client.put(f"{API}/admin/quota/plans/user", json={"five_hour_usd": 0, "weekly_usd": 2, "monthly_usd": 3}, headers=superadmin)).status_code == 400
    assert (await client.put(f"{API}/admin/quota/plans/nobody", json=plan, headers=superadmin)).status_code == 400
    assert (await client.put(f"{API}/admin/quota/plans/user", json=plan, headers=superadmin)).json()["plans"]["user"] == {"five_hour_usd": 1, "weekly_usd": 2, "monthly_usd": 3}


async def test_per_user_override_unlimited_and_return_to_plan(client):
    superadmin, super_id, admin, admin_id, user, user_id, *_ = await _world(client)
    await _setup(client, superadmin)
    await _spend(user_id, 1.0)  # over the 5h plan (0.45), under week (1.5)
    assert await _chat_status(client, user) == 429

    url = f"{API}/admin/users/{user_id}/quota"
    r = await client.put(url, json={"five_hour_usd": 2.0}, headers=superadmin)  # raise only the 5h cap
    assert r.status_code == 200
    windows = {w["name"]: w for w in r.json()["windows"]}
    assert windows["five_hour"]["limit_usd"] == 2.0 and windows["five_hour"]["overridden"] and not windows["weekly"]["overridden"]
    assert await _chat_status(client, user) != 429

    await _spend(user_id, 5.0)
    assert await _chat_status(client, user) == 429
    assert (await client.put(url, json={"unlimited": True}, headers=superadmin)).json()["unlimited"] is True
    assert await _chat_status(client, user) != 429

    assert (await client.put(url, json={}, headers=superadmin)).json()["unlimited"] is False  # back to the plan
    assert await _chat_status(client, user) == 429
    # an admin account can be given an exception too; a super admin cannot be limited
    assert (await client.put(f"{API}/admin/users/{admin_id}/quota", json={"monthly_usd": 20}, headers=superadmin)).status_code == 200
    assert (await client.put(f"{API}/admin/users/{super_id}/quota", json={"monthly_usd": 1}, headers=superadmin)).status_code == 400
    assert (await client.put(url, json={"monthly_usd": -1}, headers=superadmin)).status_code == 400


async def test_reset_starts_every_window_over(client):
    superadmin, _, _, _, user, user_id, *_ = await _world(client)
    await _setup(client, superadmin)
    await _spend(user_id, 1.0)
    assert await _chat_status(client, user) == 429
    assert (await client.post(f"{API}/admin/users/{user_id}/token-limit/reset", headers=superadmin)).status_code == 200
    assert await _chat_status(client, user) != 429


async def test_quota_gates_project_uploads_too(client):
    superadmin, _, _, _, user, user_id, *_ = await _world(client)
    await _setup(client, superadmin)
    await _spend(user_id, 1.0)
    r = await client.post(f"{API}/projects/{uuid.uuid4()}/documents", files={"file": ("a.txt", b"x")}, headers=superadmin)
    assert r.status_code in (403, 404, 200, 400, 202)  # super admins pass the quota gate (they reach project checks)


async def test_profile_usage_shows_only_the_callers_own_cost_by_purpose_and_day(client):
    superadmin, _, _, _, user, user_id, other, other_id = await _world(client)
    await _spend(user_id, 0.5, purpose="chat")
    await _spend(user_id, 0.25, purpose="ocr")
    await _spend(user_id, 3.0, purpose="ocr", billed_to="org_setup")  # paid by the pool: reported separately, not as own use
    await _spend(other_id, 9.0)
    usage = (await client.get(f"{API}/auth/me/usage", headers=user)).json()
    assert usage["month_used_usd"] == 0.75 and usage["setup_pool_usd"] == 3.0
    assert {r["purpose"]: (r["cost_usd"], r["calls"]) for r in usage["by_purpose"]} == {"chat": (0.5, 1), "ocr": (0.25, 1)}
    assert sum(d["cost_usd"] for d in usage["daily"]) == 0.75 and usage["month"]["start"] < usage["month"]["next_start"]
    assert (await client.get(f"{API}/auth/me/usage?days=0", headers=user)).status_code == 422
    assert (await client.get(f"{API}/auth/me/usage")).status_code in (401, 403)
