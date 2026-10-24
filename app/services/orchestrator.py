"""Autonomous Engineering Agent Orchestrator for VERIQ.
Executes the full state-machine driven engineering workflow with bounded self-repair,
evidence accumulation, and event streaming.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger, redact_sensitive
from app.schemas.runs import RunStatus, RoutingDecision, PatchFileChange
from app.schemas.events import EventType, RunEvent
from app.schemas.evidence import ClaimCategory, ClaimStatus
from app.storage.repositories import RunRepository, EventRepository
from app.services.state_machine import RunStateMachine
from app.services.evidence_ledger import EvidenceLedger
from app.services.repository_manager import repository_manager
from app.services.model_router import model_router
from app.services.nebius_client import nebius_client
from app.services.research import research_service
from app.services.patch_generator import patch_generator
from app.services.verification import verification_engine
from app.services.report_generator import report_generator


class AgentOrchestrator:
    """Coordinates the end-to-end autonomous engineering run."""

    def __init__(self):
        # In-memory queues for SSE listeners keyed by run_id
        self.event_queues: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        """Subscribes an SSE connection to events for a specific run."""
        queue: asyncio.Queue = asyncio.Queue()
        if run_id not in self.event_queues:
            self.event_queues[run_id] = []
        self.event_queues[run_id].append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        """Unsubscribes an SSE connection."""
        if run_id in self.event_queues and queue in self.event_queues[run_id]:
            self.event_queues[run_id].remove(queue)

    async def emit_event(
        self,
        run_id: str,
        event_type: EventType,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> RunEvent:
        """Publishes an event to the database and all active SSE subscribers."""
        event = RunEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:8]}",
            run_id=run_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            message=message,
            data=data or {},
        )
        EventRepository.add_event(event)

        # Notify active SSE queues
        if run_id in self.event_queues:
            for q in self.event_queues[run_id]:
                await q.put(event)

        logger.info(f"[{run_id}] Event: {event_type.value} - {message}")
        return event

    async def start_run(
        self,
        run_id: str,
        title: str,
        description: str,
        sample_name: str = "calculator",
        enable_research: bool = True,
        max_repair_attempts: int = 1,
        mode: str = "auto",
    ) -> None:
        """Launches the run workflow asynchronously."""
        force_replay = (mode == "replay") or (not settings.is_live_inference_configured)
        execution_mode = "replay" if force_replay else "live"
        created_at = datetime.now(timezone.utc).isoformat()

        # Synchronously create record in DB so it is immediately queryable
        RunRepository.create_run(
            run_id=run_id,
            task_title=title,
            task_description=description,
            status=RunStatus.CREATED,
            execution_mode=execution_mode,
            created_at=created_at,
        )

        asyncio.create_task(
            self._execute_run(
                run_id=run_id,
                title=title,
                description=description,
                sample_name=sample_name,
                enable_research=enable_research,
                max_repair_attempts=max_repair_attempts,
                mode=mode,
                created_at=created_at,
                execution_mode=execution_mode,
            )
        )

    async def _execute_run(
        self,
        run_id: str,
        title: str,
        description: str,
        sample_name: str,
        enable_research: bool,
        max_repair_attempts: int,
        mode: str,
        created_at: Optional[str] = None,
        execution_mode: Optional[str] = None,
    ) -> None:
        start_time = time.perf_counter()
        created_at = created_at or datetime.now(timezone.utc).isoformat()
        state_machine = RunStateMachine(RunStatus.CREATED)
        ledger = EvidenceLedger(run_id)
        routing_history: List[RoutingDecision] = []
        workspace_path: Optional[Path] = None

        # Determine effective execution mode
        force_replay = (mode == "replay") or (not settings.is_live_inference_configured)
        execution_mode = execution_mode or ("replay" if force_replay else "live")

        # Ensure run record exists in DB (idempotent)
        RunRepository.create_run(
            run_id=run_id,
            task_title=title,
            task_description=description,
            status=RunStatus.CREATED,
            execution_mode=execution_mode,
            created_at=created_at,
        )

        await self.emit_event(
            run_id,
            EventType.RUN_CREATED,
            f"Run initialized in {execution_mode.upper()} mode.",
            {"execution_mode": execution_mode, "sample_name": sample_name},
        )

        try:
            # Register Core Claims in the Verification Ledger
            c1 = ledger.register_claim(
                "CLAIM-001",
                "Patch Structural Integrity & Bounds",
                "Ensures the generated patch modifies permitted files within size limits without path traversal.",
                ClaimCategory.PATCH_INTEGRITY,
                file_refs=["calculator.py"],
            )
            c2 = ledger.register_claim(
                "CLAIM-002",
                "AST Syntax Validity",
                "Validates that all changed Python source files parse without syntax errors.",
                ClaimCategory.SYNTAX,
                file_refs=["calculator.py"],
            )
            c3 = ledger.register_claim(
                "CLAIM-003",
                "Clean Module Import Execution",
                "Confirms the modified module initializes cleanly in an isolated sandbox without import errors.",
                ClaimCategory.IMPORT,
                file_refs=["calculator.py"],
            )
            c4 = ledger.register_claim(
                "CLAIM-004",
                "Test Suite & Regression Verification",
                "Executes pytest regression tests inside the isolated sandbox to prove behavior holds.",
                ClaimCategory.REGRESSION_TEST,
                file_refs=["test_calculator.py"],
            )
            c5 = ledger.register_claim(
                "CLAIM-005",
                "Technical Documentation Grounding",
                "Correlates changes with official Python documentation and specifications.",
                ClaimCategory.RESEARCH_GROUNDING,
            )
            c6 = ledger.register_claim(
                "CLAIM-006",
                "Prohibited Calls & Security Audit",
                "Inspects modified code for dangerous system, process, or evaluation calls.",
                ClaimCategory.SECURITY_AUDIT,
                file_refs=["calculator.py"],
            )

            # Step 1: Research (Optional / Grounding)
            if enable_research:
                state_machine.transition_to(RunStatus.RESEARCHING)
                RunRepository.update_run_status(run_id, RunStatus.RESEARCHING)
                await self.emit_event(run_id, EventType.RESEARCH_STARTED, "Querying technical documentation...")

                results, res_evidence, res_mode = await research_service.perform_research(
                    task_title=title,
                    task_description=description,
                    claim_id="CLAIM-005",
                    force_replay=force_replay,
                )
                ledger.attach_evidence(res_evidence)
                await self.emit_event(
                    run_id,
                    EventType.RESEARCH_COMPLETED,
                    f"Research complete ({res_mode}): {len(results)} authoritative passages retrieved.",
                    {"sources_count": len(results), "mode": res_mode},
                )

            # Step 2: Planning & Snapshot
            state_machine.transition_to(RunStatus.PLANNING)
            RunRepository.update_run_status(run_id, RunStatus.PLANNING)
            await self.emit_event(run_id, EventType.PLAN_GENERATED, "Inspecting repository and capturing isolated working snapshot.")

            source_path = repository_manager.get_sample_path(sample_name)
            workspace_path = repository_manager.create_working_snapshot(run_id, source_path)

            # Read existing files for context
            existing_files: Dict[str, str] = {}
            for py_file in workspace_path.glob("*.py"):
                with open(py_file, "r", encoding="utf-8") as f:
                    existing_files[py_file.name] = f.read()

            # Step 3: Model Selection & Patch Generation (Attempt 1)
            initial_decision = model_router.select_model(
                task_description=description,
                affected_files=1,
                attempt=1,
                is_repair=False,
            )
            routing_history.append(initial_decision)

            await self.emit_event(
                run_id,
                EventType.MODEL_SELECTED,
                f"Selected model {initial_decision.model_id} ({initial_decision.tier.value} Tier). Trigger: {initial_decision.trigger}",
                initial_decision.model_dump(),
            )

            state_machine.transition_to(RunStatus.GENERATING_PATCH)
            RunRepository.update_run_status(run_id, RunStatus.GENERATING_PATCH)
            await self.emit_event(run_id, EventType.PATCH_GENERATED, "Synthesizing code patch...")

            changes, tokens, latency = await patch_generator.generate_patch(
                task_title=title,
                task_description=description,
                files_context=existing_files,
                model_id=initial_decision.model_id,
                is_repair=False,
                force_replay=force_replay,
            )
            initial_decision.latency_ms = latency
            initial_decision.total_tokens = tokens.get("total_tokens", 0)
            initial_decision.prompt_tokens = tokens.get("prompt_tokens", 0)
            initial_decision.completion_tokens = tokens.get("completion_tokens", 0)
            initial_decision.estimated_cost_usd = model_router.calculate_cost(
                initial_decision.tier, initial_decision.total_tokens
            )

            # Step 4: Patch Validation & Application
            state_machine.transition_to(RunStatus.VALIDATING_PATCH)
            RunRepository.update_run_status(run_id, RunStatus.VALIDATING_PATCH)

            # Verify integrity
            ev_integ = verification_engine.verify_patch_integrity("CLAIM-001", workspace_path, changes)
            ledger.attach_evidence(ev_integ)

            # Verify security
            ev_sec = verification_engine.verify_security_risks("CLAIM-006", changes)
            ledger.attach_evidence(ev_sec)

            # Apply patch
            unified_diff, changed_files = repository_manager.apply_patch(workspace_path, changes)

            # Verify AST
            for c in changes:
                ev_ast = verification_engine.verify_ast_syntax("CLAIM-002", c.file_path, c.new_content)
                ledger.attach_evidence(ev_ast)

            await self.emit_event(
                run_id,
                EventType.PATCH_VALIDATED,
                f"Patch applied cleanly across {len(changed_files)} files.",
                {"changed_files": changed_files},
            )

            # Step 5: Executing Isolated Checks
            state_machine.transition_to(RunStatus.EXECUTING_CHECKS)
            RunRepository.update_run_status(run_id, RunStatus.EXECUTING_CHECKS)
            await self.emit_event(run_id, EventType.TESTS_EXECUTED, "Running isolated sandbox tests...")

            # Isolated import check
            ev_imp = verification_engine.verify_import("CLAIM-003", workspace_path, "calculator")
            ledger.attach_evidence(ev_imp)

            # Pytest test execution
            ev_test = verification_engine.verify_tests("CLAIM-004", workspace_path, "test_calculator.py")
            ledger.attach_evidence(ev_test)

            # Step 6: Bounded Self-Repair Loop if checks failed
            if ev_test.status == ClaimStatus.FAILED and max_repair_attempts > 0:
                await self.emit_event(
                    run_id,
                    EventType.FAILURE_DETECTED,
                    f"Regression detected in test execution: {ev_test.stderr or 'Test assertion failure'}. Initiating bounded self-repair.",
                    {"exit_code": ev_test.exit_code, "test_details": ev_test.details},
                )

                state_machine.transition_to(RunStatus.REPAIRING)
                RunRepository.update_run_status(run_id, RunStatus.REPAIRING)

                # Escalate model tier for repair
                repair_decision = model_router.select_model(
                    task_description=description,
                    affected_files=1,
                    attempt=2,
                    failure_type="REGRESSION_TEST",
                    is_repair=True,
                )
                routing_history.append(repair_decision)

                await self.emit_event(
                    run_id,
                    EventType.MODEL_SELECTED,
                    f"Escalated to {repair_decision.model_id} ({repair_decision.tier.value} Tier) for corrective repair.",
                    repair_decision.model_dump(),
                )

                await self.emit_event(run_id, EventType.REPAIR_ATTEMPTED, "Generating minimal corrective patch to fix regression...")

                # Read current working files
                re_existing: Dict[str, str] = {}
                for py_file in workspace_path.glob("*.py"):
                    with open(py_file, "r", encoding="utf-8") as f:
                        re_existing[py_file.name] = f.read()

                re_changes, re_tokens, re_latency = await patch_generator.generate_patch(
                    task_title=title,
                    task_description=description,
                    files_context=re_existing,
                    model_id=repair_decision.model_id,
                    is_repair=True,
                    failure_diagnostics=f"{ev_test.stdout}\n{ev_test.stderr or ''}",
                    force_replay=force_replay,
                )
                repair_decision.latency_ms = re_latency
                repair_decision.total_tokens = re_tokens.get("total_tokens", 0)
                repair_decision.prompt_tokens = re_tokens.get("prompt_tokens", 0)
                repair_decision.completion_tokens = re_tokens.get("completion_tokens", 0)
                repair_decision.estimated_cost_usd = model_router.calculate_cost(
                    repair_decision.tier, repair_decision.total_tokens
                )

                # Apply repaired patch
                re_diff, re_changed = repository_manager.apply_patch(workspace_path, re_changes)
                changed_files = list(set(changed_files + re_changed))
                unified_diff = repository_manager.compute_cumulative_diff(source_path, workspace_path, changed_files)

                # Re-verify AST
                for c in re_changes:
                    re_ev_ast = verification_engine.verify_ast_syntax("CLAIM-002", c.file_path, c.new_content)
                    ledger.attach_evidence(re_ev_ast)

                # Re-run isolated import check
                re_ev_imp = verification_engine.verify_import("CLAIM-003", workspace_path, "calculator")
                ledger.attach_evidence(re_ev_imp)

                # Re-run pytest in sandbox
                re_ev_test = verification_engine.verify_tests("CLAIM-004", workspace_path, "test_calculator.py")
                ledger.attach_evidence(re_ev_test)

                await self.emit_event(
                    run_id,
                    EventType.REPAIR_COMPLETED,
                    f"Corrective repair completed. Pytest outcome: {re_ev_test.status.value}.",
                    {"re_test_exit_code": re_ev_test.exit_code, "status": re_ev_test.status.value},
                )

            # Step 7: Finalizing & Report Generation
            state_machine.transition_to(RunStatus.FINALIZING)
            RunRepository.update_run_status(run_id, RunStatus.FINALIZING)

            summary = ledger.get_summary()
            duration_total = round(time.perf_counter() - start_time, 2)
            completed_at = datetime.now(timezone.utc).isoformat()

            final_status = RunStatus.COMPLETED if summary.failed_count == 0 else RunStatus.VERIFICATION_FAILED
            outcome_text = (
                f"Engineering run completed with {summary.verified_count}/{summary.total_claims} verified claims."
                if final_status == RunStatus.COMPLETED
                else f"Run finished with {summary.failed_count} failing checks requiring attention."
            )

            state_machine.transition_to(final_status)

            RunRepository.update_run_status(
                run_id=run_id,
                status=final_status,
                completed_at=completed_at,
                duration_seconds=duration_total,
                unified_diff=unified_diff,
                changed_files=changed_files,
                routing_history=routing_history,
                final_outcome=outcome_text,
            )

            await self.emit_event(
                run_id,
                EventType.VERIFICATION_COMPLETED,
                f"Verification complete: {summary.verified_count} verified, {summary.supported_count} supported, {summary.failed_count} failed.",
                summary.model_dump(),
            )

            await self.emit_event(
                run_id,
                EventType.REPORT_GENERATED,
                "Verification ledger report generated and available for download.",
                {"run_id": run_id},
            )

            await self.emit_event(
                run_id,
                EventType.RUN_COMPLETED,
                outcome_text,
                {"status": final_status.value, "duration_seconds": duration_total},
            )

        except Exception as e:
            logger.error(f"Error during orchestrator run {run_id}: {redact_sensitive(str(e))}", exc_info=True)
            RunRepository.update_run_status(
                run_id=run_id,
                status=RunStatus.FAILED,
                completed_at=datetime.now(timezone.utc).isoformat(),
                duration_seconds=round(time.perf_counter() - start_time, 2),
                error_message=redact_sensitive(str(e)),
            )
            await self.emit_event(
                run_id,
                EventType.RUN_FAILED,
                f"Run encountered failure: {redact_sensitive(str(e))}",
                {"error": redact_sensitive(str(e))},
            )


orchestrator = AgentOrchestrator()
