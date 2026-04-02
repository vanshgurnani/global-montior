from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "Global Intelligence Monitor API"
    app_env: str = "dev"
    debug: bool = False  # Disabled by default for production

    mongodb_url: str = "mongodb://mongo:27017"
    mongodb_db_name: str = "gim"
    
    # Request timeouts for external services
    request_timeout: int = 20  # seconds
    external_api_timeout: int = 30  # seconds

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
    use_transformer_sentiment: bool = False
    rl_enabled: bool = True
    rl_policy_name: str = "market_q_policy_v1"

    # Optional event classification enrichment for articles.
    # - Transformer mode uses a zero-shot classifier (may download weights if not cached).
    # - OpenAI mode uses embeddings and lightweight prototype matching.
    use_transformer_event_classifier: bool = False
    use_openai_event_classifier: bool = False
    openai_api_key: Optional[str] = None
    openai_embeddings_model: str = "text-embedding-3-small"

    # Ground truth datasets for train/validate (ACLED requires free registration)
    ground_truth_enabled: bool = True
    acled_api_key: Optional[str] = None
    acled_email: Optional[str] = None

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        # Support dynamic origins for Render deployment
        if self.app_env == "production":
            # In production, allow your frontend domain and prevent wildcards
            origins = [
                "https://global-montior.vercel.app",
                "https://global-montior.netlify.app",  # If using Netlify
            ]
        else:
            origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return origins or ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore")


settings = Settings()
