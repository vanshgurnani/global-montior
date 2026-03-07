from pydantic import BaseModel


class CountryRiskOut(BaseModel):
    country: str
    avg_war_risk: float
    article_count: int


class GlobalRiskOverview(BaseModel):
    global_sentiment: float
    global_war_risk: float
    risk_level: str
    high_risk_countries: list[CountryRiskOut]
