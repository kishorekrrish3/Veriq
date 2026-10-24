"""Security policies and validation for VERIQ.
Prevents path traversal, zip bombs, command injection, and unauthorized file access.
"""

from pathlib import Path
import os
import zipfile
import tarfile
from app.core.errors import PatchValidationError, RepositorySafetyError
from app.core.config import settings

# Allowed execution commands in the sandbox runner
ALLOWED_SANDBOX_COMMANDS = {
    "pytest",
    "python",
    "python3",
    "ruff",
}

# Subcommands or arguments strictly permitted for python in sandbox
SAFE_PYTHON_FLAGS = {"-m", "-c"}


def is_safe_relative_path(base_dir: Path | str, target_path: str) -> bool:
    """Verifies that target_path is relative and strictly inside base_dir without traversal."""
    try:
        base = Path(base_dir).resolve()
        # Disallow leading slash or backslash indicating absolute paths
        target = Path(target_path)
        if target.is_absolute() or target_path.startswith(("/", "\\")):
            return False

        # Resolve path against base
        resolved = (base / target).resolve()
        # Must start with base path
        return base == resolved or base in resolved.parents
    except Exception:
        return False


def resolve_safe_path(base_dir: Path | str, relative_path: str) -> Path:
    """Safely resolves a path, raising PatchValidationError if traversal is attempted."""
    if not is_safe_relative_path(base_dir, relative_path):
        raise PatchValidationError(
            f"Path traversal or invalid path detected: '{relative_path}'",
            details={"path": relative_path, "base_dir": str(base_dir)},
        )
    return (Path(base_dir).resolve() / relative_path).resolve()


def validate_archive_safety(archive_path: Path, max_uncompressed_bytes: int = 20_000_000, max_files: int = 500) -> None:
    """Inspects a zip or tar archive to protect against decompression bombs, absolute paths, and traversal."""
    total_size = 0
    file_count = 0

    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zf:
            for info in zf.infolist():
                file_count += 1
                total_size += info.file_size
                name = info.filename

                if name.startswith(("/", "\\")) or ".." in name.split("/") or ".." in name.split("\\"):
                    raise RepositorySafetyError(f"Malicious archive member detected with traversal: {name}")

                if file_count > max_files:
                    raise RepositorySafetyError(f"Archive exceeds maximum allowable files ({max_files})")
                if total_size > max_uncompressed_bytes:
                    raise RepositorySafetyError(f"Archive exceeds maximum allowable uncompressed size ({max_uncompressed_bytes} bytes)")

    elif tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r") as tf:
            for member in tf.getmembers():
                file_count += 1
                total_size += member.size
                name = member.name

                if member.islnk() or member.issym():
                    raise RepositorySafetyError(f"Symlinks and hard links in archive are prohibited: {name}")

                if name.startswith(("/", "\\")) or ".." in name.split("/") or ".." in name.split("\\"):
                    raise RepositorySafetyError(f"Malicious tar entry detected with traversal: {name}")

                if file_count > max_files:
                    raise RepositorySafetyError(f"Archive exceeds maximum allowable files ({max_files})")
                if total_size > max_uncompressed_bytes:
                    raise RepositorySafetyError(f"Archive exceeds maximum allowable uncompressed size ({max_uncompressed_bytes} bytes)")
    else:
        raise RepositorySafetyError(f"Unsupported archive format for file: {archive_path.name}")


def validate_sandbox_command(command: list[str]) -> None:
    """Ensures a command to be executed in the sandbox matches the strict security allowlist."""
    if not command:
        raise PatchValidationError("Empty command cannot be executed")

    binary = Path(command[0]).name
    # Strip any .exe on windows
    if binary.endswith(".exe"):
        binary = binary[:-4]

    if binary not in ALLOWED_SANDBOX_COMMANDS:
        raise PatchValidationError(f"Command '{binary}' is not permitted in sandbox allowlist: {ALLOWED_SANDBOX_COMMANDS}")
