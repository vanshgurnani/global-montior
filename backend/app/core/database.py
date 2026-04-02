from pymongo import ASCENDING, DESCENDING, MongoClient

from app.core.config import settings


mongo_client = MongoClient(
    settings.mongodb_url,
    serverSelectionTimeoutMS=30000,  # Increased for Render
    connectTimeoutMS=30000,  # Increased for Render
    socketTimeoutMS=30000,  # Increased for Render
    maxPoolSize=50,  # Connection pooling
    minPoolSize=10,  # Maintain minimum connections
    waitQueueTimeoutMS=10000,
    retryWrites=True,
)


def get_db():
    yield mongo_client[settings.mongodb_db_name]


def get_db_direct():
    return mongo_client[settings.mongodb_db_name]


def create_indexes() -> None:
    db = get_db_direct()
    try:
        db.articles.create_index([("url", ASCENDING)], unique=True)
        db.articles.create_index([("published_at", DESCENDING)])
        db.articles.create_index([("country", ASCENDING)])
        db.articles.create_index([("event_type", ASCENDING)])

        db.market_snapshots.create_index([("symbol", ASCENDING)])
        db.market_snapshots.create_index([("prob_up", DESCENDING)])
        db.market_snapshots.create_index([("as_of", DESCENDING)])

        db.ground_truth_vix.create_index([("date", ASCENDING)])
        db.ground_truth_economic.create_index([("year", ASCENDING), ("country_iso", ASCENDING), ("indicator", ASCENDING)])
        db.ground_truth_conflicts.create_index([("event_date", ASCENDING)])
        db.ground_truth_conflicts.create_index([("country", ASCENDING)])
    except Exception as exc:
        print(f"[db] index creation skipped: {exc.__class__.__name__}")
