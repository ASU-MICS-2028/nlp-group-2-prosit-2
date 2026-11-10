"""Accounts, passwords and login tokens (step 2). Plain functions, no FastAPI here.

Terms:
- Hash: a one-way scramble. We can check a password against it but cannot turn it back.
- Salt: random bytes mixed into each password before hashing, so two equal passwords look different.
- scrypt: a password hash that is slow on purpose, so guessing millions of passwords is expensive.
- Token: a long random string the browser sends instead of the password on every request.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session as DbSession
from sqlmodel import func, select

from app.config import settings
from app.db import TokenRow, UsageRow, UserRow, get_engine

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLES = {ROLE_USER, ROLE_ADMIN}

# scrypt cost settings (the standard library's recommended minimum for interactive logins)
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


class AuthError(ValueError):
    """A problem we can show to the person as-is (plain English)."""


# --------------------------------------------------------------------------- passwords


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    # Store the method, salt and hash together so we can check the password later
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        method, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if method != "scrypt":
        return False
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt_hex), n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    # compare_digest takes the same time whether the first or last byte differs (no timing hints)
    return hmac.compare_digest(digest.hex(), digest_hex)


# --------------------------------------------------------------------------- accounts


def normalise_email(email: str) -> str:
    """Lower-case and trimmed, so 'Ama@Shop.com ' and 'ama@shop.com' are one account."""
    clean = email.strip().lower()
    name, at, domain = clean.partition("@")
    if not at or not name or "." not in domain or " " in clean or len(clean) > 254:
        raise AuthError("Please enter a real email address, like ama@example.com.")
    return clean


def register(email: str, password: str) -> UserRow:
    clean = normalise_email(email)
    user = UserRow(email=clean, password_hash=hash_password(password), role=ROLE_USER)
    with DbSession(get_engine()) as db:
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # The unique rule on email caught a second account, even if two sign-ups raced
            raise AuthError("An account with this email already exists. Try logging in.") from None
        db.refresh(user)
        return user


def find_user(email: str) -> UserRow | None:
    with DbSession(get_engine()) as db:
        return db.exec(select(UserRow).where(UserRow.email == email.strip().lower())).first()


def set_role(email: str, role: str) -> UserRow:
    if role not in ROLES:
        raise AuthError(f"Role must be one of: {', '.join(sorted(ROLES))}.")
    with DbSession(get_engine()) as db:
        user = db.exec(select(UserRow).where(UserRow.email == email.strip().lower())).first()
        if not user:
            raise AuthError(f"No account uses {email}. Ask them to sign up first.")
        user.role = role
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# --------------------------------------------------------------------------- tokens


def _hash_token(token: str) -> str:
    # A fast hash is fine here: tokens are long and random, so they cannot be guessed
    return hashlib.sha256(token.encode()).hexdigest()


def _expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=settings.token_days)).isoformat(timespec="seconds")


def login(email: str, password: str) -> tuple[str, UserRow]:
    user = find_user(email)
    # Same message for "no such email" and "wrong password", so outsiders cannot test which emails exist
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Email or password is wrong.")
    token = secrets.token_urlsafe(32)
    with DbSession(get_engine()) as db:
        db.add(TokenRow(token_hash=_hash_token(token), user_id=user.id, expires_at=_expiry()))
        db.commit()
    return token, user


def user_for_token(token: str) -> UserRow | None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with DbSession(get_engine()) as db:
        row = db.get(TokenRow, _hash_token(token))
        if not row:
            return None
        if row.expires_at <= now:
            db.delete(row)  # tidy up the expired token
            db.commit()
            return None
        return db.get(UserRow, row.user_id)


def logout(token: str) -> None:
    with DbSession(get_engine()) as db:
        row = db.get(TokenRow, _hash_token(token))
        if row:
            db.delete(row)
            db.commit()


# --------------------------------------------------------------------------- daily limit


def requests_in_last_day(user_id: int) -> int:
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
    with DbSession(get_engine()) as db:
        query = select(func.count()).select_from(UsageRow).where(
            UsageRow.user_id == user_id, UsageRow.created_at > since
        )
        return db.exec(query).one()


def record_usage(user_id: int, kind: str) -> None:
    with DbSession(get_engine()) as db:
        db.add(UsageRow(user_id=user_id, kind=kind))
        db.commit()
