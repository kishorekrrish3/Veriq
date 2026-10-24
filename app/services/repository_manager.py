"""Repository intake, snapshotting, and patch application service.
Guarantees the original repository is never modified, enforces path safety,
computes unified diffs, and manages isolated working copies.
"""

import shutil
import difflib
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from app.core.config import settings
from app.core.security import is_safe_relative_path, resolve_safe_path
from app.core.errors import PatchValidationError, RepositorySafetyError
from app.schemas.runs import PatchFileChange
from app.core.logging import logger


class RepositoryManager:
    """Manages immutable snapshots and isolated working copies for runs."""

    def __init__(self):
        self.samples_dir = Path("examples")
        self.workspaces_dir = Path(settings.DATA_DIR) / "workspaces"
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)

    def get_sample_path(self, sample_name: str = "calculator") -> Path:
        """Returns the base path of a known sample project."""
        target = self.samples_dir / "sample_python_project"
        if not target.exists():
            raise RepositorySafetyError(f"Sample project '{sample_name}' not found at {target}")
        return target

    def create_working_snapshot(self, run_id: str, source_dir: Path) -> Path:
        """Creates an isolated temporary copy of the repository for the specific run.
        The original repository is never modified.
        """
        dest_dir = self.workspaces_dir / run_id
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        shutil.copytree(source_dir, dest_dir)
        logger.info(f"Created isolated working snapshot for run {run_id} at {dest_dir}")
        return dest_dir

    def cleanup_workspace(self, run_id: str) -> None:
        """Removes the working copy after run finalization."""
        dest_dir = self.workspaces_dir / run_id
        if dest_dir.exists():
            try:
                shutil.rmtree(dest_dir)
            except Exception as e:
                logger.warning(f"Could not remove workspace {dest_dir}: {e}")

    def validate_patch(self, workspace_path: Path, changes: List[PatchFileChange]) -> None:
        """Validates patch integrity, file limits, byte limits, and path traversal."""
        if len(changes) > settings.MAX_PATCH_FILES:
            raise PatchValidationError(
                f"Patch modifies {len(changes)} files, exceeding limit of {settings.MAX_PATCH_FILES}"
            )

        total_bytes = sum(len(c.new_content.encode("utf-8")) for c in changes)
        if total_bytes > settings.MAX_PATCH_BYTES:
            raise PatchValidationError(
                f"Patch size {total_bytes} bytes exceeds maximum limit of {settings.MAX_PATCH_BYTES} bytes"
            )

        for change in changes:
            if not is_safe_relative_path(workspace_path, change.file_path):
                raise PatchValidationError(
                    f"Path traversal attempt or forbidden path in patch: '{change.file_path}'"
                )

    def apply_patch(
        self,
        workspace_path: Path,
        changes: List[PatchFileChange],
    ) -> Tuple[str, List[str]]:
        """Applies validated changes to the working copy and produces a unified diff.
        Returns: (unified_diff_string, list_of_changed_files)
        """
        self.validate_patch(workspace_path, changes)

        diff_outputs: List[str] = []
        changed_files: List[str] = []

        for change in changes:
            target_file = resolve_safe_path(workspace_path, change.file_path)
            target_file.parent.mkdir(parents=True, exist_ok=True)

            old_lines: List[str] = []
            if target_file.exists():
                with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                    old_lines = f.readlines()
                change.old_content = "".join(old_lines)
            else:
                change.old_content = ""

            new_lines = change.new_content.splitlines(keepends=True)

            # Generate unified diff
            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{change.file_path}",
                tofile=f"b/{change.file_path}",
            )
            diff_text = "".join(diff)
            change.diff = diff_text
            diff_outputs.append(diff_text)

            # Write new content to working copy
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(change.new_content)

            changed_files.append(change.file_path)

        full_diff = "\n".join(diff_outputs)
        logger.info(f"Applied patch modifying {len(changed_files)} files in workspace {workspace_path}")
        return full_diff, changed_files

    def compute_cumulative_diff(
        self,
        source_dir: Path,
        workspace_path: Path,
        changed_files: List[str],
    ) -> str:
        """Computes the complete cumulative unified diff between the original source and working copy."""
        diff_outputs = []
        for file_rel in changed_files:
            orig_file = source_dir / file_rel
            work_file = workspace_path / file_rel

            orig_lines: List[str] = []
            if orig_file.exists():
                with open(orig_file, "r", encoding="utf-8", errors="replace") as f:
                    orig_lines = f.readlines()

            work_lines: List[str] = []
            if work_file.exists():
                with open(work_file, "r", encoding="utf-8", errors="replace") as f:
                    work_lines = f.readlines()

            diff = difflib.unified_diff(
                orig_lines,
                work_lines,
                fromfile=f"a/{file_rel}",
                tofile=f"b/{file_rel}",
            )
            diff_outputs.append("".join(diff))

        return "\n".join(diff_outputs)


repository_manager = RepositoryManager()
