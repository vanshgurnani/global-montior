from fastapi import APIRouter

from app.api.routes import health, jobs, markets, news, risk

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(news.router)
api_router.include_router(risk.router)
api_router.include_router(markets.router)
api_router.include_router(jobs.router)
