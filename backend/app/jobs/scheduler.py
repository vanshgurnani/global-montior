from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import get_db_direct
from app.services.market_pipeline import market_pipeline
from app.services.news_service import news_service

scheduler = BackgroundScheduler()


def scheduled_ingestion():
    db = get_db_direct()
    try:
        news_service.ingest(db)
    except Exception:
        pass
    try:
        market_pipeline.refresh(db)
    except Exception:
        pass


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        return
    if scheduler.running:
        return

    # Populate data immediately so dashboards are not empty on cold start.
    scheduled_ingestion()

    scheduler.add_job(
        scheduled_ingestion,
        "interval",
        minutes=settings.scheduler_interval_minutes,
        id="news_market_job",
        replace_existing=True,
    )
    scheduler.start()
