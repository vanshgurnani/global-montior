from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.core.database import get_db
from app.schemas.risk import GlobalRiskOverview
from app.services.risk_map_service import risk_map_service
from app.services.risk_service import risk_service

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("/overview", response_model=GlobalRiskOverview)
def overview(db: Database = Depends(get_db)):
    return risk_service.global_overview(db)


@router.get("/map-layers")
def map_layers():
    return risk_map_service.latest_layers()
