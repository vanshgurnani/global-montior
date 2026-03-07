from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MarketSnapshotOut(BaseModel):
    symbol: str
    name: str
    asset_type: Optional[str] = None
    price: float
    momentum_7d: float
    volume_spike_pct: float
    ma20: float
    ma50: float
    vix_proxy: float
    prob_up: float
    prob_down: float
    risk_level: str
    explanation: str
    predicted_return_5d: Optional[float] = None
    confidence: Optional[float] = None
    model_used: Optional[str] = None
    as_of: datetime

    class Config:
        from_attributes = True
