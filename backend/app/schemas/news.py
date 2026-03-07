from datetime import datetime

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

    class Config:
        from_attributes = True
