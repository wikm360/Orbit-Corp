"""Delegated per-project permissions: who can grant them, what they unlock, and where they stop."""


async def _register(client, email: str) -> tuple[dict, str]:
    body = (await client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret"})).json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["id"]


async def _world(client):
    admin, _ = await _register(client, "perm-admin@example.com")  # first user = super admin
    leader, leader_id = await _register(client, "perm-leader@example.com")
    member, member_id = await _register(client, "perm-member@example.com")
    other, other_id = await _register(client, "perm-other@example.com")
    team_id = (await client.post("/api/v1/teams", json={"name": "T"}, headers=admin)).json()["id"]
    other_team_id = (await client.post("/api/v1/teams", json={"name": "T2"}, headers=admin)).json()["id"]
    await client.post(f"/api/v1/teams/{team_id}/members", json={"user_id": leader_id, "role": "leader"}, headers=admin)
    await client.post(f"/api/v1/teams/{team_id}/members", json={"user_id": member_id, "role": "member"}, headers=admin)
    await client.post(f"/api/v1/teams/{other_team_id}/members", json={"user_id": other_id, "role": "leader"}, headers=admin)
    p1 = (await client.post(f"/api/v1/teams/{team_id}/projects", json={"name": "P1"}, headers=leader)).json()["id"]
    p2 = (await client.post(f"/api/v1/teams/{team_id}/projects", json={"name": "P2"}, headers=leader)).json()["id"]
    for pid in (p1, p2):
        await client.post(f"/api/v1/projects/{pid}/members", json={"user_id": member_id}, headers=leader)
    return admin, leader, member, member_id, other, p1, p2


def _grant(client, headers, project_id, user_id, permissions):
    return client.put(f"/api/v1/projects/{project_id}/members/{user_id}/permissions", json={"permissions": permissions}, headers=headers)


async def _make_folder(client, headers, project_id):
    return await client.post(f"/api/v1/projects/{project_id}/folders", json={"name": "docs"}, headers=headers)


async def test_member_has_no_permissions_by_default(client):
    _, leader, member, member_id, _, p1, _ = await _world(client)
    assert (await _make_folder(client, member, p1)).status_code == 403
    assert (await client.get(f"/api/v1/projects/{p1}/memories", headers=member)).status_code == 403
    assert (await client.get(f"/api/v1/projects/{p1}", headers=member)).json()["my_permissions"] == []
    members = (await client.get(f"/api/v1/projects/{p1}/members", headers=leader)).json()
    assert {m["user"]["id"]: m["permissions"] for m in members}[member_id] == []


async def test_leader_grants_documents_only_in_that_project(client):
    _, leader, member, member_id, _, p1, p2 = await _world(client)
    r = await _grant(client, leader, p1, member_id, ["documents"])
    assert r.status_code == 200 and r.json()["permissions"] == ["documents"]

    assert (await _make_folder(client, member, p1)).status_code == 201
    assert (await _make_folder(client, member, p2)).status_code == 403  # another project: no grant
    assert (await client.get(f"/api/v1/projects/{p1}/memories", headers=member)).status_code == 403  # other permission
    assert (await client.get(f"/api/v1/projects/{p1}", headers=member)).json()["my_permissions"] == ["documents"]
    mine = {p["id"]: p["my_permissions"] for p in (await client.get("/api/v1/projects/mine", headers=member)).json()}
    assert mine == {p1: ["documents"], p2: []}


async def test_memory_permission_and_revoke_take_effect_immediately(client):
    _, leader, member, member_id, _, p1, _ = await _world(client)
    await _grant(client, leader, p1, member_id, ["memory", "documents", "memory"])  # duplicates collapse, canonical order
    assert (await client.get(f"/api/v1/projects/{p1}/memories", headers=member)).status_code == 200
    assert (await _grant(client, leader, p1, member_id, [])).json()["permissions"] == []
    assert (await client.get(f"/api/v1/projects/{p1}/memories", headers=member)).status_code == 403
    assert (await _make_folder(client, member, p1)).status_code == 403


async def test_only_leader_or_admin_can_delegate_and_never_to_oneself(client):
    admin, leader, member, member_id, other, p1, _ = await _world(client)
    assert (await _grant(client, member, p1, member_id, ["documents"])).status_code == 403  # a member cannot raise own access
    await _grant(client, leader, p1, member_id, ["documents", "memory"])
    assert (await _grant(client, member, p1, member_id, ["documents", "memory"])).status_code == 403  # even with permissions
    assert (await client.post(f"/api/v1/projects/{p1}/members", json={"user_id": member_id}, headers=member)).status_code == 403
    assert (await _grant(client, other, p1, member_id, ["documents"])).status_code == 403  # leader of another team
    assert (await _grant(client, admin, p1, member_id, ["memory"])).status_code == 200  # admin may


async def test_validation_and_unknown_membership(client):
    _, leader, _, member_id, _, p1, _ = await _world(client)
    assert (await _grant(client, leader, p1, member_id, ["root"])).status_code == 400
    outsider, outsider_id = await _register(client, "perm-outsider@example.com")
    assert (await _grant(client, leader, p1, outsider_id, ["documents"])).status_code == 404  # not a project member
    assert (await client.get("/api/v1/project-permissions", headers=outsider)).json() == ["documents", "memory"]


async def test_permissions_vanish_with_membership_and_leader_has_all(client):
    _, leader, member, member_id, _, p1, _ = await _world(client)
    assert (await client.get(f"/api/v1/projects/{p1}", headers=leader)).json()["my_permissions"] == ["documents", "memory"]
    await _grant(client, leader, p1, member_id, ["documents"])
    assert (await client.delete(f"/api/v1/projects/{p1}/members/{member_id}", headers=leader)).status_code == 204
    assert (await _make_folder(client, member, p1)).status_code == 403
    await client.post(f"/api/v1/projects/{p1}/members", json={"user_id": member_id}, headers=leader)
    assert (await client.get(f"/api/v1/projects/{p1}", headers=member)).json()["my_permissions"] == []  # a fresh membership starts empty
