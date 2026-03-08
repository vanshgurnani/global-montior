from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.database import create_indexes

CODE_LEVEL_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://global-montior.vercel.app"
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_indexes()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CODE_LEVEL_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "disclaimer": "Not financial advice",
    }
