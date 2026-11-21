"""FastAPI application entry point for QUANT-X Algorithm Engine."""
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import get_settings
from app.api.v1 import data, strategies, backtest, optimization, analytics, risk
from app.api import websocket as ws_router

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    Path(settings.PARQUET_DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.LOG_DIR).mkdir(parents=True, exist_ok=True)
    logging.getLogger(__name__).info("QUANT-X Algorithm Engine started successfully")
    yield
    logging.getLogger(__name__).info("QUANT-X Algorithm Engine shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="QUANT-X Algorithm Engine",
        description="Multi-Asset Algorithmic Trading & Backtesting Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = f"/api/{settings.API_VERSION}"
    app.include_router(data.router, prefix=prefix, tags=["Data Management"])
    app.include_router(strategies.router, prefix=prefix, tags=["Strategies"])
    app.include_router(backtest.router, prefix=prefix, tags=["Backtesting"])
    app.include_router(optimization.router, prefix=prefix, tags=["Optimization"])
    app.include_router(analytics.router, prefix=prefix, tags=["Analytics"])
    app.include_router(risk.router, prefix=prefix, tags=["Risk Management"])
    app.include_router(ws_router.router, tags=["WebSockets"])

    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "healthy",
            "version": "1.0.0",
            "engine_uptime_seconds": round(time.time() - START_TIME, 1),
            "data_dir": settings.PARQUET_DATA_DIR,
            "database_connected": True
        }

    static_index = Path(__file__).parent / "static" / "index.html"

    @app.get("/", tags=["Terminal Web App"])
    @app.get("/app", tags=["Terminal Web App"])
    async def serve_mobile_app():
        if static_index.exists():
            return FileResponse(static_index)
        return {"status": "QUANT-X Backend Active", "docs": "/docs"}

    return app


app = create_app()
