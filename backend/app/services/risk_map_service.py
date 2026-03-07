from datetime import datetime, timezone
from typing import Any

import requests


class RiskMapService:
    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _fetch_gdelt_geo(self, query: str, max_records: int = 40) -> list[dict]:
        try:
            response = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": query,
                    "mode": "Geo",
                    "maxrecords": max_records,
                    "format": "json",
                    "sort": "DateDesc",
                    "timespan": "3days",
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        features = payload.get("features", []) or payload.get("articles", []) or []
        out = []
        for idx, item in enumerate(features):
            lat = (
                item.get("lat")
                or item.get("latitude")
                or item.get("locationlat")
                or item.get("LocationLat")
            )
            lon = (
                item.get("lon")
                or item.get("lng")
                or item.get("longitude")
                or item.get("locationlong")
                or item.get("LocationLong")
            )
            if lat is None or lon is None:
                continue

            out.append(
                {
                    "id": str(item.get("id") or f"gdelt-{idx}"),
                    "name": item.get("name") or item.get("location") or item.get("title") or "Unknown",
                    "lat": self._to_float(lat),
                    "lon": self._to_float(lon),
                    "intensity": self._to_float(item.get("count") or item.get("toneabs") or item.get("sourcecount"), 1.0),
                    "source": "https://www.gdeltproject.org/",
                }
            )
        return out

    def latest_layers(self) -> dict:
        war_points = self._fetch_gdelt_geo(
            "war OR invasion OR missile OR bombing OR artillery OR frontline OR ceasefire",
            max_records=60,
        )[:25]
        nuclear_points = self._fetch_gdelt_geo(
            "nuclear OR reactor OR IAEA OR uranium enrichment OR missile test",
            max_records=50,
        )[:25]
        bunker_points = self._fetch_gdelt_geo(
            "bunker OR underground base OR hardened facility OR command bunker",
            max_records=30,
        )[:20]

        # Precision anchors for critical facilities/chokepoints.
        nuclear_static = [
            {
                "id": "nuke-zap",
                "name": "Zaporizhzhia NPP",
                "lat": 47.511,
                "lon": 34.585,
                "intensity": 1.0,
                "source": "https://www.iaea.org/newscenter/focus/ukraine",
            },
            {
                "id": "nuke-natanz",
                "name": "Natanz Facility",
                "lat": 33.724,
                "lon": 51.726,
                "intensity": 1.0,
                "source": "https://www.iaea.org/",
            },
            {
                "id": "nuke-buschr",
                "name": "Bushehr NPP",
                "lat": 28.829,
                "lon": 50.886,
                "intensity": 1.0,
                "source": "https://www.iaea.org/",
            },
        ]

        chokepoints = [
            {
                "id": "choke-hormuz",
                "name": "Strait of Hormuz",
                "lat": 26.6,
                "lon": 56.5,
                "intensity": 1.0,
                "source": "https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints",
            },
            {
                "id": "choke-suez",
                "name": "Suez Canal",
                "lat": 30.5,
                "lon": 32.55,
                "intensity": 1.0,
                "source": "https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints",
            },
            {
                "id": "choke-malacca",
                "name": "Strait of Malacca",
                "lat": 2.5,
                "lon": 101.0,
                "intensity": 1.0,
                "source": "https://www.eia.gov/international/analysis/special-topics/World_Oil_Transit_Chokepoints",
            },
        ]

        return {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "war_zones": war_points,
            "nuclear_sites": (nuclear_points + nuclear_static)[:35],
            "bunkers": bunker_points,
            "chokepoints": chokepoints,
        }


risk_map_service = RiskMapService()
