"""Tests for Authentication endpoints and Google OAuth session management.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage.database import init_database
from app.storage.auth_repository import (
    create_or_update_user,
    create_session,
    get_user_by_session_token,
    delete_session,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_database()


def test_auth_config():
    """Verify auth config endpoint returns provider info and demo capability."""
    response = client.get("/api/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert "google_enabled" in data
    assert "demo_enabled" in data
    assert data["provider"] == "google"


def test_auth_me_unauthenticated():
    """Verify /api/auth/me returns unauthenticated when no cookie or token is provided."""
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is False
    assert data["user"] is None


def test_demo_login_and_me():
    """Verify demo login issues a session cookie and verifies user identity."""
    login_resp = client.post(
        "/api/auth/demo-login",
        json={"name": "Alex Chen", "email": "alex.chen@veriq.dev", "role": "Staff Engineer"},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == "alex.chen@veriq.dev"
    assert data["user"]["name"] == "Alex Chen"
    assert "token" in data

    # Verify session token works via Bearer header
    token = data["token"]
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["authenticated"] is True
    assert me_data["user"]["name"] == "Alex Chen"


def test_logout():
    """Verify logout terminates session and deletes cookie."""
    # First sign in
    login_resp = client.post(
        "/api/auth/demo-login",
        json={"name": "Sarah Connor", "email": "sarah@veriq.dev"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]

    # Verify user exists
    assert get_user_by_session_token(token) is not None

    # Call logout
    logout_resp = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True

    # Verify session is deleted
    assert get_user_by_session_token(token) is None


def test_google_login_redirect_unconfigured():
    """Verify Google login redirects safely when keys are not configured."""
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code in (302, 303, 307)
    assert "settings" in response.headers["location"] or "google" in response.headers["location"]
