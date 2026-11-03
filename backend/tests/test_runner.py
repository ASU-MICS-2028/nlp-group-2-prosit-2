"""Tests for the sandbox runner (W-2)."""

from backend.runner import run_tests

# A tiny "AI-written project": one file whose test passes.
PASSING_PROJECT = {
    "test_math.py": "def test_add():\n    assert 1 + 1 == 2\n",
}

# The same project, but the test is wrong, so it fails.
FAILING_PROJECT = {
    "test_math.py": "def test_add():\n    assert 1 + 1 == 3\n",
}


def test_passing_project_is_reported_as_passed() -> None:
    result = run_tests(PASSING_PROJECT)
    assert result.passed is True


def test_failing_project_is_reported_as_failed() -> None:
    result = run_tests(FAILING_PROJECT)
    assert result.passed is False
