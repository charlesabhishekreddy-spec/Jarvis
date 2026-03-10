from __future__ import annotations

from pathlib import Path
from typing import Any

from jarvis.core.context import JarvisContext

from .base import Tool, ToolSpec


class RememberTool(Tool):
    spec = ToolSpec(name="memory.remember", description="Persist a user memory or note.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        content = kwargs["content"]
        category = kwargs.get("category", "general")
        item = await context.memory.remember(content=content, category=category, metadata=kwargs.get("metadata", {}))
        return {"ok": True, "item_id": item.item_id, "content": item.content, "category": item.category}


class RecallTool(Tool):
    spec = ToolSpec(name="memory.recall", description="Search semantic memory.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        results = await context.memory.recall(query=kwargs["query"], limit=kwargs.get("limit", 5))
        return {"ok": True, "results": results}


class WebSearchTool(Tool):
    spec = ToolSpec(name="web.search", description="Research the web, news, and public knowledge sources.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        query = kwargs["query"]
        results = await context.web.search(query)
        return {"ok": True, "results": results}


class ShellTool(Tool):
    spec = ToolSpec(
        name="system.shell",
        description="Run a shell command inside the configured sandbox.",
        requires_confirmation=True,
    )

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        result = await context.system_controller.run_command(kwargs["command"], kwargs.get("workdir"))
        return {"ok": result["returncode"] == 0, "result": result}


class FileWriteTool(Tool):
    spec = ToolSpec(name="system.write_file", description="Write a UTF-8 text file inside approved directories.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        path = Path(kwargs["path"]).expanduser().resolve()
        if not context.security.is_path_allowed(str(path.parent)):
            return {"ok": False, "error": f"Blocked path: {path}"}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(kwargs["content"], encoding="utf-8")
        return {"ok": True, "path": str(path)}


class ScheduleReminderTool(Tool):
    spec = ToolSpec(name="automation.reminder", description="Schedule a reminder or background automation.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        job = await context.automation.schedule_reminder(message=kwargs["message"], run_at=kwargs["run_at"])
        return {"ok": True, "job": job}


def register_builtin_tools(registry: "ToolRegistry") -> None:
    registry.register(RememberTool())
    registry.register(RecallTool())
    registry.register(WebSearchTool())
    registry.register(ShellTool())
    registry.register(FileWriteTool())
    registry.register(ScheduleReminderTool())
