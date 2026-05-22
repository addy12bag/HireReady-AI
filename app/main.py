import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.api.routes import sessions, documents, scoring, generation, chat
from app.web.routes import router as web_router

logging.basicConfig(level=getattr(logging, get_settings().log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Resume AI Platform...")
    # Create tables if they don't exist (SQLite dev convenience)
    from app.db.engine import engine
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    yield
    logger.info("Shutting down Resume AI Platform...")


BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="Resume AI Platform",
    description="Multi-Agent AI Resume Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Static files and templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.state.templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# API routers
app.include_router(sessions.router)
app.include_router(documents.router)
app.include_router(scoring.router)
app.include_router(generation.router)
app.include_router(chat.router)

# Web UI router
app.include_router(web_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
