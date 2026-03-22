from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.core.config import settings
from app.core.database import get_db
from app.services.ground_truth_service import ground_truth_service
from app.services.market_pipeline import market_pipeline
from app.services.news_service import news_service
from app.services.prediction_service import prediction_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/refresh")
def refresh_all(db: Database = Depends(get_db)):
    result = {"ok": True, "training": None, "news": None, "markets": None, "ground_truth": None, "errors": []}

    if settings.model_auto_train_on_refresh:
        try:
            result["training"] = prediction_service.train_if_needed(force=False)
        except Exception as exc:
            result["ok"] = False
            result["errors"].append(f"model_training_failed: {exc}")
    else:
        result["training"] = {"trained": False, "cached": True, "reason": "auto_train_disabled"}

    try:
        result["news"] = news_service.ingest_with_stats(db)
    except Exception as exc:
        result["ok"] = False
        result["errors"].append(f"ingestion_failed: {exc}")

    try:
        refreshed = market_pipeline.refresh(db)
        result["markets"] = {"refreshed": refreshed}
    except Exception as exc:
        result["ok"] = False
        result["errors"].append(f"market_refresh_failed: {exc}")

    if settings.ground_truth_enabled:
        try:
            result["ground_truth"] = ground_truth_service.ingest_all(db)
        except Exception as exc:
            result["ok"] = False
            result["errors"].append(f"ground_truth_failed: {exc}")

    return result
