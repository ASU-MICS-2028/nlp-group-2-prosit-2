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

# A project whose test never ends.
ENDLESS_PROJECT = {
    "test_loop.py": "def test_forever():\n    while True:\n        pass\n",
}


def test_endless_project_is_stopped_by_the_timeout() -> None:
    result = run_tests(ENDLESS_PROJECT, timeout_seconds=2)
    assert result.passed is False
    assert result.timed_out is True


# A project that tries to write a file outside the throwaway folder.
SNEAKY_PROJECT = {
    "../escaped.py": "print('I escaped!')\n",
}


def test_file_name_that_leaves_the_folder_is_refused() -> None:
    result = run_tests(SNEAKY_PROJECT)
    assert result.passed is False
    assert "Unsafe file name" in result.output