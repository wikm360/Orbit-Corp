import uuid
import pytest

from app.features.auth.models import UserRole


async def _register(client, email: str) -> tuple[str, str]:
    res = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecretpassword"}
    )
    body = res.json()
    return body["access_token"], body["user"]["id"]


async def test_super_admin_can_impersonate_user(client):
    admin_token, admin_id = await _register(client, "superadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_token, user_id = await _register(client, "regular@example.com")

    # 1. Super admin impersonates regular user
    imp_res = await client.post(
        f"/api/v1/admin/impersonate/{user_id}",
        headers=admin_headers,
    )
    assert imp_res.status_code == 200
    imp_data = imp_res.json()
    assert imp_data["user"]["id"] == user_id
    assert imp_data["user"]["email"] == "regular@example.com"
    imp_token = imp_data["access_token"]
    imp_headers = {"Authorization": f"Bearer {imp_token}"}

    # 2. /auth/me with impersonated token reflects target user + impersonation info
    me_res = await client.get("/api/v1/auth/me", headers=imp_headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == "regular@example.com"
    assert me_data["role"] == "user"
    assert me_data["is_impersonated"] is True
    assert me_data["impersonator_email"] == "superadmin@example.com"


async def test_impersonated_session_can_switch_to_another_user_and_stop(client):
    admin_token, admin_id = await _register(client, "superadmin2@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    _, user1_id = await _register(client, "user1@example.com")
    _, user2_id = await _register(client, "user2@example.com")

    # Impersonate user1
    imp1 = await client.post(f"/api/v1/admin/impersonate/{user1_id}", headers=admin_headers)
    assert imp1.status_code == 200
    token1 = imp1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Switch directly to user2 while impersonating user1
    imp2 = await client.post(f"/api/v1/admin/impersonate/{user2_id}", headers=headers1)
    assert imp2.status_code == 200
    assert imp2.json()["user"]["email"] == "user2@example.com"
    token2 = imp2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Verify user2 is active
    me2 = await client.get("/api/v1/auth/me", headers=headers2)
    assert me2.json()["email"] == "user2@example.com"
    assert me2.json()["impersonator_email"] == "superadmin2@example.com"

    # Stop impersonation
    stop_res = await client.post("/api/v1/admin/stop-impersonation", headers=headers2)
    assert stop_res.status_code == 200
    restored_token = stop_res.json()["access_token"]
    restored_headers = {"Authorization": f"Bearer {restored_token}"}

    me_admin = await client.get("/api/v1/auth/me", headers=restored_headers)
    assert me_admin.json()["id"] == admin_id
    assert me_admin.json()["email"] == "superadmin2@example.com"
    assert me_admin.json()["role"] == "super_admin"
    assert me_admin.json()["is_impersonated"] is False


async def test_non_super_admin_cannot_impersonate(client):
    admin_token, _ = await _register(client, "owner-sec@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_token, user_id = await _register(client, "regular-sec@example.com")
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Plain user cannot impersonate
    res = await client.post(f"/api/v1/admin/impersonate/{user_id}", headers=user_headers)
    assert res.status_code == 403

    # Promote to plain admin
    await client.patch(
        f"/api/v1/admin/users/{user_id}/role",
        json={"role": "admin"},
        headers=admin_headers,
    )

    # Plain admin (not super admin) still cannot impersonate
    res_admin = await client.post(f"/api/v1/admin/impersonate/{user_id}", headers=user_headers)
    assert res_admin.status_code == 403
