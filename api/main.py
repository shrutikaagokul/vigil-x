"""
Vigil-X Investigation & FWA Intelligence Backend.
FastAPI Application Entry Point.
"""
from __future__ import annotations

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import (
    ask,
    audit,
    brief,
    cases,
    claims,
    decisions,
    evaluation,
    health,
    networks,
    providers,
    queue,
    risk,
    summary,
)
from contracts.investigation import get_current_as_of

logger = logging.getLogger("vigilx.api")

app = FastAPI(
    title="Vigil-X Investigation API",
    description="AI-powered healthcare payer Fraud, Waste & Abuse (FWA) intelligence platform for Special Investigation Units (SIU).",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local frontend dev servers (Vite, Next.js, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log incoming API requests and processing duration."""
    import time
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000.0
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled errors and return structured JSON."""
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc) or "Internal server error occurred.",
            "error_type": type(exc).__name__,
            "as_of": get_current_as_of(),
            "synthetic": True,
        },
    )


# Register all API routers under /api prefix
api_prefix = "/api"
app.include_router(health.router, prefix=api_prefix)
app.include_router(summary.router, prefix=api_prefix)
app.include_router(queue.router, prefix=api_prefix)
app.include_router(cases.router, prefix=api_prefix)
app.include_router(networks.router, prefix=api_prefix)
app.include_router(claims.router, prefix=api_prefix)
app.include_router(providers.router, prefix=api_prefix)
app.include_router(risk.router, prefix=api_prefix)
app.include_router(brief.router, prefix=api_prefix)
app.include_router(ask.router, prefix=api_prefix)
app.include_router(decisions.router, prefix=api_prefix)
app.include_router(audit.router, prefix=api_prefix)
app.include_router(evaluation.router, prefix=api_prefix)


@app.get("/")
def root():
    """Root status endpoint."""
    return {
        "service": "Vigil-X Investigation API",
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
        "as_of": get_current_as_of(),
        "synthetic": True,
    }
