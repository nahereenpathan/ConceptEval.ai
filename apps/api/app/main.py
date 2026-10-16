"""
Concept-Aware Code Evaluation FastAPI Application Entrypoint
"""

import logging
import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import os
import sys
from pathlib import Path

# Ensure execution-runner package is available in sys.path
_cur = Path(__file__).resolve().parent
while _cur.parent != _cur:
    candidate = _cur / "apps" / "execution-runner"
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
        break
    if (_cur / "execution-runner").exists() and str(_cur / "execution-runner") not in sys.path:
        sys.path.insert(0, str(_cur / "execution-runner"))
        break
    _cur = _cur.parent

from app.api.v1.router import api_router
from app.core.config import settings

logger = logging.getLogger("app.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

@app.middleware("http")
async def request_id_and_timing_middleware(request: Request, call_next: Callable) -> Response:
    """Injects a unique request_id, measures latency, and guarantees structured 500 responses."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path} (request_id={request_id}): {exc}",
            exc_info=True,
        )
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred while processing your request.",
                    "request_id": request_id,
                }
            },
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-MS"] = f"{duration_ms:.2f}"
        return response

    duration_ms = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = f"{duration_ms:.2f}"
    return response


# Outermost middleware: CORS (added after HTTP middleware so all error responses pass through CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Response-Time-MS"],
    max_age=600,
)


# Standard Error Handler adhering to Section 7.7
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", None)
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "HTTP_ERROR")
        message = detail.get("message", str(detail))
    else:
        code = "HTTP_ERROR"
        message = str(detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request payload failed schema validation.",
                "request_id": request_id,
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler ensuring internal server errors return standard JSON and preserve CORS headers."""
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        f"Unhandled server error on {request.method} {request.url.path} (request_id={request_id}): {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred while processing your request.",
                "request_id": request_id,
            }
        },
    )


# Health & Readiness Probes
@app.get("/healthz", tags=["System Health"])
async def health_check():
    """Liveness probe returning application operational status."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/readyz", tags=["System Health"])
async def readiness_check():
    """Readiness probe verifying API readiness."""
    return {"status": "ready"}


# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)
