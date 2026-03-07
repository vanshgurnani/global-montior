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


@router.get("/stocks", response_model=list[MarketSnapshotOut])
def stocks(limit: int = 25, db: Database = Depends(get_db)):
    cursor = (
        db.market_snapshots.find({"asset_type": {"$in": ["stock", "index", "etf"]}}, {"_id": 0})
        .sort("prob_up", -1)
        .limit(max(1, min(limit, 100)))
    )
    return list(cursor)


@router.get("/crypto", response_model=list[MarketSnapshotOut])
def crypto(limit: int = 25, db: Database = Depends(get_db)):
    cursor = (
        db.market_snapshots.find(
            {"$or": [{"asset_type": "crypto"}, {"symbol": {"$regex": "-USD$"}}]},
            {"_id": 0},
        )
        .sort("prob_up", -1)
        .limit(max(1, min(limit, 100)))
    )
    return list(cursor)
