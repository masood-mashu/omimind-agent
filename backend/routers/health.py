"""
health.py - Health check and system observability endpoints
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.shared import orchestrator

router = APIRouter(tags=["Health & Status"])


@router.get("/health")
def health():
    stats = orchestrator.memory.get_stats()
    emb_health = stats.get("embedding_health", {})
    emb_status = emb_health.get("status", "ready")
    is_healthy = emb_status == "ready"

    health_data = {
        "status": "healthy" if is_healthy else "degraded",
        "service": "omimind-agent",
        "version": "2.0.0",
        "embedding_provider": stats.get("embedding_provider", "fastembed"),
        "vector_dimension": stats.get("vector_dimension", 384),
        "qdrant_persistence_mode": stats.get("persistence_mode", "cloud"),
        "lyzr_status": {
            "configured": orchestrator.lyzr.configured,
            "agent_id_configured": bool(orchestrator.lyzr.agent_id),
            "provider": "lyzr_studio_cloud" if orchestrator.lyzr.configured else "unconfigured",
        },
        "embedding_health": emb_health,
        "qdrant_stats": stats,
    }

    if not is_healthy:
        return JSONResponse(status_code=503, content=health_data)
    return health_data
