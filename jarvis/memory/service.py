from __future__ import annotations

import re
from typing import Any

from jarvis.core.models import (
    ActivityRecord,
    CommandRequest,
    CommandResponse,
    GoalRecord,
    GoalStatus,
    TaskPlan,
    WorkflowRecord,
    WorkflowStepRecord,
    utc_now,
)
from jarvis.core.service import Service

from .knowledge_graph import KnowledgeGraphExtractor
from .models import MemoryItem
from .sqlite_store import SQLiteMemoryStore
from .vector_store import JsonVectorStore


class MemoryService(Service):
    def __init__(self, sqlite_path: str, semantic_index_path: str) -> None:
        super().__init__("jarvis.memory")
        self.sqlite = SQLiteMemoryStore(sqlite_path)
        self.semantic = JsonVectorStore(semantic_index_path)
        self.graph = KnowledgeGraphExtractor()

    async def start(self) -> None:
        await self.sqlite.initialize()
        await self.semantic.initialize()
        await super().start()

    async def remember(self, content: str, category: str = "general", metadata: dict | None = None) -> MemoryItem:
        item = MemoryItem(content=content, category=category, metadata=metadata or {})
        await self.sqlite.save_memory(
            item_id=item.item_id,
            category=item.category,
            content=item.content,
            metadata=item.metadata,
            created_at=item.created_at.isoformat(),
        )
        await self.semantic.add(item.item_id, item.content, {"category": item.category, **item.metadata})
        await self.ingest_text(item.content, source=category, metadata=item.metadata)
        return item

    async def recall(self, query: str, limit: int = 5) -> list[dict]:
        return await self.semantic.search(query, limit)

    async def save_exchange(self, request: CommandRequest, response: CommandResponse) -> None:
        await self.sqlite.save_conversation(request, response)

    async def save_task(self, plan: TaskPlan) -> None:
        await self.sqlite.save_task(plan)

    async def log_activity(self, category: str, message: str, details: dict | None = None) -> None:
        await self.sqlite.log_activity(ActivityRecord(category=category, message=message, details=details or {}))

    async def recent_conversations(self, limit: int = 20) -> list[dict]:
        return await self.sqlite.recent_conversations(limit)

    async def recent_tasks(self, limit: int = 20) -> list[dict]:
        return await self.sqlite.recent_tasks(limit)

    async def recent_activities(self, limit: int = 50) -> list[dict]:
        return await self.sqlite.recent_activities(limit)

    async def ingest_text(self, text: str, source: str = "general", metadata: dict | None = None) -> list[dict]:
        facts = self.graph.extract(text, metadata={"source": source, **(metadata or {})})
        stored: list[dict] = []
        timestamp = utc_now().isoformat()
        for fact in facts:
            subject_key = self._node_key("person", fact.subject)
            object_key = self._node_key("entity", fact.object_value)
            await self.sqlite.upsert_graph_node(
                node_key=subject_key,
                label=fact.subject,
                node_type="person",
                metadata=fact.metadata,
                updated_at=timestamp,
            )
            await self.sqlite.upsert_graph_node(
                node_key=object_key,
                label=fact.object_value,
                node_type="entity",
                metadata=fact.metadata,
                updated_at=timestamp,
            )
            edge_key = self._edge_key(subject_key, fact.predicate, object_key)
            await self.sqlite.upsert_graph_edge(
                edge_key=edge_key,
                subject_key=subject_key,
                predicate=fact.predicate,
                object_key=object_key,
                metadata=fact.metadata,
                updated_at=timestamp,
            )
            stored.append(
                {
                    "subject_key": subject_key,
                    "predicate": fact.predicate,
                    "object_key": object_key,
                }
            )
        return stored

    async def graph_snapshot(self, limit: int = 25) -> dict:
        return await self.sqlite.graph_snapshot(limit)

    async def record_pattern(self, pattern: str, metadata: dict | None = None) -> None:
        await self.sqlite.record_pattern(pattern=pattern, metadata=metadata or {}, updated_at=utc_now().isoformat())

    async def top_patterns(self, limit: int = 10) -> list[dict]:
        return await self.sqlite.top_patterns(limit)

    async def save_automation_job(self, job: dict) -> None:
        await self.sqlite.save_automation_job(job)

    async def automation_jobs(self, status: str | None = None, limit: int = 100) -> list[dict]:
        return await self.sqlite.automation_jobs(status=status, limit=limit)

    async def save_confirmation(self, confirmation: dict) -> None:
        await self.sqlite.save_confirmation(confirmation)

    async def get_confirmation(self, confirmation_id: str) -> dict | None:
        return await self.sqlite.get_confirmation(confirmation_id)

    async def confirmations(self, status: str | None = None, limit: int = 100) -> list[dict]:
        return await self.sqlite.confirmations(status=status, limit=limit)

    async def save_project_context(self, context: dict) -> None:
        await self.sqlite.save_project_context(context)

    async def project_context(self, project_id: str) -> dict | None:
        return await self.sqlite.project_context(project_id)

    async def project_contexts(self, status: str | None = None, limit: int = 25) -> list[dict]:
        return await self.sqlite.project_contexts(status=status, limit=limit)

    async def replace_proactive_suggestions(self, suggestions: list[dict]) -> None:
        await self.sqlite.replace_proactive_suggestions(suggestions)

    async def proactive_suggestions(self, status: str | None = None, limit: int = 25) -> list[dict]:
        return await self.sqlite.proactive_suggestions(status=status, limit=limit)

    async def create_goal(
        self,
        title: str,
        detail: str = "",
        priority: int = 50,
        project_id: str | None = None,
        next_action: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GoalRecord:
        goal = GoalRecord(
            title=title,
            detail=detail or title,
            priority=max(1, min(int(priority), 100)),
            project_id=project_id,
            next_action=next_action,
            metadata=metadata or {},
        )
        await self.sqlite.save_goal(goal.to_dict())
        return goal

    async def save_goal(self, goal: dict[str, Any]) -> None:
        await self.sqlite.save_goal(goal)

    async def goal(self, goal_id: str) -> dict[str, Any] | None:
        return await self.sqlite.goal(goal_id)

    async def find_goal(self, title: str, statuses: list[str] | None = None) -> dict[str, Any] | None:
        return await self.sqlite.find_goal(title, statuses=statuses)

    async def goals(self, status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return await self.sqlite.goals(status=status, limit=limit)

    async def update_goal(self, goal_id: str, **updates: Any) -> dict[str, Any] | None:
        goal = await self.goal(goal_id)
        if goal is None:
            return None
        goal.update({key: value for key, value in updates.items() if value is not None})
        goal["priority"] = max(1, min(int(goal.get("priority", 50)), 100))
        goal["updated_at"] = utc_now().isoformat()
        if goal.get("status") == GoalStatus.COMPLETED.value and not goal.get("completed_at"):
            goal["completed_at"] = goal["updated_at"]
        if goal.get("status") != GoalStatus.COMPLETED.value:
            goal["completed_at"] = None
        await self.sqlite.save_goal(goal)
        return goal

    async def create_workflow(
        self,
        title: str,
        commands: list[str],
        goal_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowRecord:
        steps: list[WorkflowStepRecord] = []
        previous_step_id: str | None = None
        for index, command in enumerate(commands, start=1):
            step = WorkflowStepRecord(
                title=f"Step {index}",
                command_text=command,
                depends_on=[previous_step_id] if previous_step_id else [],
            )
            steps.append(step)
            previous_step_id = step.step_id
        workflow = WorkflowRecord(title=title, steps=steps, goal_id=goal_id, metadata=metadata or {})
        await self.sqlite.save_workflow(workflow.to_dict())
        return workflow

    async def save_workflow(self, workflow: dict[str, Any]) -> None:
        await self.sqlite.save_workflow(workflow)

    async def workflow(self, workflow_id: str) -> dict[str, Any] | None:
        return await self.sqlite.workflow(workflow_id)

    async def workflows(self, status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return await self.sqlite.workflows(status=status, limit=limit)

    async def find_workflow(self, title: str, statuses: list[str] | None = None) -> dict[str, Any] | None:
        return await self.sqlite.find_workflow(title, statuses=statuses)

    def _node_key(self, node_type: str, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
        return f"{node_type}:{slug}"

    def _edge_key(self, subject_key: str, predicate: str, object_key: str) -> str:
        return f"{subject_key}|{predicate}|{object_key}"
