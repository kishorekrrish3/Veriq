"""Integration tests for SQLite persistence and repository operations.
"""

import uuid
from app.storage.repositories import RunRepository, EventRepository, LedgerRepository
from app.schemas.runs import RunStatus
from app.schemas.events import RunEvent, EventType
from app.schemas.evidence import ClaimRecord, EvidenceRecord, ClaimStatus, ClaimCategory


def test_database_run_lifecycle_persistence():
    run_id = f"TEST-DB-{uuid.uuid4().hex[:6]}"
    RunRepository.create_run(
        run_id=run_id,
        task_title="DB Test Task",
        task_description="Testing DB operations",
        status=RunStatus.CREATED,
        execution_mode="replay",
        created_at="2026-10-24T00:00:00Z",
    )

    loaded = RunRepository.get_run(run_id)
    assert loaded is not None
    assert loaded.run_id == run_id
    assert loaded.status == RunStatus.CREATED

    # Update status and diff
    RunRepository.update_run_status(
        run_id=run_id,
        status=RunStatus.COMPLETED,
        duration_seconds=5.2,
        unified_diff="--- a\n+++ b\n",
        changed_files=["calculator.py"],
    )

    updated = RunRepository.get_run(run_id)
    assert updated is not None
    assert updated.status == RunStatus.COMPLETED
    assert updated.duration_seconds == 5.2
    assert updated.changed_files == ["calculator.py"]


def test_database_events_persistence():
    run_id = f"TEST-EVT-{uuid.uuid4().hex[:6]}"
    ev = RunEvent(
        event_id="EVT-01",
        run_id=run_id,
        event_type=EventType.RUN_CREATED,
        timestamp="2026-10-24T00:00:00Z",
        message="Test event",
        data={"key": "value"},
    )
    EventRepository.add_event(ev)

    events = EventRepository.get_events(run_id)
    assert len(events) == 1
    assert events[0].event_id == "EVT-01"
    assert events[0].data == {"key": "value"}
