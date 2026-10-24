"""Authentication API router for VERIQ.
Supports direct Google OAuth 2.0 / OpenID Connect, Google Identity Services,
and instant Demo Google Sign-In with full session management.
"""

from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx
from urllib.parse import urlencode

from app.core.config import settings
from app.core.logging import logger
from app.storage.auth_repository import (
    create_or_update_user,
    get_user_by_session_token,
    delete_session,
    create_session,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class GoogleVerifyRequest(BaseModel):
    credential: str


class DemoLoginRequest(BaseModel):
    name: Optional[str] = "Alex Chen"
    email: Optional[str] = "alex.chen@veriq.dev"
    role: Optional[str] = "Senior Engineer"


def _extract_session_token(request: Request) -> Optional[str]:
    """Extracts session token from cookie or Authorization Bearer header."""
    cookie_token = request.cookies.get("veriq_session")
    if cookie_token:
        return cookie_token

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "").strip()

    return None


@router.get("/config")
async def get_auth_config():
    """Returns the current authentication capabilities and Google client config."""
    return {
        "google_enabled": settings.is_google_auth_configured,
        "google_client_id": settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "demo_enabled": settings.ALLOW_DEMO_LOGIN,
        "provider": "google",
    }


@router.get("/google/login")
async def google_login_redirect():
    """Redirects the browser to Google's official OAuth2 consent screen."""
    if not settings.is_google_auth_configured:
        # If credentials are not configured in .env, redirect to home with friendly notification
        return RedirectResponse(
            url="/?auth_notice=google_keys_missing#settings",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=google_auth_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/google/callback")
async def google_auth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
):
    """Handles Google OAuth2 callback, exchanges authorization code for tokens, and creates session."""
    if error or not code:
        logger.warning(f"Google OAuth callback error: {error}")
        return RedirectResponse(url=f"/?auth_error={error or 'missing_code'}", status_code=303)

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(token_url, data=token_data)
            if token_resp.status_code != 200:
                logger.error(f"Failed to exchange Google OAuth code: {token_resp.text}")
                return RedirectResponse(url="/?auth_error=token_exchange_failed", status_code=303)

            tokens = token_resp.json()
            access_token = tokens.get("access_token")

            # Fetch Google user profile
            user_info_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_info_resp.status_code != 200:
                logger.error(f"Failed to fetch Google userinfo: {user_info_resp.text}")
                return RedirectResponse(url="/?auth_error=userinfo_failed", status_code=303)

            user_info = user_info_resp.json()

        user_id = f"google_{user_info.get('sub')}"
        email = user_info.get("email", "")
        name = user_info.get("name", email.split("@")[0] if email else "Google User")
        picture = user_info.get("picture", "")

        user = create_or_update_user(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture,
            provider="google",
            role="developer",
        )

        session_token = create_session(user_id=user_id)
        logger.info(f"User signed in with Google: {email} (user_id={user_id})")

        response = RedirectResponse(url="/?auth_success=google", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="veriq_session",
            value=session_token,
            max_age=14 * 24 * 3600,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return response

    except Exception as e:
        logger.error(f"Unexpected error in Google OAuth callback: {e}", exc_info=True)
        return RedirectResponse(url="/?auth_error=server_error", status_code=303)


@router.post("/google/verify")
async def google_verify_credential(req: GoogleVerifyRequest, response: Response):
    """Verifies a Google Identity Services (GIS) ID token and logs the user in."""
    id_token = req.credential
    if not id_token:
        raise HTTPException(status_code=400, detail="Missing Google ID token")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tokeninfo_resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            )
            if tokeninfo_resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Google ID token")

            info = tokeninfo_resp.json()

        # Check audience matches our client ID if configured
        if settings.GOOGLE_CLIENT_ID and info.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=401, detail="Token audience does not match configured Google Client ID")

        user_id = f"google_{info.get('sub')}"
        email = info.get("email", "")
        name = info.get("name", "Google User")
        picture = info.get("picture", "")

        user = create_or_update_user(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture,
            provider="google",
            role="developer",
        )
        session_token = create_session(user_id=user_id)

        response.set_cookie(
            key="veriq_session",
            value=session_token,
            max_age=14 * 24 * 3600,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return {"authenticated": True, "user": user, "token": session_token}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying Google ID token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to verify Google token")


@router.post("/demo-login")
async def demo_login(req: DemoLoginRequest, response: Response):
    """Instant 1-click Google Demo Login for evaluation and hackathon testing."""
    if not settings.ALLOW_DEMO_LOGIN:
        raise HTTPException(status_code=403, detail="Demo login is disabled")

    # High-resolution Google Developer Profile avatar
    avatar_url = "https://lh3.googleusercontent.com/a/ACg8ocIS0e4wK8X9hT7eX_W2qJ3kY4Z9=s96-c"
    # Fallback SVG data URI if external image fails
    demo_user_id = f"google_demo_{abs(hash(req.email)) % 10000000}"

    user = create_or_update_user(
        user_id=demo_user_id,
        email=req.email,
        name=req.name,
        picture=avatar_url,
        provider="google",
        role=req.role,
    )
    session_token = create_session(user_id=demo_user_id)

    response.set_cookie(
        key="veriq_session",
        value=session_token,
        max_age=14 * 24 * 3600,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"authenticated": True, "user": user, "token": session_token}


@router.get("/me")
async def get_current_user(request: Request):
    """Returns the authenticated user for the current session."""
    token = _extract_session_token(request)
    if not token:
        return {"authenticated": False, "user": None}

    user = get_user_by_session_token(token)
    if not user:
        return {"authenticated": False, "user": None}

    return {"authenticated": True, "user": user}


@router.post("/logout")
async def logout(request: Request, response: Response):
    """Terminates user session and removes cookie."""
    token = _extract_session_token(request)
    if token:
        delete_session(token)

    response.delete_cookie(key="veriq_session", path="/")
    return {"success": True, "message": "Successfully logged out"}
