from __future__ import annotations

from jarvis.core.models import ActivityRecord, CommandRequest, CommandResponse, TaskPlan
from jarvis.core.service import Service

from .models import MemoryItem
from .sqlite_store import SQLiteMemoryStore
from .vector_store import JsonVectorStore


class MemoryService(Service):
    def __init__(self, sqlite_path: str, semantic_index_path: str) -> None:
        super().__init__("jarvis.memory")
        self.sqlite = SQLiteMemoryStore(sqlite_path)
        self.semantic = JsonVectorStore(semantic_index_path)

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
