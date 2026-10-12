"""User-owned run history and account lifecycle endpoints."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException

from backend.auth import AuthenticatedUser, get_current_user
from backend.config import settings
from backend.shared import orchestrator
from backend.tenant_store import tenant_store
from backend.webhook_inbox import default_webhook_inbox

router = APIRouter(tags=["workspace"])


@router.get("/api/runs/{run_id}/events")
def run_events(run_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    return {"run_id": run_id, "events": tenant_store.list_events(user.uid, run_id)}


@router.delete("/api/account")
def delete_account(user: AuthenticatedUser = Depends(get_current_user)):
    try:
        deleted_points = orchestrator.memory.delete_owner_data(user.uid)
        tenant_store.delete_owner(user.uid)
        deleted_webhooks = default_webhook_inbox.delete_owner(user.uid)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Account deletion could not remove all workspace data; Supabase account deletion was not attempted. Retry after the storage issue is resolved.") from exc
    if settings.supabase_url and settings.supabase_service_role_key and user.uid:
        try:
            response = httpx.delete(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user.uid}",
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                },
                timeout=20,
            )
            response.raise_for_status()
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Account data was removed, but Supabase account deletion could not be completed.") from exc
    return {"success": True, "deleted_qdrant_points": deleted_points, "deleted_webhook_events": deleted_webhooks}
