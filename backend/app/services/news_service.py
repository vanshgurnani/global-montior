from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import requests
from pymongo.database import Database

from app.core.config import settings
from app.services.sentiment_service import sentiment_service
from app.services.war_risk_service import RISK_KEYWORDS, war_risk_service


class NewsService:
    @staticmethod
    def _resolve_sources() -> list[str]:
        configured = (settings.news_sources or "").strip()
        if configured:
            return [s.strip().lower() for s in configured.split(",") if s.strip()]

        provider = settings.news_provider.lower()
        if provider in ("gdelt", "newsapi", "rss"):
            return [provider]

        sources = ["gdelt"]
        if settings.news_api_key:
            sources.append("newsapi")
        return sources

    @staticmethod
    def _parse_published_at(value: Optional[str]) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            pass
        try:
            # GDELT often uses YYYYMMDDHHMMSS.
            return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)

    def _fetch_newsapi(self) -> list[dict]:
        if not settings.news_api_key:
            return []
        query = " OR ".join(RISK_KEYWORDS)
        url = (
            "https://newsapi.org/v2/everything"
            f"?q={query}&language=en&sortBy=publishedAt&pageSize=50&apiKey={settings.news_api_key}"
        )
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            print(f"Fetched {len(data.get('articles', []))} articles from NewsAPI")
        except Exception:
            return []
        articles = data.get("articles", [])
        return [
            {
                "title": a.get("title", ""),
                "summary": a.get("description") or "",
                "url": a.get("url", ""),
                "source": (a.get("source") or {}).get("name", "unknown"),
                "published_at": a.get("publishedAt") or datetime.now(timezone.utc).isoformat(),
                "_source_type": "newsapi",
            }
            for a in articles
        ]

    def _fetch_gdelt(self) -> list[dict]:
        query = "%20OR%20".join(RISK_KEYWORDS)
        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={query}&mode=ArtList&maxrecords=50&format=json"
        )
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []
        articles = data.get("articles", [])
        return [
            {
                "title": a.get("title", ""),
                "summary": a.get("seendate", ""),
                "url": a.get("url", ""),
                "source": a.get("sourcecountry", "gdelt"),
                "published_at": a.get("seendate") or datetime.now(timezone.utc).isoformat(),
                "_source_type": "gdelt",
            }
            for a in articles
        ]

    @staticmethod
    def _parse_rss_datetime(value: Optional[str]) -> str:
        if not value:
            return datetime.now(timezone.utc).isoformat()
        try:
            dt = parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _strip_tag(tag: str) -> str:
        return tag.split("}", 1)[1] if "}" in tag else tag

    @staticmethod
    def _atom_link(entry: ET.Element) -> str:
        for link in entry.findall("{*}link"):
            href = (link.get("href") or "").strip()
            rel = (link.get("rel") or "alternate").strip().lower()
            if href and rel in ("alternate", ""):
                return href
        return ""

    def _fetch_rss(self) -> list[dict]:
        feeds = [f.strip() for f in settings.rss_feeds.split(",") if f.strip()]
        if not feeds:
            return []

        out: list[dict] = []
        query_terms = tuple(k.lower() for k in RISK_KEYWORDS)

        for feed_url in feeds:
            try:
                response = requests.get(feed_url, timeout=20)
                response.raise_for_status()
                root = ET.fromstring(response.content)
            except Exception:
                continue

            root_tag = self._strip_tag(root.tag).lower()
            feed_host = urlparse(feed_url).netloc or "rss"

            if root_tag == "rss":
                channel = root.find("channel")
                feed_name = (channel.findtext("title", default="") if channel is not None else "") or feed_host
                items = channel.findall("item") if channel is not None else []
                for item in items:
                    title = (item.findtext("title", default="") or "").strip()
                    summary = (item.findtext("description", default="") or "").strip()
                    text = f"{title} {summary}".lower()
                    if not any(term in text for term in query_terms):
                        continue
                    out.append(
                        {
                            "title": title,
                            "summary": summary,
                            "url": (item.findtext("link", default="") or "").strip(),
                            "source": feed_name,
                            "published_at": self._parse_rss_datetime(item.findtext("pubDate")),
                            "_source_type": "rss",
                        }
                    )
                continue

            if root_tag == "feed":
                feed_name = (root.findtext("{*}title", default="") or "").strip() or feed_host
                entries = root.findall("{*}entry")
                for entry in entries:
                    title = (entry.findtext("{*}title", default="") or "").strip()
                    summary = (entry.findtext("{*}summary", default="") or entry.findtext("{*}content", default="") or "").strip()
                    text = f"{title} {summary}".lower()
                    if not any(term in text for term in query_terms):
                        continue
                    out.append(
                        {
                            "title": title,
                            "summary": summary,
                            "url": self._atom_link(entry),
                            "source": feed_name,
                            "published_at": self._parse_rss_datetime(
                                entry.findtext("{*}published") or entry.findtext("{*}updated")
                            ),
                            "_source_type": "rss",
                        }
                    )

        return out

    def fetch_articles(self) -> list[dict]:
        sources = self._resolve_sources()

        articles: list[dict] = []
        for source in sources:
            if source == "gdelt":
                articles.extend(self._fetch_gdelt())
            elif source == "newsapi":
                articles.extend(self._fetch_newsapi())
            elif source == "rss":
                articles.extend(self._fetch_rss())

        # De-duplicate across all sources by URL.
        deduped: list[dict] = []
        seen: set = set()
        for item in articles:
            url = (item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(item)
        limit = max(10, int(settings.news_ingest_limit))
        return deduped[:limit]

    def ingest_with_stats(self, db: Database) -> dict:
        incoming = self.fetch_articles()
        inserted = 0
        duplicates = 0
        invalid = 0
        source_counts = {}

        for item in incoming:
            if not item.get("url"):
                invalid += 1
                continue

            existing = db.articles.find_one({"url": item["url"]}, {"_id": 1})
            if existing:
                duplicates += 1
                continue

            text = f"{item.get('title', '')} {item.get('summary', '')}"
            sentiment_score = sentiment_service.analyze(text)
            keyword_score, hits = war_risk_service.keyword_score(text)
            war_risk_score = war_risk_service.combined_war_risk(sentiment_score, keyword_score)
            country = war_risk_service.country_from_text(text)

            doc = {
                "title": item.get("title", ""),
                "source": item.get("source", "unknown"),
                "url": item.get("url", ""),
                "summary": item.get("summary", ""),
                "country": country,
                "published_at": self._parse_published_at(item.get("published_at")),
                "created_at": datetime.now(timezone.utc),
                "sentiment_score": float(sentiment_score),
                "keyword_score": float(keyword_score),
                "war_risk_score": float(war_risk_score),
                "matched_keywords": hits,
            }

            db.articles.insert_one(doc)
            inserted += 1
            source_type = (item.get("_source_type") or "unknown").lower()
            source_counts[source_type] = int(source_counts.get(source_type, 0)) + 1

        return {
            "provider": settings.news_provider.lower(),
            "sources": self._resolve_sources(),
            "fetched": len(incoming),
            "inserted": inserted,
            "duplicates": duplicates,
            "invalid": invalid,
            "source_counts": source_counts,
        }

    def ingest(self, db: Database) -> int:
        return int(self.ingest_with_stats(db)["inserted"])


news_service = NewsService()
