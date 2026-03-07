from collections import Counter


RISK_KEYWORDS = ["war", "sanctions", "military", "invasion", "oil", "economy"]
COUNTRIES = [
    "United States", "China", "Russia", "Ukraine", "India", "United Kingdom", "Germany",
    "France", "Israel", "Iran", "Saudi Arabia", "Japan", "South Korea", "Taiwan"
]


class WarRiskService:
    def keyword_score(self, text: str) -> tuple[float, list[str]]:
        normalized = (text or "").lower()
        hits = [k for k in RISK_KEYWORDS if k in normalized]
        density = len(hits) / max(len(RISK_KEYWORDS), 1)
        return round(min(1.0, density), 4), hits

    def country_from_text(self, text: str) -> str:
        normalized = (text or "").lower()
        counts = Counter(c for c in COUNTRIES if c.lower() in normalized)
        return counts.most_common(1)[0][0] if counts else "Unknown"

    def combined_war_risk(self, sentiment_score: float, keyword_score: float) -> float:
        sentiment_risk = max(0.0, -sentiment_score)
        combined = 0.65 * keyword_score + 0.35 * sentiment_risk
        return round(min(1.0, combined), 4)


war_risk_service = WarRiskService()
