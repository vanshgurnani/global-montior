from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
from pymongo.database import Database


COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "ukraine": (48.3794, 31.1656),
    "russia": (61.5240, 105.3188),
    "israel": (31.0461, 34.8516),
    "palestine": (31.9522, 35.2332),
    "gaza": (31.3547, 34.3088),
    "syria": (34.8021, 38.9968),
    "lebanon": (33.8547, 35.8623),
    "iran": (32.4279, 53.6880),
    "iraq": (33.2232, 43.6793),
    "yemen": (15.5527, 48.5164),
    "sudan": (12.8628, 30.2176),
    "myanmar": (21.9162, 95.9560),
    "taiwan": (23.6978, 120.9605),
    "china": (35.8617, 104.1954),
    "armenia": (40.0691, 45.0382),
    "azerbaijan": (40.1431, 47.5769),
}

WAR_ZONE_BASELINES: list[dict[str, Any]] = [
    {"id": "baseline-ukraine", "name": "Ukraine Frontline", "country": "Ukraine", "lat": 48.4, "lon": 31.2, "intensity": 3.4, "confidence": "confirmed", "status": "ongoing"},
    {"id": "baseline-gaza", "name": "Gaza-Israel Theater", "country": "Israel", "lat": 31.4, "lon": 34.3, "intensity": 3.2, "confidence": "confirmed", "status": "ongoing"},
    {"id": "baseline-sudan", "name": "Sudan Civil War Zone", "country": "Sudan", "lat": 15.6, "lon": 30.3, "intensity": 2.8, "confidence": "confirmed", "status": "ongoing"},
    {"id": "baseline-yemen-redsea", "name": "Red Sea / Yemen Escalation", "country": "Yemen", "lat": 15.2, "lon": 43.1, "intensity": 2.5, "confidence": "emerging", "status": "escalation-risk"},
    {"id": "baseline-lebanon-israel", "name": "Lebanon-Israel Border Tension", "country": "Lebanon", "lat": 33.2, "lon": 35.5, "intensity": 2.4, "confidence": "emerging", "status": "flashpoint"},
    {"id": "baseline-taiwan", "name": "Taiwan Strait Flashpoint", "country": "Taiwan", "lat": 23.8, "lon": 121.0, "intensity": 2.2, "confidence": "emerging", "status": "upcoming-risk"},
    {"id": "baseline-korea", "name": "Korean Peninsula Missile Tension", "country": "South Korea", "lat": 37.5, "lon": 127.9, "intensity": 2.1, "confidence": "low-confidence", "status": "upcoming-risk"},
    {"id": "baseline-armenia-azer", "name": "Armenia-Azerbaijan Border", "country": "Armenia", "lat": 40.2, "lon": 45.1, "intensity": 1.9, "confidence": "low-confidence", "status": "flashpoint"},
]

CURRENCY_RISK_BY_COUNTRY: dict[str, dict[str, str]] = {
    "ukraine": {"currency": "EUR", "reason": "Proximity war shock in Europe can weaken regional growth and pressure EUR risk premium."},
    "russia": {"currency": "RUB", "reason": "Sanctions, capital controls, and commodity volatility drive RUB stress."},
    "israel": {"currency": "ILS", "reason": "Security risk and fiscal strain can pressure ILS and local assets."},
    "sudan": {"currency": "SDG", "reason": "Conflict-driven instability can accelerate inflation and currency devaluation."},
    "yemen": {"currency": "USD", "reason": "Red Sea disruption risk can strengthen USD via global risk-off flows."},
    "lebanon": {"currency": "LBP", "reason": "Escalation risk worsens confidence in domestic currency conditions."},
    "taiwan": {"currency": "TWD", "reason": "Taiwan Strait tensions can trigger semiconductor-linked FX repricing."},
    "china": {"currency": "CNY", "reason": "Geopolitical risk and trade pressure can increase CNY volatility."},
    "south korea": {"currency": "KRW", "reason": "Regional military tension and tech export sensitivity impact KRW."},
    "armenia": {"currency": "AMD", "reason": "Border escalation risk can raise sovereign and FX risk premiums."},
    "azerbaijan": {"currency": "AZN", "reason": "Conflict and energy corridor risk can amplify AZN sensitivity."},
    "iran": {"currency": "IRR", "reason": "Sanctions and military escalation can intensify currency weakness."},
}

OSINT_OVERLAY_QUERIES: dict[str, str] = {
    "fire_hotspots": "wildfire OR forest fire OR satellite hotspot OR industrial fire OR thermal anomaly",
    "ship_density": "shipping lane congestion OR vessel traffic OR AIS disruption OR port backlog OR maritime route",
    "flight_diversions": "flight diversion OR airspace closure OR NOTAM OR rerouted flights OR aviation disruption",
}

OSINT_OVERLAY_LIMITS: dict[str, int] = {
    "fire_hotspots": 30,
    "ship_density": 25,
    "flight_diversions": 25,
}

OSINT_OVERLAY_FALLBACKS: dict[str, list[dict[str, Any]]] = {
    "fire_hotspots": [
        {"id": "fire-ca", "name": "California Fire Belt", "lat": 36.8, "lon": -119.7, "intensity": 2.4, "source": "https://firms.modaps.eosdis.nasa.gov/"},
        {"id": "fire-amazon", "name": "Amazon Basin Burn Zone", "lat": -8.8, "lon": -63.9, "intensity": 2.0, "source": "https://firms.modaps.eosdis.nasa.gov/"},
        {"id": "fire-aus", "name": "SE Australia Bushfire Corridor", "lat": -36.3, "lon": 147.7, "intensity": 2.1, "source": "https://firms.modaps.eosdis.nasa.gov/"},
    ],
    "ship_density": [
        {"id": "ship-singapore", "name": "Singapore Strait Traffic Cluster", "lat": 1.18, "lon": 103.8, "intensity": 2.6, "source": "https://www.marinetraffic.com/"},
        {"id": "ship-rotterdam", "name": "North Sea - Rotterdam Approaches", "lat": 51.95, "lon": 3.8, "intensity": 2.0, "source": "https://www.marinetraffic.com/"},
        {"id": "ship-la", "name": "Los Angeles / Long Beach Queue", "lat": 33.6, "lon": -118.2, "intensity": 1.9, "source": "https://www.marinetraffic.com/"},
    ],
    "flight_diversions": [
        {"id": "flight-middle-east", "name": "Levant Airspace Reroutes", "lat": 33.5, "lon": 38.0, "intensity": 2.3, "source": "https://www.flightradar24.com/"},
        {"id": "flight-black-sea", "name": "Black Sea Diversion Arc", "lat": 44.8, "lon": 33.6, "intensity": 2.0, "source": "https://www.flightradar24.com/"},
        {"id": "flight-red-sea", "name": "Red Sea Corridor Reroutes", "lat": 20.6, "lon": 39.4, "intensity": 2.1, "source": "https://www.flightradar24.com/"},
    ],
}


class RiskMapService:
    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _extract_lat_lon(self, item: dict[str, Any]) -> tuple[Optional[float], Optional[float]]:
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
        if lat is not None and lon is not None:
            return self._to_float(lat), self._to_float(lon)

        geometry = item.get("geometry") or {}
        coords = geometry.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            # GeoJSON coordinates are [lon, lat].
            return self._to_float(coords[1]), self._to_float(coords[0])

        return None, None

    def _feature_name(self, item: dict[str, Any], default: str = "Unknown") -> str:
        props = item.get("properties") or {}
        return str(
            item.get("name")
            or props.get("name")
            or item.get("location")
            or item.get("title")
            or props.get("title")
            or default
        )

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
                    "timespan": "7days",
                },
                headers={"User-Agent": "global-intelligence-monitor/1.0"},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        features = payload.get("features", []) or payload.get("articles", []) or []
        out = []
        for idx, item in enumerate(features):
            lat, lon = self._extract_lat_lon(item)
            if lat is None or lon is None:
                # Some GDELT variants attach geos under `locations`.
                locations = item.get("locations")
                if isinstance(locations, list):
                    for lidx, loc in enumerate(locations):
                        ll_lat, ll_lon = self._extract_lat_lon(loc if isinstance(loc, dict) else {})
                        if ll_lat is None or ll_lon is None:
                            continue
                        out.append(
                            {
                                "id": str(item.get("id") or f"gdelt-{idx}-loc-{lidx}"),
                                "name": self._feature_name(loc if isinstance(loc, dict) else {}, self._feature_name(item)),
                                "lat": ll_lat,
                                "lon": ll_lon,
                                "intensity": self._to_float(
                                    item.get("count") or item.get("toneabs") or item.get("sourcecount"),
                                    1.0,
                                ),
                                "source": "https://www.gdeltproject.org/",
                            }
                        )
                continue

            out.append(
                {
                    "id": str(item.get("id") or f"gdelt-{idx}"),
                    "name": self._feature_name(item),
                    "lat": lat,
                    "lon": lon,
                    "intensity": self._to_float(item.get("count") or item.get("toneabs") or item.get("sourcecount"), 1.0),
                    "source": "https://www.gdeltproject.org/",
                }
            )
        # Keep unique points by rounded coordinates+name to reduce duplicates in dense feeds.
        dedup: dict[str, dict[str, Any]] = {}
        for row in out:
            key = f"{round(self._to_float(row.get('lat')),3)}:{round(self._to_float(row.get('lon')),3)}:{str(row.get('name','')).strip().lower()}"
            if key not in dedup:
                dedup[key] = row
        return list(dedup.values())

    def _currency_profile(self, country: str, point_name: str = "") -> dict[str, str]:
        key = (country or "").strip().lower()
        if key in CURRENCY_RISK_BY_COUNTRY:
            return CURRENCY_RISK_BY_COUNTRY[key]

        lower_name = (point_name or "").lower()
        for ck, profile in CURRENCY_RISK_BY_COUNTRY.items():
            if ck in lower_name:
                return profile

        return {
            "currency": "USD",
            "reason": "Global tension usually drives defensive USD demand and broader FX volatility.",
        }

    def _attach_currency_risk(self, points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for point in points:
            name = str(point.get("name", ""))
            country_guess = str(point.get("country", "")).strip()
            if not country_guess and " conflict zone" in name.lower():
                country_guess = name.lower().replace(" conflict zone", "").strip().title()
            profile = self._currency_profile(country_guess, name)
            enriched = dict(point)
            enriched["currency"] = profile["currency"]
            enriched["tension_risk"] = round(min(1.0, max(0.2, self._to_float(point.get("intensity"), 1.0) / 4.0)), 3)
            enriched["reason"] = profile["reason"]
            out.append(enriched)
        return out

    def _top_currency_risks(self, war_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bucket: dict[str, dict[str, Any]] = {}
        for p in war_points:
            ccy = str(p.get("currency") or "USD")
            score = self._to_float(p.get("tension_risk"), 0.3)
            if ccy not in bucket:
                bucket[ccy] = {"currency": ccy, "score": 0.0, "count": 0, "reason": str(p.get("reason", ""))}
            bucket[ccy]["score"] += score
            bucket[ccy]["count"] += 1
        rows = list(bucket.values())
        for row in rows:
            row["score"] = round(min(1.0, row["score"] / max(row["count"], 1)), 4)
        rows.sort(key=lambda x: (x["score"], x["count"]), reverse=True)
        return rows[:8]

    def _war_points_from_articles(self, db: Database, limit: int = 40) -> list[dict]:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)
        pipeline = [
            {
                "$match": {
                    "published_at": {"$gte": since},
                    "$or": [
                        {"war_risk_score": {"$gte": 0.55}},
                        {"keyword_score": {"$gte": 0.4}},
                        {"matched_keywords": {"$in": ["war", "missile", "invasion", "military"]}},
                    ]
                }
            },
            {
                "$group": {
                    "_id": "$country",
                    "avg_risk": {"$avg": "$war_risk_score"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"avg_risk": -1, "count": -1}},
            {"$limit": max(1, min(limit, 80))},
        ]

        points: list[dict] = []
        for idx, row in enumerate(db.articles.aggregate(pipeline)):
            country = str(row.get("_id") or "").strip()
            if not country:
                continue
            centroid = COUNTRY_CENTROIDS.get(country.lower())
            if not centroid:
                continue
            avg_risk = self._to_float(row.get("avg_risk"), 0.6)
            count = int(row.get("count") or 1)
            strength = avg_risk * (1.0 + min(count / 6.0, 1.0))
            if strength >= 1.2:
                confidence = "confirmed"
            elif strength >= 0.75:
                confidence = "emerging"
            else:
                confidence = "low-confidence"
            points.append(
                {
                    "id": f"live-war-{idx}",
                    "name": f"{country} Conflict Zone",
                    "country": country,
                    "lat": centroid[0],
                    "lon": centroid[1],
                    "intensity": round(min(4.0, max(1.0, avg_risk * 4 + min(count / 6, 1.0))), 2),
                    "source": "internal-live-news-24h",
                    "confidence": confidence,
                    "status": "live-24h",
                }
            )
        return points

    def _normalize_overlay_keys(self, overlay_keys: Optional[list[str]] = None) -> list[str]:
        if not overlay_keys:
            return list(OSINT_OVERLAY_QUERIES.keys())
        cleaned: list[str] = []
        seen: set[str] = set()
        for key in overlay_keys:
            k = str(key or "").strip().lower()
            if k in OSINT_OVERLAY_QUERIES and k not in seen:
                cleaned.append(k)
                seen.add(k)
        return cleaned

    def _osint_overlays(self, overlay_keys: Optional[list[str]] = None) -> dict[str, list[dict[str, Any]]]:
        overlays: dict[str, list[dict[str, Any]]] = {}
        for key in self._normalize_overlay_keys(overlay_keys):
            points = self._fetch_gdelt_geo(OSINT_OVERLAY_QUERIES[key], max_records=OSINT_OVERLAY_LIMITS.get(key, 20))
            overlays[key] = points[: OSINT_OVERLAY_LIMITS.get(key, 20)] or list(OSINT_OVERLAY_FALLBACKS.get(key, []))
        return overlays

    def latest_layers(
        self,
        db: Database,
        include_osint: bool = False,
        overlay_keys: Optional[list[str]] = None,
    ) -> dict:
        war_points_gdelt = self._fetch_gdelt_geo(
            "war OR invasion OR missile OR bombing OR artillery OR frontline OR ceasefire",
            max_records=140,
        )[:70]
        war_points_live = self._war_points_from_articles(db, limit=30)
        # Include baseline ongoing/upcoming flashpoints and top up with live+gdelt.
        raw_war_points = (war_points_live + WAR_ZONE_BASELINES + war_points_gdelt)[:60]
        war_points = self._attach_currency_risk(raw_war_points)
        top_currency_risks = self._top_currency_risks(war_points)
        nuclear_points = self._fetch_gdelt_geo(
            "nuclear OR reactor OR IAEA OR uranium enrichment OR missile test",
            max_records=90,
        )[:45]
        bunker_points = self._fetch_gdelt_geo(
            "bunker OR underground base OR hardened facility OR command bunker",
            max_records=60,
        )[:30]

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

        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "war_zones": war_points,
            "nuclear_sites": (nuclear_points + nuclear_static)[:35],
            "bunkers": bunker_points,
            "chokepoints": chokepoints,
            "top_currency_risks": top_currency_risks,
            "diagnostics": {
                "war_live_count": len(war_points_live),
                "war_gdelt_count": len(war_points_gdelt),
                "war_baseline_count": len(WAR_ZONE_BASELINES),
                "nuclear_gdelt_count": len(nuclear_points),
                "bunker_gdelt_count": len(bunker_points),
            },
        }
        if include_osint:
            overlays = self._osint_overlays(overlay_keys)
            payload["osint_overlays"] = overlays
            payload["diagnostics"]["osint_counts"] = {k: len(v) for k, v in overlays.items()}
        return payload


risk_map_service = RiskMapService()
