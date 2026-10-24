"""Security tests: Path traversal protection, absolute paths, and archive safety.
"""

from pathlib import Path
import pytest
from app.core.security import is_safe_relative_path, resolve_safe_path
from app.core.errors import PatchValidationError


def test_safe_relative_paths(tmp_path: Path):
    assert is_safe_relative_path(tmp_path, "calculator.py")
    assert is_safe_relative_path(tmp_path, "sub/dir/module.py")


def test_reject_directory_traversal(tmp_path: Path):
    assert not is_safe_relative_path(tmp_path, "../outside.py")
    assert not is_safe_relative_path(tmp_path, "../../etc/passwd")
    assert not is_safe_relative_path(tmp_path, "dir/../../outside.py")


def test_reject_absolute_paths(tmp_path: Path):
    assert not is_safe_relative_path(tmp_path, "/etc/shadow")
    assert not is_safe_relative_path(tmp_path, "C:\\Windows\\System32\\calc.exe")


def test_resolve_safe_path_raises_on_traversal(tmp_path: Path):
    with pytest.raises(PatchValidationError):
        resolve_safe_path(tmp_path, "../escape.py")
