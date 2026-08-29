async def test_register_first_user_becomes_admin(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "supersecret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["role"] == "admin"
    assert body["access_token"]


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
