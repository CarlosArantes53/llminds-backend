import pytest
from unittest.mock import MagicMock, AsyncMock
import app.services.gemini_service as service
from google.genai import types

@pytest.mark.asyncio
async def test_generate_dataset_response_uses_async_client(monkeypatch):
    """
    Test verifies that generate_dataset_response uses the async client (aio)
    instead of the blocking client.
    """
    # 1. Setup Mock Client
    mock_client = MagicMock()

    # Mock 'aio' attribute for async access
    mock_aio = MagicMock()
    mock_models = MagicMock()

    # generate_content must be an async method (AsyncMock)
    mock_models.generate_content = AsyncMock()
    mock_models.generate_content.return_value.text = "Async Response"

    mock_aio.models = mock_models
    mock_client.aio = mock_aio

    # Also mock synchronous 'models' to ensure it's NOT called
    mock_sync_models = MagicMock()
    mock_sync_models.generate_content = MagicMock()
    mock_client.models = mock_sync_models

    # 2. Patch dependencies
    monkeypatch.setattr(service, "_build_client", lambda: mock_client)
    monkeypatch.setattr(service.settings, "GEMINI_MODEL", "test-model")
    monkeypatch.setattr(service.settings, "GEMINI_API_KEY", "fake-key")

    # 3. Execute
    response = await service.generate_dataset_response("Hello")

    # 4. Verify
    assert response == "Async Response"

    # Ensure async method was called
    mock_models.generate_content.assert_awaited_once()

    # Ensure sync method was NOT called
    mock_sync_models.generate_content.assert_not_called()
