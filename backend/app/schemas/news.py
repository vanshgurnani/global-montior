from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ArticleOut(BaseModel):
    title: str
    source: str
    url: str
    country: str
    published_at: datetime
    sentiment_score: float
    keyword_score: float
    war_risk_score: float
    event_type: Optional[str] = None
    event_severity: Optional[str] = None
    event_confidence: Optional[float] = None

    class Config:
        from_attributes = True
