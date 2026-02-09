import pytest
from httpx import AsyncClient
from app.main import app
from app.presentation.api.v1.endpoints.auth import register_limiter
from app.presentation.api.v1.limiter import InMemoryRateLimiter

@pytest.mark.asyncio
async def test_register_rate_limit(client: AsyncClient):
    """
    Test rate limiting on registration endpoint.
    We override the global override (which disables limits) with a real limiter for this test.
    """
    # Create a fresh limiter instance for testing
    # 5 requests per 60 seconds
    test_limiter = InMemoryRateLimiter(requests=5, window=60)

    # Store the current override (which is likely the no-op from conftest)
    original_override = app.dependency_overrides.get(register_limiter)

    # Apply our test limiter
    app.dependency_overrides[register_limiter] = test_limiter

    try:
        # 1. Send 5 valid requests (should succeed)
        for i in range(5):
            resp = await client.post("/api/v1/auth/register", json={
                "username": f"rate_limit_user_{i}",
                "email": f"rate_limit_{i}@test.com",
                "password": "securepassword123",
            })
            assert resp.status_code == 201, f"Request {i+1} failed with {resp.status_code}: {resp.text}"

        # 2. Send the 6th request (should fail with 429)
        resp = await client.post("/api/v1/auth/register", json={
            "username": "rate_limit_user_fail",
            "email": "rate_limit_fail@test.com",
            "password": "securepassword123",
        })

        assert resp.status_code == 429
        data = resp.json()
        assert data["detail"] == "Too many requests"

    finally:
        # Restore the original override
        if original_override:
            app.dependency_overrides[register_limiter] = original_override
        else:
            # If there was no override, remove ours
            app.dependency_overrides.pop(register_limiter, None)
