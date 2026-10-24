"""Pytest shared fixtures and test configuration for VERIQ.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure root directory is on python path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from app.core.config import settings
from app.storage.database import init_database
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes the database schema before tests run."""
    settings.APP_ENV = "testing"
    settings.DATABASE_URL = "sqlite:///./data/test_veriq.db"
    init_database()
    yield
    # Cleanup test db file if exists
    test_db = Path("./data/test_veriq.db")
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass


@pytest.fixture
def api_client():
    """Provides a TestClient for FastAPI endpoints."""
    return TestClient(app)
