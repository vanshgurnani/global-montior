"""
Ground truth data services for training/validation instead of guessing.

Sources:
- Conflict data: ACLED (Armed Conflict Location & Event Data) – requires ACLED_API_KEY + ACLED_EMAIL
- Economic indicators: World Bank API (free, no key)
- Market volatility: CBOE VIX via yfinance (^VIX)
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
import yfinance as yf
from pymongo.database import Database

from app.core.config import settings

# World Bank indicators: GDP growth (%), inflation (%), debt (% GDP)
WB_INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
    "FP.CPI.TOTL.ZG": "inflation_pct",
    "GC.DOD.TOTL.GD.ZS": "debt_pct_gdp",
}
WB_BASE = "https://api.worldbank.org/v2"
ACLED_BASE = "https://api.acleddata.com/acled/read"


class GroundTruthService:
    """Fetch and store ground truth datasets for model training/validation."""

    def ingest_all(self, db: Database) -> dict[str, Any]:
        """Ingest from all configured sources. Returns stats."""
        stats: dict[str, Any] = {
            "vix": {"fetched": 0, "stored": 0, "error": None},
            "world_bank": {"fetched": 0, "stored": 0, "error": None},
            "acled": {"fetched": 0, "stored": 0, "error": None, "skipped": "no_credentials"},
        }

        stats["vix"] = self._ingest_vix(db)
        stats["world_bank"] = self._ingest_world_bank(db)
        if settings.acled_api_key and settings.acled_email:
            stats["acled"] = self._ingest_acled(db)
        return stats

    def _ingest_vix(self, db: Database) -> dict[str, Any]:
        """Store CBOE VIX history for validation. Already used in training via yfinance."""
        try:
            ticker = yf.Ticker("^VIX")
            hist = ticker.history(period="2y")
            if hist.empty or len(hist) < 10:
                return {"fetched": 0, "stored": 0, "error": "insufficient_vix_data"}

            db.ground_truth_vix.delete_many({"source": "yfinance"})
            docs = []
            for dt, row in hist.iterrows():
                docs.append({
                    "date": dt.date().isoformat() if hasattr(dt, "date") else str(dt)[:10],
                    "close": float(row.get("Close", 0)),
                    "open": float(row.get("Open", 0)),
                    "high": float(row.get("High", 0)),
                    "low": float(row.get("Low", 0)),
                    "source": "yfinance",
                    "ingested_at": datetime.now(timezone.utc),
                })
            if docs:
                db.ground_truth_vix.insert_many(docs)
            return {"fetched": len(docs), "stored": len(docs), "error": None}
        except Exception as exc:
            return {"fetched": 0, "stored": 0, "error": str(exc)}

    def _ingest_world_bank(self, db: Database) -> dict[str, Any]:
        """Fetch World Bank economic indicators (GDP growth, inflation, debt)."""
        try:
            end_year = datetime.now(timezone.utc).year
            start_year = end_year - 6
            date_range = f"{start_year}:{end_year}"
            stored = 0

            for indicator_code, field_name in WB_INDICATORS.items():
                url = f"{WB_BASE}/country/all/indicator/{indicator_code}"
                params = {"date": date_range, "format": "json", "per_page": 2500}
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                if not data or len(data) < 2:
                    continue
                records = data[1]
                if not records:
                    continue

                db.ground_truth_economic.delete_many({"indicator": field_name})
                docs = []
                for r in records:
                    if r.get("value") is None:
                        continue
                    docs.append({
                        "country_iso": r.get("countryiso3code", ""),
                        "country": r.get("country", {}).get("value", ""),
                        "year": int(r.get("date", 0)),
                        "value": float(r["value"]),
                        "indicator": field_name,
                        "indicator_code": indicator_code,
                        "ingested_at": datetime.now(timezone.utc),
                    })
                if docs:
                    db.ground_truth_economic.insert_many(docs)
                    stored += len(docs)

            return {"fetched": stored, "stored": stored, "error": None}
        except Exception as exc:
            return {"fetched": 0, "stored": 0, "error": str(exc)}

    def _ingest_acled(self, db: Database) -> dict[str, Any]:
        """Fetch ACLED conflict events. Requires ACLED_API_KEY and ACLED_EMAIL from developer.acleddata.com."""
        try:
            email = (settings.acled_email or "").strip()
            key = (settings.acled_api_key or "").strip()
            if not email or not key:
                return {"fetched": 0, "stored": 0, "error": None, "skipped": "no_credentials"}

            end_year = datetime.now(timezone.utc).year
            start_year = end_year - 2
            # ACLED read API: key + email as query params (see acleddata.com/api-documentation)
            url = "https://api.acleddata.com/acled/read"
            params = {
                "key": key,
                "email": email,
                "limit": 5000,
                "year": f"{start_year}|{end_year}",
                "fields": "event_id_cnty|event_date|event_type|country|fatalities|latitude|longitude",
                "_format": "json",
            }
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 401 or resp.status_code == 403:
                return {"fetched": 0, "stored": 0, "error": "auth_failed", "skipped": None}
            resp.raise_for_status()
            data = resp.json()
            if not data or "data" not in data:
                return {"fetched": 0, "stored": 0, "error": "no_data", "skipped": None}

            events = data.get("data", [])
            db.ground_truth_conflicts.delete_many({"source": "acled"})
            docs = []
            for ev in events[:3000]:  # Cap for storage
                event_date = ev.get("event_date", "")[:10]
                docs.append({
                    "event_id": ev.get("event_id_cnty", ""),
                    "event_date": event_date,
                    "event_type": ev.get("event_type", ""),
                    "country": ev.get("country", ""),
                    "fatalities": int(ev.get("fatalities") or 0),
                    "lat": ev.get("latitude"),
                    "lon": ev.get("longitude"),
                    "source": "acled",
                    "ingested_at": datetime.now(timezone.utc),
                })
            if docs:
                db.ground_truth_conflicts.insert_many(docs)
            return {"fetched": len(events), "stored": len(docs), "error": None, "skipped": None}
        except requests.RequestException as exc:
            return {"fetched": 0, "stored": 0, "error": str(exc), "skipped": None}
        except Exception as exc:
            return {"fetched": 0, "stored": 0, "error": str(exc), "skipped": None}

    def get_vix_for_date(self, db: Database, date_str: str) -> Optional[float]:
        """Get VIX close for a given date (YYYY-MM-DD)."""
        row = db.ground_truth_vix.find_one({"date": date_str, "source": "yfinance"})
        return float(row["close"]) if row else None

    def get_economic_for_year(self, db: Database, year: int, country_iso: str = "USA") -> dict[str, float]:
        """Get World Bank indicators for a year/country. country_iso e.g. USA, CHN."""
        cursor = db.ground_truth_economic.find({"year": year, "country_iso": country_iso})
        return {r["indicator"]: r["value"] for r in cursor}

    def get_conflict_counts_by_country(self, db: Database, start_date: str, end_date: str) -> dict[str, int]:
        """Get conflict event counts by country in date range."""
        pipeline = [
            {"$match": {"event_date": {"$gte": start_date, "$lte": end_date}, "source": "acled"}},
            {"$group": {"_id": "$country", "count": {"$sum": 1}, "fatalities": {"$sum": "$fatalities"}}},
        ]
        rows = list(db.ground_truth_conflicts.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in rows if r.get("_id")}


ground_truth_service = GroundTruthService()
