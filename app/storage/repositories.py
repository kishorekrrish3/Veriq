"""Data Access Repositories for VERIQ SQLite persistence.
"""

import json
from typing import List, Optional, Dict, Any
from app.storage.database import get_db_connection
from app.schemas.runs import RunResponse, RunStatus, RoutingDecision
from app.schemas.events import RunEvent, EventType
from app.schemas.evidence import (
    ClaimRecord,
    EvidenceRecord,
    VerificationLedgerSummary,
    ClaimStatus,
    ClaimCategory,
)


class RunRepository:
    @staticmethod
    def create_run(
        run_id: str,
        task_title: str,
        task_description: str,
        status: RunStatus,
        execution_mode: str,
        created_at: str,
    ) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, task_title, task_description, status, execution_mode,
                    created_at, changed_files, routing_history
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    task_title,
                    task_description,
                    status.value,
                    execution_mode,
                    created_at,
                    json.dumps([]),
                    json.dumps([]),
                ),
            )

    @staticmethod
    def update_run_status(
        run_id: str,
        status: RunStatus,
        completed_at: Optional[str] = None,
        duration_seconds: float = 0.0,
        unified_diff: Optional[str] = None,
        changed_files: Optional[List[str]] = None,
        routing_history: Optional[List[RoutingDecision]] = None,
        final_outcome: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            updates = ["status = ?"]
            params: List[Any] = [status.value]

            if completed_at is not None:
                updates.append("completed_at = ?")
                params.append(completed_at)
            if duration_seconds > 0.0:
                updates.append("duration_seconds = ?")
                params.append(duration_seconds)
            if unified_diff is not None:
                updates.append("unified_diff = ?")
                params.append(unified_diff)
            if changed_files is not None:
                updates.append("changed_files = ?")
                params.append(json.dumps(changed_files))
            if routing_history is not None:
                updates.append("routing_history = ?")
                params.append(json.dumps([r.model_dump() for r in routing_history]))
            if final_outcome is not None:
                updates.append("final_outcome = ?")
                params.append(final_outcome)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            params.append(run_id)
            query = f"UPDATE runs SET {', '.join(updates)} WHERE run_id = ?"
            cursor.execute(query, params)

    @staticmethod
    def get_run(run_id: str) -> Optional[RunResponse]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None

            routing_raw = json.loads(row["routing_history"] or "[]")
            routing = [RoutingDecision(**r) for r in routing_raw]
            changed_files = json.loads(row["changed_files"] or "[]")

            # Load ledger summary
            ledger_summary = LedgerRepository.get_summary(run_id)

            return RunResponse(
                run_id=row["run_id"],
                task_title=row["task_title"],
                task_description=row["task_description"],
                status=RunStatus(row["status"]),
                execution_mode=row["execution_mode"],
                created_at=row["created_at"],
                completed_at=row["completed_at"],
                duration_seconds=row["duration_seconds"] or 0.0,
                unified_diff=row["unified_diff"],
                changed_files=changed_files,
                routing_history=routing,
                ledger_summary=ledger_summary,
                final_outcome=row["final_outcome"] or "",
                error_message=row["error_message"],
            )

    @staticmethod
    def list_runs(limit: int = 50) -> List[RunResponse]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT run_id FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                run = RunRepository.get_run(r["run_id"])
                if run:
                    results.append(run)
            return results


class EventRepository:
    @staticmethod
    def add_event(event: RunEvent) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (event_id, run_id, event_type, timestamp, message, data)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.run_id,
                    event.event_type.value,
                    event.timestamp,
                    event.message,
                    json.dumps(event.data),
                ),
            )

    @staticmethod
    def get_events(run_id: str) -> List[RunEvent]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY timestamp ASC",
                (run_id,),
            )
            rows = cursor.fetchall()
            return [
                RunEvent(
                    event_id=row["event_id"],
                    run_id=row["run_id"],
                    event_type=EventType(row["event_type"]),
                    timestamp=row["timestamp"],
                    message=row["message"],
                    data=json.loads(row["data"]),
                )
                for row in rows
            ]


class LedgerRepository:
    @staticmethod
    def save_claim(run_id: str, claim: ClaimRecord) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO claims (
                    claim_id, run_id, title, description, category, status,
                    evidence_ids, file_refs, limitations, unresolved_questions, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim.claim_id,
                    run_id,
                    claim.title,
                    claim.description,
                    claim.category.value,
                    claim.status.value,
                    json.dumps(claim.evidence_ids),
                    json.dumps(claim.file_refs),
                    json.dumps(claim.limitations),
                    json.dumps(claim.unresolved_questions),
                    claim.timestamp,
                ),
            )

    @staticmethod
    def save_evidence(run_id: str, evidence: EvidenceRecord) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO evidence (
                    evidence_id, run_id, claim_id, check_type, status, command,
                    exit_code, duration_ms, stdout, stderr, file_ref, line_ref,
                    details, limitations, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    run_id,
                    evidence.claim_id,
                    evidence.check_type,
                    evidence.status.value,
                    evidence.command,
                    evidence.exit_code,
                    evidence.duration_ms,
                    evidence.stdout,
                    evidence.stderr,
                    evidence.file_ref,
                    evidence.line_ref,
                    json.dumps(evidence.details),
                    json.dumps(evidence.limitations),
                    evidence.timestamp,
                ),
            )

    @staticmethod
    def get_summary(run_id: str) -> VerificationLedgerSummary:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM claims WHERE run_id = ? ORDER BY claim_id ASC", (run_id,))
            claim_rows = cursor.fetchall()
            claims = [
                ClaimRecord(
                    claim_id=r["claim_id"],
                    title=r["title"],
                    description=r["description"],
                    category=ClaimCategory(r["category"]),
                    status=ClaimStatus(r["status"]),
                    evidence_ids=json.loads(r["evidence_ids"]),
                    file_refs=json.loads(r["file_refs"]),
                    limitations=json.loads(r["limitations"]),
                    unresolved_questions=json.loads(r["unresolved_questions"]),
                    timestamp=r["timestamp"],
                )
                for r in claim_rows
            ]

            cursor.execute("SELECT * FROM evidence WHERE run_id = ? ORDER BY timestamp ASC", (run_id,))
            ev_rows = cursor.fetchall()
            evidence = [
                EvidenceRecord(
                    evidence_id=r["evidence_id"],
                    claim_id=r["claim_id"],
                    check_type=r["check_type"],
                    status=ClaimStatus(r["status"]),
                    command=r["command"],
                    exit_code=r["exit_code"],
                    duration_ms=r["duration_ms"] or 0.0,
                    stdout=r["stdout"],
                    stderr=r["stderr"],
                    file_ref=r["file_ref"],
                    line_ref=r["line_ref"],
                    details=json.loads(r["details"] or "{}"),
                    limitations=json.loads(r["limitations"] or "[]"),
                    timestamp=r["timestamp"],
                )
                for r in ev_rows
            ]

            counts = {
                ClaimStatus.VERIFIED: 0,
                ClaimStatus.SUPPORTED: 0,
                ClaimStatus.FAILED: 0,
                ClaimStatus.UNRESOLVED: 0,
                ClaimStatus.NOT_RUN: 0,
            }
            for c in claims:
                counts[c.status] = counts.get(c.status, 0) + 1

            return VerificationLedgerSummary(
                total_claims=len(claims),
                verified_count=counts[ClaimStatus.VERIFIED],
                supported_count=counts[ClaimStatus.SUPPORTED],
                failed_count=counts[ClaimStatus.FAILED],
                unresolved_count=counts[ClaimStatus.UNRESOLVED],
                not_run_count=counts[ClaimStatus.NOT_RUN],
                claims=claims,
                evidence=evidence,
            )


class BenchmarkRepository:
    @staticmethod
    def save_benchmark(benchmark_id: str, created_at: str, data: Dict[str, Any]) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO benchmarks (benchmark_id, created_at, data) VALUES (?, ?, ?)",
                (benchmark_id, created_at, json.dumps(data)),
            )

    @staticmethod
    def get_latest_benchmark() -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM benchmarks ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return json.loads(row["data"])
            return None
