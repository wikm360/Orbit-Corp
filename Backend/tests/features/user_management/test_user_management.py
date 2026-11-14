import uuid

import pytest

BASE = "/api/v1/user-management"


async def _register(client, email):
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret"})
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, uuid.UUID(body["user"]["id"]), body["refresh_token"]


async def _setup(client):
    root, root_id, _ = await _register(client, "root@example.com")  # first user = super admin
    it, it_id, _ = await _register(client, "it@example.com")
    r = await client.put(f"/api/v1/admin/users/{it_id}/user-management-access", json={"enabled": True}, headers=root)
    assert r.status_code == 200 and r.json()["user_management_access"] is True
    return root, root_id, it, it_id


@pytest.mark.asyncio
async def test_no_access_by_default_and_only_super_admin_delegates(client):
    root, root_id, it, it_id = await _setup(client)
    plain, plain_id, _ = await _register(client, "plain@example.com")
    assert (await client.get(f"{BASE}/users", headers=plain)).status_code == 403
    # a holder cannot delegate further, nor can a plain admin
    r = await client.put(f"/api/v1/admin/users/{plain_id}/user-management-access", json={"enabled": True}, headers=it)
    assert r.status_code == 403
    assert (await client.put(f"/api/v1/admin/users/{root_id}/user-management-access", json={"enabled": False}, headers=root)).status_code == 400
    # the holder is not an admin: /admin stays closed
    assert (await client.get("/api/v1/admin/users", headers=it)).status_code == 403
    assert (await client.get(f"{BASE}/users", headers=it)).status_code == 200
    # revoke is immediate
    await client.put(f"/api/v1/admin/users/{it_id}/user-management-access", json={"enabled": False}, headers=root)
    assert (await client.get(f"{BASE}/users", headers=it)).status_code == 403


@pytest.mark.asyncio
async def test_holder_creates_edits_resets_and_deletes_plain_users(client):
    root, root_id, it, it_id = await _setup(client)
    r = await client.post(f"{BASE}/users", json={"email": "new@example.com", "password": "firstpass1", "full_name": "New"}, headers=it)
    assert r.status_code == 201 and r.json()["role"] == "user"
    uid = r.json()["id"]
    assert (await client.post(f"{BASE}/users", json={"email": "new@example.com", "password": "firstpass1", "full_name": "x"}, headers=it)).status_code == 409
    assert (await client.post("/api/v1/auth/login", json={"email": "new@example.com", "password": "firstpass1"})).status_code == 200

    r = await client.patch(f"{BASE}/users/{uid}", json={"email": "renamed@example.com"}, headers=it)
    assert r.status_code == 200 and r.json()["email"] == "renamed@example.com"
    assert (await client.patch(f"{BASE}/users/{uid}", json={"email": "root@example.com"}, headers=it)).status_code == 409

    _, _, refresh = await _register(client, "victim@example.com")
    victim = next(u for u in (await client.get(f"{BASE}/users", headers=it)).json() if u["email"] == "victim@example.com")
    assert (await client.post(f"{BASE}/users/{victim['id']}/reset-password", json={"password": "short"}, headers=it)).status_code == 422
    assert (await client.post(f"{BASE}/users/{victim['id']}/reset-password", json={"password": "brandnew99"}, headers=it)).status_code == 204
    assert (await client.post("/api/v1/auth/login", json={"email": "victim@example.com", "password": "supersecret"})).status_code == 401
    assert (await client.post("/api/v1/auth/login", json={"email": "victim@example.com", "password": "brandnew99"})).status_code == 200
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})).status_code == 401  # sessions revoked

    assert (await client.delete(f"{BASE}/users/{uid}", headers=it)).status_code == 204
    assert (await client.post("/api/v1/auth/login", json={"email": "renamed@example.com", "password": "firstpass1"})).status_code == 401
    assert (await client.delete(f"{BASE}/users/{uid}", headers=it)).status_code == 404


@pytest.mark.asyncio
async def test_holder_cannot_touch_admins_super_admins_or_peers(client):
    root, root_id, it, it_id = await _setup(client)
    boss, boss_id, _ = await _register(client, "boss@example.com")
    await client.patch(f"/api/v1/admin/users/{boss_id}/role", json={"role": "admin"}, headers=root)
    peer, peer_id, _ = await _register(client, "peer@example.com")
    await client.put(f"/api/v1/admin/users/{peer_id}/user-management-access", json={"enabled": True}, headers=root)

    for target in (root_id, boss_id, peer_id):
        assert (await client.post(f"{BASE}/users/{target}/reset-password", json={"password": "hijack1234"}, headers=it)).status_code == 403
        assert (await client.patch(f"{BASE}/users/{target}", json={"email": "x@example.com"}, headers=it)).status_code == 403
        assert (await client.delete(f"{BASE}/users/{target}", headers=it)).status_code == 403
    listing = {u["email"]: u["manageable"] for u in (await client.get(f"{BASE}/users", headers=it)).json()}
    assert listing == {"root@example.com": False, "it@example.com": False, "boss@example.com": False, "peer@example.com": False}
    # own password is fine, own deletion is not
    assert (await client.post(f"{BASE}/users/{it_id}/reset-password", json={"password": "mynewpass1"}, headers=it)).status_code == 204
    assert (await client.delete(f"{BASE}/users/{it_id}", headers=it)).status_code == 400


@pytest.mark.asyncio
async def test_super_admin_manages_everyone_but_not_self_deletion(client):
    root, root_id, it, it_id = await _setup(client)
    assert (await client.post(f"{BASE}/users/{it_id}/reset-password", json={"password": "resetbyroot1"}, headers=root)).status_code == 204
    assert (await client.delete(f"{BASE}/users/{root_id}", headers=root)).status_code == 400
    assert (await client.delete(f"{BASE}/users/{it_id}", headers=root)).status_code == 204
