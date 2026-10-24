"""SQLite database layer for VERIQ.
Provides persistent storage for runs, events, ledger claims, evidence, and benchmarks.
"""

import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from app.core.config import settings
from app.core.logging import logger


def get_db_path() -> Path:
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        raw_path = db_url.replace("sqlite:///", "")
        p = Path(raw_path)
    else:
        p = Path(settings.DATA_DIR) / "veriq.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Provides a transactional SQLite database connection."""
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Creates database tables and indexes if they do not exist."""
    db_path = get_db_path()
    logger.info(f"Initializing VERIQ database at {db_path}")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                task_title TEXT NOT NULL,
                task_description TEXT NOT NULL,
                status TEXT NOT NULL,
                execution_mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                duration_seconds REAL DEFAULT 0.0,
                unified_diff TEXT,
                changed_files TEXT,
                routing_history TEXT,
                final_outcome TEXT,
                error_message TEXT
            )
        """)

        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_run_id ON events (run_id)")

        # Ledger Claims table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_ids TEXT NOT NULL,
                file_refs TEXT NOT NULL,
                limitations TEXT NOT NULL,
                unresolved_questions TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (claim_id, run_id),
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_run_id ON claims (run_id)")

        # Evidence table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                check_type TEXT NOT NULL,
                status TEXT NOT NULL,
                command TEXT,
                exit_code INTEGER,
                duration_ms REAL DEFAULT 0.0,
                stdout TEXT,
                stderr TEXT,
                file_ref TEXT,
                line_ref INTEGER,
                details TEXT,
                limitations TEXT,
                timestamp TEXT NOT NULL,
                PRIMARY KEY (evidence_id, run_id),
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_run_id ON evidence (run_id)")

        # Benchmarks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmarks (
                benchmark_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)

        # Users table (Google OAuth & local accounts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                picture TEXT,
                provider TEXT NOT NULL,
                role TEXT DEFAULT 'developer',
                created_at TEXT NOT NULL,
                last_login TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id)")
