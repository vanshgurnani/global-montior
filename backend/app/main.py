import threading
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.database import create_indexes
from app.jobs.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        create_indexes()
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
    
    # Start scheduler in background thread so initial ingestion doesn't block app startup
    thread = threading.Thread(target=start_scheduler, daemon=True)
    thread.start()
    logger.info("Background scheduler started")
    yield
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.app_name, 
    debug=settings.debug,  # Now controlled by environment
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,  # Cache CORS preflight for 10 minutes
)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "disclaimer": "Not financial advice",
    }
