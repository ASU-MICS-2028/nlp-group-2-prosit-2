"""Tools the ADK agent can call while it builds a project (task W-1).

The language model cannot touch files or run code by itself. It can only ask
for one of these tools by name. ADK then runs the plain Python function and
sends the returned dictionary back to the model.

Each project gets its own `Workspace`: the files the agent has written so far,
kept in a dictionary {file name: file text}. Nothing is written to our disk;
`run_tests` hands the dictionary to the sandbox runner (backend/runner.py),
which copies it into a throwaway folder and runs pytest there.

Every tool returns {"status": "ok", ...} or {"status": "error", "message": ...}.
Tools never raise, so a mistake by the model becomes a message it can read and
fix, instead of crashing the build.
"""

from dataclasses import dataclass, field
from pathlib import PurePosixPath

from backend import runner

MAX_FILES = 30  # a generated project is about 10 files; more means the model is looping
MAX_FILE_CHARACTERS = 50_000  # one file larger than this is almost surely a mistake
MAX_RESULT_CHARACTERS = 4_000  # longest test output we send back to the model (saves free-tier quota)
MAX_READ_CHARACTERS = 20_000  # longest file read_file returns whole; the model must see a file from its first line
TEST_TIMEOUT_SECONDS = 30


@dataclass
class Workspace:
    """Everything one project's agent has written, plus how often it ran the tests."""

    files: dict[str, str] = field(default_factory=dict)
    test_runs: int = 0  # the build loop (W-3) uses this to stop after too many tries


def clean_path(path: str) -> str | None:
    """Return a safe relative file name like "app/main.py", or None if the name is not allowed."""
    path = path.strip()
    if not path or "\\" in path or ":" in path:  # empty, or a Windows-style path like "C:/x"
        return None
    parts = path.split("/")
    # No absolute paths ("/etc/passwd"), no climbing out ("../x"), no "./" or "a//b" tricks.
    if path.startswith("/") or any(part in ("", "..", ".") for part in parts):
        return None
    return str(PurePosixPath(path))


def keep_end(text: str, limit: int = MAX_RESULT_CHARACTERS) -> str:
    """Trim long text to its last `limit` characters. pytest prints its summary at the end."""
    if len(text) <= limit:
        return text
    return "[earlier output cut]\n" + text[-limit:]


def error(message: str) -> dict:
    return {"status": "error", "message": message}


def make_tools(workspace: Workspace) -> list:
    """Make the tool functions for one project. Give the returned list to the ADK Agent as `tools=`.

    The functions are created inside this function so each one already knows
    its project's workspace; the model never has to pass it in.
    ADK reads each function's name, type hints and docstring to tell the model how to call it.
    """

    def write_file(path: str, content: str) -> dict:
        """Create or replace one text file in the project.

        Args:
            path: file name relative to the project folder, for example "app/main.py" or "tests/test_books.py".
            content: the complete text of the file (not just the changed part).
        """
        name = clean_path(path)
        if name is None:
            return error(f"'{path}' is not an allowed file name. Use a relative name like 'app/main.py'.")
        if len(content) > MAX_FILE_CHARACTERS:
            return error(f"The file is too long ({len(content)} characters; the limit is {MAX_FILE_CHARACTERS}).")
        if name not in workspace.files and len(workspace.files) >= MAX_FILES:
            return error(f"The project already has {MAX_FILES} files, the maximum.")
        workspace.files[name] = content
        return {"status": "ok", "path": name, "characters": len(content)}

    def read_file(path: str) -> dict:
        """Read one file of the project, for example to check it before fixing a failing test.

        Args:
            path: file name relative to the project folder, for example "app/main.py".
        """
        name = clean_path(path)
        if name is None or name not in workspace.files:
            return error(f"There is no file '{path}'. Call list_files to see the files.")
        content = workspace.files[name]
        if len(content) > MAX_READ_CHARACTERS:
            # Never send part of a file: the model would rewrite it without the missing part.
            return error(f"'{name}' is too long to read ({len(content)} characters). Write it again in smaller files.")
        return {"status": "ok", "path": name, "content": content}

    def list_files() -> dict:
        """List the names of all files written so far."""
        return {"status": "ok", "files": sorted(workspace.files)}

    def run_tests() -> dict:
        """Run the project's pytest tests in a safe throwaway folder and report the result.

        Call this after writing the code and the tests. If tests fail, read the output,
        fix the files with write_file, and run the tests again.
        """
        if not workspace.files:
            return error("There are no files yet. Write the code and its tests first.")
        workspace.test_runs += 1
        try:
            result = runner.run_tests(workspace.files, timeout_seconds=TEST_TIMEOUT_SECONDS)
        except Exception:  # a bug in the runner must not crash the build
            return error("The test runner itself failed. This is not your code's fault.")
        return {
            "status": "ok",
            "passed": result.passed,
            "timed_out": result.timed_out,
            "output": keep_end(result.output),
        }

    return [write_file, read_file, list_files, run_tests]
