"""Custom typed error definitions for VERIQ.
"""


class VeriqError(Exception):
    """Base exception for all VERIQ errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PatchValidationError(VeriqError):
    """Raised when patch integrity, path traversal, or size limits fail."""
    pass


class SandboxExecutionError(VeriqError):
    """Raised when sandbox execution fails, times out, or violates security policy."""
    pass


class ModelRoutingError(VeriqError):
    """Raised when model selection, invocation, or fallback fails."""
    pass


class ProviderUnavailableError(VeriqError):
    """Raised when a remote AI or research provider is unreachable or unconfigured."""
    pass


class RepositorySafetyError(VeriqError):
    """Raised when repository intake discovers unsafe paths or archives."""
    pass
