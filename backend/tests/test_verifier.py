"""Tests for the verifier service (app/services/verifier.py)."""

from __future__ import annotations

import pytest

from app.services.verifier import Verifier, get_verifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sandbox_result(
    test_passed: bool = True,
    test_count: int = 0,
    test_results: list[dict] | None = None,
    stdout: str = "",
    stderr: str = "",
) -> dict:
    """Build a minimal sandbox_result dict for Verifier.score()."""
    return {
        "test_passed": test_passed,
        "test_count": test_count,
        "test_results": test_results or [],
        "stdout": stdout,
        "stderr": stderr,
    }


@pytest.fixture
def verifier() -> Verifier:
    return Verifier()


# ===========================================================================
# Score range guarantee
# ===========================================================================


def test_score_range_perfect(verifier: Verifier):
    """All-pass sandbox result yields a score between 0 and 100 (inclusive)."""
    result = verifier.score(_sandbox_result(test_passed=True))
    assert 0 <= result["score"] <= 100


def test_score_range_zero(verifier: Verifier):
    """All-fail sandbox result still yields a score between 0 and 100."""
    result = verifier.score(_sandbox_result(test_passed=False, stderr="error error error error"))
    assert 0 <= result["score"] <= 100


@pytest.mark.parametrize(
    "test_passed, test_count, passed_count",
    [
        (True, 10, 10),
        (False, 10, 0),
        (True, 4, 3),
        (False, 0, 0),
    ],
)
def test_score_always_in_range(
    verifier: Verifier, test_passed: bool, test_count: int, passed_count: int
):
    """Score is always between 0 and 100 regardless of input combination."""
    test_results = [
        {"status": "passed" if i < passed_count else "failed"}
        for i in range(test_count)
    ]
    sr = _sandbox_result(
        test_passed=test_passed,
        test_count=test_count,
        test_results=test_results,
    )
    result = verifier.score(sr)
    assert 0 <= result["score"] <= 100


# ===========================================================================
# Perfect / zero score
# ===========================================================================


def test_perfect_score(verifier: Verifier):
    """All components passing gives a high score (≥ 70)."""
    sr = _sandbox_result(
        test_passed=True,
        test_count=5,
        test_results=[{"status": "passed"}] * 5,
        stdout="coverage: 85%",
        stderr="",
    )
    result = verifier.score(sr)
    assert result["score"] >= 70


def test_zero_score_approximately(verifier: Verifier):
    """All components failing gives a low score (≤ 30)."""
    sr = _sandbox_result(
        test_passed=False,
        test_count=5,
        test_results=[{"status": "failed"}] * 5,
        stdout="",
        stderr="error error error error error",
    )
    result = verifier.score(sr)
    assert result["score"] <= 30


# ===========================================================================
# Reproducer weight (0.40)
# ===========================================================================


def test_reproducer_weight_impact(verifier: Verifier):
    """test_passed=True vs False changes the score by approximately 40 points."""
    passed = verifier.score(_sandbox_result(test_passed=True, test_count=0))
    failed = verifier.score(_sandbox_result(test_passed=False, test_count=0))
    diff = passed["score"] - failed["score"]
    # Reproducer is 40% weight; with all other components equal, diff ~ 40
    assert 30 <= diff <= 50


# ===========================================================================
# Heuristic risk penalty
# ===========================================================================


def test_heuristic_penalty_eval(verifier: Verifier):
    """Code containing eval() in output lowers the heuristic_risk_penalty score."""
    clean = verifier.score(_sandbox_result(stdout="all good"))
    risky = verifier.score(_sandbox_result(stdout="eval(user_input)"))

    clean_risk = next(
        e["score"] for e in clean["evidence"] if e["component"] == "heuristic_risk_penalty"
    )
    risky_risk = next(
        e["score"] for e in risky["evidence"] if e["component"] == "heuristic_risk_penalty"
    )
    assert risky_risk < clean_risk


def test_heuristic_penalty_exec(verifier: Verifier):
    """exec() in output is penalised."""
    sr = _sandbox_result(stdout="exec(code_string)")
    result = verifier.score(sr)
    risk_evidence = next(
        e for e in result["evidence"] if e["component"] == "heuristic_risk_penalty"
    )
    assert risk_evidence["score"] < 100


def test_heuristic_penalty_multiple_hits(verifier: Verifier):
    """Multiple risk patterns compound the penalty (floor at 0)."""
    sr = _sandbox_result(
        stdout="eval(x) exec(y) os.system('rm') subprocess.call(['ls']) credentials password="
    )
    result = verifier.score(sr)
    risk_evidence = next(
        e for e in result["evidence"] if e["component"] == "heuristic_risk_penalty"
    )
    assert risk_evidence["score"] == 0


# ===========================================================================
# Unit test pass rate
# ===========================================================================


def test_partial_test_pass_rate(verifier: Verifier):
    """75% test pass rate yields a unit_test_pass_rate score of 75."""
    test_results = [
        {"status": "passed"},
        {"status": "passed"},
        {"status": "passed"},
        {"status": "failed"},
    ]
    sr = _sandbox_result(
        test_passed=False,
        test_count=4,
        test_results=test_results,
    )
    result = verifier.score(sr)
    utp = next(
        e for e in result["evidence"] if e["component"] == "unit_test_pass_rate"
    )
    assert utp["score"] == 75


def test_no_tests_neutral_score(verifier: Verifier):
    """When test_count == 0, unit_test_pass_rate is 50 (neutral)."""
    sr = _sandbox_result(test_passed=False, test_count=0)
    result = verifier.score(sr)
    utp = next(
        e for e in result["evidence"] if e["component"] == "unit_test_pass_rate"
    )
    assert utp["score"] == 50


# ===========================================================================
# Evidence structure
# ===========================================================================


def test_evidence_returned(verifier: Verifier):
    """score() returns an evidence list with one entry per component."""
    sr = _sandbox_result()
    result = verifier.score(sr)

    assert "evidence" in result
    assert isinstance(result["evidence"], list)
    assert len(result["evidence"]) >= 4

    for item in result["evidence"]:
        assert "component" in item
        assert "score" in item
        assert "weight" in item
        assert "details" in item


def test_evidence_weights_sum_to_one(verifier: Verifier):
    """The weights of all evidence components sum to approximately 1.0."""
    result = verifier.score(_sandbox_result())
    total_weight = sum(e["weight"] for e in result["evidence"])
    assert abs(total_weight - 1.0) < 0.01


# ===========================================================================
# Coverage parsing
# ===========================================================================


def test_coverage_high_score(verifier: Verifier):
    """Output reporting ≥ 80% coverage → coverage_delta score of 80."""
    sr = _sandbox_result(stdout="TOTAL   1234   200   84%")
    result = verifier.score(sr)
    cov = next(e for e in result["evidence"] if e["component"] == "coverage_delta")
    assert cov["score"] == 80


def test_coverage_medium_score(verifier: Verifier):
    """Output reporting 60-79% coverage → coverage_delta score of 60."""
    sr = _sandbox_result(stdout="TOTAL   500   200   70%")
    result = verifier.score(sr)
    cov = next(e for e in result["evidence"] if e["component"] == "coverage_delta")
    assert cov["score"] == 60


def test_coverage_no_data(verifier: Verifier):
    """No coverage percentage in output → neutral coverage_delta score of 50."""
    sr = _sandbox_result(stdout="tests passed")
    result = verifier.score(sr)
    cov = next(e for e in result["evidence"] if e["component"] == "coverage_delta")
    assert cov["score"] == 50


# ===========================================================================
# Lint / static analysis
# ===========================================================================


def test_lint_no_errors(verifier: Verifier):
    """No error keywords in stderr → lint_and_static_ok score of 100."""
    sr = _sandbox_result(stderr="")
    result = verifier.score(sr)
    lint = next(e for e in result["evidence"] if e["component"] == "lint_and_static_ok")
    assert lint["score"] == 100


def test_lint_with_errors(verifier: Verifier):
    """Each 'error' keyword in stderr reduces the lint score by 20."""
    # Use 'error' as a standalone word (the regex uses \berror\b)
    sr = _sandbox_result(stderr="error: undefined variable\nerror: type mismatch")
    result = verifier.score(sr)
    lint = next(e for e in result["evidence"] if e["component"] == "lint_and_static_ok")
    assert lint["score"] < 100


# ===========================================================================
# Singleton
# ===========================================================================


def test_get_verifier_singleton():
    """get_verifier() returns the same instance on every call."""
    import app.services.verifier as v_module

    v_module._verifier_instance = None  # reset
    a = get_verifier()
    b = get_verifier()
    assert a is b
