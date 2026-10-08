"""
backend/auth.py
Centralized authentication and tenant authorization for OmiMind.

Security Architecture:
1. Server-side User Identity:
   - For single-user deployments / demo hackathon mode, identity is derived from settings.default_user_id.
   - Test-only tenant-scoped credentials may use a token suffix; production callers cannot mint tenant IDs.
   - Callers cannot override their identity via query parameters, request bodies, or webhook payloads.
2. Header-only Secrets:
   - Authentication credentials in query parameters (api_key, key, token, secret) are strictly rejected with HTTP 401.
   - Accepted headers: `Authorization: Bearer <token>` or `X-API-Key: <token>`.
3. Constant-Time Comparison:
   - All secret verification uses `hmac.compare_digest` to prevent timing attacks.
4. Dedicated Omi Webhook Verification:
   - Validates `OMI_WEBHOOK_SECRET` via `X-Omi-Webhook-Secret`, `X-Omi-Signature`, or `Authorization: Bearer <secret>`.
   - Replay protection verifies `X-Omi-Timestamp` (within 5-minute tolerance window).
   - Maps verified webhook credentials to the server-side user identity.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request

from backend.config import is_testing, settings

logger = logging.getLogger("omimind.auth")

FORBIDDEN_QUERY_SECRETS = {"api_key", "key", "token", "secret"}


@dataclass(frozen=True)
class AuthenticatedUser:
    uid: str
    auth_type: str = "api_key"


def check_no_query_secrets(request: Request) -> None:
    """Rejects authentication secrets supplied via query parameters."""
    for param in FORBIDDEN_QUERY_SECRETS:
        if param in request.query_params:
            raise HTTPException(
                status_code=401,
                detail="Query-string credentials are not permitted. Use Authorization: Bearer <token> or X-API-Key header.",
            )


def extract_header_token(request: Request) -> str | None:
    """Extracts token from Authorization: Bearer <token> or X-API-Key header."""
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    x_api_key = request.headers.get("x-api-key", "").strip()
    if x_api_key:
        return x_api_key
    return None


def get_current_user(request: Request) -> AuthenticatedUser:
    """
    Validates API authentication headers and derives the server-side user identity.
    Does NOT trust caller-supplied UID in query or body.
    """
    check_no_query_secrets(request)

    secret = settings.api_secret_key
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="This endpoint is disabled until API_SECRET_KEY is configured.",
        )

    token = extract_header_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials. Provide Authorization: Bearer <token> or X-API-Key header.",
        )

    # The shared API secret identifies one configured tenant. Never allow a
    # caller to mint an arbitrary tenant identity by appending a UID suffix.
    uid: str | None = settings.default_user_id if hmac.compare_digest(token, secret) else None
    if uid is None and is_testing() and ":" in token:
        prefix, candidate_uid = token.split(":", 1)
        if hmac.compare_digest(prefix, secret) and candidate_uid.strip():
            uid = candidate_uid.strip()

    if not uid:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key or credentials.",
        )

    return AuthenticatedUser(uid=uid, auth_type="api_key")


def _verify_webhook_timestamp(request: Request) -> None:
    """Require a fresh timestamp for every webhook request."""
    ts_header = request.headers.get("x-omi-timestamp") or request.headers.get("x-timestamp")
    if not ts_header and is_testing():
        return
    if not ts_header:
        raise HTTPException(status_code=401, detail="Missing webhook timestamp header.")
    try:
        req_time = float(ts_header)
        if abs(time.time() - req_time) > 300:  # 5-minute tolerance window
            raise HTTPException(
                status_code=401,
                detail="Webhook timestamp expired or outside allowable 5-minute window.",
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail="Malformed webhook timestamp header.",
        ) from exc


def _match_webhook_secret(supplied_token: str, secret: str) -> tuple[bool, str | None]:
    """Match the provisioned webhook secret to the configured tenant."""
    if hmac.compare_digest(supplied_token, secret):
        return True, settings.default_user_id
    if is_testing() and ":" in supplied_token:
        prefix, candidate_uid = supplied_token.split(":", 1)
        if hmac.compare_digest(prefix, secret) and candidate_uid.strip():
            return True, candidate_uid.strip()
    return False, None


async def verify_omi_webhook(request: Request) -> AuthenticatedUser:
    """
    Validates Omi webhook credentials and maps to configured server-side identity.
    Enforces constant-time comparison, replay protection, and header-only authentication.
    """
    check_no_query_secrets(request)
    _verify_webhook_timestamp(request)

    signature = request.headers.get("x-omi-signature", "").strip()
    supplied_token = (
        request.headers.get("x-omi-webhook-secret", "").strip()
        or request.headers.get("x-webhook-secret", "").strip()
        or extract_header_token(request)
    )

    if not signature and not supplied_token:
        raise HTTPException(
            status_code=401,
            detail="Missing webhook authentication credentials. Provide X-Omi-Webhook-Secret header.",
        )

    webhook_secret = settings.omi_webhook_secret or settings.api_secret_key
    if not webhook_secret:
        raise HTTPException(
            status_code=503,
            detail="Webhook authentication not configured.",
        )

    if signature:
        timestamp = request.headers.get("x-omi-timestamp") or request.headers.get("x-timestamp")
        body = await request.body()
        signed_payload = f"{timestamp}.{body.decode('utf-8')}".encode()
        expected = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        provided = signature.removeprefix("sha256=")
        is_valid = hmac.compare_digest(provided, expected)
        user_id = settings.default_user_id if is_valid else None
    else:
        is_valid, user_id = _match_webhook_secret(supplied_token, webhook_secret)
    if not is_valid or not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook credentials.",
        )

    return AuthenticatedUser(uid=user_id, auth_type="webhook")
