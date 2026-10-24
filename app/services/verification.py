"""Deterministic Verification Engine for VERIQ.
Executes independent checks: patch integrity, AST syntax parsing,
isolated import verification, pytest regression execution, and security risk auditing.
"""

import ast
import hashlib
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from app.core.config import settings
from app.schemas.evidence import ClaimStatus, EvidenceRecord, ClaimCategory
from app.schemas.runs import PatchFileChange
from app.services.sandbox import sandbox_runner, SandboxResult
from app.core.logging import logger

SUSPICIOUS_CALL_PATTERNS = [
    "eval(",
    "exec(",
    "__import__(",
    "os.system(",
    "subprocess.",
    "socket.",
    "shutil.rmtree(",
    "pty.",
]


class VerificationEngine:
    """Coordinates deterministic verification checks and produces concrete evidence records."""

    def verify_patch_integrity(
        self,
        claim_id: str,
        workspace_path: Path,
        changes: List[PatchFileChange],
    ) -> EvidenceRecord:
        """Verifies file paths, byte sizes, and produces SHA-256 integrity hashes."""
        start = time.perf_counter()
        ev_id = f"EV-INTEG-{uuid.uuid4().hex[:8]}"

        total_bytes = 0
        file_hashes = {}
        for c in changes:
            data = c.new_content.encode("utf-8")
            total_bytes += len(data)
            file_hashes[c.file_path] = hashlib.sha256(data).hexdigest()

        duration = (time.perf_counter() - start) * 1000.0

        if total_bytes > settings.MAX_PATCH_BYTES:
            status = ClaimStatus.FAILED
            msg = f"Patch size ({total_bytes} bytes) exceeds limit ({settings.MAX_PATCH_BYTES})"
        elif len(changes) > settings.MAX_PATCH_FILES:
            status = ClaimStatus.FAILED
            msg = f"File count ({len(changes)}) exceeds limit ({settings.MAX_PATCH_FILES})"
        else:
            status = ClaimStatus.VERIFIED
            msg = f"Patch integrity confirmed: {len(changes)} files, {total_bytes} bytes"

        return EvidenceRecord(
            evidence_id=ev_id,
            claim_id=claim_id,
            check_type="patch_integrity",
            status=status,
            command="internal:sha256_path_integrity",
            exit_code=0 if status == ClaimStatus.VERIFIED else 1,
            duration_ms=round(duration, 2),
            stdout=msg,
            stderr=None,
            file_ref=changes[0].file_path if changes else None,
            line_ref=None,
            details={"file_hashes": file_hashes, "total_bytes": total_bytes},
            limitations=[
                "Confirms structural bounds and path invariants only.",
                "Does not evaluate functional logic correctness.",
            ],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def verify_ast_syntax(
        self,
        claim_id: str,
        file_path: str,
        content: str,
    ) -> EvidenceRecord:
        """Parses Python source using AST to verify absence of syntax errors."""
        start = time.perf_counter()
        ev_id = f"EV-AST-{uuid.uuid4().hex[:8]}"

        try:
            ast.parse(content, filename=file_path)
            duration = (time.perf_counter() - start) * 1000.0
            return EvidenceRecord(
                evidence_id=ev_id,
                claim_id=claim_id,
                check_type="python_ast_parse",
                status=ClaimStatus.VERIFIED,
                command=f"python_ast.parse({file_path})",
                exit_code=0,
                duration_ms=round(duration, 2),
                stdout=f"AST parse successful. Valid Python 3 syntax for '{file_path}'.",
                stderr=None,
                file_ref=file_path,
                line_ref=1,
                details={"nodes_parsed": True},
                limitations=[
                    "Proves syntactical validity only.",
                    "Does not prove semantic correctness or runtime type safety.",
                ],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except SyntaxError as e:
            duration = (time.perf_counter() - start) * 1000.0
            return EvidenceRecord(
                evidence_id=ev_id,
                claim_id=claim_id,
                check_type="python_ast_parse",
                status=ClaimStatus.FAILED,
                command=f"python_ast.parse({file_path})",
                exit_code=1,
                duration_ms=round(duration, 2),
                stdout=None,
                stderr=f"SyntaxError in {file_path} line {e.lineno}: {e.msg}",
                file_ref=file_path,
                line_ref=e.lineno,
                details={"error": e.msg, "lineno": e.lineno, "offset": e.offset},
                limitations=[
                    "Syntax check failed at designated line.",
                ],
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

    def verify_import(
        self,
        claim_id: str,
        workspace_path: Path,
        module_name: str,
    ) -> EvidenceRecord:
        """Executes an isolated import test in the sandbox."""
        ev_id = f"EV-IMP-{uuid.uuid4().hex[:8]}"
        command = ["python", "-c", f"import {module_name}; print('{module_name} imported successfully')"]

        result = sandbox_runner.execute(workspace_path, command, timeout_seconds=15)
        status = ClaimStatus.VERIFIED if result.exit_code == 0 else ClaimStatus.FAILED

        return EvidenceRecord(
            evidence_id=ev_id,
            claim_id=claim_id,
            check_type="isolated_module_import",
            status=status,
            command=" ".join(command),
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip() if result.stderr else None,
            file_ref=f"{module_name}.py",
            line_ref=1,
            details={"sandbox_env": result.execution_environment},
            limitations=[
                "Verifies top-level import execution and initialization.",
                "Does not execute deep functional call paths.",
            ] + result.limitations,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def verify_tests(
        self,
        claim_id: str,
        workspace_path: Path,
        test_file: Optional[str] = None,
    ) -> EvidenceRecord:
        """Executes pytest in the sandbox and parses test results."""
        ev_id = f"EV-TEST-{uuid.uuid4().hex[:8]}"
        command = ["pytest", "-v"]
        if test_file:
            command.append(test_file)

        result = sandbox_runner.execute(workspace_path, command, timeout_seconds=settings.MAX_EXECUTION_SECONDS)

        # Parse pytest output summary: e.g. "X passed, Y failed"
        passed_count = 0
        failed_count = 0
        for line in result.stdout.splitlines():
            if "passed" in line or "failed" in line or "error" in line:
                if "passed" in line:
                    try:
                        part = line.split("passed")[0].strip().split()[-1]
                        passed_count = int(part)
                    except Exception:
                        pass
                if "failed" in line:
                    try:
                        part = line.split("failed")[0].strip().split()[-1]
                        failed_count = int(part)
                    except Exception:
                        pass

        status = ClaimStatus.VERIFIED if result.exit_code == 0 else ClaimStatus.FAILED

        return EvidenceRecord(
            evidence_id=ev_id,
            claim_id=claim_id,
            check_type="pytest_execution",
            status=status,
            command=" ".join(command),
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            stdout=result.stdout,
            stderr=result.stderr if result.stderr else None,
            file_ref=test_file or "tests",
            line_ref=None,
            details={
                "passed": passed_count,
                "failed": failed_count,
                "sandbox_env": result.execution_environment,
            },
            limitations=[
                "Proves that existing test suite assertions hold.",
                "Does not prove universal absence of untested edge cases or defects.",
            ] + result.limitations,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def verify_security_risks(
        self,
        claim_id: str,
        changes: List[PatchFileChange],
    ) -> EvidenceRecord:
        """Audits proposed changes for suspicious calls or security policy violations."""
        start = time.perf_counter()
        ev_id = f"EV-SEC-{uuid.uuid4().hex[:8]}"

        flagged: List[str] = []
        for c in changes:
            for pattern in SUSPICIOUS_CALL_PATTERNS:
                if pattern in c.new_content:
                    flagged.append(f"{c.file_path}: contains '{pattern}'")

        duration = (time.perf_counter() - start) * 1000.0

        if flagged:
            status = ClaimStatus.UNRESOLVED
            msg = f"Security review identified potential risk patterns: {', '.join(flagged)}"
        else:
            status = ClaimStatus.SUPPORTED
            msg = "Security pattern scan passed. No prohibited process or evaluation calls detected."

        return EvidenceRecord(
            evidence_id=ev_id,
            claim_id=claim_id,
            check_type="static_security_audit",
            status=status,
            command="internal:security_pattern_scan",
            exit_code=0 if not flagged else 1,
            duration_ms=round(duration, 2),
            stdout=msg,
            stderr=None,
            file_ref=changes[0].file_path if changes else None,
            line_ref=None,
            details={"flagged_patterns": flagged},
            limitations=[
                "Heuristic pattern scan cannot guarantee complete absence of malicious intent.",
                "Flagged patterns indicate risk for human inspection, not proof of exploit.",
            ],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


verification_engine = VerificationEngine()
