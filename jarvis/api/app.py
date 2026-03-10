from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

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

    app = FastAPI(title="JARVIS API", version="0.3.0", lifespan=lifespan)

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

    @app.post("/voice/text")
    async def voice_text(payload: CommandPayload) -> dict[str, Any]:
        response = await runtime.voice.submit_text_command(payload.text, confirmed=payload.confirmed)
        return {
            "status": response.status.value,
            "message": response.message,
            "task_id": response.task_id,
            "data": response.data,
        }

    @app.post("/plan")
    async def plan(payload: CommandPayload) -> dict[str, Any]:
        request = CommandRequest(text=payload.text, source="api-plan", metadata={"confirmed": payload.confirmed})
        task_plan = runtime.reasoning.planner.create_plan(request)
        return task_plan.to_dict()

    @app.get("/tasks")
    async def tasks(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
        return await runtime.memory.recent_tasks(limit)

    @app.get("/activities")
    async def activities(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return await runtime.memory.recent_activities(limit)

    @app.get("/memory/search")
    async def memory_search(q: str = Query(..., min_length=1), limit: int = Query(default=5, ge=1, le=20)) -> dict[str, Any]:
        return {"results": await runtime.memory.recall(q, limit)}

    @app.get("/memory/graph")
    async def memory_graph(limit: int = Query(default=25, ge=1, le=100)) -> dict[str, Any]:
        return await runtime.memory.graph_snapshot(limit)

    @app.get("/insights")
    async def insights() -> dict[str, Any]:
        return await runtime.learning.insights()

    @app.get("/tools")
    async def tools() -> list[dict[str, Any]]:
        return runtime.tools.list_tools()

    @app.post("/tools/{tool_name}")
    async def execute_tool(tool_name: str, payload: ToolPayload) -> dict[str, Any]:
        return await runtime.tools.execute(tool_name, runtime.context, **payload.params)

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
