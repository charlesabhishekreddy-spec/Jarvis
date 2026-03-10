from __future__ import annotations

from typing import Any

import httpx

from jarvis.core.service import Service

from .news import NewsService
from .weather import WeatherService


class WebIntelligenceService(Service):
    def __init__(self, news_api_key: str = "", weather_api_key: str = "") -> None:
        super().__init__("jarvis.web")
        self.news = NewsService(news_api_key)
        self.weather = WeatherService(weather_api_key)

    async def search(self, query: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            return [
                {
                    "title": query,
                    "snippet": f"Search provider unavailable: {exc}",
                    "url": "",
                    "source": "fallback",
                }
            ]
        results: list[dict[str, Any]] = []
        abstract = payload.get("AbstractText")
        if abstract:
            results.append(
                {
                    "title": payload.get("Heading") or query,
                    "snippet": abstract,
                    "url": payload.get("AbstractURL", ""),
                    "source": "duckduckgo",
                }
            )
        for topic in payload.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append(
                    {
                        "title": topic["Text"].split(" - ")[0],
                        "snippet": topic["Text"],
                        "url": topic.get("FirstURL", ""),
                        "source": "duckduckgo",
                    }
                )
        if not results:
            results.append(
                {
                    "title": query,
                    "snippet": "No structured result was returned. Add a dedicated search provider for richer research.",
                    "url": "",
                    "source": "fallback",
                }
            )
        return results
