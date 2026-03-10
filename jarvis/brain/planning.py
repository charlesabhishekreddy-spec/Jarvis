from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from jarvis.core.models import CommandRequest, TaskPlan, TaskStep


WEEKLY_PATTERN = re.compile(
    r"every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+([0-2]?\d(?::[0-5]\d)?\s*(?:am|pm)?)",
    re.IGNORECASE,
)
DAILY_PATTERN = re.compile(r"every\s+day\s+at\s+([0-2]?\d(?::[0-5]\d)?\s*(?:am|pm)?)", re.IGNORECASE)
REMEMBER_PATTERN = re.compile(r"remember(?:\s+that)?\s+(.*)", re.IGNORECASE)
RECALL_PATTERN = re.compile(r"(?:recall|what do you know about|what did i say about)\s+(.*)", re.IGNORECASE)
OPEN_PATTERN = re.compile(r"(?:open|launch)\s+(.+)", re.IGNORECASE)
WEATHER_PATTERN = re.compile(r"weather(?:\s+in)?\s+(.+)", re.IGNORECASE)
NEWS_PATTERN = re.compile(r"(?:news|latest)\s+(?:about\s+)?(.+)", re.IGNORECASE)
STATUS_PATTERN = re.compile(r"(?:status|health|resources)", re.IGNORECASE)
TOOLS_PATTERN = re.compile(r"(?:tools|capabilities|what can you do)", re.IGNORECASE)


class TaskPlanner:
    def __init__(self, workspace_root: str | None = None) -> None:
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()

    def create_plan(self, request: CommandRequest) -> TaskPlan:
        text = self._normalize(request.text)
        steps = self._build_steps(text)
        return TaskPlan(goal=text, steps=steps)

    def _normalize(self, text: str) -> str:
        lowered = text.strip()
        return re.sub(r"^(hey\s+jarvis|jarvis)[,\s:]+", "", lowered, flags=re.IGNORECASE)

    def _build_steps(self, text: str) -> list[TaskStep]:
        remember_match = REMEMBER_PATTERN.search(text)
        if remember_match:
            return [
                TaskStep(
                    title="Store memory",
                    description=remember_match.group(1),
                    agent_hint="memory",
                    metadata={"operation": "remember", "content": remember_match.group(1), "category": "user_preference"},
                )
            ]

        recall_match = RECALL_PATTERN.search(text)
        if recall_match:
            return [
                TaskStep(
                    title="Recall memory",
                    description=recall_match.group(1),
                    agent_hint="memory",
                    metadata={"operation": "recall", "query": recall_match.group(1)},
                )
            ]

        daily_match = DAILY_PATTERN.search(text)
        if daily_match:
            return [
                TaskStep(
                    title="Schedule daily reminder",
                    description=text,
                    agent_hint="automation",
                    metadata={
                        "schedule_type": "daily",
                        "message": text,
                        "time_of_day": self._normalize_time(daily_match.group(1)),
                    },
                )
            ]

        weekly_match = WEEKLY_PATTERN.search(text)
        if weekly_match:
            return [
                TaskStep(
                    title="Schedule weekly reminder",
                    description=text,
                    agent_hint="automation",
                    metadata={
                        "schedule_type": "weekly",
                        "message": text,
                        "day_name": weekly_match.group(1),
                        "time_of_day": self._normalize_time(weekly_match.group(2)),
                    },
                )
            ]

        if text.lower().startswith("remind me"):
            return [
                TaskStep(
                    title="Schedule reminder",
                    description=text,
                    agent_hint="automation",
                    metadata={"schedule_type": "once", "message": text, "run_at": self._extract_iso_datetime(text)},
                )
            ]

        weather_match = WEATHER_PATTERN.search(text)
        if weather_match:
            return [
                TaskStep(
                    title="Lookup weather",
                    description=text,
                    agent_hint="research",
                    metadata={"query_type": "weather", "location": weather_match.group(1).strip()},
                )
            ]

        news_match = NEWS_PATTERN.search(text)
        if "news" in text.lower() or "latest" in text.lower():
            topic = news_match.group(1).strip() if news_match else text
            return [
                TaskStep(
                    title="Get latest news",
                    description=text,
                    agent_hint="research",
                    metadata={"query_type": "news", "topic": topic},
                )
            ]

        if "screen" in text.lower() or "ocr" in text.lower():
            return [
                TaskStep(
                    title="Inspect screen",
                    description=text,
                    agent_hint="vision",
                    metadata={"source": "screen"},
                )
            ]

        if STATUS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Inspect system status",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "resource_usage"},
                )
            ]

        if TOOLS_PATTERN.search(text):
            return [
                TaskStep(
                    title="Describe available tools",
                    description=text,
                    agent_hint="commander",
                    metadata={"include_tools": True},
                )
            ]

        open_match = OPEN_PATTERN.search(text)
        if open_match:
            target = open_match.group(1).strip()
            candidate = Path(target)
            action = "open_path" if candidate.exists() else "launch_application"
            metadata = {"action": action}
            if action == "open_path":
                metadata["path"] = str(candidate)
            else:
                metadata["application"] = target
            return [TaskStep(title="Open target", description=text, agent_hint="system", metadata=metadata)]

        if any(word in text.lower() for word in ("report", "research", "prepare")):
            slug = self._slugify(text)[:50]
            output_path = self.workspace_root / "reports" / f"{slug or uuid4().hex}.md"
            return [
                TaskStep(
                    title="Research topic",
                    description=text,
                    agent_hint="research",
                    metadata={"query": text},
                ),
                TaskStep(
                    title="Compose report",
                    description="Summarize findings into a structured note.",
                    agent_hint="commander",
                    metadata={"write_report": True},
                ),
                TaskStep(
                    title="Save report",
                    description=f"Write the report to {output_path}",
                    agent_hint="system",
                    metadata={"action": "write_file", "path": str(output_path), "content_from_previous": True},
                ),
            ]

        if any(word in text.lower() for word in ("run", "execute", "terminal")):
            return [
                TaskStep(
                    title="Evaluate execution safety",
                    description=text,
                    agent_hint="security",
                    metadata={"command": text},
                ),
                TaskStep(
                    title="Run command",
                    description=text,
                    agent_hint="system",
                    metadata={"action": "shell", "command": text},
                ),
            ]

        return [
            TaskStep(
                title="Respond to request",
                description=text,
                agent_hint="commander",
            )
        ]

    def _normalize_time(self, raw: str) -> str:
        value = raw.strip().lower()
        formats = ("%H:%M:%S", "%H:%M", "%I%p", "%I:%M%p", "%I %p", "%I:%M %p")
        normalized = value.replace(" ", "")
        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt).strftime("%H:%M:%S")
            except ValueError:
                continue
        raise ValueError(f"Unsupported time format: {raw}")

    def _extract_iso_datetime(self, text: str) -> str | None:
        iso_match = re.search(r"\d{4}-\d{2}-\d{2}[tT ]\d{2}:\d{2}(?::\d{2})?", text)
        if iso_match:
            return iso_match.group(0).replace(" ", "T")
        tomorrow_match = re.search(r"tomorrow\s+at\s+([0-2]?\d(?::[0-5]\d)?\s*(?:am|pm)?)", text, re.IGNORECASE)
        if tomorrow_match:
            target = datetime.now(timezone.utc) + timedelta(days=1)
            hour, minute, second = [int(part) for part in self._normalize_time(tomorrow_match.group(1)).split(":")]
            return target.replace(hour=hour, minute=minute, second=second, microsecond=0).isoformat()
        relative_match = re.search(r"in\s+(\d+)\s+(minute|minutes|hour|hours|day|days)", text, re.IGNORECASE)
        if relative_match:
            count = int(relative_match.group(1))
            unit = relative_match.group(2).lower()
            if "hour" in unit:
                delta = timedelta(hours=count)
            elif "day" in unit:
                delta = timedelta(days=count)
            else:
                delta = timedelta(minutes=count)
            return (datetime.now(timezone.utc) + delta).replace(microsecond=0).isoformat()
        at_match = re.search(r"\bat\s+([0-2]?\d(?::[0-5]\d)?\s*(?:am|pm)?)", text, re.IGNORECASE)
        if at_match:
            now = datetime.now(timezone.utc)
            hour, minute, second = [int(part) for part in self._normalize_time(at_match.group(1)).split(":")]
            target = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.isoformat()
        return None

    def _slugify(self, text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
