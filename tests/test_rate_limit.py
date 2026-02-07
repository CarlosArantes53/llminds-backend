import pytest
from httpx import AsyncClient
from app.main import app
from app.presentation.api.v1.endpoints.auth import login_limiter, register_limiter
from app.presentation.api.v1.limiter import InMemoryRateLimiter

@pytest.mark.asyncio
async def test_rate_limiter_blocks_excessive_requests(client: AsyncClient):
    # Setup: Use a strict limiter for this test
    # 2 requests allowed per 60 seconds
    strict_limiter = InMemoryRateLimiter(requests=2, window=60)

    # Save original override to restore later
    original_override = app.dependency_overrides.get(login_limiter)

    # Apply strict limiter
    app.dependency_overrides[login_limiter] = strict_limiter

    try:
        # Register user first (to have valid credentials)
        # Note: register is NOT rate limited in this implementation, only login
        await client.post("/api/v1/auth/register", json={
            "username": "limit_test",
            "email": "limit@test.com",
            "password": "password123",
            "role": "user",
        })

        creds = {"username": "limit_test", "password": "password123"}

        # Request 1: OK
        resp1 = await client.post("/api/v1/auth/login", json=creds)
        assert resp1.status_code == 200

        # Request 2: OK
        resp2 = await client.post("/api/v1/auth/login", json=creds)
        assert resp2.status_code == 200

        # Request 3: Blocked
        resp3 = await client.post("/api/v1/auth/login", json=creds)
        assert resp3.status_code == 429
        assert "Too many requests" in resp3.json()["detail"]

    finally:
        # Restore original override
        if original_override:
            app.dependency_overrides[login_limiter] = original_override
        else:
            del app.dependency_overrides[login_limiter]


@pytest.mark.asyncio
async def test_register_rate_limit(client: AsyncClient):
    """Verifica se o rate limit de registro (5/min) está funcionando."""

    # Save original override
    original_override = app.dependency_overrides.get(register_limiter)

    # Remove override to use the real limiter
    if register_limiter in app.dependency_overrides:
        del app.dependency_overrides[register_limiter]

    # Reset internal state
    register_limiter.reset()

    try:
        # Envia 5 requisições
        for i in range(5):
            resp = await client.post("/api/v1/auth/register", json={
                "username": f"user_limiter_{i}",
                "email": f"limiter_{i}@test.com",
                "password": "senha123",
            })
            assert resp.status_code != 429, f"Request {i+1} bloqueado prematuramente. Status: {resp.status_code}"

        # A 6ª requisição deve ser bloqueada
        resp = await client.post("/api/v1/auth/register", json={
            "username": "user_limiter_block",
            "email": "limiter_block@test.com",
            "password": "senha123",
        })
        assert resp.status_code == 429
        assert "Too many requests" in resp.json()["detail"]

    finally:
        # Restore override
        if original_override:
            app.dependency_overrides[register_limiter] = original_override
