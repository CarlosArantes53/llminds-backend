
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_idor_attachment_download(client: AsyncClient):
    # 1. Create two users
    await client.post("/api/v1/auth/register", json={
        "username": "user1",
        "email": "user1@example.com",
        "password": "password123",
    })
    resp1 = await client.post("/api/v1/auth/login", json={
        "username": "user1",
        "password": "password123",
    })
    token1 = resp1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    await client.post("/api/v1/auth/register", json={
        "username": "user2",
        "email": "user2@example.com",
        "password": "password123",
    })
    resp2 = await client.post("/api/v1/auth/login", json={
        "username": "user2",
        "password": "password123",
    })
    token2 = resp2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 2. User 1 creates a ticket
    resp_ticket = await client.post(
        "/api/v1/tickets/",
        json={"title": "Private Ticket", "description": "Top secret"},
        headers=headers1,
    )
    assert resp_ticket.status_code == 201
    ticket_id = resp_ticket.json()["id"]

    # 3. User 1 uploads an attachment
    # Create a dummy file
    files = {"file": ("secret.txt", b"This is a secret", "text/plain")}
    # Wait, the endpoint expects specific content types. Let's use image/png.
    files = {"file": ("secret.png", b"fakeimagecontent", "image/png")}

    resp_upload = await client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files=files,
        headers=headers1,
    )
    assert resp_upload.status_code == 201
    attachment_id = resp_upload.json()["id"]

    # 4. User 2 tries to download the attachment
    resp_download = await client.get(
        f"/api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download",
        headers=headers2,
    )

    # 5. Assert that access is denied (403)
    # Currently this will likely fail (return 200) because the vulnerability exists
    assert resp_download.status_code == 403
