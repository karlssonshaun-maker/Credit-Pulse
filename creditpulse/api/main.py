from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from creditpulse.api.middleware.audit import AuditMiddleware
from creditpulse.api.middleware.ratelimit import RateLimitMiddleware
from creditpulse.api.routes import analytics, businesses, history, lenders, score, statements
from creditpulse.config import get_settings
from creditpulse.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("api_starting", env=get_settings().env)
    yield
    logger.info("api_stopping")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CreditPulse SA",
        description="Alternative credit scoring API for South African SMEs",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware, per_minute=settings.rate_limit_per_minute)

    app.include_router(score.router)
    app.include_router(businesses.router)
    app.include_router(statements.router)
    app.include_router(lenders.router)
    app.include_router(history.router)
    app.include_router(analytics.router)

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "service": "creditpulse",
            "version": "0.1.0",
            "time": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/")
    async def root() -> dict:
        return {
            "name": "CreditPulse SA",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
