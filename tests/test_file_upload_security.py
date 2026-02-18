import pytest
from httpx import AsyncClient
from tests.conftest import auth_header

@pytest.mark.asyncio
async def test_upload_malicious_file_extension(client: AsyncClient, user_token: str):
    # 1. Create a ticket
    resp = await client.post("/api/v1/tickets/", json={
        "title": "Upload Test",
        "description": "Testing file upload security",
    }, headers=auth_header(user_token))
    assert resp.status_code == 201
    ticket_id = resp.json()["id"]

    # 2. Try to upload a file with .php extension but image/jpeg content type
    files = {
        "file": ("exploit.php", b"<?php echo 'hack'; ?>", "image/jpeg")
    }

    resp = await client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files=files,
        headers=auth_header(user_token)
    )

    # Assert 400 Bad Request due to extension mismatch
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "Extensão inválida" in detail
    assert ".jpg" in detail or ".jpeg" in detail
