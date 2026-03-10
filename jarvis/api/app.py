from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from jarvis.core.config import load_settings
from jarvis.core.runtime import JarvisRuntime


class CommandPayload(BaseModel):
    text: str = Field(..., min_length=1)
    confirmed: bool = False


def create_app(settings_path: str | None = None) -> FastAPI:
    settings = load_settings(settings_path)
    runtime = JarvisRuntime(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await runtime.start()
        app.state.runtime = runtime
        yield
        await runtime.stop()

    app = FastAPI(title="JARVIS API", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        snapshot = await runtime.status_snapshot()
        return {"ok": True, "runtime": snapshot["runtime"], "services": snapshot["services"]}

    @app.get("/status")
    async def status() -> dict[str, Any]:
        return await runtime.dashboard_snapshot()

    @app.post("/command")
    async def command(payload: CommandPayload) -> dict[str, Any]:
        response = await runtime.execute_text(payload.text, source="api", confirmed=payload.confirmed)
        return {
            "status": response.status.value,
            "message": response.message,
            "task_id": response.task_id,
            "data": response.data,
        }

    @app.get("/tasks")
    async def tasks(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
        return await runtime.memory.recent_tasks(limit)

    @app.get("/activities")
    async def activities(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return await runtime.memory.recent_activities(limit)

    @app.get("/memory/search")
    async def memory_search(q: str = Query(..., min_length=1), limit: int = Query(default=5, ge=1, le=20)) -> dict[str, Any]:
        return {"results": await runtime.memory.recall(q, limit)}

    @app.get("/plugins")
    async def plugins() -> list[dict[str, Any]]:
        return runtime.plugins.list_plugins()

    @app.get("/jobs")
    async def jobs() -> list[dict[str, Any]]:
        return runtime.automation.list_jobs()

    @app.get("/events")
    async def events(limit: int = Query(default=25, ge=1, le=200)) -> list[dict[str, Any]]:
        return runtime.bus.recent_events(limit)

    return app
