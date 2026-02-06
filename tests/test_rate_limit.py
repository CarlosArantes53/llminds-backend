import pytest
from httpx import AsyncClient
from app.main import app
from app.presentation.api.v1.endpoints.auth import login_limiter
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
