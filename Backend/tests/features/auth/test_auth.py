async def test_register_first_user_becomes_super_admin(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "supersecret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "super_admin"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "password": "supersecret"}
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 200

    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


async def test_login_and_me(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "supersecret"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "supersecret"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


async def test_login_wrong_password_unauthorized(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpw@example.com", "password": "supersecret"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "nope"},
    )
    assert response.status_code == 401


async def test_refresh_token_rotates_and_issues_new_access_token(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "supersecret"},
    )
    first_refresh_token = register.json()["refresh_token"]

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first_refresh_token}
    )
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["access_token"]
    assert body["refresh_token"] != first_refresh_token

    # The old refresh token was rotated out, so reusing it is rejected.
    reused = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": first_refresh_token}
    )
    assert reused.status_code == 401

    # But the newly issued one still works.
    second_refresh = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert second_refresh.status_code == 200


async def test_logout_revokes_refresh_token(client):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": "logout@example.com", "password": "supersecret"},
    )
    refresh_token = register.json()["refresh_token"]

    logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 401


async def test_refresh_with_invalid_token_unauthorized(client):
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert response.status_code == 401
