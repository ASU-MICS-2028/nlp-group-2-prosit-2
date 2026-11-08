"""Tests for the agent's tools (W-1). The runner is faked except in the last two tests."""

import pytest

from agent import tools
from backend.runner import RunResult


@pytest.fixture
def workspace():
    return tools.Workspace()


def get_tools(workspace):
    write_file, read_file, list_files, run_tests = tools.make_tools(workspace)
    return write_file, read_file, list_files, run_tests


# --- file names -------------------------------------------------------------


@pytest.mark.parametrize("name", ["app/main.py", "main.py", " tests/test_a.py "])
def test_normal_names_are_allowed(name):
    assert tools.clean_path(name) == name.strip()


@pytest.mark.parametrize("name", ["", "   ", "../secret.py", "app/../../x.py", "/etc/passwd", "./a.py", "app\\main.py", "C:/x.py"])
def test_unsafe_names_are_refused(name):
    assert tools.clean_path(name) is None


# --- write_file / read_file / list_files ------------------------------------


def test_write_then_read_gives_the_same_text(workspace):
    write_file, read_file, _, _ = get_tools(workspace)

    assert write_file("app/main.py", "print('hi')")["status"] == "ok"
    assert read_file("app/main.py") == {"status": "ok", "path": "app/main.py", "content": "print('hi')"}


def test_writing_again_replaces_the_file(workspace):
    write_file, read_file, _, _ = get_tools(workspace)
    write_file("a.py", "old")
    write_file("a.py", "new")

    assert read_file("a.py")["content"] == "new"
    assert len(workspace.files) == 1


def test_unsafe_write_is_an_error_and_writes_nothing(workspace):
    write_file, _, _, _ = get_tools(workspace)

    result = write_file("../escape.py", "x")

    assert result["status"] == "error"
    assert workspace.files == {}


def test_too_long_file_is_refused(workspace):
    write_file, _, _, _ = get_tools(workspace)

    result = write_file("big.py", "a" * (tools.MAX_FILE_CHARACTERS + 1))

    assert result["status"] == "error"
    assert "too long" in result["message"]


def test_too_many_files_is_refused_but_replacing_still_works(workspace):
    write_file, _, _, _ = get_tools(workspace)
    for number in range(tools.MAX_FILES):
        write_file(f"f{number}.py", "x")

    assert write_file("one_more.py", "x")["status"] == "error"
    assert write_file("f0.py", "changed")["status"] == "ok"


def test_reading_a_missing_file_is_an_error(workspace):
    _, read_file, _, _ = get_tools(workspace)

    assert read_file("nope.py")["status"] == "error"


def test_reading_a_file_longer_than_test_output_gives_the_whole_file(workspace):
    # A file is not cut like test output: the model must see it from the first line.
    write_file, read_file, _, _ = get_tools(workspace)
    text = "import os\n" + "a" * (tools.MAX_RESULT_CHARACTERS + 500)
    write_file("app/main.py", text)

    assert read_file("app/main.py")["content"] == text


def test_reading_a_file_too_long_to_send_is_an_error_not_a_part(workspace):
    write_file, read_file, _, _ = get_tools(workspace)
    write_file("big.py", "a" * (tools.MAX_READ_CHARACTERS + 1))

    result = read_file("big.py")

    assert result["status"] == "error"
    assert "content" not in result


def test_list_files_is_sorted(workspace):
    write_file, _, list_files, _ = get_tools(workspace)
    write_file("b.py", "")
    write_file("a.py", "")

    assert list_files() == {"status": "ok", "files": ["a.py", "b.py"]}


def test_each_project_has_its_own_files():
    first, second = tools.Workspace(), tools.Workspace()
    write_first = get_tools(first)[0]
    write_first("a.py", "x")

    assert second.files == {}


# --- run_tests --------------------------------------------------------------


def test_run_tests_with_no_files_is_an_error(workspace):
    *_, run_tests = get_tools(workspace)

    assert run_tests()["status"] == "error"
    assert workspace.test_runs == 0


def test_run_tests_passes_the_files_and_reports_the_result(workspace, monkeypatch):
    seen = {}

    def fake_runner(files, timeout_seconds):
        seen["files"] = dict(files)
        return RunResult(passed=True, output="2 passed", timed_out=False)

    monkeypatch.setattr(tools.runner, "run_tests", fake_runner)
    write_file, *_, run_tests = get_tools(workspace)
    write_file("a.py", "x")

    result = run_tests()

    assert result == {"status": "ok", "passed": True, "timed_out": False, "output": "2 passed"}
    assert seen["files"] == {"a.py": "x"}
    assert workspace.test_runs == 1


def test_long_test_output_keeps_the_end(workspace, monkeypatch):
    long_output = "x" * 10_000 + "1 failed"
    monkeypatch.setattr(tools.runner, "run_tests", lambda files, timeout_seconds: RunResult(False, long_output, False))
    write_file, *_, run_tests = get_tools(workspace)
    write_file("a.py", "x")

    output = run_tests()["output"]

    assert output.endswith("1 failed")
    assert len(output) < tools.MAX_RESULT_CHARACTERS + 50


def test_a_crashing_runner_becomes_an_error_message(workspace, monkeypatch):
    def broken_runner(files, timeout_seconds):
        raise OSError("disk full")

    monkeypatch.setattr(tools.runner, "run_tests", broken_runner)
    write_file, *_, run_tests = get_tools(workspace)
    write_file("a.py", "x")

    result = run_tests()

    assert result["status"] == "error"
    assert "disk full" not in result["message"]  # internal details are not sent to the model


def test_timeout_is_reported(workspace, monkeypatch):
    monkeypatch.setattr(
        tools.runner, "run_tests", lambda files, timeout_seconds: RunResult(False, "stopped", True)
    )
    write_file, *_, run_tests = get_tools(workspace)
    write_file("a.py", "x")

    assert run_tests()["timed_out"] is True


# --- with the real sandbox runner -------------------------------------------


def test_real_runner_passing_project(workspace):
    write_file, *_, run_tests = get_tools(workspace)
    write_file("calc.py", "def add(a, b):\n    return a + b\n")
    write_file("test_calc.py", "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")

    result = run_tests()

    assert result["passed"] is True


def test_real_runner_failing_project_shows_why(workspace):
    write_file, *_, run_tests = get_tools(workspace)
    write_file("calc.py", "def add(a, b):\n    return a - b\n")
    write_file("test_calc.py", "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n")

    result = run_tests()

    assert result["passed"] is False
    assert "test_add" in result["output"]
