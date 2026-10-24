"""Unit tests for AST Syntax verification.
"""

from app.services.verification import verification_engine
from app.schemas.evidence import ClaimStatus


def test_ast_checker_valid_syntax():
    code = "def calculate_sum(a: int, b: int) -> int:\n    return a + b\n"
    ev = verification_engine.verify_ast_syntax("C-01", "math_utils.py", code)
    assert ev.status == ClaimStatus.VERIFIED
    assert ev.exit_code == 0
    assert "AST parse successful" in (ev.stdout or "")


def test_ast_checker_syntax_error():
    broken_code = "def invalid_syntax(a\n    return a\n"
    ev = verification_engine.verify_ast_syntax("C-02", "math_utils.py", broken_code)
    assert ev.status == ClaimStatus.FAILED
    assert ev.exit_code == 1
    assert "SyntaxError" in (ev.stderr or "")
