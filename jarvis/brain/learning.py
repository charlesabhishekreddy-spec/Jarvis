from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jarvis.core.models import CommandRequest, CommandResponse, utc_now
from jarvis.core.service import Service
from jarvis.memory.service import MemoryService

from .intelligence import IntelligenceService


class AdaptiveLearningService(Service):
    def __init__(
        self,
        memory: MemoryService,
        intelligence: IntelligenceService,
        enabled: bool = True,
        workspace_root: str | None = None,
    ) -> None:
        super().__init__("jarvis.learning")
        self.memory = memory
        self.intelligence = intelligence
        self.enabled = enabled
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None

    async def capture_interaction(self, request: CommandRequest, response: CommandResponse) -> None:
        if not self.enabled:
            return
        intent = await self.intelligence.classify_intent(request.text)
        await self.memory.record_pattern(
            pattern=intent,
            metadata={"source": request.source, "status": response.status.value},
        )
        await self.memory.ingest_text(
            request.text,
            source="interaction",
            metadata={"source": request.source, "intent": intent},
        )
        project_context = self._build_project_context(request, response, intent)
        await self.memory.save_project_context(project_context)
        await self.memory.replace_proactive_suggestions(await self._generate_proactive_suggestions(project_context))

    async def insights(self) -> dict[str, Any]:
        return {
            "patterns": await self.memory.top_patterns(10),
            "graph": await self.memory.graph_snapshot(25),
            "projects": await self.memory.project_contexts(limit=5),
            "goals": await self.memory.goals(limit=5),
            "suggestions": await self.memory.proactive_suggestions(limit=5),
        }

    def _build_project_context(self, request: CommandRequest, response: CommandResponse, intent: str) -> dict[str, Any]:
        workspace = Path(request.metadata.get("workspace_root") or self.workspace_root or Path.cwd()).resolve()
        project_name = request.metadata.get("project_name") or workspace.name or "workspace"
        project_id = request.metadata.get("project_id") or f"project:{self._slugify(str(workspace))}"
        plan = response.data.get("plan", {}) if isinstance(response.data, dict) else {}
        step_titles = [step.get("title", "") for step in plan.get("steps", [])[:6] if isinstance(step, dict)]
        summary = (
            f"Project {project_name} is {response.status.value}. "
            f"Latest request: {request.text}. "
            f"Intent: {intent}."
        )
        if plan.get("goal"):
            summary += f" Active goal: {plan['goal']}."
        if step_titles:
            summary += f" Planned steps: {', '.join(step_titles)}."

        status = "blocked" if response.status.value == "failed" else "active"
        if response.status.value == "completed" and not plan.get("goal"):
            status = "active"

        return {
            "project_id": project_id,
            "project_name": project_name,
            "summary": summary,
            "status": status,
            "updated_at": utc_now().isoformat(),
            "metadata": {
                "workspace_root": str(workspace),
                "last_request_text": request.text,
                "last_source": request.source,
                "last_status": response.status.value,
                "last_intent": intent,
                "last_task_id": response.task_id,
                "last_goal": plan.get("goal", request.text),
                "recent_step_titles": step_titles,
            },
        }

    async def _generate_proactive_suggestions(self, project_context: dict[str, Any]) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        now = utc_now().isoformat()
        recent_tasks = await self.memory.recent_tasks(5)
        patterns = await self.memory.top_patterns(5)
        goals = await self.memory.goals(status="active", limit=5)

        if recent_tasks:
            latest = recent_tasks[0]
            latest_goal = latest.get("goal", "the latest task")
            if latest.get("status") == "failed":
                failed_step = next(
                    (step.get("title") for step in latest.get("steps", []) if step.get("status") == "failed"),
                    "a recent step",
                )
                suggestions.append(
                    {
                        "suggestion_id": f"task-failure:{latest.get('plan_id', 'latest')}",
                        "category": "follow_up",
                        "title": "Review blocked task",
                        "detail": f"The task '{latest_goal}' failed at '{failed_step}'. Review the blocker or retry with more context.",
                        "priority": 100,
                        "status": "active",
                        "created_at": now,
                        "updated_at": now,
                        "metadata": {"plan_id": latest.get("plan_id"), "project_id": project_context["project_id"]},
                    }
                )
            elif self._contains_any_term(latest_goal, ("report", "research", "summary")):
                suggestions.append(
                    {
                        "suggestion_id": f"deliverable-review:{latest.get('plan_id', 'latest')}",
                        "category": "follow_up",
                        "title": "Review latest deliverable",
                        "detail": f"The task '{latest_goal}' completed recently. Consider reviewing, refining, or sharing the output.",
                        "priority": 80,
                        "status": "active",
                        "created_at": now,
                        "updated_at": now,
                        "metadata": {"plan_id": latest.get("plan_id"), "project_id": project_context["project_id"]},
                    }
                )

        for pattern in patterns:
            if pattern.get("count", 0) >= 3:
                suggestions.append(
                    {
                        "suggestion_id": f"pattern:{pattern['pattern']}",
                        "category": "automation",
                        "title": "Automate a recurring request",
                        "detail": f"You have repeated '{pattern['pattern']}' {pattern['count']} times. Convert it into a workflow or scheduled action.",
                        "priority": 60,
                        "status": "active",
                        "created_at": now,
                        "updated_at": now,
                        "metadata": {"pattern": pattern["pattern"], "count": pattern["count"]},
                    }
                )
                break

        suggestions.append(
            {
                "suggestion_id": f"project:{project_context['project_id']}",
                "category": "project",
                "title": f"Continue {project_context['project_name']}",
                "detail": project_context["summary"],
                "priority": 50,
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "metadata": {"project_id": project_context["project_id"]},
            }
        )
        if goals:
            focus_goal = goals[0]
            next_action = focus_goal.get("next_action") or focus_goal.get("detail") or focus_goal["title"]
            suggestions.append(
                {
                    "suggestion_id": f"goal:{focus_goal['goal_id']}",
                    "category": "goal",
                    "title": f"Focus on {focus_goal['title']}",
                    "detail": next_action,
                    "priority": max(int(focus_goal.get("priority", 50)), 65),
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                    "metadata": {"goal_id": focus_goal["goal_id"], "project_id": focus_goal.get("project_id")},
                }
            )
        return suggestions[:5]

    def _slugify(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")

    def _contains_any_term(self, text: str, terms: tuple[str, ...]) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in terms)
