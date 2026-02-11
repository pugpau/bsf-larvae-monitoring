"""
BSF-LoopTech — 廃棄物処理配合最適化システム API
"""

from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api.routes import auth, waste
from src.api.routes.materials import router as materials_router
from src.api.routes.ml import router as ml_router
from src.api.routes.optimization import router as optimization_router
from src.auth.middleware import AuthenticationMiddleware, RateLimitMiddleware
from src.config import settings
from src.utils.logging import setup_logging, get_logger

load_dotenv()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting BSF-LoopTech API")

    try:
        from src.database.postgresql import check_database_health, init_database

        await init_database()
        logger.info("Database initialised")

        if await check_database_health():
            logger.info("PostgreSQL connection OK")
        else:
            logger.error("PostgreSQL connection failed")
    except Exception as e:
        logger.error(f"Startup error: {e}")

    yield

    logger.info("Shutting down BSF-LoopTech API")
    try:
        from src.database.postgresql import close_database

        await close_database()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


app = FastAPI(
    title="BSF-LoopTech API",
    description="廃棄物処理配合最適化システム — Waste treatment formulation optimisation API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Authentication
app.add_middleware(
    AuthenticationMiddleware,
    exempt_paths=[
        "/docs", "/redoc", "/openapi.json", "/health", "/ready", "/", "/favicon.ico",
        "/auth/login", "/auth/refresh", "/auth/health",
        "/api/v1/suppliers", "/api/v1/solidification-materials",
        "/api/v1/leaching-suppressants", "/api/v1/recipes",
        "/api/v1/predict", "/api/v1/ml", "/api/v1/optimize",
    ],
)

# Routers
app.include_router(auth.router)
app.include_router(waste.router)
app.include_router(materials_router)
app.include_router(ml_router)
app.include_router(optimization_router)


@app.get("/")
async def read_root():
    return {"message": "BSF-LoopTech — 廃棄物処理配合最適化システム"}


@app.get("/favicon.ico")
async def favicon():
    return {"message": "No favicon available"}


@app.get("/health")
async def health_check():
    from src.database.postgresql import check_database_health

    pg_ok = False
    pg_detail = ""
    try:
        pg_ok = await check_database_health()
    except Exception as e:
        pg_detail = str(e)

    return {
        "status": "healthy" if pg_ok else "degraded",
        "services": {
            "api": "ok",
            "postgresql": "ok" if pg_ok else "error",
        },
        "details": {} if pg_ok else {"postgresql": pg_detail or "Connection failed"},
    }


@app.get("/ready")
async def readiness_check():
    """Readiness probe — returns 503 when DB is unavailable (deploy script uses this)."""
    from fastapi.responses import JSONResponse
    from src.database.postgresql import check_database_health

    try:
        db_ok = await check_database_health()
    except Exception:
        db_ok = False

    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "reason": "database unavailable"},
        )

    return {"ready": True}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
