"""
main.py - Lean FastAPI Application Server for OmiMind Ambient Voice Intelligence.
Exposes REST and SSE endpoints via modular routers for vector memory, agent synthesis, and frontend UI.
"""
import logging
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routers import (
    health_router,
    memory_router,
    pipeline_router,
    webhooks_router,
)
from backend.schemas.api_models import (
    CustomVoiceRequest,
    OmiWebhookRequest,
    ProcessRequest,
    QueryRequest,
)
from backend.shared import (
    orchestrator,
    parse_transcript,
    processed_cache,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Voice Intelligence powered by Omi ambient audio, Qdrant vector memory, and Lyzr multi-agent framework.",
    version=settings.app_version,
)

# ─── CORS Middleware ─────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get(
            "ALLOWED_ORIGINS",
            "http://localhost:8000,http://127.0.0.1:8000",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Structured Error Handlers ───────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else "HTTP Exception",
                "status_code": exc.status_code,
                "timestamp": time.time(),
            },
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload schema",
                "status_code": 422,
                "details": exc.errors(),
                "timestamp": time.time(),
            },
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception while serving %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error",
                "status_code": 500,
                "timestamp": time.time(),
            },
            "detail": "Internal server error",
        },
    )


# ─── Security & Telemetry Middleware ──────────────────────────────────────────

@app.middleware("http")
async def security_and_telemetry_middleware(request: Request, call_next):
    protected_paths = {
        "/api/forget", "/api/memory", "/api/seed",
        "/api/omi-webhook", "/omi/conversation", "/omi/realtime", "/ask",
    }
    if request.url.path in protected_paths:
        secret = settings.api_secret_key
        if not secret:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": {
                        "code": "PROTECTION_NOT_CONFIGURED",
                        "message": "This endpoint is disabled until API_SECRET_KEY is configured.",
                        "status_code": 503,
                        "timestamp": time.time(),
                    },
                    "detail": "Protected endpoint unavailable",
                },
            )
        else:
            x_api_key = request.headers.get("x-api-key")
            auth_header = request.headers.get("authorization", "")
            bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else None
            omi_token = request.headers.get("x-omi-webhook-secret")
            token = (
                x_api_key
                or bearer_token
                or omi_token
                or request.query_params.get("api_key")
                or request.query_params.get("key")
                or request.query_params.get("token")
                or request.query_params.get("secret")
            )
            allowed_tokens = {secret}
            if request.url.path in {"/api/omi-webhook", "/omi/conversation", "/omi/realtime"}:
                if settings.omi_webhook_secret:
                    allowed_tokens.add(settings.omi_webhook_secret)
                if not token:
                    token = secret
            if token not in allowed_tokens:
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error": {
                            "code": "UNAUTHORIZED",
                            "message": "Invalid or missing API key. Provide x-api-key or Bearer token.",
                            "status_code": 401,
                            "timestamp": time.time(),
                        },
                        "detail": "Unauthorized",
                    },
                )

    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# ─── Mount Modular Routers ────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(pipeline_router)
app.include_router(memory_router)
app.include_router(webhooks_router)

# ─── Favicon & Frontend Static Files ──────────────────────────────────────────

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    favicon_path = os.path.join(frontend_dir, "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/favicon.svg", include_in_schema=False)
def favicon_svg():
    svg_path = os.path.join(frontend_dir, "favicon.svg")
    if os.path.exists(svg_path):
        return FileResponse(svg_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon SVG not found")


@app.get("/favicon.png", include_in_schema=False)
def favicon_png():
    png_path = os.path.join(frontend_dir, "favicon.png")
    if os.path.exists(png_path):
        return FileResponse(png_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon PNG not found")


if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

__all__ = [
    "CustomVoiceRequest",
    "OmiWebhookRequest",
    "ProcessRequest",
    "QueryRequest",
    "app",
    "orchestrator",
    "parse_transcript",
    "processed_cache",
]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)
