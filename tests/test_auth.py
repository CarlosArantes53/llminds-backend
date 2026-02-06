"""Testes de Autenticação — register, login, refresh, me, change-password."""

import pytest
from httpx import AsyncClient
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "username": "novo_user",
        "email": "novo@test.com",
        "password": "senha123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "novo_user"
    assert data["role"] == "user"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "user1",
        "email": "dup@test.com",
        "password": "senha123",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "username": "user2",
        "email": "dup@test.com",
        "password": "senha123",
    })
    assert resp.status_code == 400
    assert "Email" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "mesmo_nome",
        "email": "a@test.com",
        "password": "senha123",
    })
    resp = await client.post("/api/v1/auth/register", json={
        "username": "mesmo_nome",
        "email": "b@test.com",
        "password": "senha123",
    })
    assert resp.status_code == 400
    assert "Username" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "login_test",
        "email": "login@test.com",
        "password": "senha123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "login_test",
        "password": "senha123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "wrong_pw",
        "email": "wrong@test.com",
        "password": "senha123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "username": "wrong_pw",
        "password": "errada",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_me(client: AsyncClient, user_token: str):
    resp = await client.get("/api/v1/auth/me", headers=auth_header(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "user_test"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_me_no_auth(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "username": "refresh_user",
        "email": "refresh@test.com",
        "password": "senha123",
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "refresh_user",
        "password": "senha123",
    })
    refresh = login_resp.json()["refresh_token"]

    import asyncio
    await asyncio.sleep(1.1)

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["access_token"] != login_resp.json()["access_token"]


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, user_token: str):
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "user123", "new_password": "novaSenha456"},
        headers=auth_header(user_token),
    )
    assert resp.status_code == 204

    # Login com nova senha
    resp2 = await client.post("/api/v1/auth/login", json={
        "username": "user_test",
        "password": "novaSenha456",
    })
    assert resp2.status_code == 200
