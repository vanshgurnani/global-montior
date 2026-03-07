from pymongo.database import Database


class RiskService:
    def global_overview(self, db: Database) -> dict:
        global_row = list(
            db.articles.aggregate(
                [
                    {
                        "$group": {
                            "_id": None,
                            "global_sentiment": {"$avg": "$sentiment_score"},
                            "global_war_risk": {"$avg": "$war_risk_score"},
                        }
                    }
                ]
            )
        )

        sentiment = float(global_row[0]["global_sentiment"]) if global_row else 0.0
        war_risk = float(global_row[0]["global_war_risk"]) if global_row else 0.0

        if war_risk >= 0.66:
            risk_level = "High"
        elif war_risk >= 0.33:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        country_rows = list(
            db.articles.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$country",
                            "avg_war_risk": {"$avg": "$war_risk_score"},
                            "article_count": {"$sum": 1},
                        }
                    },
                    {"$sort": {"avg_war_risk": -1}},
                    {"$limit": 8},
                ]
            )
        )

        countries = [
            {
                "country": (row.get("_id") or "Unknown"),
                "avg_war_risk": round(float(row.get("avg_war_risk", 0.0)), 4),
                "article_count": int(row.get("article_count", 0)),
            }
            for row in country_rows
        ]

        return {
            "global_sentiment": round(sentiment, 4),
            "global_war_risk": round(war_risk, 4),
            "risk_level": risk_level,
            "high_risk_countries": countries,
        }


risk_service = RiskService()
