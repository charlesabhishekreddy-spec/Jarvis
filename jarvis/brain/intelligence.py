from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from jarvis.core.config import IntelligenceSettings
from jarvis.core.service import Service


STOPWORDS = {
    "the",
    "and",
    "that",
    "with",
    "this",
    "from",
    "have",
    "your",
    "about",
    "into",
    "when",
    "what",
    "will",
    "would",
    "could",
    "should",
    "please",
    "jarvis",
}


@dataclass(slots=True)
class GenerationResult:
    text: str
    provider: str
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ReasoningProvider(ABC):
    name = "provider"
    model = "unknown"

    @abstractmethod
    async def respond(self, prompt: str, context: dict[str, Any] | None = None) -> GenerationResult:
        raise NotImplementedError

    async def summarize(self, goal: str, fragments: list[str], context: dict[str, Any] | None = None) -> GenerationResult:
        prompt = f"Goal: {goal}\n\nContext:\n" + "\n".join(f"- {fragment}" for fragment in fragments)
        return await self.respond(prompt, context=context)


class HeuristicReasoningProvider(ReasoningProvider):
    name = "heuristic"
    model = "local-heuristic"

    async def respond(self, prompt: str, context: dict[str, Any] | None = None) -> GenerationResult:
        context = context or {}
        memories = context.get("memories", [])
        plan = context.get("plan")
        results = context.get("results", [])
        reply_lines: list[str] = []

        if memories:
            memory_lines = [f"- {item['content']}" for item in memories[:3]]
            reply_lines.append("Relevant memory:")
            reply_lines.extend(memory_lines)

        if results:
            reply_lines.append("Latest findings:")
            reply_lines.extend(self._select_key_points(prompt, results))

        if plan and plan.get("steps"):
            reply_lines.append("Execution plan:")
            reply_lines.extend(f"{index}. {step['title']}" for index, step in enumerate(plan["steps"], start=1))

        if not reply_lines:
            reply_lines.append(self._default_response(prompt))

        return GenerationResult(
            text="\n".join(reply_lines).strip(),
            provider=self.name,
            model=self.model,
            metadata={"memory_count": len(memories), "result_count": len(results)},
        )

    async def summarize(self, goal: str, fragments: list[str], context: dict[str, Any] | None = None) -> GenerationResult:
        ranked = self._rank_sentences(goal, fragments)
        memory_lines: list[str] = []
        if context and context.get("memories"):
            memory_lines = [f"- {item['content']}" for item in context["memories"][:3]]

        sections = ["# Report", "", f"Goal: {goal}", "", "## Summary"]
        if ranked:
            sections.extend(ranked[:3])
        else:
            sections.append("No high-confidence findings were available.")

        sections.extend(["", "## Key Findings"])
        key_points = self._select_key_points(goal, fragments)
        sections.extend(key_points or ["- No concrete findings available."])

        if memory_lines:
            sections.extend(["", "## Relevant Preferences"])
            sections.extend(memory_lines)

        return GenerationResult(
            text="\n".join(sections).strip(),
            provider=self.name,
            model=self.model,
            metadata={"fragment_count": len(fragments)},
        )

    def _default_response(self, prompt: str) -> str:
        normalized = prompt.strip().rstrip(".")
        return f"I understood the request: {normalized}. Connect a local model provider for deeper reasoning."

    def _select_key_points(self, goal: str, fragments: list[str]) -> list[str]:
        sentences = self._collect_sentences(fragments)
        keywords = self._keywords(goal)
        ranked = []
        for sentence in sentences:
            score = sum(1 for token in self._keywords(sentence) if token in keywords)
            ranked.append((score, sentence))
        ranked.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        selected = [sentence for _, sentence in ranked[:5] if sentence]
        return [f"- {sentence}" for sentence in selected]

    def _rank_sentences(self, goal: str, fragments: list[str]) -> list[str]:
        sentences = self._collect_sentences(fragments)
        keywords = self._keywords(goal)
        ranked = []
        for sentence in sentences:
            overlap = len(self._keywords(sentence) & keywords)
            ranked.append((overlap, len(sentence), sentence))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [sentence for _, _, sentence in ranked[:5]]

    def _collect_sentences(self, fragments: list[str]) -> list[str]:
        sentences: list[str] = []
        for fragment in fragments:
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", fragment):
                cleaned = sentence.strip(" -")
                if cleaned:
                    sentences.append(cleaned)
        return sentences

    def _keywords(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 2 and token not in STOPWORDS}


class OllamaReasoningProvider(ReasoningProvider):
    name = "ollama"

    def __init__(self, model: str, endpoint: str, timeout_seconds: int = 20) -> None:
        self.model = model
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    async def respond(self, prompt: str, context: dict[str, Any] | None = None) -> GenerationResult:
        payload = {
            "model": self.model,
            "prompt": self._build_prompt(prompt, context or {}),
            "stream": False,
        }
        data = await asyncio.to_thread(self._post_json, payload)
        return GenerationResult(
            text=data.get("response", "").strip(),
            provider=self.name,
            model=self.model,
            metadata={"done": data.get("done", False)},
        )

    async def summarize(self, goal: str, fragments: list[str], context: dict[str, Any] | None = None) -> GenerationResult:
        summary_prompt = (
            f"Write a concise structured report for the goal: {goal}\n\n"
            "Source material:\n"
            + "\n".join(f"- {fragment}" for fragment in fragments)
        )
        return await self.respond(summary_prompt, context=context)

    def _build_prompt(self, prompt: str, context: dict[str, Any]) -> str:
        sections = [
            "You are JARVIS, a local-first AI operating layer focused on concise, useful answers.",
            prompt.strip(),
        ]
        memories = context.get("memories") or []
        if memories:
            sections.append("Relevant memory:")
            sections.extend(f"- {item['content']}" for item in memories[:5])
        return "\n\n".join(section for section in sections if section)

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(
            self.endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib_error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc


class IntelligenceService(Service):
    def __init__(self, settings: IntelligenceSettings) -> None:
        super().__init__("jarvis.intelligence")
        self.settings = settings
        self.heuristic = HeuristicReasoningProvider()
        self.provider = self._build_provider(settings)

    def _build_provider(self, settings: IntelligenceSettings) -> ReasoningProvider:
        if settings.provider.lower() == "ollama":
            return OllamaReasoningProvider(
                model=settings.model,
                endpoint=settings.endpoint,
                timeout_seconds=settings.timeout_seconds,
            )
        return self.heuristic

    async def respond(self, prompt: str, context: dict[str, Any] | None = None) -> GenerationResult:
        try:
            result = await self.provider.respond(prompt, context=context)
            if result.text.strip():
                return result
        except Exception as exc:
            self.logger.warning("Primary intelligence provider failed: %s", exc)
        return await self.heuristic.respond(prompt, context=context)

    async def summarize(self, goal: str, fragments: list[str], context: dict[str, Any] | None = None) -> GenerationResult:
        try:
            result = await self.provider.summarize(goal, fragments, context=context)
            if result.text.strip():
                return result
        except Exception as exc:
            self.logger.warning("Primary intelligence summarizer failed: %s", exc)
        return await self.heuristic.summarize(goal, fragments, context=context)

    async def classify_intent(self, text: str) -> str:
        normalized = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if not normalized:
            return "empty"
        counts = Counter(token for token in normalized if token not in STOPWORDS)
        common = [token for token, _ in counts.most_common(2)]
        return ":".join(common) if common else normalized[0]
