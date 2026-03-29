import re
from collections import Counter


RISK_KEYWORDS = ["war", "sanctions", "military", "invasion", "oil", "economy"]

# Extended country database with aliases to avoid ambiguity
COUNTRIES_DB = {
    "United States": ["usa", "us", "america", "american"],
    "United Kingdom": ["uk", "britain", "british"],
    "Russia": ["russian"],
    "China": ["chinese"],
    "Iran": ["iranian"],
    "Saudi Arabia": ["saudi"],
    "South Korea": ["korea", "south korea"],
    "Israel": ["israeli"],
    "Ukraine": ["ukrainian"],
    "India": ["indian"],
    "Germany": ["german"],
    "France": ["french"],
    "Japan": ["japanese"],
    "Taiwan": ["taiwanese"],
}

COUNTRIES = list(COUNTRIES_DB.keys())

# Conflict pairs: when both mentioned, which is primary actor?
CONFLICT_PAIRS = {
    frozenset(["United States", "Iran"]): "United States",
    frozenset(["Israel", "Iran"]): "Israel",
    frozenset(["Russia", "Ukraine"]): "Ukraine",
    frozenset(["China", "Taiwan"]): "China",
    frozenset(["Saudi Arabia", "Iran"]): "Saudi Arabia",
}

CONFLICT_KEYWORDS = ["war", "conflict", "attack", "offensive", "sanctions", "tension", "threat", "missile"]


class WarRiskService:
    def keyword_score(self, text: str) -> tuple[float, list[str]]:
        normalized = (text or "").lower()
        hits = [k for k in RISK_KEYWORDS if k in normalized]
        density = len(hits) / max(len(RISK_KEYWORDS), 1)
        return round(min(1.0, density), 4), hits

    def country_from_text(self, text: str, title: str = "") -> str:
        """
        Extract country with improved context awareness.
        
        Uses:
        1. Word boundary matching to avoid "Kingdom" in "United Kingdom" matching "United States"
        2. Title context (title gets 2x weight)
        3. Conflict pair detection to identify primary actor
        4. Fallback to most common mention
        """
        if not text:
            return "Unknown"
        
        text_lower = text.lower()
        title_lower = (title or "").lower()
        
        # Extract entities with position/weight
        country_scores = {}
        
        # First pass: find all countries with word boundaries
        for country in COUNTRIES:
            # Create regex with word boundaries to match whole country names
            pattern = r'\b' + re.escape(country.lower()) + r'\b'
            text_matches = len(re.findall(pattern, text_lower))
            title_matches = len(re.findall(pattern, title_lower))
            
            # Title matches weighted 2x higher (article about THIS country)
            total_score = (title_matches * 2) + text_matches
            
            if total_score > 0:
                country_scores[country] = total_score
        
        if not country_scores:
            return "Unknown"
        
        # If only one country found, return it
        if len(country_scores) == 1:
            return list(country_scores.keys())[0]
        
        # If multiple countries found, detect conflict and pick primary actor
        countries_found = list(country_scores.keys())
        
        # Check if this is a known conflict pair
        for pair, primary in CONFLICT_PAIRS.items():
            if len(pair & set(countries_found)) == 2:  # Both countries in pair are mentioned
                # Verify conflict keywords present
                if any(kw in text_lower for kw in CONFLICT_KEYWORDS):
                    return primary
        
        # Otherwise return highest scoring country
        return max(country_scores, key=country_scores.get)

    def combined_war_risk(self, sentiment_score: float, keyword_score: float) -> float:
        sentiment_risk = max(0.0, -sentiment_score)
        combined = 0.65 * keyword_score + 0.35 * sentiment_risk
        return round(min(1.0, combined), 4)


war_risk_service = WarRiskService()
