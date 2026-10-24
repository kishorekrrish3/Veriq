"""Authentication and Session Repository for VERIQ.
Manages users, Google OAuth identities, and session tokens in SQLite.
"""

import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from app.storage.database import get_db_connection
from app.core.logging import logger


def create_or_update_user(
    user_id: str,
    email: str,
    name: str,
    picture: Optional[str] = None,
    provider: str = "google",
    role: str = "developer",
) -> Dict[str, Any]:
    """Upserts a user into the database."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (user_id, email, name, picture, provider, role, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                picture = excluded.picture,
                last_login = excluded.last_login
            """,
            (user_id, email, name, picture or "", provider, role, now, now),
        )
        return {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture or "",
            "provider": provider,
            "role": role,
            "created_at": now,
            "last_login": now,
        }


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user by their unique identifier."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user by email."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_session(user_id: str, duration_days: int = 14) -> str:
    """Generates a secure random session token and stores it in SQLite."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=duration_days)).isoformat()
    now_str = now.isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, now_str, expires_at),
        )
    return token


def get_user_by_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Validates session token and returns the associated user if not expired."""
    if not token:
        return None

    now_str = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT u.*, s.expires_at 
            FROM sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.token = ? AND s.expires_at > ?
            """,
            (token, now_str),
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        user_dict = dict(row)
        user_dict.pop("expires_at", None)
        return user_dict


def delete_session(token: str) -> bool:
    """Deletes a session token on logout."""
    if not token:
        return False
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return cursor.rowcount > 0
