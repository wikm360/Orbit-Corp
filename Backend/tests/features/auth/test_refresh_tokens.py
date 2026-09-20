import asyncio


async def _login(client) -> dict:
    await client.post(
        "/api/v1/auth/register", json={"email": "rt@example.com", "password": "supersecret"}
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "rt@example.com", "password": "supersecret"}
    )
    return login.json()


async def test_refresh_rotates_and_rejects_reuse(client):
    tokens = await _login(client)

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    assert first.json()["refresh_token"] != tokens["refresh_token"]

    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


async def test_concurrent_refresh_with_same_token_succeeds_only_once(client):
    tokens = await _login(client)

    responses = await asyncio.gather(
        *(
            client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
            for _ in range(5)
        )
    )

    assert sorted(r.status_code for r in responses).count(200) == 1


async def test_concurrent_first_registrations_yield_a_single_super_admin(client):
    responses = await asyncio.gather(
        *(
            client.post(
                "/api/v1/auth/register",
                json={"email": f"race{i}@example.com", "password": "supersecret"},
            )
            for i in range(5)
        )
    )

    roles = [r.json()["user"]["role"] for r in responses]
    assert roles.count("super_admin") == 1
