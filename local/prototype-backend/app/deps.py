"""FastAPI dependencies for step 2.

A dependency is a function FastAPI runs before an endpoint. If it raises an HTTPException the
endpoint never runs. Writing `user: UserRow = Depends(current_user)` on an endpoint means
"only logged-in people get in, and tell me who they are".
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import auth
from app.config import settings
from app.db import UserRow

# Reads the "Authorization: Bearer <token>" header. auto_error=False lets us write our own message.
_bearer = HTTPBearer(auto_error=False)

NOT_LOGGED_IN = "Please log in first."


def current_token(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=NOT_LOGGED_IN,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def current_user(token: str = Depends(current_token)) -> UserRow:
    user = auth.user_for_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your login has ended. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: UserRow = Depends(current_user)) -> UserRow:
    if user.role != auth.ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only an admin can see this.")
    return user


def can_see(owner_id: int, user: UserRow) -> bool:
    """Owners see their own projects; admins see everyone's."""
    return user.role == auth.ROLE_ADMIN or owner_id == user.id


def check_daily_limit(user: UserRow, kind: str) -> None:
    """Stops one person spending the whole OpenAI budget. Admins are not limited.
    Note: check-then-record is not atomic, so two requests at the same instant could go one over."""
    if user.role == auth.ROLE_ADMIN:
        return
    used = auth.requests_in_last_day(user.id)
    if used >= settings.daily_request_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have used today's {settings.daily_request_limit} requests. Please try again tomorrow.",
        )
    auth.record_usage(user.id, kind)
