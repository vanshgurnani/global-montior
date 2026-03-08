from fastapi import APIRouter, Depends, Query
from pymongo.database import Database
from typing import Optional

from app.core.database import get_db
from app.schemas.risk import GlobalRiskOverview
from app.services.risk_map_service import risk_map_service
from app.services.risk_service import risk_service

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.get("/overview", response_model=GlobalRiskOverview)
def overview(db: Database = Depends(get_db)):
    return risk_service.global_overview(db)


@router.get("/map-layers")
def map_layers(
    db: Database = Depends(get_db),
    include_osint: bool = Query(default=False),
    overlays: Optional[str] = Query(default=None, description="Comma-separated: fire_hotspots,ship_density,flight_diversions"),
):
    overlay_keys = [x.strip().lower() for x in overlays.split(",")] if overlays else None
    return risk_map_service.latest_layers(db, include_osint=include_osint, overlay_keys=overlay_keys)
