from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo.database import Database

from app.services.market_pipeline import market_pipeline
from app.services.news_service import news_service
from app.services.event_classification_service import EventClassificationService


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return _utc_now()


def _clip(v: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(v)))


def _escalation_label(score: float) -> str:
    if score >= 0.72:
        return "Critical"
    if score >= 0.52:
        return "High"
    if score >= 0.32:
        return "Elevated"
    return "Guarded"


def _risk_label(score: float) -> str:
    if score >= 0.66:
        return "High"
    if score >= 0.33:
        return "Medium"
    return "Low"


class IntelligenceService:
    CONFLICTS = [
        {
            "id": "russia-ukraine",
            "name": "Russia-Ukraine War",
            "aliases": ["russia", "ukraine", "donbas", "crimea", "kyiv", "moscow"],
        },
        {
            "id": "israel-hamas",
            "name": "Israel-Hamas War",
            "aliases": ["israel", "hamas", "gaza", "idf", "west bank", "hezbollah"],
        },
        {
            "id": "taiwan-strait",
            "name": "Taiwan Strait Tensions",
            "aliases": ["taiwan", "strait", "pla", "beijing", "south china sea"],
        },
    ]

    CLASSIFIER_RULES = [
        ("war", ["war", "invasion", "offensive", "ceasefire", "frontline", "missile", "drone"]),
        ("sanctions", ["sanction", "export ban", "trade restriction", "tariff", "embargo"]),
        ("diplomacy", ["summit", "talks", "diplomatic", "agreement", "treaty", "negotiation"]),
        ("economic_crisis", ["recession", "inflation", "debt", "currency", "default", "bank run"]),
        ("terrorism", ["terror", "bombing", "hostage", "insurgent", "attack"]),
    ]

    MILITARY_WORDS = ["missile", "mobilization", "troop", "naval", "drill", "airstrike", "fighter", "submarine"]
    NUCLEAR_WORDS = ["nuclear", "reactor", "uranium", "iaea", "enrichment", "warhead"]
    UNREST_WORDS = ["protest", "riot", "strike", "demonstration", "curfew", "coup", "civil unrest"]
    ENERGY_WORDS = ["oil", "crude", "natural gas", "lng", "pipeline", "energy", "opec"]
    HIGH_IMPACT_WORDS = [
        "missile",
        "mobilization",
        "sanctions",
        "airstrike",
        "nuclear",
        "blockade",
        "drone attack",
    ]

    CHOKEPOINTS = [
        {"name": "Strait of Hormuz", "aliases": ["hormuz", "persian gulf"]},
        {"name": "Suez Canal", "aliases": ["suez", "red sea"]},
        {"name": "Bab el-Mandeb", "aliases": ["bab el-mandeb", "yemen"]},
        {"name": "Taiwan Strait", "aliases": ["taiwan strait", "taiwan"]},
    ]

    NUCLEAR_ZONES = [
        {"name": "Zaporizhzhia", "lat": 47.5, "lon": 34.6},
        {"name": "Natanz", "lat": 33.7, "lon": 51.7},
        {"name": "Bushehr", "lat": 28.9, "lon": 50.9},
        {"name": "Yongbyon", "lat": 39.8, "lon": 125.8},
    ]

    REGION_BY_COUNTRY = {
        "Ukraine": "Europe",
        "Russia": "Europe",
        "Israel": "Middle East",
        "Iran": "Middle East",
        "Saudi Arabia": "Middle East",
        "Taiwan": "Asia-Pacific",
        "China": "Asia-Pacific",
        "Japan": "Asia-Pacific",
        "South Korea": "Asia-Pacific",
        "United States": "North America",
        "Germany": "Europe",
        "France": "Europe",
        "India": "South Asia",
    }

    def _stale_or_missing(self, db: Database, collection: str, time_field: str, min_rows: int, max_age_hours: int) -> bool:
        now = _utc_now()
        horizon = now - timedelta(hours=max_age_hours)
        recent_count = db[collection].count_documents({time_field: {"$gte": horizon}})
        return recent_count < min_rows

    def _ensure_live_inputs(self, db: Database) -> dict[str, Any]:
        status = {
            "news_refreshed": False,
            "markets_refreshed": False,
            "news_reason": "",
            "markets_reason": "",
        }
        try:
            if self._stale_or_missing(db, "articles", "published_at", min_rows=24, max_age_hours=12):
                result = news_service.ingest_with_stats(db)
                status["news_refreshed"] = bool(result.get("inserted", 0) > 0)
                status["news_reason"] = f"auto-refresh (inserted={int(result.get('inserted', 0))})"
        except Exception as exc:
            status["news_reason"] = f"auto-refresh failed: {exc.__class__.__name__}"

        try:
            if self._stale_or_missing(db, "market_snapshots", "as_of", min_rows=10, max_age_hours=12):
                refreshed = market_pipeline.refresh(db)
                status["markets_refreshed"] = refreshed > 0
                status["markets_reason"] = f"auto-refresh (refreshed={int(refreshed)})"
        except Exception as exc:
            status["markets_reason"] = f"auto-refresh failed: {exc.__class__.__name__}"

        return status

    def _latest_articles(self, db: Database, limit: int = 250) -> list[dict[str, Any]]:
        return list(db.articles.find({}, {"_id": 0}).sort("published_at", -1).limit(limit))

    def _latest_markets(self, db: Database) -> list[dict[str, Any]]:
        return list(db.market_snapshots.find({}, {"_id": 0}).sort("prob_up", -1))

    def _text(self, article: dict[str, Any]) -> str:
        title = str(article.get("title", ""))
        summary = str(article.get("summary", ""))
        return f"{title} {summary}".strip().lower()

    def _classify_event(self, article: dict[str, Any]) -> dict[str, Any]:
        text = self._text(article)
        stored_type = str(article.get("event_type") or "").strip()
        stored_sev = article.get("event_severity_score")
        if stored_type:
            category = EventClassificationService.LABELS.get(stored_type, stored_type.replace("_", " "))
            severity = _clip(float(stored_sev)) if stored_sev is not None else _clip(float(article.get("war_risk_score", 0.0)))
            return {
                "category": category,
                "severity": round(float(severity), 4),
                "high_impact": any(word in text for word in self.HIGH_IMPACT_WORDS) or float(severity) >= 0.7,
            }

        category = "diplomacy"
        best_hits = 0
        for label, words in self.CLASSIFIER_RULES:
            hits = sum(1 for w in words if w in text)
            if hits > best_hits:
                best_hits = hits
                category = label
        severity = _clip(
            0.55 * float(article.get("war_risk_score", 0.0))
            + 0.25 * float(article.get("keyword_score", 0.0))
            + 0.20 * max(0.0, -float(article.get("sentiment_score", 0.0)))
        )
        return {
            "category": category,
            "severity": round(severity, 4),
            "high_impact": any(word in text for word in self.HIGH_IMPACT_WORDS) or severity >= 0.7,
        }

    def _brief(self, article: dict[str, Any], cls: dict[str, Any]) -> str:
        title = str(article.get("title", "")).strip()
        country = str(article.get("country", "Unknown")).strip() or "Unknown"
        risk = _risk_label(float(article.get("war_risk_score", 0.0)))
        return f"{title[:140]} | {country} | {cls['category']} | {risk} risk"

    def _conflict_score(self, items: list[dict[str, Any]]) -> float:
        if not items:
            return 0.15
        avg_war = sum(float(x.get("war_risk_score", 0.0)) for x in items) / len(items)
        avg_keyword = sum(float(x.get("keyword_score", 0.0)) for x in items) / len(items)
        avg_negative = sum(max(0.0, -float(x.get("sentiment_score", 0.0))) for x in items) / len(items)
        return _clip(0.5 * avg_war + 0.3 * avg_keyword + 0.2 * avg_negative)

    def _articles_for_aliases(self, articles: list[dict[str, Any]], aliases: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for a in articles:
            t = self._text(a)
            if any(alias in t for alias in aliases):
                out.append(a)
        return out

    def _sentiment_by_country(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for a in articles:
            buckets[str(a.get("country", "Unknown"))].append(a)
        result = []
        for country, items in buckets.items():
            avg_sentiment = sum(float(x.get("sentiment_score", 0.0)) for x in items) / len(items)
            avg_risk = sum(float(x.get("war_risk_score", 0.0)) for x in items) / len(items)
            result.append(
                {
                    "country": country,
                    "sentiment": round(avg_sentiment, 4),
                    "war_risk": round(avg_risk, 4),
                    "articles": len(items),
                }
            )
        result.sort(key=lambda x: x["war_risk"], reverse=True)
        return result[:40]

    def _global_risk_index(self, articles: list[dict[str, Any]], markets: list[dict[str, Any]]) -> dict[str, Any]:
        if articles:
            war = sum(float(x.get("war_risk_score", 0.0)) for x in articles) / len(articles)
            energy_mentions = sum(1 for x in articles if any(w in self._text(x) for w in self.ENERGY_WORDS))
            energy = _clip((energy_mentions / max(len(articles), 1)) * 1.6)
        else:
            war = 0.2
            energy = 0.2

        if markets:
            avg_down = sum(float(x.get("prob_down", 0.5)) for x in markets) / len(markets)
            avg_vix = sum(float(x.get("vix_proxy", 18.0)) for x in markets) / len(markets)
            market = _clip(0.7 * avg_down + 0.3 * _clip((avg_vix - 12) / 28))
        else:
            market = 0.25

        instability = _clip(0.45 * war + 0.30 * energy + 0.25 * market)
        return {
            "war_risk": round(war, 4),
            "energy_risk": round(energy, 4),
            "market_risk": round(market, 4),
            "global_instability_score": round(instability, 4),
            "risk_level": _risk_label(instability),
        }

    def _market_impact(self, markets: list[dict[str, Any]], risk_index: dict[str, Any]) -> list[dict[str, Any]]:
        # Prefer deterministic symbol selection so "Gold" and "Defense" don't flip between
        # multiple matching rows based on sort order.
        asset_specs: dict[str, dict[str, list[str]]] = {
            "S&P 500": {"preferred_symbols": ["^GSPC", "SPY"], "keys": ["s&p 500", "spdr s&p 500", "^gspc", "spy"]},
            "Nasdaq": {"preferred_symbols": ["^IXIC", "QQQ"], "keys": ["nasdaq", "^ixic", "qqq"]},
            "Oil": {"preferred_symbols": ["CL=F", "USO"], "keys": ["cl=f", "crude", "united states oil", "uso"]},
            "Gold": {"preferred_symbols": ["GLD", "GC=F"], "keys": ["gld", "gc=f", "spdr gold", "gold futures"]},
            "Bitcoin": {"preferred_symbols": ["BTC-USD"], "keys": ["btc-usd", "bitcoin"]},
            "Defense": {"preferred_symbols": ["ITA", "RTX", "LMT", "NOC"], "keys": ["ita", "aerospace", "defense", "lockheed", "raytheon", "northrop"]},
        }

        by_symbol: dict[str, dict[str, Any]] = {}
        for row in markets:
            sym = str(row.get("symbol", "")).strip()
            if sym:
                by_symbol[sym.upper()] = row

        results: list[dict[str, Any]] = []
        for asset, spec in asset_specs.items():
            found = None
            for sym in spec.get("preferred_symbols", []):
                found = by_symbol.get(sym.upper())
                if found:
                    break

            if not found:
                best_row = None
                best_score = 0.0
                keys = [k.lower() for k in spec.get("keys", [])]
                for row in markets:
                    name = str(row.get("name", "")).lower()
                    symbol = str(row.get("symbol", "")).lower()
                    text = f"{name} {symbol}".strip()
                    hits = sum(1 for k in keys if k and k in text)
                    if hits <= 0:
                        continue
                    score = hits + (0.5 if symbol in keys else 0.0)
                    if score > best_score:
                        best_score = score
                        best_row = row
                found = best_row
            if found:
                down_prob = float(found.get("prob_down", 0.5))
                ret = float(found.get("predicted_return_5d", 0.0) or 0.0)
                risk = _clip(0.55 * down_prob + 0.45 * _clip(abs(ret) / 4.0))
                results.append(
                    {
                        "asset": asset,
                        "price": round(float(found.get("price", 0.0)), 4),
                        "predicted_return_5d": round(ret, 4),
                        "prob_down": round(down_prob, 4),
                        "impact_risk": round(risk, 4),
                    }
                )
            else:
                baseline = float(risk_index["global_instability_score"])
                results.append(
                    {
                        "asset": asset,
                        "price": 0.0,
                        "predicted_return_5d": round((0.5 - baseline) * 1.8, 4),
                        "prob_down": round(_clip(0.45 + baseline * 0.4), 4),
                        "impact_risk": round(_clip(baseline * 0.9), 4),
                    }
                )
        return results

    def _timeline(self, articles: list[dict[str, Any]], limit: int = 60) -> list[dict[str, Any]]:
        out = []
        for a in articles[: limit * 2]:
            cls = self._classify_event(a)
            out.append(
                {
                    "time": _to_dt(a.get("published_at")).isoformat(),
                    "title": str(a.get("title", "")),
                    "country": str(a.get("country", "Unknown")),
                    "source": str(a.get("source", "unknown")),
                    "url": str(a.get("url", "")),
                    "category": cls["category"],
                    "severity": cls["severity"],
                    "high_impact": cls["high_impact"],
                }
            )
        out.sort(key=lambda x: x["time"], reverse=True)
        return out[:limit]

    def _forecast(self, articles: list[dict[str, Any]], risk_index: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        d1 = [a for a in articles if _to_dt(a.get("published_at")) >= now - timedelta(days=1)]
        d7 = [a for a in articles if _to_dt(a.get("published_at")) >= now - timedelta(days=7)]
        prev7 = [a for a in articles if now - timedelta(days=14) <= _to_dt(a.get("published_at")) < now - timedelta(days=7)]

        avg7 = sum(float(x.get("war_risk_score", 0.0)) for x in d7) / len(d7) if d7 else float(risk_index["war_risk"])
        prev = sum(float(x.get("war_risk_score", 0.0)) for x in prev7) / len(prev7) if prev7 else avg7
        momentum = avg7 - prev

        base = float(risk_index["global_instability_score"])
        trend_7d = _clip(base + 0.4 * momentum + (0.05 if len(d1) >= 20 else 0.0))
        trend_30d = _clip(base + 0.8 * momentum + (0.07 if len(d7) >= 120 else 0.0))

        return {
            "next_7d_instability": round(trend_7d, 4),
            "next_30d_instability": round(trend_30d, 4),
            "trend": "rising" if momentum > 0.015 else ("cooling" if momentum < -0.015 else "sideways"),
            "signal_strength": round(abs(momentum), 4),
        }

    def dashboard(self, db: Database) -> dict[str, Any]:
        freshness = self._ensure_live_inputs(db)
        articles = self._latest_articles(db, limit=320)
        markets = self._latest_markets(db)
        timeline = self._timeline(articles, limit=80)
        risk_index = self._global_risk_index(articles, markets)

        conflicts = []
        for conflict in self.CONFLICTS:
            rows = self._articles_for_aliases(articles, conflict["aliases"])
            score = self._conflict_score(rows)
            recent_events = []
            for row in rows[:5]:
                cls = self._classify_event(row)
                recent_events.append(
                    {
                        "title": str(row.get("title", "")),
                        "source": str(row.get("source", "unknown")),
                        "time": _to_dt(row.get("published_at")).isoformat(),
                        "category": cls["category"],
                        "severity": cls["severity"],
                    }
                )
            conflicts.append(
                {
                    "id": conflict["id"],
                    "name": conflict["name"],
                    "escalation_level": _escalation_label(score),
                    "war_probability": round(score, 4),
                    "event_count": len(rows),
                    "recent_events": recent_events,
                }
            )

        breaking = [x for x in timeline if x["high_impact"]][:15]
        sentiment_heatmap = self._sentiment_by_country(articles)
        market_impact = self._market_impact(markets, risk_index)

        commodity_keys = {"oil", "gold", "natural gas", "lng", "crude"}
        commodity_items = []
        for row in market_impact:
            asset_name = row["asset"].lower()
            if any(k in asset_name for k in commodity_keys):
                commodity_items.append(
                    {
                        "commodity": row["asset"],
                        "predicted_return_5d": row["predicted_return_5d"],
                        "risk": row["impact_risk"],
                    }
                )

        chokepoints = []
        for cp in self.CHOKEPOINTS:
            related = self._articles_for_aliases(articles, cp["aliases"])
            cp_risk = self._conflict_score(related) if related else _clip(float(risk_index["global_instability_score"]) * 0.7)
            chokepoints.append(
                {
                    "name": cp["name"],
                    "shipping_disruption_risk": round(cp_risk, 4),
                    "related_events": len(related),
                    "risk_level": _risk_label(cp_risk),
                }
            )

        military = []
        nuclear_events = []
        unrest = []
        summaries = []
        for article in articles[:80]:
            text = self._text(article)
            cls = self._classify_event(article)
            base = {
                "title": str(article.get("title", "")),
                "country": str(article.get("country", "Unknown")),
                "time": _to_dt(article.get("published_at")).isoformat(),
                "source": str(article.get("source", "unknown")),
                "url": str(article.get("url", "")),
                "severity": cls["severity"],
                "category": cls["category"],
            }
            if any(w in text for w in self.MILITARY_WORDS):
                region = self.REGION_BY_COUNTRY.get(base["country"], "Global")
                military.append({**base, "region": region})
            if any(w in text for w in self.NUCLEAR_WORDS):
                nuclear_events.append(base)
            if any(w in text for w in self.UNREST_WORDS):
                unrest.append(base)
            summaries.append(
                {
                    "title": base["title"],
                    "country": base["country"],
                    "briefing": self._brief(article, cls),
                    "category": cls["category"],
                    "risk_level": _risk_label(float(article.get("war_risk_score", 0.0))),
                    "time": base["time"],
                    "source": base["source"],
                }
            )

        military_by_region: dict[str, int] = defaultdict(int)
        for row in military:
            military_by_region[row["region"]] += 1

        country_dash = []
        by_country: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for article in articles:
            by_country[str(article.get("country", "Unknown"))].append(article)
        for country, rows in by_country.items():
            avg_sentiment = sum(float(x.get("sentiment_score", 0.0)) for x in rows) / len(rows)
            avg_risk = sum(float(x.get("war_risk_score", 0.0)) for x in rows) / len(rows)
            military_hits = sum(1 for x in rows if any(w in self._text(x) for w in self.MILITARY_WORDS))
            top_news = [str(x.get("title", "")) for x in rows[:3]]
            country_dash.append(
                {
                    "country": country,
                    "risk_score": round(avg_risk, 4),
                    "sentiment": round(avg_sentiment, 4),
                    "military_activity": military_hits,
                    "news": top_news,
                    "predicted_market_impact": round(_clip(0.6 * avg_risk + 0.4 * max(0.0, -avg_sentiment)), 4),
                }
            )
        country_dash.sort(key=lambda x: x["risk_score"], reverse=True)

        predictive_engine = []
        for conflict in conflicts:
            p7 = _clip(float(conflict["war_probability"]) + (0.05 if conflict["event_count"] >= 8 else 0.0))
            p30 = _clip(float(conflict["war_probability"]) + (0.1 if conflict["event_count"] >= 12 else 0.0))
            predictive_engine.append(
                {
                    "conflict": conflict["name"],
                    "war_probability_7d": round(p7, 4),
                    "war_probability_30d": round(p30, 4),
                    "confidence": round(_clip(0.4 + min(conflict["event_count"], 20) / 40), 4),
                }
            )

        forecast = self._forecast(articles, risk_index)
        instability = risk_index["global_instability_score"]
        top_conflict_prob = max((float(c["war_probability"]) for c in conflicts), default=0.2)
        upcoming_world_war_probability = _clip(0.55 * top_conflict_prob + 0.45 * float(instability))

        return {
            "generated_at": _utc_now().isoformat(),
            "global_conflict_tracker": conflicts,
            "real_time_sentiment": {
                "overall_geopolitical_sentiment": round(
                    sum(float(x.get("sentiment", 0.0)) for x in sentiment_heatmap) / max(len(sentiment_heatmap), 1), 4
                ),
                "country_sentiment": sentiment_heatmap,
            },
            "breaking_event_detection": {
                "high_impact_alerts": breaking,
                "alert_banner": breaking[0]["title"] if breaking else "",
            },
            "global_risk_index": risk_index,
            "market_impact_predictor": market_impact,
            "commodity_risk_monitor": commodity_items,
            "trade_route_chokepoints": chokepoints,
            "military_activity_monitor": {
                "feeds": military[:30],
                "by_region": dict(sorted(military_by_region.items(), key=lambda x: x[1], reverse=True)),
            },
            "nuclear_activity_monitor": {
                "risk_zones": self.NUCLEAR_ZONES,
                "events": nuclear_events[:20],
            },
            "civil_unrest_tracker": unrest[:20],
            "live_news_wall": [
                {"name": "TRT World", "watchUrl": "https://www.youtube.com/@TRTWorld/live"},
            ],
            "ai_news_summaries": summaries[:24],
            "event_timeline": timeline,
            "country_risk_dashboard": country_dash[:40],
            "predictive_geopolitics_engine": predictive_engine,
            "event_classification_ai": [
                {"title": item["title"], "category": item["category"], "severity": item["severity"]}
                for item in timeline[:30]
            ],
            "global_sentiment_heatmap": sentiment_heatmap,
            "geopolitical_forecast_panel": forecast,
            "multi_screen_layout": {"enabled": True, "panels": 6},
            "ui_mode": {
                "theme": "boomerang-terminal",
                "density": "high",
                "global_instability_score": instability,
                "attention_mode": instability >= 0.65,
            },
            "upcoming_world_war_probability": round(upcoming_world_war_probability, 4),
            "live_data_status": {
                **freshness,
                "article_count_used": len(articles),
                "market_rows_used": len(markets),
            },
        }


intelligence_service = IntelligenceService()
