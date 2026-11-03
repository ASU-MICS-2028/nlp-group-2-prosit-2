"""Sandbox runner (W-2): run an AI-written project's tests in a throwaway folder."""

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# The most text (all files added together) we accept. A real generated project is far smaller.
MAX_TOTAL_CHARACTERS = 200_000


@dataclass
class RunResult:
    passed: bool  # True only if every test passed
    output: str  # what pytest printed, so we can see why something failed
    timed_out: bool  # True if we had to stop pytest because it took too long


def is_inside(folder: Path, name: str) -> bool:
    # resolve() works out where the path really ends up, so tricks like "../" are undone.
    target = (folder / name).resolve()
    return target.is_relative_to(folder.resolve())


def run_tests(files: dict[str, str], timeout_seconds: int = 30) -> RunResult:
    total = sum(len(content) for content in files.values())
    if total > MAX_TOTAL_CHARACTERS:
        return RunResult(passed=False, output=f"Project is too big: {total} characters", timed_out=False)

    # The folder is deleted automatically when the "with" block ends, even if something goes wrong.
    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)

        for name, content in files.items():
            if not is_inside(folder, name):
                return RunResult(passed=False, output=f"Unsafe file name: {name}", timed_out=False)
            target = folder / name
            # Make any missing folders first (e.g. "app/" for "app/main.py"). exist_ok: fine if it's already there.
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

        try:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],  # sys.executable = the same Python running us (the venv one)
                cwd=folder,  # run inside the throwaway folder
                capture_output=True,  # keep what pytest prints instead of showing it on screen
                text=True,  # give us the output as text, not raw bytes
                timeout=timeout_seconds,  # stop pytest if it runs longer than this
            )
        except subprocess.TimeoutExpired:
            # subprocess.run has already stopped pytest; we only need to report it.
            message = f"Tests took longer than {timeout_seconds} seconds and were stopped."
            return RunResult(passed=False, output=message, timed_out=True)

    # pytest finishes with code 0 only when all tests passed.
    return RunResult(passed=completed.returncode == 0, output=completed.stdout, timed_out=False)
