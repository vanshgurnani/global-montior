from pymongo import ASCENDING, DESCENDING, MongoClient

from app.core.config import settings


mongo_client = MongoClient(settings.mongodb_url)


def get_db():
    yield mongo_client[settings.mongodb_db_name]


def get_db_direct():
    return mongo_client[settings.mongodb_db_name]


def create_indexes() -> None:
    db = get_db_direct()

    db.articles.create_index([("url", ASCENDING)], unique=True)
    db.articles.create_index([("published_at", DESCENDING)])
    db.articles.create_index([("country", ASCENDING)])

    db.market_snapshots.create_index([("symbol", ASCENDING)])
    db.market_snapshots.create_index([("prob_up", DESCENDING)])
    db.market_snapshots.create_index([("as_of", DESCENDING)])
