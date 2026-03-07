from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "Global Intelligence Monitor API"
    app_env: str = "dev"
    debug: bool = True

    mongodb_url: str = "mongodb://mongo:27017"
    mongodb_db_name: str = "gim"

    news_api_key: Optional[str] = None
    news_provider: str = "gdelt"  # newsapi | gdelt
    news_sources: str = ""  # optional csv: gdelt,newsapi,rss
    news_ingest_limit: int = 40
    youtube_api_key: Optional[str] = None
    rss_feeds: str = (
        "https://feeds.reuters.com/reuters/worldNews,"
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml,"
        "https://feeds.bbci.co.uk/news/world/rss.xml"
    )

    scheduler_enabled: bool = True
    scheduler_interval_minutes: int = 15

    stock_symbols: str = "DEFAULT"  # csv symbols or DEFAULT
    stock_history_period: str = "6mo"
    stock_min_points: int = 55
    stock_max_symbols: int = 30
    model_auto_train_on_refresh: bool = False
    model_train_retry_minutes: int = 60

    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")


settings = Settings()
