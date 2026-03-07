from pymongo.database import Database

from app.services.prediction_service import prediction_service
from app.services.stock_service import stock_service


class MarketPipeline:
    def refresh(self, db: Database) -> int:
        snapshots = stock_service.fetch_snapshots()
        if not snapshots:
            return 0

        avg_sentiment_row = list(
            db.articles.aggregate(
                [{"$group": {"_id": None, "avg_sentiment": {"$avg": "$sentiment_score"}}}]
            )
        )
        avg_sentiment = float(avg_sentiment_row[0]["avg_sentiment"]) if avg_sentiment_row else 0.0

        avg_war_row = list(
            db.articles.aggregate(
                [{"$group": {"_id": None, "avg_war_risk": {"$avg": "$war_risk_score"}}}]
            )
        )
        avg_war_risk = float(avg_war_row[0]["avg_war_risk"]) if avg_war_row else 0.3

        db.market_snapshots.delete_many({})

        docs = []
        for snap in snapshots:
            pred = prediction_service.predict(
                sentiment_score=avg_sentiment,
                keyword_risk=avg_war_risk,
                momentum_7d=snap["momentum_7d"],
                volume_spike_pct=snap["volume_spike_pct"],
                vix_proxy=snap["vix_proxy"],
                ma20=snap["ma20"],
                ma50=snap["ma50"],
            )

            docs.append(
                {
                    "symbol": snap["symbol"],
                    "name": snap["name"],
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
                    "as_of": snap["as_of"],
                }
            )

        if docs:
            db.market_snapshots.insert_many(docs)

        return len(docs)


market_pipeline = MarketPipeline()
