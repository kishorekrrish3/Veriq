"""Integration tests for Nebius Token Factory client with mocked inference.
"""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from app.services.nebius_client import NebiusClient
from app.core.errors import ProviderUnavailableError


@pytest.mark.asyncio
async def test_nebius_client_generates_completion_mocked():
    client = NebiusClient()
    client.api_key = "mock_nebius_key"

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"files": [{"file_path": "calc.py", "action": "modify", "new_content": "pass"}]}'
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 150
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 200

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch.object(client, "get_client", return_value=mock_openai):
        content, usage, latency = await client.generate_chat_completion(
            model="nvidia/Llama-3.1-Nemotron-70B-Instruct-HF",
            messages=[{"role": "user", "content": "test"}],
        )

        assert "calc.py" in content
        assert usage["total_tokens"] == 200
        assert latency >= 0


@pytest.mark.asyncio
async def test_nebius_health_check_unconfigured():
    client = NebiusClient()
    client.api_key = ""
    health = await client.check_health()
    assert health["status"] == "unconfigured"
    assert not health["configured"]
