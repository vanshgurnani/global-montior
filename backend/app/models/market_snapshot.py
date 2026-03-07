from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    price: Mapped[float] = mapped_column(Float)
    momentum_7d: Mapped[float] = mapped_column(Float)
    volume_spike_pct: Mapped[float] = mapped_column(Float)
    ma20: Mapped[float] = mapped_column(Float)
    ma50: Mapped[float] = mapped_column(Float)
    vix_proxy: Mapped[float] = mapped_column(Float)

    prob_up: Mapped[float] = mapped_column(Float)
    prob_down: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    explanation: Mapped[str] = mapped_column(Text)

    as_of: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
