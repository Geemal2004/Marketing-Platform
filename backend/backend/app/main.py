"""
AgentSociety Marketing Platform - FastAPI Backend
"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    from app.config import get_settings
    settings = get_settings()
    
    # Startup
    logger.info("Starting AgentSociety API...")
    logger.info(
        "HF media storage: repo=%s type=%s",
        settings.hf_video_repo_id,
        settings.hf_video_repo_type,
    )

    # Create upload directory
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Additive schema updates for multimedia projects (no Alembic migrations in repo)
    try:
        from app.database import engine
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS media_subtype VARCHAR(50) DEFAULT 'video_ad'"
            ))
            conn.execute(text(
                "ALTER TABLE projects ADD COLUMN IF NOT EXISTS media_modality VARCHAR(20) DEFAULT 'video'"
            ))
            # Allow paste-only text projects with no stored asset URL
            try:
                conn.execute(text("ALTER TABLE projects ALTER COLUMN video_path DROP NOT NULL"))
            except Exception as col_err:
                logger.debug(f"video_path nullability update skipped: {col_err}")
            conn.execute(text(
                "UPDATE projects SET media_subtype = 'video_ad' WHERE media_subtype IS NULL"
            ))
            conn.execute(text(
                "UPDATE projects SET media_modality = 'video' WHERE media_modality IS NULL"
            ))
        logger.info("Ensured multimedia columns on projects table")
    except Exception as e:
        logger.warning(f"Could not apply multimedia schema updates: {e}")
    
    # Start results listener (receives simulation results from Ray worker)
    from app.results_listener import start_results_listener
    start_results_listener(redis_url=settings.redis_url)
    logger.info("Results listener started - listening for Ray worker results")
    
    yield
    
    # Shutdown
    from app.results_listener import stop_results_listener
    stop_results_listener()
    logger.info("Shutting down AgentSociety API...")


# Create FastAPI app - disable redirect_slashes to prevent 307 that strips auth headers
app = FastAPI(
    title="AgentSociety Marketing Platform",
    description="AI-powered marketing simulation platform that simulates 1,000+ AI agents reacting to multimedia advertisements",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

# CORS configuration - allow any frontend origin.
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register routers
from app.routers import auth_router, projects_router, simulations_router, agents_router, billing_router
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(simulations_router)
app.include_router(agents_router)
app.include_router(billing_router)


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AgentSociety API",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """Detailed health check"""
    from app.config import get_settings
    from app.services.hf_storage import _resolve_hf_config, _backend_env_path
    settings = get_settings()

    health = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "hf_video_repo_id": None,
        "hf_env_file": str(_backend_env_path()),
    }

    try:
        _, repo_id, repo_type, _ = _resolve_hf_config()
        health["hf_video_repo_id"] = repo_id
        health["hf_video_repo_type"] = repo_type
    except Exception as e:
        health["hf_video_repo_id"] = f"error: {e}"
    
    # Check database
    try:
        from app.database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            health["database"] = "healthy"
    except Exception as e:
        health["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        import redis
        import ssl as ssl_module
        redis_kwargs = {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        }
        if settings.redis_url.startswith("rediss://"):
            redis_kwargs["ssl_cert_reqs"] = ssl_module.CERT_REQUIRED
        r = redis.from_url(settings.redis_url, **redis_kwargs)
        r.ping()
        health["redis"] = "healthy"
    except Exception as e:
        health["redis"] = f"unhealthy: {str(e)}"
    
    return health
