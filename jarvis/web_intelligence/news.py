from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib import parse as urllib_parse
from urllib import request as urllib_request


class NewsService:
    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    async def latest(self, topic: str) -> list[dict[str, Any]]:
        if not self.api_key:
            return [
                {
                    "title": f"News provider not configured for topic: {topic}",
                    "url": "",
                    "summary": "Add a News API key to enable live headlines.",
                }
            ]
        try:
            payload = await asyncio.to_thread(self._fetch_payload, topic)
        except Exception as exc:
            return [{"title": f"News lookup failed for {topic}", "url": "", "summary": str(exc)}]
        return [
            {
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "summary": article.get("description", ""),
            }
            for article in payload.get("articles", [])
        ]

    def _fetch_payload(self, topic: str) -> dict[str, Any]:
        encoded = urllib_parse.urlencode(
            {"q": topic, "sortBy": "publishedAt", "pageSize": 5, "apiKey": self.api_key}
        )
        with urllib_request.urlopen(f"https://newsapi.org/v2/everything?{encoded}", timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
