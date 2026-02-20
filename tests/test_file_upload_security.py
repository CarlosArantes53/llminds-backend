import pytest
from httpx import AsyncClient
from tests.conftest import auth_header

@pytest.mark.asyncio
async def test_upload_malicious_file_extension_blocked(client: AsyncClient, user_token: str):
    # 1. Create a ticket
    ticket_resp = await client.post("/api/v1/tickets/", json={
        "title": "Upload Exploit Ticket",
        "description": "Testing file upload security",
    }, headers=auth_header(user_token))
    assert ticket_resp.status_code == 201
    ticket_id = ticket_resp.json()["id"]

    # 2. Prepare malicious file (HTML as JPEG)
    # This should now FAIL because magic bytes don't match JPEG signature
    files = {
        "file": ("exploit.html", b"<script>alert('XSS')</script>", "image/jpeg")
    }

    # 3. Upload file
    upload_resp = await client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files=files,
        headers=auth_header(user_token)
    )

    # 4. Verify upload is BLOCKED
    assert upload_resp.status_code == 400
    assert "Conteúdo do arquivo não corresponde ao tipo declarado" in upload_resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_valid_file_wrong_extension(client: AsyncClient, user_token: str):
    # Test uploading a valid JPEG but with .html extension
    # It should be accepted but saved with .jpg extension

    # 1. Create ticket
    ticket_resp = await client.post("/api/v1/tickets/", json={
        "title": "Upload Valid Ticket",
        "description": "Testing extension fix",
    }, headers=auth_header(user_token))
    ticket_id = ticket_resp.json()["id"]

    # 2. Valid JPEG content
    jpeg_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xFF\xDB\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xFF\xC0\x00\x0b\x08\x00\x01\x00\x01\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01\xFF\xC4\x00\x15\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xFF\xDA\x00\x08\x03\x01\x00\x02\x11\x03\x11\x00\x3F\x00\xbf\x00"

    files = {
        "file": ("innocent.html", jpeg_content, "image/jpeg")
    }

    upload_resp = await client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files=files,
        headers=auth_header(user_token)
    )

    assert upload_resp.status_code == 201
    data = upload_resp.json()

    # 3. Verify extension is corrected to .jpg
    assert data["original_filename"] == "innocent.html"
    assert data["stored_filename"].endswith(".jpg")
    assert not data["stored_filename"].endswith(".html")
