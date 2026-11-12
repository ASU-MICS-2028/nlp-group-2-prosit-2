"""Save the backend's OpenAPI schema (its self-description) to a file.

The frontend's API types are generated from this file (task W-6, decision D-001).
Run it through `npm run api:generate` from the frontend folder, with the backend's
virtual environment switched on. It does not start the server: FastAPI can describe
itself without running.
"""

import json
import sys
from pathlib import Path

# This file is frontend/scripts/export_openapi.py, so the repo root is two folders up.
# Python needs the repo root on its path to find the `backend` package.
REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPO_ROOT / "frontend" / "src" / "api" / "openapi.json"


def main() -> None:
    sys.path.insert(0, str(REPO_ROOT))
    from backend.main import app  # imported here so the path above is set first

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # indent=2 keeps the file readable and makes git show small, clear changes.
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
