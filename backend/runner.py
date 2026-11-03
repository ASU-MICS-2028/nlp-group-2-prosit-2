"""Sandbox runner (W-2): run an AI-written project's tests in a throwaway folder."""

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    passed: bool  # True only if every test passed
    output: str  # what pytest printed, so we can see why something failed


def run_tests(files: dict[str, str]) -> RunResult:
    # The folder is deleted automatically when the "with" block ends, even if something goes wrong.
    with tempfile.TemporaryDirectory() as folder:
        for name, content in files.items():
            (Path(folder) / name).write_text(content)

        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],  # sys.executable = the same Python running us (the venv one)
            cwd=folder,  # run inside the throwaway folder
            capture_output=True,  # keep what pytest prints instead of showing it on screen
            text=True,  # give us the output as text, not raw bytes
        )

    # pytest finishes with code 0 only when all tests passed.
    return RunResult(passed=completed.returncode == 0, output=completed.stdout)
