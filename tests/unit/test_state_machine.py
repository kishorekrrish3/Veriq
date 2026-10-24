"""Unit tests for RunStateMachine transitions.
"""

import pytest
from app.schemas.runs import RunStatus
from app.services.state_machine import RunStateMachine, InvalidStateTransitionError


def test_valid_state_machine_flow():
    sm = RunStateMachine()
    assert sm.current_state == RunStatus.CREATED

    sm.transition_to(RunStatus.RESEARCHING)
    assert sm.current_state == RunStatus.RESEARCHING

    sm.transition_to(RunStatus.PLANNING)
    assert sm.current_state == RunStatus.PLANNING

    sm.transition_to(RunStatus.GENERATING_PATCH)
    assert sm.current_state == RunStatus.GENERATING_PATCH

    sm.transition_to(RunStatus.VALIDATING_PATCH)
    assert sm.current_state == RunStatus.VALIDATING_PATCH

    sm.transition_to(RunStatus.EXECUTING_CHECKS)
    assert sm.current_state == RunStatus.EXECUTING_CHECKS

    sm.transition_to(RunStatus.FINALIZING)
    assert sm.current_state == RunStatus.FINALIZING

    sm.transition_to(RunStatus.COMPLETED)
    assert sm.current_state == RunStatus.COMPLETED


def test_invalid_state_transition_raises():
    sm = RunStateMachine(RunStatus.CREATED)
    # Jumping directly from CREATED to COMPLETED is forbidden
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(RunStatus.COMPLETED)


def test_terminal_states_cannot_transition():
    sm = RunStateMachine(RunStatus.COMPLETED)
    with pytest.raises(InvalidStateTransitionError):
        sm.transition_to(RunStatus.PLANNING)
