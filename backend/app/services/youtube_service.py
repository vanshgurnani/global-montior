from typing import Any
import requests

from app.core.config import settings


DEFAULT_CHANNELS = [
    {
        "name": "DW News",
        "channel_id": "UCknLrEdhRCp1aegoMqRaCZg",
        "watch_url": "https://www.youtube.com/@DWNews/live",
    },
    {
        "name": "France 24",
        "channel_id": "UCQfwfsi5VrQ8yKZ-UWmAEFg",
        "watch_url": "https://www.youtube.com/@FRANCE24/live",
    },
    {
        "name": "TRT World",
        "channel_id": "UC7fWeaHhqgM4Ry-RMpM2YYw",
        "watch_url": "https://www.youtube.com/@TRTWorld/live",
    },
    {
        "name": "Republic Bharat",
        "channel_id": "UC7wXt18fO9iAexX9jqtFj9A",
        "watch_url": "https://www.youtube.com/@RepublicBharat/live",
        "fallback_video": "RlRtHNTxt3M",
    }
]


class YouTubeService:

    def _search_live_video_id(self, channel_id: str) -> str:
        if not settings.youtube_api_key:
            return ""

        try:
            response = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "id",
                    "channelId": channel_id,
                    "eventType": "live",
                    "type": "video",
                    "maxResults": 1,
                    "key": settings.youtube_api_key,
                },
                timeout=12,
            )

            response.raise_for_status()
            payload = response.json()

            items = payload.get("items", [])

            if not items:
                return ""

            return ((items[0] or {}).get("id") or {}).get("videoId") or ""

        except Exception:
            return ""


    def resolve_live_channels(self) -> dict[str, Any]:

        channels = []

        for item in DEFAULT_CHANNELS:

            channel_id = item["channel_id"]

            live_video_id = self._search_live_video_id(channel_id)

            # Priority 1 → actual live stream detected
            if live_video_id:
                embed_url = f"https://www.youtube.com/embed/{live_video_id}?autoplay=1&mute=1"

            # Priority 2 → manual fallback video
            elif item.get("fallback_video"):
                embed_url = f"https://www.youtube.com/embed/{item['fallback_video']}?autoplay=1&mute=1"
                live_video_id = item["fallback_video"]

            # Priority 3 → channel live endpoint
            else:
                embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_id}&autoplay=1&mute=1"

            channels.append(
                {
                    "name": item["name"],
                    "channelId": channel_id,
                    "embedUrl": embed_url,
                    "watchUrl": item["watch_url"],
                    "liveVideoId": live_video_id or None,
                }
            )

        return {
            "used_api_key": bool(settings.youtube_api_key),
            "channels": channels,
        }


youtube_service = YouTubeService()