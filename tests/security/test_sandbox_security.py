"""Security tests: Sandbox command allowlist and environment isolation.
"""

from pathlib import Path
import os
import pytest
from app.core.security import validate_sandbox_command
from app.core.errors import PatchValidationError
from app.services.sandbox import sandbox_runner


def test_command_allowlist_permits_safe_tools():
    # Safe commands must not raise
    validate_sandbox_command(["pytest", "-v"])
    validate_sandbox_command(["python", "-m", "py_compile", "file.py"])
    validate_sandbox_command(["python3", "-c", "import math"])


def test_command_allowlist_rejects_arbitrary_binaries():
    forbidden = [
        ["curl", "https://evil.com"],
        ["bash", "-c", "whoami"],
        ["sh", "-c", "id"],
        ["powershell", "-Command", "dir"],
        ["cmd.exe", "/c", "dir"],
        ["rm", "-rf", "/"],
        ["wget", "http://malicious.com"],
    ]
    for cmd in forbidden:
        with pytest.raises(PatchValidationError, match="not permitted in sandbox allowlist"):
            validate_sandbox_command(cmd)


def test_sandbox_fallback_strips_host_secrets(tmp_path: Path):
    """Verifies that the isolated subprocess runner does NOT pass host secrets into child environment."""
    # Temporarily set a dummy secret in parent env
    os.environ["SECRET_API_KEY"] = "super_secret_token_12345"

    code = "import os; print('SECRET_FOUND' if 'SECRET_API_KEY' in os.environ else 'CLEAN_ENV')"
    res = sandbox_runner.execute(tmp_path, ["python", "-c", code])

    # Clean up test parent env
    del os.environ["SECRET_API_KEY"]

    assert res.exit_code == 0
    assert "CLEAN_ENV" in res.stdout
    assert "SECRET_FOUND" not in res.stdout
