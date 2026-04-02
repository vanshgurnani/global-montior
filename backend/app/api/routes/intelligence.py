from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.core.database import get_db
from app.services.intelligence_service import intelligence_service

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.get("/dashboard")
def dashboard(db: Database = Depends(get_db)):
    return intelligence_service.dashboard(db)


@router.get("/prediction-accuracy")
def prediction_accuracy(db: Database = Depends(get_db)):
    """
    Returns prediction vs reality data showing:
    - What the model predicted BEFORE news was declared
    - What actually happened (the news)
    - How accurate the prediction was
    """
    articles = intelligence_service._latest_articles(db, limit=320)
    markets = intelligence_service._latest_markets(db)
    prediction_data = intelligence_service._prediction_vs_reality(db, articles, markets)
    
    return {
        "generated_at": intelligence_service._utc_now().isoformat() if hasattr(intelligence_service, '_utc_now') else __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        "predictions": prediction_data,
        "total_predictions_analyzed": len(prediction_data),
        "average_accuracy": round(sum(p["prediction_accuracy"] for p in prediction_data) / max(len(prediction_data), 1), 4) if prediction_data else 0.0,
    }


@router.get("/country/{country}")
def country_dashboard(country: str, db: Database = Depends(get_db)):
    data = intelligence_service.dashboard(db)
    normalized = country.strip().lower()
    matches = [x for x in data["country_risk_dashboard"] if x["country"].strip().lower() == normalized]
    return {"country": country, "snapshot": matches[0] if matches else None}
