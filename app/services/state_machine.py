"""Explicit Run State Machine for VERIQ.
Enforces valid state transitions and lifecycle invariants.
"""

from typing import Set, Dict
from app.schemas.runs import RunStatus
from app.core.errors import VeriqError


class InvalidStateTransitionError(VeriqError):
    """Raised when an invalid state machine transition is attempted."""
    pass


ALLOWED_TRANSITIONS: Dict[RunStatus, Set[RunStatus]] = {
    RunStatus.CREATED: {
        RunStatus.RESEARCHING,
        RunStatus.PLANNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.RESEARCHING: {
        RunStatus.PLANNING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.PLANNING: {
        RunStatus.GENERATING_PATCH,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.GENERATING_PATCH: {
        RunStatus.VALIDATING_PATCH,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.VALIDATING_PATCH: {
        RunStatus.EXECUTING_CHECKS,
        RunStatus.REPAIRING,
        RunStatus.FAILED,
        RunStatus.VERIFICATION_FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.EXECUTING_CHECKS: {
        RunStatus.REPAIRING,
        RunStatus.FINALIZING,
        RunStatus.VERIFICATION_FAILED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.REPAIRING: {
        RunStatus.GENERATING_PATCH,
        RunStatus.VALIDATING_PATCH,
        RunStatus.EXECUTING_CHECKS,
        RunStatus.FINALIZING,
        RunStatus.FAILED,
        RunStatus.VERIFICATION_FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.FINALIZING: {
        RunStatus.COMPLETED,
        RunStatus.VERIFICATION_FAILED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
    RunStatus.VERIFICATION_FAILED: set(),
}


class RunStateMachine:
    def __init__(self, initial_state: RunStatus = RunStatus.CREATED):
        self.current_state = initial_state

    def can_transition_to(self, new_state: RunStatus) -> bool:
        return new_state in ALLOWED_TRANSITIONS.get(self.current_state, set())

    def transition_to(self, new_state: RunStatus) -> None:
        if not self.can_transition_to(new_state):
            raise InvalidStateTransitionError(
                f"Illegal state transition from {self.current_state.value} to {new_state.value}."
            )
        self.current_state = new_state
