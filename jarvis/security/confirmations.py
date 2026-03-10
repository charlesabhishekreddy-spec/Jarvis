from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from jarvis.core.events import AsyncEventBus
from jarvis.core.models import CommandRequest, ConfirmationRecord, ConfirmationStatus, ExecutionRecord, utc_now
from jarvis.core.service import Service
from jarvis.memory.service import MemoryService


Submitter = Callable[[CommandRequest], Awaitable[ExecutionRecord]]


class ConfirmationService(Service):
    def __init__(self, memory: MemoryService, bus: AsyncEventBus, submitter: Submitter) -> None:
        super().__init__("jarvis.confirmations")
        self.memory = memory
        self.bus = bus
        self.submitter = submitter

    async def create(
        self,
        request: CommandRequest,
        risk_level: str,
        reason: str,
        recommended_action: str,
    ) -> ConfirmationRecord:
        record = ConfirmationRecord(
            request_id=request.request_id,
            text=request.text,
            source=request.source,
            risk_level=risk_level,
            reason=reason,
            recommended_action=recommended_action,
            metadata=dict(request.metadata),
        )
        await self.memory.save_confirmation(record.to_dict())
        await self.bus.publish("security.confirmation.created", record.to_dict())
        return record

    async def get(self, confirmation_id: str) -> dict[str, Any] | None:
        return await self.memory.get_confirmation(confirmation_id)

    async def list(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        return await self.memory.confirmations(status=status, limit=limit)

    async def approve(self, confirmation_id: str, decision_note: str | None = None) -> dict[str, Any] | None:
        record = await self.memory.get_confirmation(confirmation_id)
        if record is None:
            return None
        if record["status"] != ConfirmationStatus.PENDING.value:
            return {"confirmation": record, "execution": None}

        record["status"] = ConfirmationStatus.APPROVED.value
        record["resolved_at"] = utc_now().isoformat()
        record["decision_note"] = decision_note
        await self.memory.save_confirmation(record)

        approved_request = CommandRequest(
            text=record["text"],
            source=f"{record['source']}:approved",
            metadata={**record.get("metadata", {}), "confirmed": True, "confirmation_id": confirmation_id},
        )
        execution_record = await self.submitter(approved_request)
        execution = execution_record.to_dict()
        await self.bus.publish(
            "security.confirmation.approved",
            {"confirmation": record, "execution_request_id": execution["request_id"]},
        )
        return {"confirmation": record, "execution": execution}

    async def reject(self, confirmation_id: str, decision_note: str | None = None) -> dict[str, Any] | None:
        record = await self.memory.get_confirmation(confirmation_id)
        if record is None:
            return None
        if record["status"] != ConfirmationStatus.PENDING.value:
            return {"confirmation": record}

        record["status"] = ConfirmationStatus.REJECTED.value
        record["resolved_at"] = utc_now().isoformat()
        record["decision_note"] = decision_note
        await self.memory.save_confirmation(record)
        await self.bus.publish("security.confirmation.rejected", record)
        return {"confirmation": record}
