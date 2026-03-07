from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.core.database import get_db
from app.schemas.market import MarketSnapshotOut

router = APIRouter(prefix="/markets", tags=["Markets"])


@router.get("/snapshots", response_model=list[MarketSnapshotOut])
def snapshots(db: Database = Depends(get_db)):
    cursor = db.market_snapshots.find({}, {"_id": 0}).sort("prob_up", -1)
    return list(cursor)


@router.get("/top-gainers", response_model=list[MarketSnapshotOut])
def top_gainers(limit: int = 5, db: Database = Depends(get_db)):
    cursor = db.market_snapshots.find({}, {"_id": 0}).sort("prob_up", -1).limit(limit)
    return list(cursor)
