"""Integration tests for Tavily technical search with mocked HTTP responses.
"""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from app.services.tavily_client import TavilyClient
from app.core.errors import ProviderUnavailableError


@pytest.mark.asyncio
async def test_tavily_search_mocked():
    client = TavilyClient()
    client.api_key = "tvly_mock_key"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "Python Math Spec",
                "url": "https://docs.python.org/3/library/math.html",
                "content": "math.factorial documentation",
                "score": 0.99,
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        results = await client.search("python math factorial spec")
        assert len(results) == 1
        assert results[0]["title"] == "Python Math Spec"
        assert "math.factorial" in results[0]["content"]


@pytest.mark.asyncio
async def test_tavily_health_unconfigured():
    client = TavilyClient()
    client.api_key = ""
    health = await client.check_health()
    assert health["status"] == "unconfigured"
    assert not health["configured"]
