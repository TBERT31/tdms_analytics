"""
TDMS Analytics API - Main FastAPI application
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from tdms_analytics.config import get_settings
from tdms_analytics.dependencies.database import get_clickhouse_client
from tdms_analytics.routes import (
    channels,
    datasets,
    health,
    ingestion,
    windows,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    logger.info(f"Starting TDMS Analytics API v{settings.VERSION}")
    
    # Test ClickHouse connection
    try:
        client = get_clickhouse_client()
        result = client.query("SELECT 1")
        logger.info("✓ ClickHouse connection successful")
    except Exception as e:
        logger.error(f"✗ ClickHouse connection failed: {e}")
        raise
    
    yield
    
    logger.info("Shutting down TDMS Analytics API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="TDMS → ClickHouse Analytics API",
        description="Analytics service for TDMS sensor data using ClickHouse",
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(ingestion.router, tags=["Ingestion"])
    app.include_router(datasets.router, tags=["Datasets"])
    app.include_router(channels.router, tags=["Channels"])
    app.include_router(windows.router, tags=["Data Windows"])
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "tdms_analytics.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )