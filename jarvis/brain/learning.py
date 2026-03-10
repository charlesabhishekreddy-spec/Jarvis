from __future__ import annotations

from typing import Any

from jarvis.core.models import CommandRequest, CommandResponse
from jarvis.core.service import Service
from jarvis.memory.service import MemoryService

from .intelligence import IntelligenceService


class AdaptiveLearningService(Service):
    def __init__(self, memory: MemoryService, intelligence: IntelligenceService, enabled: bool = True) -> None:
        super().__init__("jarvis.learning")
        self.memory = memory
        self.intelligence = intelligence
        self.enabled = enabled

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

    async def insights(self) -> dict[str, Any]:
        return {
            "patterns": await self.memory.top_patterns(10),
            "graph": await self.memory.graph_snapshot(25),
        }
