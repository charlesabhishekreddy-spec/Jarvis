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


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


class ReasoningProvider(ABC):
    name = "provider"
    model = "unknown"

    @abstractmethod
    async def respond(self, prompt: str, context: dict[str, Any] | None = None) -> GenerationResult:
        raise NotImplementedError

    async def summarize(self, goal: str, fragments: list[str], context: dict[str, Any] | None = None) -> GenerationResult:
        prompt = f"Goal: {goal}\n\nContext:\n" + "\n".join(f"- {fragment}" for fragment in fragments)
        return await self.respond(prompt, context=context)

    async def plan_tool_usage(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        max_calls: int = 3,
    ) -> list[ToolCall]:
        return []


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

    async def plan_tool_usage(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        max_calls: int = 3,
    ) -> list[ToolCall]:
        available = {tool["name"] for tool in tools}
        normalized = prompt.strip()
        lowered = normalized.lower()
        calls: list[ToolCall] = []

        def maybe_add(name: str, arguments: dict[str, Any], reason: str) -> None:
            if len(calls) >= max_calls or name not in available:
                return
            calls.append(ToolCall(name=name, arguments=arguments, reason=reason))

        file_read = re.search(r"(?:read|show|display)\s+(?:the\s+)?file\s+(.+)", normalized, re.IGNORECASE)
        if file_read:
            maybe_add("system.read_file", {"path": self._clean_path(file_read.group(1))}, "Read the requested file.")
            return calls

        open_path = re.search(r"(?:open)\s+(?:the\s+)?(?:file|folder|directory|path)\s+(.+)", normalized, re.IGNORECASE)
        if open_path:
            maybe_add("system.open_path", {"path": self._clean_path(open_path.group(1))}, "Open the requested path.")
            return calls

        find_named = re.search(r"(?:find|search for)\s+files?\s+(?:named\s+)?([^\n]+)", normalized, re.IGNORECASE)
        if find_named:
            maybe_add(
                "system.list_files",
                {"path": ".", "recursive": True, "limit": 50, "pattern": self._clean_path(find_named.group(1))},
                "Search the workspace for matching files.",
            )
            return calls

        list_files = re.search(r"(?:list|show)\s+(?:the\s+)?(?:files|folders|directory|workspace)(?:\s+in\s+(.+))?", normalized, re.IGNORECASE)
        if list_files or any(token in lowered for token in ("workspace", "project files", "directory contents")):
            path = self._clean_path(list_files.group(1)) if list_files and list_files.group(1) else "."
            maybe_add("system.list_files", {"path": path, "recursive": False, "limit": 50}, "List files in the requested location.")
            return calls

        if any(token in lowered for token in ("running processes", "process list", "what is running", "running apps")):
            maybe_add("system.processes", {"limit": 20}, "Inspect active processes.")
            return calls

        if any(token in lowered for token in ("startup status", "autostart status", "start on boot", "start on login")):
            maybe_add("system.startup_status", {}, "Check whether JARVIS is configured to start automatically.")
            return calls

        web_match = re.search(r"(?:search the web for|research|look up|find information about)\s+(.+)", normalized, re.IGNORECASE)
        if web_match:
            maybe_add("web.search", {"query": web_match.group(1).strip()}, "Research the requested topic.")
            return calls

        recall_match = re.search(r"(?:recall|remembered|what do you know about|what did i say about)\s+(.+)", normalized, re.IGNORECASE)
        if recall_match:
            maybe_add("memory.recall", {"query": recall_match.group(1).strip(), "limit": 5}, "Search long-term memory.")
            return calls

        remember_match = re.search(r"remember(?:\s+that)?\s+(.+)", normalized, re.IGNORECASE)
        if remember_match:
            maybe_add("memory.remember", {"content": remember_match.group(1).strip(), "category": "general"}, "Store the new fact.")
            return calls

        if any(token in lowered for token in ("system status", "resource usage", "cpu", "memory usage")):
            maybe_add("system.processes", {"limit": 10}, "Inspect current process state.")
            return calls

        return calls

    def _default_response(self, prompt: str) -> str:
        normalized = prompt.strip().rstrip(".")
        return f"I understood the request: {normalized}. Connect a local model provider for deeper reasoning."

    def _clean_path(self, value: str) -> str:
        return value.strip().strip("\"'`").rstrip(".")

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

    async def plan_tool_usage(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        max_calls: int = 3,
    ) -> list[ToolCall]:
        tool_lines = "\n".join(f"- {tool['name']}: {tool['description']}" for tool in tools)
        planning_prompt = (
            "Return only JSON with the shape {\"tool_calls\":[{\"name\":\"tool.name\",\"arguments\":{},\"reason\":\"...\"}]}. "
            f"Use at most {max_calls} calls.\n\n"
            f"Available tools:\n{tool_lines}\n\n"
            f"User request: {prompt}"
        )
        result = await self.respond(planning_prompt, context=context)
        match = re.search(r"\{.*\}", result.text, re.DOTALL)
        if not match:
            return []
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
        calls: list[ToolCall] = []
        for item in payload.get("tool_calls", [])[:max_calls]:
            name = item.get("name")
            if not isinstance(name, str):
                continue
            arguments = item.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}
            calls.append(ToolCall(name=name, arguments=arguments, reason=str(item.get("reason", ""))))
        return calls

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

    async def plan_tool_usage(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        max_calls: int = 3,
    ) -> list[ToolCall]:
        try:
            calls = await self.provider.plan_tool_usage(prompt, tools, context=context, max_calls=max_calls)
            if calls:
                return calls
        except Exception as exc:
            self.logger.warning("Primary intelligence tool planner failed: %s", exc)
        return await self.heuristic.plan_tool_usage(prompt, tools, context=context, max_calls=max_calls)
