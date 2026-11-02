"""Settings read from environment variables, in one place."""

import os

# Browser addresses allowed to call this server (CORS). Comma separated.
# Locally the frontend runs on port 5173 (or 5174 if 5173 is busy).
# In production set ALLOWED_ORIGINS to the Vercel address only.
DEFAULT_ORIGINS = "http://localhost:5173,http://localhost:5174"


def allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
