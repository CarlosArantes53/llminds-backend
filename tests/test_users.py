"""Testes de Users — admin CRUD, RBAC, audit logs."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_list_users_admin(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/users/", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_list_users_forbidden_for_user(client: AsyncClient, user_token: str):
    resp = await client.get("/api/v1/users/", headers=auth_header(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_own_profile(client: AsyncClient, user_token: str):
    me = await client.get("/api/v1/auth/me", headers=auth_header(user_token))
    uid = me.json()["id"]

    resp = await client.patch(f"/api/v1/users/{uid}", json={
        "username": "updated_user",
    }, headers=auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "updated_user"


@pytest.mark.asyncio
async def test_user_cannot_change_role(client: AsyncClient, user_token: str):
    me = await client.get("/api/v1/auth/me", headers=auth_header(user_token))
    uid = me.json()["id"]

    resp = await client.patch(f"/api/v1/users/{uid}", json={
        "role": "admin",
    }, headers=auth_header(user_token))
    # Should either fail or not change role (depends on use case logic)
    assert resp.status_code in (200, 403)
    if resp.status_code == 200:
        assert resp.json()["role"] == "user"  # role should not change


@pytest.mark.asyncio
async def test_admin_delete_user(client: AsyncClient, admin_token: str):
    # Create a user to delete
    await client.post("/api/v1/auth/register", json={
        "username": "to_delete",
        "email": "delete@test.com",
        "password": "senha123",
    })
    users = await client.get("/api/v1/users/", headers=auth_header(admin_token))
    target = [u for u in users.json() if u["username"] == "to_delete"][0]

    resp = await client.delete(f"/api/v1/users/{target['id']}", headers=auth_header(admin_token))
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "version" in data
