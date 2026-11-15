"""Files added to every take-home zip (task F-6), so a person can run their API without us.

The files are kept here as plain files (Dockerfile, docker-compose.yml, HOW_TO_RUN.md), so the team can
read and review them. backend/projects.py puts them into the zip next to the project the agent wrote.
They match the fixed project layout in agent/prompts/builder.md: requirements.txt and app/main.py with `app`.
"""

from pathlib import Path

TAKEHOME_FOLDER = Path(__file__).parent

# The files added to every zip, under these names. "docker compose up" is the contract's run_command.
# .dockerignore keeps a local .venv or app.db out of the container.
TAKEHOME_NAMES = ("Dockerfile", "docker-compose.yml", ".dockerignore", "HOW_TO_RUN.md")


def takehome_files() -> dict[str, str]:
    """Return {file name: file text} for the files that go into every take-home zip."""
    return {name: (TAKEHOME_FOLDER / name).read_text(encoding="utf-8") for name in TAKEHOME_NAMES}
