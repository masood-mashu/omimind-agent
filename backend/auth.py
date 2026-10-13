"""Authentication and tenant identity for the multi-user OMIMIND service."""
from __future__ import annotations

import hashlib
import hmac
import logging
import math
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fastapi import HTTPException, Request

from backend.config import allow_test_tenant_overrides, is_testing, settings

logger = logging.getLogger("omimind.auth")
FORBIDDEN_QUERY_SECRETS = {"api_key", "key", "token", "secret"}
COOKIE_NAME = "omimind_session"
SESSION_MAX_AGE_SECONDS = 86400 * 7


@dataclass(frozen=True)
class AuthenticatedUser:
    uid: str
    auth_type: str = "supabase_jwt"
    email: str | None = None
    claims: dict[str, Any] | None = None


def check_no_query_secrets(request: Request) -> None:
    for param in FORBIDDEN_QUERY_SECRETS:
        if param in request.query_params:
            raise HTTPException(status_code=401, detail="Query-string credentials are not permitted. Use an Authorization header.")


def extract_header_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    return request.headers.get("x-api-key", "").strip() or None


def create_session_token(uid: str, secret: str) -> str:
    timestamp = int(time.time())
    payload = f"{uid}:{timestamp}".encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"{uid}:{timestamp}:{sig}"


def verify_session_token(token: str, secret: str) -> str | None:
    parts = token.split(":")
    if len(parts) != 3:
        return None
    uid, timestamp_str, sig = parts
    try:
        ts = int(timestamp_str)
    except ValueError:
        return None
    if time.time() - ts > SESSION_MAX_AGE_SECONDS or ts > time.time() + 300:
        return None
    expected = hmac.new(secret.encode(), f"{uid}:{timestamp_str}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return uid


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str):
    try:
        from jwt import PyJWKClient
    except ImportError as exc:
        raise RuntimeError("PyJWT is required for Supabase authentication.") from exc
    return PyJWKClient(jwks_url)


def verify_supabase_token(token: str) -> AuthenticatedUser:
    if not settings.supabase_url:
        status_code = 401 if (is_testing() or settings.environment.lower() != "production") else 503
        raise HTTPException(status_code=status_code, detail="Invalid authentication credentials; provider is unconfigured.")
    jwks_url = settings.supabase_jwks_url or f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"
    try:
        import jwt

        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=issuer,
            options={"require": ["sub", "exp", "iat"]},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.info("Supabase token rejected: %s", exc.__class__.__name__)
        raise HTTPException(status_code=401, detail="Invalid or expired authentication session.") from exc
    uid = str(claims.get("sub", "")).strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Authentication session has no user identity.")
    return AuthenticatedUser(uid=uid, email=claims.get("email"), claims=claims)


def _verify_local_compat_token(token: str) -> AuthenticatedUser | None:
    if not (is_testing() or settings.environment.lower() != "production"):
        return None
    secret = settings.api_secret_key
    if secret and hmac.compare_digest(token, secret):
        return AuthenticatedUser(uid=settings.default_user_id or "local-user", auth_type="local_api_key")
    if is_testing() and token in {"test-secret", "test-user"}:
        return AuthenticatedUser(uid="test-user", auth_type="test_token")
    if is_testing() and allow_test_tenant_overrides() and (token.startswith("test-secret:") or (secret and token.startswith(f"{secret}:"))):
        candidate = token.split(":", 1)[1].strip()
        if candidate:
            return AuthenticatedUser(uid=candidate, auth_type="test_token")
    return None


def get_current_user(request: Request) -> AuthenticatedUser:
    check_no_query_secrets(request)
    token = extract_header_token(request)
    if token:
        local_user = _verify_local_compat_token(token)
        return local_user or verify_supabase_token(token)
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token and settings.api_secret_key and (is_testing() or settings.environment.lower() != "production"):
        uid = verify_session_token(cookie_token, settings.api_secret_key)
        if uid:
            return AuthenticatedUser(uid=uid, auth_type="session_cookie")
        raise HTTPException(status_code=401, detail="Invalid or expired session cookie.")
    raise HTTPException(status_code=401, detail="Missing authentication credentials. Sign in to continue.")


def _verify_webhook_timestamp(request: Request) -> None:
    ts_header = request.headers.get("x-omi-timestamp") or request.headers.get("x-timestamp")
    if not ts_header and allow_test_tenant_overrides():
        return
    if not ts_header:
        raise HTTPException(status_code=401, detail="Missing webhook timestamp header.")
    try:
        req_time = float(ts_header)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Malformed webhook timestamp header.") from exc
    if not math.isfinite(req_time) or req_time > time.time() + 300 or time.time() - req_time > 300:
        raise HTTPException(status_code=401, detail="Webhook timestamp expired or outside allowable 5-minute window.")


def _match_webhook_secret(supplied_token: str, secret: str) -> tuple[bool, str | None]:
    if secret and hmac.compare_digest(supplied_token, secret):
        if not is_testing() or (settings.deployment_mode == "multi_user" and not allow_test_tenant_overrides()):
            return True, None
        return True, settings.default_user_id or None
    if is_testing() and allow_test_tenant_overrides() and ":" in supplied_token:
        prefix, candidate_uid = supplied_token.split(":", 1)
        if (prefix == "test-secret" or (secret and hmac.compare_digest(prefix, secret))) and candidate_uid.strip():
            return True, candidate_uid.strip()
    return False, None


async def verify_omi_webhook(request: Request) -> AuthenticatedUser:
    check_no_query_secrets(request)
    _verify_webhook_timestamp(request)
    signature = request.headers.get("x-omi-signature", "").strip()
    supplied_token = (
        request.headers.get("x-omi-webhook-secret", "").strip()
        or request.headers.get("x-webhook-secret", "").strip()
        or extract_header_token(request)
    )
    secret = settings.omi_webhook_secret or settings.api_secret_key
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook authentication is not configured.")
    matched_uid = ""
    if signature:
        timestamp = request.headers.get("x-omi-timestamp") or request.headers.get("x-timestamp")
        body = await request.body()
        if not timestamp or not body:
            raise HTTPException(status_code=401, detail="Signed webhooks require timestamp and raw request body.")
        expected = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        valid = hmac.compare_digest(signature.removeprefix("sha256="), expected)
        matched_uid = settings.default_user_id or "local-user"
    else:
        valid, matched = _match_webhook_secret(supplied_token or "", secret)
        matched_uid = matched or ""
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid webhook credentials.")
    if is_testing() and allow_test_tenant_overrides() and request.query_params.get("uid"):
        matched_uid = request.query_params["uid"].strip()
    return AuthenticatedUser(uid=matched_uid, auth_type="webhook")
