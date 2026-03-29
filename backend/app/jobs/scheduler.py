from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import get_db_direct
from app.services.ground_truth_service import ground_truth_service
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
    if settings.ground_truth_enabled:
        try:
            ground_truth_service.ingest_all(db)
        except Exception:
            pass


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        return
    if scheduler.running:
        return

    scheduler.add_job(
        scheduled_ingestion,
        "interval",
        minutes=settings.scheduler_interval_minutes,
        id="news_market_job",
        replace_existing=True,
    )
    scheduler.start()

    # Run initial ingestion after 2s so app can serve health/API immediately; data populates shortly
    scheduler.add_job(
        scheduled_ingestion,
        "date",
        run_date=datetime.now(timezone.utc) + timedelta(seconds=2),
        id="cold_start_ingestion",
    )
