"""Nebius Token Factory Client for NVIDIA Nemotron Models.
Uses AsyncOpenAI with custom base_url, exponential retry backoff,
latency tracking, token accounting, and credential redaction.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
from app.core.config import settings
from app.core.logging import logger, redact_sensitive
from app.core.errors import ProviderUnavailableError


class NebiusClient:
    def __init__(self):
        self.api_key = settings.NEBIUS_API_KEY.strip()
        self.base_url = settings.NEBIUS_BASE_URL.strip()
        self._client: Optional[AsyncOpenAI] = None

    def get_client(self) -> AsyncOpenAI:
        if not self._client:
            if not self.api_key:
                raise ProviderUnavailableError("Nebius API key is not configured")
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=45.0,
                max_retries=2,
            )
        return self._client

    async def check_health(self) -> Dict[str, Any]:
        """Validates connection to the Nebius Token Factory endpoint."""
        if not self.api_key:
            return {
                "status": "unconfigured",
                "configured": False,
                "provider": "Nebius Token Factory",
                "message": "NEBIUS_API_KEY is not set. Operating in Recorded Replay Mode.",
            }

        try:
            client = self.get_client()
            start = time.perf_counter()
            # Fast ping using models.list()
            models_page = await client.models.list()
            latency = (time.perf_counter() - start) * 1000.0
            model_ids = [m.id for m in models_page.data][:10]

            return {
                "status": "healthy",
                "configured": True,
                "provider": "Nebius Token Factory",
                "latency_ms": round(latency, 2),
                "available_models": model_ids,
                "message": f"Connected to Nebius Token Factory at {self.base_url}",
            }
        except Exception as e:
            logger.warning(f"Nebius health check failed: {redact_sensitive(str(e))}")
            return {
                "status": "unreachable",
                "configured": True,
                "provider": "Nebius Token Factory",
                "error": redact_sensitive(str(e)),
                "message": "Nebius endpoint unreachable or invalid credentials.",
            }

    async def generate_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        max_retries: int = 3,
    ) -> Tuple[str, Dict[str, int], float]:
        """Calls Nebius Token Factory with bounded exponential retries.
        
        Returns:
            Tuple of (response_text, usage_dict, latency_ms)
        """
        client = self.get_client()
        start = time.perf_counter()
        attempt = 0
        backoff = 1.0

        while attempt < max_retries:
            attempt += 1
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency_ms = (time.perf_counter() - start) * 1000.0
                msg = response.choices[0].message
                content = msg.content
                if not content:
                    # Capture reasoning_content if model put generation there
                    content = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""

                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
                return content, usage, latency_ms

            except (RateLimitError, APITimeoutError) as e:
                if attempt >= max_retries:
                    raise ProviderUnavailableError(f"Nebius rate limit or timeout exceeded after {attempt} attempts: {e}")
                logger.warning(f"Nebius retryable error on attempt {attempt}: {e}. Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff *= 2.0
            except APIError as e:
                logger.error(f"Nebius API error on attempt {attempt}: {redact_sensitive(str(e))}")
                raise ProviderUnavailableError(f"Nebius API error: {redact_sensitive(str(e))}")
            except Exception as e:
                logger.error(f"Unexpected Nebius client error: {redact_sensitive(str(e))}")
                raise ProviderUnavailableError(f"Unexpected error contacting Nebius: {redact_sensitive(str(e))}")

        raise ProviderUnavailableError("Exhausted retries calling Nebius inference")


nebius_client = NebiusClient()
