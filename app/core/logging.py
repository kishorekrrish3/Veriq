"""Structured, secure logging for VERIQ.
Automatically redacts API keys and sensitive tokens from log records.
"""

import logging
import re
import sys
from typing import Any

# Sensitive patterns to redact
REDACTION_PATTERNS = [
    re.compile(r"(nebius[-_]?[a-zA-Z0-9_\-]{8,})", re.IGNORECASE),
    re.compile(r"(tvly[-_]?[a-zA-Z0-9_\-]{8,})", re.IGNORECASE),
    re.compile(r"(Bearer\s+[a-zA-Z0-9_\-\.]{10,})", re.IGNORECASE),
    re.compile(r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9_\-]{8,})", re.IGNORECASE),
]


def redact_sensitive(text: str) -> str:
    """Redacts potential API keys and tokens from a string."""
    if not isinstance(text, str):
        return text
    sanitized = text
    for pattern in REDACTION_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


class RedactingFormatter(logging.Formatter):
    """Custom formatter ensuring sensitive credentials are never emitted."""

    def format(self, record: logging.LogRecord) -> str:
        orig = super().format(record)
        return redact_sensitive(orig)


def setup_logger(name: str = "veriq") -> logging.Logger:
    """Initializes and returns a configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = RedactingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = setup_logger("veriq")
