from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from jarvis.core.events import AsyncEventBus
from jarvis.core.models import CommandRequest, ExecutionRecord, TaskStatus, utc_now
from jarvis.core.service import Service
from jarvis.memory.service import MemoryService


SubmitCallable = Callable[[CommandRequest], Awaitable[ExecutionRecord]]
LookupCallable = Callable[[str], dict[str, Any] | None]
CancelCallable = Callable[[str], Awaitable[ExecutionRecord | None]]


class OrchestrationService(Service):
    def __init__(
        self,
        bus: AsyncEventBus,
        memory: MemoryService,
        submit_request: SubmitCallable,
        lookup_execution: LookupCallable,
        cancel_execution: CancelCallable,
    ) -> None:
        super().__init__("jarvis.orchestration")
        self.bus = bus
        self.memory = memory
        self.submit_request = submit_request
        self.lookup_execution = lookup_execution
        self.cancel_execution = cancel_execution
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def snapshot(self) -> dict[str, Any]:
        running = [workflow_id for workflow_id, task in self._tasks.items() if not task.done()]
        return {"running": running, "count": len(running)}

    async def start(self) -> None:
        await super().start()
        await self._restore_workflows()

    async def create_workflow(
        self,
        title: str,
        commands: list[str],
        goal_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workflow = await self.memory.create_workflow(title=title, commands=commands, goal_id=goal_id, metadata=metadata)
        payload = workflow.to_dict()
        await self.bus.publish("workflow.created", payload)
        return payload

    async def run_workflow(self, workflow_id: str) -> dict[str, Any]:
        workflow = await self.memory.workflow(workflow_id)
        if workflow is None:
            return {"ok": False, "error": f"Workflow not found: {workflow_id}"}

        if workflow_id in self._tasks and not self._tasks[workflow_id].done():
            return {"ok": True, "workflow": workflow, "message": "Workflow is already running."}

        for step in workflow["steps"]:
            step["status"] = TaskStatus.PENDING.value
            step["result"] = None
            step["request_id"] = None
        workflow["status"] = TaskStatus.QUEUED.value
        workflow["updated_at"] = utc_now().isoformat()
        await self.memory.save_workflow(workflow)
        await self.bus.publish("workflow.queued", workflow)

        self._tasks[workflow_id] = asyncio.create_task(self._runner(workflow_id))
        return {"ok": True, "workflow": workflow}

    async def cancel_workflow(self, workflow_id: str) -> dict[str, Any]:
        workflow = await self.memory.workflow(workflow_id)
        if workflow is None:
            return {"ok": False, "error": f"Workflow not found: {workflow_id}"}

        task = self._tasks.get(workflow_id)
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            self._tasks.pop(workflow_id, None)

        for step in workflow["steps"]:
            if step["status"] == TaskStatus.IN_PROGRESS.value and step.get("request_id"):
                await self.cancel_execution(step["request_id"])
                step["status"] = TaskStatus.CANCELLED.value
                step["result"] = "Workflow cancelled."

        workflow["status"] = TaskStatus.CANCELLED.value
        workflow["updated_at"] = utc_now().isoformat()
        await self.memory.save_workflow(workflow)
        await self.bus.publish("workflow.cancelled", workflow)
        return {"ok": True, "workflow": workflow}

    async def workflows(self, status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return await self.memory.workflows(status=status, limit=limit)

    async def stop(self) -> None:
        for workflow_id in list(self._tasks):
            await self._mark_interrupted(workflow_id)
        for task in self._tasks.values():
            task.cancel()
        for task in list(self._tasks.values()):
            with suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()
        await super().stop()

    async def _runner(self, workflow_id: str) -> None:
        try:
            workflow = await self.memory.workflow(workflow_id)
            if workflow is None:
                return

            workflow["status"] = TaskStatus.IN_PROGRESS.value
            workflow["updated_at"] = utc_now().isoformat()
            await self.memory.save_workflow(workflow)
            await self.bus.publish("workflow.started", workflow)

            while True:
                workflow = await self.memory.workflow(workflow_id)
                if workflow is None:
                    return

                if all(step["status"] == TaskStatus.COMPLETED.value for step in workflow["steps"]):
                    workflow["status"] = TaskStatus.COMPLETED.value
                    workflow["updated_at"] = utc_now().isoformat()
                    await self.memory.save_workflow(workflow)
                    await self.bus.publish("workflow.completed", workflow)
                    return

                ready_step = next(
                    (
                        step
                        for step in workflow["steps"]
                        if step["status"] == TaskStatus.PENDING.value and self._dependencies_satisfied(workflow["steps"], step)
                    ),
                    None,
                )
                if ready_step is None:
                    workflow["status"] = TaskStatus.FAILED.value
                    workflow["updated_at"] = utc_now().isoformat()
                    await self.memory.save_workflow(workflow)
                    await self.bus.publish(
                        "workflow.failed",
                        {
                            **workflow,
                            "error": "No runnable workflow step remained. Dependencies may be blocked by a failed step.",
                        },
                    )
                    return

                ready_step["status"] = TaskStatus.QUEUED.value
                workflow["updated_at"] = utc_now().isoformat()
                await self.memory.save_workflow(workflow)

                record = await self.submit_request(
                    CommandRequest(
                        text=ready_step["command_text"],
                        source=f"workflow:{workflow_id}",
                        metadata={
                            "workflow_id": workflow_id,
                            "workflow_title": workflow["title"],
                            "workflow_step_id": ready_step["step_id"],
                        },
                    )
                )
                ready_step["request_id"] = record.request_id
                ready_step["status"] = TaskStatus.IN_PROGRESS.value
                workflow["updated_at"] = utc_now().isoformat()
                await self.memory.save_workflow(workflow)
                await self.bus.publish(
                    "workflow.step.started",
                    {"workflow_id": workflow_id, "step_id": ready_step["step_id"], "request_id": record.request_id},
                )

                execution = await self._wait_for_execution(record.request_id)
                ready_step["status"] = execution["status"]
                ready_step["result"] = execution.get("message") or execution.get("error")
                workflow["updated_at"] = utc_now().isoformat()
                await self.memory.save_workflow(workflow)
                await self.bus.publish(
                    "workflow.step.completed",
                    {
                        "workflow_id": workflow_id,
                        "step_id": ready_step["step_id"],
                        "status": ready_step["status"],
                        "request_id": record.request_id,
                    },
                )

                if ready_step["status"] == TaskStatus.COMPLETED.value:
                    continue

                workflow["status"] = ready_step["status"]
                workflow["updated_at"] = utc_now().isoformat()
                await self.memory.save_workflow(workflow)
                await self.bus.publish("workflow.updated", workflow)
                return
        finally:
            self._tasks.pop(workflow_id, None)

    async def _wait_for_execution(self, request_id: str) -> dict[str, Any]:
        while True:
            execution = self.lookup_execution(request_id)
            if execution is None:
                await asyncio.sleep(0.05)
                continue
            if execution["status"] in {
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
                TaskStatus.CANCELLED.value,
                TaskStatus.REQUIRES_CONFIRMATION.value,
            }:
                return execution
            await asyncio.sleep(0.05)

    def _dependencies_satisfied(self, steps: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
        completed = {step["step_id"] for step in steps if step["status"] == TaskStatus.COMPLETED.value}
        return all(step_id in completed for step_id in candidate.get("depends_on", []))

    async def _restore_workflows(self) -> None:
        workflows = await self.memory.workflows(limit=200)
        for workflow in workflows:
            if workflow["status"] not in {TaskStatus.QUEUED.value, TaskStatus.IN_PROGRESS.value}:
                continue
            normalized = self._normalize_resume_state(workflow, reason="restored")
            await self.memory.save_workflow(normalized)
            self._tasks[workflow["workflow_id"]] = asyncio.create_task(self._runner(workflow["workflow_id"]))
            await self.bus.publish("workflow.restored", normalized)

    async def _mark_interrupted(self, workflow_id: str) -> None:
        workflow = await self.memory.workflow(workflow_id)
        if workflow is None:
            return
        normalized = self._normalize_resume_state(workflow, reason="interrupted")
        await self.memory.save_workflow(normalized)

    def _normalize_resume_state(self, workflow: dict[str, Any], reason: str) -> dict[str, Any]:
        metadata = dict(workflow.get("metadata", {}))
        metadata[f"{reason}_at"] = utc_now().isoformat()
        workflow["metadata"] = metadata
        workflow["status"] = TaskStatus.QUEUED.value
        workflow["updated_at"] = utc_now().isoformat()
        for step in workflow["steps"]:
            if step["status"] in {TaskStatus.QUEUED.value, TaskStatus.IN_PROGRESS.value}:
                step["status"] = TaskStatus.PENDING.value
                step["result"] = None
                step["request_id"] = None
        return workflow
