import uuid

import pytest

API = "/api/v1"


async def _register(client, email):
    r = await client.post(f"{API}/auth/register", json={"email": email, "password": "supersecret"})
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


async def _setup(client):
    root, _ = await _register(client, "root@example.com")  # super admin
    mgr, mgr_id = await _register(client, "mgr@example.com")
    bob, bob_id = await _register(client, "bob@example.com")
    r = await client.put(f"{API}/admin/users/{mgr_id}/workspace-access", json={"enabled": True}, headers=root)
    assert r.status_code == 200 and r.json()["workspace_access"] is True
    return root, mgr, mgr_id, bob, bob_id


@pytest.mark.asyncio
async def test_only_super_admin_delegates_and_default_is_closed(client):
    root, mgr, mgr_id, bob, bob_id = await _setup(client)
    assert (await client.post(f"{API}/teams", json={"name": "X"}, headers=bob)).status_code == 403
    assert (await client.get(f"{API}/teams/directory/users", headers=bob)).status_code == 403
    assert (await client.put(f"{API}/admin/users/{bob_id}/workspace-access", json={"enabled": True}, headers=mgr)).status_code == 403
    me = (await client.get(f"{API}/auth/me", headers=bob)).json()
    assert me["workspace_access"] is False
    assert (await client.get(f"{API}/auth/me", headers=root)).json()["workspace_access"] is True
    # an admin cannot be toggled
    root_id = (await client.get(f"{API}/auth/me", headers=root)).json()["id"]
    assert (await client.put(f"{API}/admin/users/{root_id}/workspace-access", json={"enabled": False}, headers=root)).status_code == 400
    # revoke is immediate
    await client.put(f"{API}/admin/users/{mgr_id}/workspace-access", json={"enabled": False}, headers=root)
    assert (await client.post(f"{API}/teams", json={"name": "X"}, headers=mgr)).status_code == 403


@pytest.mark.asyncio
async def test_manager_runs_teams_projects_and_permissions(client):
    root, mgr, mgr_id, bob, bob_id = await _setup(client)
    carol, carol_id = await _register(client, "carol@example.com")

    team_id = (await client.post(f"{API}/teams", json={"name": "Ops"}, headers=mgr)).json()["id"]
    assert len((await client.get(f"{API}/teams", headers=mgr)).json()) == 1
    directory = (await client.get(f"{API}/teams/directory/users", headers=mgr)).json()
    assert {u["email"] for u in directory} == {"root@example.com", "mgr@example.com", "bob@example.com", "carol@example.com"}
    assert set(directory[0]) == {"id", "email", "full_name"}

    assert (await client.post(f"{API}/teams/{team_id}/members", json={"user_id": bob_id, "role": "member"}, headers=mgr)).status_code == 204
    assert (await client.post(f"{API}/teams/{team_id}/members", json={"user_id": carol_id, "role": "leader"}, headers=mgr)).status_code == 204
    assert len((await client.get(f"{API}/teams/{team_id}/members", headers=mgr)).json()) == 2

    project_id = (await client.post(f"{API}/teams/{team_id}/projects", json={"name": "P"}, headers=mgr)).json()["id"]
    assert len((await client.get(f"{API}/teams/{team_id}/projects", headers=mgr)).json()) == 1
    assert (await client.post(f"{API}/projects/{project_id}/members", json={"user_id": bob_id}, headers=mgr)).status_code == 204
    r = await client.put(f"{API}/projects/{project_id}/members/{bob_id}/permissions", json={"permissions": ["documents"]}, headers=mgr)
    assert r.status_code == 200 and r.json()["permissions"] == ["documents"]
    assert len((await client.get(f"{API}/projects/{project_id}/members", headers=mgr)).json()) == 1
    assert (await client.delete(f"{API}/projects/{project_id}/members/{bob_id}", headers=mgr)).status_code == 204
    assert (await client.delete(f"{API}/teams/{team_id}/members/{carol_id}", headers=mgr)).status_code == 204


@pytest.mark.asyncio
async def test_manager_never_gets_content_access_nor_self_grant(client):
    root, mgr, mgr_id, bob, bob_id = await _setup(client)
    team_id = (await client.post(f"{API}/teams", json={"name": "Ops"}, headers=mgr)).json()["id"]
    await client.post(f"{API}/teams/{team_id}/members", json={"user_id": bob_id, "role": "member"}, headers=mgr)
    project_id = (await client.post(f"{API}/teams/{team_id}/projects", json={"name": "P"}, headers=mgr)).json()["id"]

    # content endpoints stay closed to a pure manager
    assert (await client.get(f"{API}/projects/{project_id}", headers=mgr)).status_code == 403
    assert (await client.get(f"{API}/projects/{project_id}/documents", headers=mgr)).status_code == 403
    assert (await client.get(f"{API}/projects/{project_id}/files", headers=mgr)).status_code == 403
    # and they cannot put themselves in
    assert (await client.post(f"{API}/teams/{team_id}/members", json={"user_id": mgr_id, "role": "member"}, headers=mgr)).status_code == 403
    assert (await client.post(f"{API}/teams/{team_id}/members", json={"user_id": mgr_id, "role": "leader"}, headers=mgr)).status_code == 403
    assert (await client.post(f"{API}/projects/{project_id}/members", json={"user_id": mgr_id}, headers=mgr)).status_code == 403


@pytest.mark.asyncio
async def test_plain_member_and_non_manager_leader_limits_unchanged(client):
    root, mgr, mgr_id, bob, bob_id = await _setup(client)
    team_id = (await client.post(f"{API}/teams", json={"name": "Ops"}, headers=root)).json()["id"]
    await client.post(f"{API}/teams/{team_id}/members", json={"user_id": bob_id, "role": "member"}, headers=root)
    project_id = (await client.post(f"{API}/teams/{team_id}/projects", json={"name": "P"}, headers=root)).json()["id"]
    await client.post(f"{API}/projects/{project_id}/members", json={"user_id": bob_id}, headers=root)
    assert (await client.post(f"{API}/teams/{team_id}/projects", json={"name": "Q"}, headers=bob)).status_code == 403
    assert (await client.put(f"{API}/projects/{project_id}/members/{bob_id}/permissions", json={"permissions": ["memory"]}, headers=bob)).status_code == 403
    assert (await client.get(f"{API}/projects/{project_id}/members", headers=bob)).status_code == 200  # member can still list
    assert (await client.get(f"{API}/projects/{uuid.uuid4()}/members", headers=bob)).status_code == 404
