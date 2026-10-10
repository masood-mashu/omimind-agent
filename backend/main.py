"""
main.py - Lean FastAPI Application Server for OmiMind Ambient Voice Intelligence.
Exposes REST and SSE endpoints via modular routers for vector memory, agent synthesis, and frontend UI.
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.auth import COOKIE_NAME
from backend.config import settings, validate_production_config
from backend.routers import (
    auth_router,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate required production settings at startup
    validate_production_config()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Voice Intelligence powered by Omi ambient audio, Qdrant vector memory, and Lyzr multi-agent framework.",
    version=settings.app_version,
    lifespan=lifespan,
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
    errors = jsonable_encoder(exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload schema",
                "status_code": 422,
                "details": errors,
                "timestamp": time.time(),
            },
            "detail": errors,
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


# ─── Security, Payload Limits & Telemetry Middleware ──────────────────────────

MAX_REQUEST_BODY_SIZE = 1_000_000  # 1 MB
FORBIDDEN_QUERY_SECRETS = {"api_key", "key", "token", "secret"}


@app.middleware("http")
async def security_and_telemetry_middleware(request: Request, call_next):
    # 1. Enforce payload size limit (HTTP 413)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "success": False,
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": "Request payload exceeds maximum allowed limit of 1MB",
                            "status_code": 413,
                            "timestamp": time.time(),
                        },
                        "detail": "Request payload too large",
                    },
                )
        except ValueError:
            pass

    # 2. Reject query-string credentials (HTTP 401)
    for q_secret in FORBIDDEN_QUERY_SECRETS:
        if q_secret in request.query_params:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Query-string credentials are not permitted. Provide header credentials only.",
                        "status_code": 401,
                        "timestamp": time.time(),
                    },
                    "detail": "Query-string credentials are not permitted. Use Authorization: Bearer <token> or X-API-Key header.",
                },
                )

    # Cookie-authenticated state changes must originate from this site. Browsers
    # normally send Origin on fetch POSTs; SameSite=Strict remains the fallback
    # protection when older clients omit it.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.cookies.get(COOKIE_NAME):
        origin = request.headers.get("origin")
        if origin:
            forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme).split(",", 1)[0].strip()
            expected_origin = f"{forwarded_proto}://{request.headers.get('host', request.url.netloc)}"
            if origin.rstrip("/") != expected_origin.rstrip("/"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": {
                            "code": "CSRF_ORIGIN_REJECTED",
                            "message": "Cross-origin state-changing requests are not permitted.",
                            "status_code": 403,
                            "timestamp": time.time(),
                        },
                        "detail": "Cross-origin state-changing requests are not permitted.",
                    },
                )

    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# ─── Mount Modular Routers ────────────────────────────────────────────────────

app.include_router(auth_router)
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
