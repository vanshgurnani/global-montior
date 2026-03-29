from datetime import datetime, timedelta, timezone

from pymongo.database import Database

from app.services.prediction_service import prediction_service
from app.services.reinforcement_learning_service import reinforcement_learning_service
from app.services.stock_service import stock_service
from app.core.config import settings


def _rolling_sentiment(db: Database, days: int) -> float:
    """Avg sentiment over last N days (time-series lag)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = list(
        db.articles.aggregate(
            [
                {"$match": {"published_at": {"$gte": cutoff}}},
                {"$group": {"_id": None, "avg": {"$avg": "$sentiment_score"}}},
            ]
        )
    )
    return float(rows[0]["avg"]) if rows else 0.0


class MarketPipeline:
    def refresh(self, db: Database) -> int:
        snapshots = stock_service.fetch_snapshots()
        if not snapshots:
            return 0

        # Rolling sentiment windows (3d, 7d, 14d) for lagged market reaction
        sentiment_3d = _rolling_sentiment(db, 3)
        sentiment_7d = _rolling_sentiment(db, 7)
        sentiment_14d = _rolling_sentiment(db, 14)
        avg_sentiment = sentiment_7d if sentiment_7d != 0 else _rolling_sentiment(db, 30)

        avg_war_row = list(
            db.articles.aggregate(
                [
                    {"$match": {"published_at": {"$gte": datetime.now(timezone.utc) - timedelta(days=14)}}},
                    {"$group": {"_id": None, "avg_war_risk": {"$avg": "$war_risk_score"}}},
                ]
            )
        )
        avg_war_risk = float(avg_war_row[0]["avg_war_risk"]) if avg_war_row else 0.3

        db.market_snapshots.delete_many({})

        docs = []
        for snap in snapshots:
            pred = prediction_service.predict(
                sentiment_score=avg_sentiment,
                keyword_risk=avg_war_risk,
                sentiment_3d=sentiment_3d,
                sentiment_7d=sentiment_7d,
                sentiment_14d=sentiment_14d,
                momentum_7d=snap["momentum_7d"],
                momentum_1d=snap.get("momentum_1d", 0.0),
                momentum_3d=snap.get("momentum_3d", 0.0),
                volume_spike_pct=snap["volume_spike_pct"],
                vix_proxy=snap["vix_proxy"],
                ma20=snap["ma20"],
                ma50=snap["ma50"],
                db=db,
                symbol=snap.get("symbol"),
            )
            rl_decision = None
            if settings.rl_enabled:
                rl_decision = reinforcement_learning_service.decide(
                    sentiment_score=avg_sentiment,
                    keyword_risk=avg_war_risk,
                    momentum_7d=snap["momentum_7d"],
                    volume_spike_pct=snap["volume_spike_pct"],
                    vix_proxy=snap["vix_proxy"],
                    predicted_return_5d=pred.predicted_return_5d,
                )

            docs.append(
                {
                    "symbol": snap["symbol"],
                    "name": snap["name"],
                    "asset_type": snap.get("asset_type", "stock"),
                    "price": snap["price"],
                    "momentum_7d": snap["momentum_7d"],
                    "volume_spike_pct": snap["volume_spike_pct"],
                    "ma20": snap["ma20"],
                    "ma50": snap["ma50"],
                    "vix_proxy": snap["vix_proxy"],
                    "prob_up": pred.prob_up,
                    "prob_down": pred.prob_down,
                    "risk_level": pred.risk_level,
                    "explanation": pred.explanation,
                    "predicted_return_5d": pred.predicted_return_5d,
                    "confidence": pred.confidence,
                    "model_used": pred.model_used,
                    "rl_action": rl_decision.action if rl_decision else None,
                    "rl_confidence": rl_decision.confidence if rl_decision else None,
                    "rl_state": rl_decision.state if rl_decision else None,
                    "rl_policy": rl_decision.policy if rl_decision else None,
                    "as_of": snap["as_of"],
                }
            )

        if docs:
            db.market_snapshots.insert_many(docs)

        return len(docs)


market_pipeline = MarketPipeline()
