import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pymongo.database import Database
from starlette.responses import StreamingResponse

from app.core.database import get_db
from app.schemas.news import ArticleOut
from app.services.youtube_service import youtube_service

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/latest", response_model=list[ArticleOut])
def latest_news(limit: int = 20, db: Database = Depends(get_db)):
    cursor = db.articles.find({}, {"_id": 0}).sort("published_at", -1).limit(limit)
    return list(cursor)


def _serialize_article(doc: dict[str, Any]) -> dict[str, Any]:
    published_at = doc.get("published_at")
    if isinstance(published_at, datetime):
        published_at = published_at.isoformat()
    return {
        "title": doc.get("title", ""),
        "source": doc.get("source", "unknown"),
        "url": doc.get("url", ""),
        "country": doc.get("country", "Unknown"),
        "published_at": published_at,
        "sentiment_score": float(doc.get("sentiment_score", 0.0)),
        "keyword_score": float(doc.get("keyword_score", 0.0)),
        "war_risk_score": float(doc.get("war_risk_score", 0.0)),
    }


@router.get("/stream")
async def news_stream(limit: int = 20, interval_seconds: int = 8, db: Database = Depends(get_db)):
    interval = max(2, min(interval_seconds, 60))

    async def event_generator():
        last_head = ""
        while True:
            try:
                rows = list(db.articles.find({}, {"_id": 0}).sort("published_at", -1).limit(limit))
                items = [_serialize_article(row) for row in rows]
                head = items[0]["url"] if items else ""
                if head != last_head:
                    last_head = head
                    payload = json.dumps({"items": items}, ensure_ascii=True)
                    yield f"event: news\ndata: {payload}\n\n"
                yield "event: ping\ndata: {}\n\n"
            except Exception as exc:
                err = json.dumps({"message": str(exc)}, ensure_ascii=True)
                yield f"event: error\ndata: {err}\n\n"
            await asyncio.sleep(interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/live-channels")
def live_channels():
    return youtube_service.resolve_live_channels()
