"""Standalone Smoke Test for VERIQ.
Verifies configuration, database, sandbox execution, AST parsing, and run orchestration.
"""

import sys
import io
import asyncio
from pathlib import Path

# Ensure UTF-8 output encoding for Windows command prompts
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import logger
from app.storage.database import init_database
from app.storage.repositories import RunRepository
from app.services.verification import verification_engine
from app.services.evidence_ledger import EvidenceLedger
from app.schemas.evidence import ClaimCategory, ClaimStatus
from app.schemas.runs import PatchFileChange
from app.services.sandbox import sandbox_runner
from app.services.orchestrator import orchestrator


async def main():
    print("=" * 60)
    print("VERIQ - Verification Engine Smoke Test")
    print("Tagline: Code is generated. Proof is earned.")
    print("=" * 60)

    # 1. Config & Database Init
    print("\n[1/5] Initializing Database & Settings...")
    init_database()
    print(f"  [OK] Database verified at {settings.DATABASE_URL}")
    print(f"  [OK] App Environment: {settings.APP_ENV}")

    # 2. Sandbox Inspection
    print("\n[2/5] Inspecting Isolated Sandbox Environment...")
    docker_ok = sandbox_runner.is_docker_available()
    print(f"  [OK] Docker Engine Reachable: {docker_ok}")
    print(f"  [OK] Execution Mode: {'CONTAINER' if docker_ok else 'ISOLATED_PROCESS_FALLBACK'}")

    sample_ws = Path("examples/sample_python_project").resolve()
    test_res = sandbox_runner.execute(sample_ws, ["python", "-c", "print('sandbox_ok')"])
    assert test_res.exit_code == 0, f"Sandbox test failed: {test_res.stderr}"
    print(f"  [OK] Sandbox Subprocess Execution Verified: stdout='{test_res.stdout.strip()}' ({test_res.duration_ms}ms)")

    # 3. Deterministic AST & Import Checks
    print("\n[3/5] Testing Deterministic Verifiers...")
    valid_py = "def test_fn(x: int) -> int: return x * 2\n"
    ev_ast = verification_engine.verify_ast_syntax("TEST-CLAIM-01", "test.py", valid_py)
    assert ev_ast.status == ClaimStatus.VERIFIED, "AST check failed on valid code"
    print(f"  [OK] AST Syntax Verifier passed on valid Python code (Status: {ev_ast.status.value})")

    invalid_py = "def broken(x: return\n"
    ev_ast_bad = verification_engine.verify_ast_syntax("TEST-CLAIM-02", "test.py", invalid_py)
    assert ev_ast_bad.status == ClaimStatus.FAILED, "AST check did not fail on invalid code"
    print(f"  [OK] AST Syntax Verifier correctly caught syntax error (Status: {ev_ast_bad.status.value})")

    # 4. Verification Ledger Status Calculation
    print("\n[4/5] Testing Verification Ledger Logic...")
    ledger = EvidenceLedger("SMOKE-TEST-RUN")
    c1 = ledger.register_claim("TEST-CLAIM-01", "Syntax Proof", "Testing AST", ClaimCategory.SYNTAX)
    assert c1.status == ClaimStatus.NOT_RUN
    ledger.attach_evidence(ev_ast)
    assert ledger.claims["TEST-CLAIM-01"].status == ClaimStatus.VERIFIED
    print(f"  [OK] Claim status dynamically calculated: {ledger.claims['TEST-CLAIM-01'].status.value}")

    # 5. Full Replay Run Lifecycle
    print("\n[5/5] Executing Full Autonomous Replay Run...")
    import uuid
    run_id = f"SMOKE-RUN-{uuid.uuid4().hex[:6].upper()}"
    await orchestrator._execute_run(
        run_id=run_id,
        title="Smoke Test Calculation Task",
        description="Verify arithmetic operations and regression boundaries",
        sample_name="calculator",
        enable_research=True,
        max_repair_attempts=1,
        mode="replay",
    )

    run = RunRepository.get_run(run_id)
    assert run is not None
    assert run.status.value == "COMPLETED"
    print(f"  [OK] Run '{run_id}' completed with status: {run.status.value}")
    print(f"  [OK] Duration: {run.duration_seconds}s")
    print(f"  [OK] Unified Diff Generated: {len(run.unified_diff or '')} chars")
    print(f"  [OK] Routing Decisions Logged: {len(run.routing_history)}")
    if run.ledger_summary:
        print(f"  [OK] Claims Verified: {run.ledger_summary.verified_count}/{run.ledger_summary.total_claims}")

    print("\n" + "=" * 60)
    print("ALL SMOKE TESTS PASSED CLEANLY.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
