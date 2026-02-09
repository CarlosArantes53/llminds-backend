import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_admin_vulnerability(client: AsyncClient):
    """
    Tries to register a user with role='admin' via the public API.
    Should fail (create 'user') if patched, but currently succeeds (creates 'admin').
    """
    payload = {
        "username": "hacker",
        "email": "hacker@example.com",
        "password": "hacker123",
        "role": "admin"
    }

    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["username"] == "hacker"
    # This assertion confirms the fix:
    assert data["role"] == "user"
