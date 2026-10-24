"""Unit tests for patch validation, file limits, and byte limits.
"""

from pathlib import Path
import pytest
from app.services.repository_manager import repository_manager
from app.schemas.runs import PatchFileChange
from app.core.errors import PatchValidationError


def test_validate_patch_within_limits(tmp_path: Path):
    changes = [
        PatchFileChange(file_path="safe_file.py", new_content="print('valid')\n")
    ]
    # Should not raise
    repository_manager.validate_patch(tmp_path, changes)


def test_validate_patch_rejects_too_many_files(tmp_path: Path):
    changes = [
        PatchFileChange(file_path=f"file_{i}.py", new_content="x = 1\n")
        for i in range(15)  # Max is 10
    ]
    with pytest.raises(PatchValidationError, match="exceeding limit"):
        repository_manager.validate_patch(tmp_path, changes)


def test_validate_patch_rejects_oversized_content(tmp_path: Path):
    changes = [
        PatchFileChange(file_path="big_file.py", new_content="A" * 60000)  # Max is 50000 bytes
    ]
    with pytest.raises(PatchValidationError, match="exceeds maximum limit"):
        repository_manager.validate_patch(tmp_path, changes)


def test_validate_patch_rejects_path_traversal(tmp_path: Path):
    changes = [
        PatchFileChange(file_path="../../etc/passwd", new_content="malicious")
    ]
    with pytest.raises(PatchValidationError, match="Path traversal"):
        repository_manager.validate_patch(tmp_path, changes)
