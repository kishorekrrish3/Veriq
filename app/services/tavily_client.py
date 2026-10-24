"""Tavily Search and Extract API Client.
Performs focused documentation and technical searches with citation tracking.
"""

import time
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger, redact_sensitive
from app.core.errors import ProviderUnavailableError


class TavilyClient:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY.strip()
        self.base_url = settings.TAVILY_BASE_URL.rstrip("/")

    async def check_health(self) -> Dict[str, Any]:
        """Validates connection to the Tavily API."""
        if not self.api_key:
            return {
                "status": "unconfigured",
                "configured": False,
                "provider": "Tavily Search",
                "message": "TAVILY_API_KEY is not set. Operating in Recorded Replay Mode.",
            }

        try:
            start = time.perf_counter()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": "python test ping",
                        "max_results": 1,
                    },
                )
                latency = (time.perf_counter() - start) * 1000.0
                if resp.status_code == 200:
                    return {
                        "status": "healthy",
                        "configured": True,
                        "provider": "Tavily Search",
                        "latency_ms": round(latency, 2),
                        "message": "Connected to Tavily Search API",
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "configured": True,
                        "provider": "Tavily Search",
                        "status_code": resp.status_code,
                        "message": f"Tavily returned HTTP {resp.status_code}",
                    }
        except Exception as e:
            logger.warning(f"Tavily health check error: {redact_sensitive(str(e))}")
            return {
                "status": "unreachable",
                "configured": True,
                "provider": "Tavily Search",
                "error": redact_sensitive(str(e)),
                "message": "Tavily API unreachable.",
            }

    async def search(
        self,
        query: str,
        search_depth: str = "advanced",
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Executes a focused search query against technical documentation."""
        if not self.api_key:
            raise ProviderUnavailableError("Tavily API key is not configured")

        payload: Dict[str, Any] = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": True,
        }
        if include_domains:
            payload["include_domains"] = include_domains

        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(f"{self.base_url}/search", json=payload)
                if response.status_code != 200:
                    raise ProviderUnavailableError(f"Tavily returned status {response.status_code}: {response.text}")

                data = response.json()
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0.0),
                    })
                return results
        except httpx.RequestError as e:
            logger.error(f"Network error querying Tavily: {redact_sensitive(str(e))}")
            raise ProviderUnavailableError(f"Network error contacting Tavily: {redact_sensitive(str(e))}")


tavily_client = TavilyClient()
