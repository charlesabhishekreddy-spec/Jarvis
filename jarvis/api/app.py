from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from jarvis.core.config import load_settings
from jarvis.core.models import CommandRequest
from jarvis.core.runtime import JarvisRuntime


class CommandPayload(BaseModel):
    text: str = Field(..., min_length=1)
    confirmed: bool = False


class ToolPayload(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


class DecisionPayload(BaseModel):
    note: str | None = None


class IntelligencePromptPayload(BaseModel):
    prompt: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class VoiceSimulatePayload(BaseModel):
    text: str = Field(..., min_length=1)
    confirmed: bool = False
    strict_wake: bool = True


class VisionCapturePayload(BaseModel):
    save_artifact: bool = True
    include_ocr: bool = True
    label: str | None = None


class ProcessTerminatePayload(BaseModel):
    pid: int | None = Field(default=None, ge=1)
    name: str | None = None
    confirmed: bool = False


class WindowActionPayload(BaseModel):
    title: str = Field(..., min_length=1)


class GoalPayload(BaseModel):
    title: str = Field(..., min_length=1)
    detail: str = ""
    priority: int = Field(default=60, ge=1, le=100)
    next_action: str | None = None
    project_id: str | None = None


class GoalStatusPayload(BaseModel):
    status: Literal["active", "paused", "blocked", "completed"]
    priority: int | None = Field(default=None, ge=1, le=100)
    next_action: str | None = None


class WorkflowPayload(BaseModel):
    title: str = Field(..., min_length=1)
    steps: list[str] = Field(..., min_length=1)
    goal_id: str | None = None


class StartupInstallPayload(BaseModel):
    mode: Literal["api", "background"] = "api"
    config_path: str | None = None
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)


def create_app(settings_path: str | None = None) -> FastAPI:
    settings = load_settings(settings_path)
    runtime = JarvisRuntime(settings)
    dashboard_dir = Path(__file__).resolve().parents[1] / "ui" / "web"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await runtime.start()
        app.state.runtime = runtime
        yield
        await runtime.stop()

    app = FastAPI(title="JARVIS API", version="0.4.0", lifespan=lifespan)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/dashboard")

    @app.get("/dashboard", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(dashboard_dir / "index.html")

    @app.get("/assets/{asset_name}", include_in_schema=False)
    async def asset(asset_name: str) -> FileResponse:
        path = (dashboard_dir / asset_name).resolve()
        if dashboard_dir.resolve() not in path.parents or not path.exists():
            raise HTTPException(status_code=404, detail="Asset not found.")
        return FileResponse(path)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        snapshot = await runtime.status_snapshot()
        return {"ok": True, "runtime": snapshot["runtime"], "services": snapshot["services"]}

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return await runtime.dashboard_snapshot()

    @app.get("/intelligence")
    async def intelligence_status() -> dict[str, Any]:
        return runtime.intelligence.snapshot()

    @app.post("/intelligence/respond")
    async def intelligence_respond(payload: IntelligencePromptPayload) -> dict[str, Any]:
        result = await runtime.intelligence.respond(payload.prompt, context=payload.context)
        return {
            "text": result.text,
            "provider": result.provider,
            "model": result.model,
            "metadata": result.metadata,
        }

    @app.get("/startup")
    async def startup_status() -> dict[str, Any]:
        return await runtime.system_controller.startup_status()

    @app.post("/startup/install")
    async def startup_install(payload: StartupInstallPayload) -> dict[str, Any]:
        return await runtime.system_controller.install_startup(
            mode=payload.mode,
            config_path=payload.config_path,
            host=payload.host,
            port=payload.port,
        )

    @app.post("/startup/uninstall")
    async def startup_uninstall() -> dict[str, Any]:
        return await runtime.system_controller.uninstall_startup()

    @app.get("/stream/events")
    async def stream_events(topic: str = Query(default="*")) -> StreamingResponse:
        queue, handler = await runtime.bus.open_stream(topic)

        async def event_generator():
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15)
                        payload = json.dumps(runtime.bus.serialize_event(event))
                        yield f"data: {payload}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
                await runtime.bus.unsubscribe(topic, handler)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket, topic: str = "*") -> None:
        await websocket.accept()
        queue, handler = await runtime.bus.open_stream(topic)
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(runtime.bus.serialize_event(event))
        except WebSocketDisconnect:
            return
        finally:
            await runtime.bus.unsubscribe(topic, handler)

    @app.post("/command")
    async def command(payload: CommandPayload) -> dict[str, Any]:
        response = await runtime.execute_text(payload.text, source="api", confirmed=payload.confirmed)
        return {
            "status": response.status.value,
            "message": response.message,
            "task_id": response.task_id,
            "data": response.data,
        }

    @app.post("/command/async")
    async def command_async(payload: CommandPayload) -> dict[str, Any]:
        return await runtime.submit_text(payload.text, source="api-async", confirmed=payload.confirmed)

    @app.post("/voice/text")
    async def voice_text(payload: CommandPayload) -> dict[str, Any]:
        response = await runtime.voice.submit_text_command(payload.text, confirmed=payload.confirmed)
        return {
            "status": response.status.value,
            "message": response.message,
            "task_id": response.task_id,
            "data": response.data,
        }

    @app.get("/voice")
    async def voice_status() -> dict[str, Any]:
        return runtime.voice.status_snapshot()

    @app.post("/voice/start")
    async def voice_start() -> dict[str, Any]:
        return await runtime.voice.start_listening()

    @app.post("/voice/stop")
    async def voice_stop() -> dict[str, Any]:
        return await runtime.voice.stop_listening()

    @app.post("/voice/simulate")
    async def voice_simulate(payload: VoiceSimulatePayload) -> dict[str, Any]:
        response = await runtime.voice.simulate_heard_text(
            payload.text,
            confirmed=payload.confirmed,
            strict_wake=payload.strict_wake,
        )
        return {
            "status": response.status.value,
            "message": response.message,
            "task_id": response.task_id,
            "data": response.data,
        }

    @app.get("/vision")
    async def vision_status() -> dict[str, Any]:
        return runtime.vision.status_snapshot()

    @app.post("/vision/screen")
    async def vision_screen(payload: VisionCapturePayload) -> dict[str, Any]:
        return await runtime.vision.inspect_screen(
            save_artifact=payload.save_artifact,
            include_ocr=payload.include_ocr,
            label=payload.label,
        )

    @app.post("/vision/camera")
    async def vision_camera(payload: VisionCapturePayload) -> dict[str, Any]:
        return await runtime.vision.inspect_camera(
            save_artifact=payload.save_artifact,
            include_ocr=payload.include_ocr,
            label=payload.label,
        )

    @app.get("/processes")
    async def processes(
        limit: int = Query(default=20, ge=1, le=200),
        q: str | None = Query(default=None),
    ) -> dict[str, Any]:
        return await runtime.system_controller.list_processes(limit=limit, query=q)

    @app.post("/processes/terminate")
    async def terminate_process(payload: ProcessTerminatePayload) -> dict[str, Any]:
        if payload.pid is None and not (payload.name or "").strip():
            raise HTTPException(status_code=400, detail="Provide pid or name.")
        target = str(payload.pid) if payload.pid is not None else str(payload.name).strip()
        response = await runtime.execute_text(
            f"Jarvis stop process {target}",
            source="api-process",
            confirmed=payload.confirmed,
        )
        return {
            "status": response.status.value,
            "message": response.message,
            "task_id": response.task_id,
            "data": response.data,
        }

    @app.get("/windows")
    async def windows(
        limit: int = Query(default=20, ge=1, le=200),
        q: str | None = Query(default=None),
    ) -> dict[str, Any]:
        return await runtime.system_controller.list_windows(limit=limit, query=q)

    @app.post("/windows/focus")
    async def window_focus(payload: WindowActionPayload) -> dict[str, Any]:
        return await runtime.system_controller.focus_window(payload.title)

    @app.post("/windows/minimize")
    async def window_minimize(payload: WindowActionPayload) -> dict[str, Any]:
        return await runtime.system_controller.minimize_window(payload.title)

    @app.post("/windows/maximize")
    async def window_maximize(payload: WindowActionPayload) -> dict[str, Any]:
        return await runtime.system_controller.maximize_window(payload.title)

    @app.post("/plan")
    async def plan(payload: CommandPayload) -> dict[str, Any]:
        request = CommandRequest(text=payload.text, source="api-plan", metadata={"confirmed": payload.confirmed})
        task_plan = runtime.reasoning.planner.create_plan(request)
        return task_plan.to_dict()

    @app.get("/tasks")
    async def tasks(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
        return await runtime.memory.recent_tasks(limit)

    @app.get("/commands")
    async def commands(limit: int = Query(default=20, ge=1, le=200)) -> list[dict[str, Any]]:
        return runtime.command_queue.list(limit)

    @app.get("/commands/{request_id}")
    async def command_status(request_id: str) -> dict[str, Any]:
        record = runtime.command_queue.get(request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Command execution not found.")
        return record

    @app.post("/commands/{request_id}/cancel")
    async def command_cancel(request_id: str) -> dict[str, Any]:
        record = await runtime.command_queue.cancel(request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Command execution not found.")
        return record.to_dict()

    @app.get("/confirmations")
    async def confirmations(
        status: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        return await runtime.confirmations.list(status=status, limit=limit)

    @app.get("/confirmations/{confirmation_id}")
    async def confirmation(confirmation_id: str) -> dict[str, Any]:
        record = await runtime.confirmations.get(confirmation_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Confirmation not found.")
        return record

    @app.post("/confirmations/{confirmation_id}/approve")
    async def approve_confirmation(confirmation_id: str, payload: DecisionPayload) -> dict[str, Any]:
        result = await runtime.confirmations.approve(confirmation_id, decision_note=payload.note)
        if result is None:
            raise HTTPException(status_code=404, detail="Confirmation not found.")
        return result

    @app.post("/confirmations/{confirmation_id}/reject")
    async def reject_confirmation(confirmation_id: str, payload: DecisionPayload) -> dict[str, Any]:
        result = await runtime.confirmations.reject(confirmation_id, decision_note=payload.note)
        if result is None:
            raise HTTPException(status_code=404, detail="Confirmation not found.")
        return result

    @app.get("/activities")
    async def activities(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return await runtime.memory.recent_activities(limit)

    @app.get("/memory/search")
    async def memory_search(q: str = Query(..., min_length=1), limit: int = Query(default=5, ge=1, le=20)) -> dict[str, Any]:
        return {"results": await runtime.memory.recall(q, limit)}

    @app.get("/memory/graph")
    async def memory_graph(limit: int = Query(default=25, ge=1, le=100)) -> dict[str, Any]:
        return await runtime.memory.graph_snapshot(limit)

    @app.get("/memory/projects")
    async def memory_projects(limit: int = Query(default=10, ge=1, le=100)) -> list[dict[str, Any]]:
        return await runtime.memory.project_contexts(limit=limit)

    @app.get("/goals")
    async def goals(
        status: str | None = Query(default=None),
        limit: int = Query(default=10, ge=1, le=100),
    ) -> list[dict[str, Any]]:
        return await runtime.memory.goals(status=status, limit=limit)

    @app.post("/goals")
    async def create_goal(payload: GoalPayload) -> dict[str, Any]:
        goal = await runtime.memory.create_goal(
            title=payload.title,
            detail=payload.detail or payload.title,
            priority=payload.priority,
            next_action=payload.next_action,
            project_id=payload.project_id,
        )
        return goal.to_dict()

    @app.post("/goals/review")
    async def review_goals() -> dict[str, Any]:
        return await runtime.proactive.review_now(source="api")

    @app.get("/goals/{goal_id}")
    async def get_goal(goal_id: str) -> dict[str, Any]:
        goal = await runtime.memory.goal(goal_id)
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found.")
        return goal

    @app.post("/goals/{goal_id}/status")
    async def update_goal_status(goal_id: str, payload: GoalStatusPayload) -> dict[str, Any]:
        goal = await runtime.memory.update_goal(
            goal_id,
            status=payload.status,
            priority=payload.priority,
            next_action=payload.next_action,
        )
        if goal is None:
            raise HTTPException(status_code=404, detail="Goal not found.")
        return goal

    @app.get("/workflows")
    async def workflows(
        status: str | None = Query(default=None),
        limit: int = Query(default=10, ge=1, le=100),
    ) -> list[dict[str, Any]]:
        return await runtime.orchestration.workflows(status=status, limit=limit)

    @app.post("/workflows")
    async def create_workflow(payload: WorkflowPayload) -> dict[str, Any]:
        return await runtime.orchestration.create_workflow(
            title=payload.title,
            commands=payload.steps,
            goal_id=payload.goal_id,
            metadata={"source": "api"},
        )

    @app.get("/workflows/{workflow_id}")
    async def get_workflow(workflow_id: str) -> dict[str, Any]:
        workflow = await runtime.memory.workflow(workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found.")
        return workflow

    @app.post("/workflows/{workflow_id}/run")
    async def run_workflow(workflow_id: str) -> dict[str, Any]:
        result = await runtime.orchestration.run_workflow(workflow_id)
        if not result.get("ok", False):
            raise HTTPException(status_code=404, detail=result.get("error", "Workflow not found."))
        return result

    @app.post("/workflows/{workflow_id}/cancel")
    async def cancel_workflow(workflow_id: str) -> dict[str, Any]:
        result = await runtime.orchestration.cancel_workflow(workflow_id)
        if not result.get("ok", False):
            raise HTTPException(status_code=404, detail=result.get("error", "Workflow not found."))
        return result

    @app.get("/suggestions")
    async def suggestions(limit: int = Query(default=10, ge=1, le=100)) -> list[dict[str, Any]]:
        return await runtime.memory.proactive_suggestions(limit=limit)

    @app.get("/insights")
    async def insights() -> dict[str, Any]:
        return await runtime.learning.insights()

    @app.get("/tools")
    async def tools() -> list[dict[str, Any]]:
        return runtime.tools.list_tools()

    @app.post("/tools/{tool_name}")
    async def execute_tool(tool_name: str, payload: ToolPayload) -> dict[str, Any]:
        return await runtime.tools.execute(tool_name, runtime.context, confirmed=payload.confirmed, **payload.params)

    @app.get("/plugins")
    async def plugins() -> list[dict[str, Any]]:
        return runtime.plugins.list_plugins()

    @app.get("/jobs")
    async def jobs() -> list[dict[str, Any]]:
        return await runtime.automation.snapshot_jobs()

    @app.post("/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str) -> dict[str, Any]:
        return await runtime.automation.cancel_job(job_id)

    @app.get("/events")
    async def events(limit: int = Query(default=25, ge=1, le=200)) -> list[dict[str, Any]]:
        return runtime.bus.recent_events(limit)

    return app
