from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    source: Mapped[str] = mapped_column(String(128))
    url: Mapped[str] = mapped_column(String(1024), unique=True, index=True)
    summary: Mapped[str] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(64), default="Unknown")
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sentiment_score: Mapped[float] = mapped_column(Float)
    keyword_score: Mapped[float] = mapped_column(Float)
    war_risk_score: Mapped[float] = mapped_column(Float)
    matched_keywords: Mapped[list[str]] = mapped_column(JSON)
