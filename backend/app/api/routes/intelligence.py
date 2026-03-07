from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.core.database import get_db
from app.services.intelligence_service import intelligence_service

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


@router.get("/dashboard")
def dashboard(db: Database = Depends(get_db)):
    return intelligence_service.dashboard(db)


@router.get("/country/{country}")
def country_dashboard(country: str, db: Database = Depends(get_db)):
    data = intelligence_service.dashboard(db)
    normalized = country.strip().lower()
    matches = [x for x in data["country_risk_dashboard"] if x["country"].strip().lower() == normalized]
    return {"country": country, "snapshot": matches[0] if matches else None}
