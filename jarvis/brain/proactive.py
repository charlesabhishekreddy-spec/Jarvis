from __future__ import annotations

import asyncio
import contextlib
import re
from typing import Any

from jarvis.core.events import AsyncEventBus
from jarvis.core.models import GoalStatus, utc_now
from jarvis.core.service import Service
from jarvis.memory.service import MemoryService

from .intelligence import IntelligenceService


class ProactiveReviewService(Service):
    def __init__(
        self,
        memory: MemoryService,
        intelligence: IntelligenceService,
        bus: AsyncEventBus,
        enabled: bool = True,
        interval_seconds: int = 300,
    ) -> None:
        super().__init__("jarvis.proactive")
        self.memory = memory
        self.intelligence = intelligence
        self.bus = bus
        self.enabled = enabled
        self.interval_seconds = max(15, int(interval_seconds))
        self._loop_task: asyncio.Task[None] | None = None
        self._last_summary: dict[str, Any] = {
            "enabled": enabled,
            "interval_seconds": self.interval_seconds,
            "last_review_at": None,
            "updated_goals": [],
            "goal_count": 0,
            "source": None,
        }

    async def start(self) -> None:
        await super().start()
        if self.enabled:
            self._loop_task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._loop_task is not None:
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task
            self._loop_task = None
        await super().stop()

    def snapshot(self) -> dict[str, Any]:
        return dict(self._last_summary)

    async def review_now(self, source: str = "manual") -> dict[str, Any]:
        now = utc_now().isoformat()
        goals = await self.memory.goals(status=GoalStatus.ACTIVE.value, limit=20)
        tasks = await self.memory.recent_tasks(10)
        projects = await self.memory.project_contexts(limit=10)
        updated_goals: list[dict[str, Any]] = []

        for goal in goals:
            reviewed = await self._review_goal(goal, tasks, projects, source=source)
            if reviewed is not None:
                updated_goals.append(reviewed)

        summary = {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "last_review_at": now,
            "updated_goals": updated_goals,
            "goal_count": len(goals),
            "source": source,
        }
        self._last_summary = summary
        await self.memory.log_activity(
            category="proactive.review",
            message=f"Reviewed {len(goals)} active goals.",
            details={"source": source, "updated_goals": len(updated_goals)},
        )
        await self.bus.publish("proactive.review.completed", summary)
        return summary

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            try:
                await self.review_now(source="background")
            except Exception as exc:  # pragma: no cover
                self.logger.warning("Proactive review failed: %s", exc)
                await self.memory.log_activity(
                    category="proactive.review.failed",
                    message="Background proactive review failed.",
                    details={"error": str(exc)},
                )

    async def _review_goal(
        self,
        goal: dict[str, Any],
        tasks: list[dict[str, Any]],
        projects: list[dict[str, Any]],
        source: str,
    ) -> dict[str, Any] | None:
        current_next_action = goal.get("next_action")
        priority = int(goal.get("priority", 50))
        project = self._match_project(goal, projects)
        related_task = self._match_task(goal, tasks)
        metadata = dict(goal.get("metadata", {}))
        metadata["last_review_at"] = utc_now().isoformat()
        metadata["last_review_source"] = source
        metadata["review_count"] = int(metadata.get("review_count", 0)) + 1

        next_action = current_next_action or f"Break '{goal['title']}' into the next concrete step."
        review_note = "Goal reviewed with no major changes."

        if related_task and related_task.get("status") == "failed":
            failed_step = next(
                (step.get("title") for step in related_task.get("steps", []) if step.get("status") == "failed"),
                "a blocked step",
            )
            next_action = f"Resolve the blocker in '{failed_step}' before continuing '{goal['title']}'."
            priority = max(priority, 90)
            review_note = f"Recent task failure detected: {failed_step}."
            metadata["blocked_by"] = failed_step
        elif related_task and related_task.get("status") == "completed":
            latest_goal = related_task.get("goal", goal["title"])
            next_action = f"Build on the completed task '{latest_goal}' to move '{goal['title']}' forward."
            priority = max(priority, 70)
            review_note = "Recent completed task can be used as the next step."
            metadata.pop("blocked_by", None)
        elif project and project.get("metadata", {}).get("last_goal"):
            next_action = f"Continue the project goal '{project['metadata']['last_goal']}'."
            priority = max(priority, 60)
            review_note = "Aligned with the latest project goal."
            metadata.pop("blocked_by", None)
        else:
            suggested = await self._generate_next_action(goal, related_task, project, tasks)
            if suggested:
                next_action = suggested
                priority = max(priority, 55)
                review_note = "Generated a new next action."
            metadata.pop("blocked_by", None)

        if next_action == current_next_action and priority == int(goal.get("priority", 50)):
            metadata["last_review_note"] = review_note
            await self.memory.update_goal(goal["goal_id"], metadata=metadata)
            return None

        metadata["last_review_note"] = review_note
        updated = await self.memory.update_goal(
            goal["goal_id"],
            priority=priority,
            next_action=next_action,
            metadata=metadata,
        )
        return updated

    async def _generate_next_action(
        self,
        goal: dict[str, Any],
        related_task: dict[str, Any] | None,
        project: dict[str, Any] | None,
        tasks: list[dict[str, Any]],
    ) -> str:
        if self.intelligence.snapshot().get("active_provider") == "heuristic":
            detail = goal.get("detail", "").strip()
            if detail and detail.lower() != goal["title"].lower():
                return f"Tackle '{detail}' to move '{goal['title']}' forward."
            if project and project.get("metadata", {}).get("last_goal"):
                return f"Turn '{project['metadata']['last_goal']}' into the next concrete task for '{goal['title']}'."
            return f"Define the next concrete deliverable for '{goal['title']}' and execute it."

        recent_fragments = []
        for task in tasks[:3]:
            recent_fragments.append(f"{task.get('status')}: {task.get('goal')}")
        response = await self.intelligence.respond(
            prompt=(
                "Suggest one concrete next action for this goal in a single sentence. "
                "Do not use bullets or numbering.\n\n"
                f"Goal: {goal['title']}\n"
                f"Detail: {goal.get('detail', goal['title'])}"
            ),
            context={
                "projects": [project] if project else [],
                "goals": [goal],
                "results": recent_fragments,
                "plan": related_task or {},
            },
        )
        line = response.text.strip().splitlines()[0].strip()
        return line.rstrip(".") + "." if line else ""

    def _match_task(self, goal: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
        goal_terms = self._keywords(" ".join([goal.get("title", ""), goal.get("detail", "")]))
        for task in tasks:
            overlap = goal_terms & self._keywords(task.get("goal", ""))
            if overlap:
                return task
        return None

    def _match_project(self, goal: dict[str, Any], projects: list[dict[str, Any]]) -> dict[str, Any] | None:
        if goal.get("project_id"):
            for project in projects:
                if project.get("project_id") == goal["project_id"]:
                    return project
        goal_terms = self._keywords(" ".join([goal.get("title", ""), goal.get("detail", "")]))
        for project in projects:
            overlap = goal_terms & self._keywords(project.get("summary", ""))
            if overlap:
                return project
        return projects[0] if projects else None

    def _keywords(self, value: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z0-9_]+", value.lower()) if len(token) > 2}
