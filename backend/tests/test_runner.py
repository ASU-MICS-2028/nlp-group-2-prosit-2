"""Tests for the sandbox runner (W-2)."""
import pytest

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


# A project with files inside sub-folders, like a real API project.
FOLDERS_PROJECT = {
    "app/maths.py": "def add(a, b):\n    return a + b\n",
    "tests/test_maths.py": "from app.maths import add\n\n\ndef test_add():\n    assert add(1, 1) == 2\n",
}


def test_files_in_sub_folders_work() -> None:
    result = run_tests(FOLDERS_PROJECT)
    assert result.passed is True

#test too big
def test_too_big_project_is_refused() -> None:
    huge_file = "x = 1\n" * 100_000  # about 600,000 characters
    result = run_tests({"big.py": huge_file})
    assert result.passed is False
    assert "too big" in result.output

# A project whose test tries to print our secret key.
SPY_PROJECT = {
    # It fails on purpose: pytest only shows what a test printed when the test fails.
    "test_spy.py": "import os\n\n\ndef test_spy():\n    print(os.environ.get('GEMINI_API_KEY'))\n    assert False\n",
}


def test_secret_keys_are_hidden_from_ai_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-secret-123")
    result = run_tests(SPY_PROJECT)
    assert "fake-secret-123" not in result.output

# A project whose test prints a huge amount of text.
NOISY_PROJECT = {
    "test_noisy.py": "def test_noisy():\n    print('x' * 5_000_000)\n    assert False\n",
}


def test_long_output_is_trimmed() -> None:
    result = run_tests(NOISY_PROJECT)
    assert len(result.output) <= 20_000


# A project whose setup file is broken, so pytest crashes before running any test.
# (conftest.py is a special file pytest always loads first.)
BROKEN_SETUP_PROJECT = {
    "conftest.py": "raise RuntimeError('broken setup')\n",
    "test_a.py": "def test_a():\n    pass\n",
}


def test_crash_message_is_kept() -> None:
    result = run_tests(BROKEN_SETUP_PROJECT)
    assert result.passed is False
    # The reason for the crash must reach the AI, so it can fix it.
    assert "broken setup" in result.output
