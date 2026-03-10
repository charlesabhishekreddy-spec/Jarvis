from __future__ import annotations

import re

from jarvis.core.models import ActivityRecord, CommandRequest, CommandResponse, TaskPlan, utc_now
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

    def _node_key(self, node_type: str, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
        return f"{node_type}:{slug}"

    def _edge_key(self, subject_key: str, predicate: str, object_key: str) -> str:
        return f"{subject_key}|{predicate}|{object_key}"
