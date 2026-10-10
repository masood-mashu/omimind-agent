"""
backend/routers/auth.py
Minimal session login/logout endpoints for single-user hackathon deployment.
Issues and clears HttpOnly, SameSite session cookies.
"""
from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from backend.auth import (
    COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    create_session_token,
    get_current_user,
)
from backend.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    secret_key: str = Field(..., description="Configured API Secret Key")


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    """
    Submits the API secret key to obtain a secure HttpOnly session cookie.
    Never exposes API credentials to frontend storage.
    """
    configured_secret = settings.api_secret_key
    if not configured_secret:
        raise HTTPException(status_code=503, detail="API authentication is not configured.")

    # Constant-time comparison
    if not hmac.compare_digest(payload.secret_key, configured_secret):
        raise HTTPException(status_code=401, detail="Invalid API secret key.")

    # Create signed session token for the server-derived default user
    session_token = create_session_token(settings.default_user_id, configured_secret)

    # Secure cookie configuration
    # Production deployments should always issue Secure cookies. The request
    # scheme may be HTTP inside a reverse proxy even when the public URL is HTTPS.
    is_secure = settings.environment.lower() == "production" or request.url.scheme == "https"
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="strict",
        secure=is_secure,
        path="/",
    )
    return {
        "success": True,
        "message": "Authenticated successfully",
        "uid": settings.default_user_id,
    }


@router.post("/logout")
def logout(response: Response) -> dict[str, Any]:
    """Clears the session cookie."""
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/status")
def auth_status(request: Request) -> dict[str, Any]:
    """Checks whether the client currently holds an authenticated session or credentials."""
    try:
        user = get_current_user(request)
        return {
            "authenticated": True,
            "uid": user.uid,
            "auth_type": user.auth_type,
        }
    except HTTPException:
        return {
            "authenticated": False,
            "uid": None,
            "auth_type": None,
        }
