"""Security tests: Secrets redaction from logs and diagnostics.
"""

from app.core.logging import redact_sensitive


def test_redact_nebius_api_key():
    raw = "Connecting with nebius-token-secret-123456789 to API"
    redacted = redact_sensitive(raw)
    assert "nebius-token-secret-123456789" not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_redact_tavily_api_key():
    raw = "Failed with key tvly-live-abc123456789 in request"
    redacted = redact_sensitive(raw)
    assert "tvly-live-abc123456789" not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_redact_bearer_auth():
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI"
    redacted = redact_sensitive(raw)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI" not in redacted
    assert "[REDACTED_SECRET]" in redacted
