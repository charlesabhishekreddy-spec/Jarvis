from __future__ import annotations

from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class ResearchAgent(BaseAgent):
    name = "research"
    description = "Retrieves and summarizes internet knowledge."
    keywords = ("research", "search", "news", "weather", "latest", "report")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        if step.metadata.get("query_type") == "weather":
            result = await context.web.weather.get_weather(step.metadata["location"])
            return {"message": f"Weather for {result['location']}: {result['temperature_c']}C, {result['description']}"}
        if step.metadata.get("query_type") == "news":
            articles = await context.web.news.latest(step.metadata["topic"])
            lines = [f"- {article['title']}" for article in articles]
            return {"message": "\n".join(lines), "articles": articles}
        results = await context.tools.execute("web.search", context, query=step.metadata.get("query", request.text))
        fragments = [
            f"{item.get('title', 'Result')}: {item.get('snippet', item.get('summary', ''))}"
            for item in results.get("results", [])
        ]
        summary = await context.intelligence.summarize(
            goal=step.metadata.get("query", request.text),
            fragments=fragments,
            context={"results": fragments},
        )
        return {"message": summary.text, "results": results.get("results", []), "provider": summary.provider}
