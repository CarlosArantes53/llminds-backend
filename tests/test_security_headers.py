
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_security_headers_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-XSS-Protection"] == "1; mode=block"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "max-age=31536000; includeSubDomains" in headers["Strict-Transport-Security"]
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net" in headers["Content-Security-Policy"]
    assert "geolocation=()" in headers["Permissions-Policy"]

@pytest.mark.asyncio
async def test_security_headers_api_endpoint(client: AsyncClient):
    # Public endpoint
    resp = await client.post("/api/v1/auth/login", json={"username": "test", "password": "wrong"})
    # Status code might be 422 or 400 depending on validation, but headers should be present

    headers = resp.headers
    assert headers["X-Frame-Options"] == "DENY"
