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


class FileListTool(Tool):
    spec = ToolSpec(name="system.list_files", description="List files and directories inside an approved path.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.list_files(
            path=kwargs.get("path"),
            recursive=kwargs.get("recursive", False),
            limit=kwargs.get("limit", 50),
            pattern=kwargs.get("pattern"),
        )


class FileReadTool(Tool):
    spec = ToolSpec(name="system.read_file", description="Read a UTF-8 text file inside approved directories.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.read_text_file(kwargs["path"], max_chars=kwargs.get("max_chars", 8000))


class ProcessesTool(Tool):
    spec = ToolSpec(name="system.processes", description="List running processes and system process telemetry.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.list_processes(limit=kwargs.get("limit", 20))


class OpenPathTool(Tool):
    spec = ToolSpec(name="system.open_path", description="Open a file or folder in the operating system.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        message = await context.system_controller.open_path(kwargs["path"])
        return {"ok": not message.lower().startswith("failed") and not message.lower().startswith("path not found"), "message": message}


class StartupStatusTool(Tool):
    spec = ToolSpec(name="system.startup_status", description="Inspect whether JARVIS is configured to start automatically.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        status = await context.system_controller.startup_status(mode=kwargs.get("mode"))
        return {"ok": True, "startup": status}


class DesktopStatusTool(Tool):
    spec = ToolSpec(name="system.desktop_status", description="Inspect desktop automation availability and screen size.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.desktop_status()


class MouseMoveTool(Tool):
    spec = ToolSpec(
        name="system.mouse_move",
        description="Move the mouse cursor to a screen position.",
        requires_confirmation=True,
    )

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.move_mouse(
            x=int(kwargs["x"]),
            y=int(kwargs["y"]),
            duration=float(kwargs.get("duration", 0.0)),
        )


class MouseClickTool(Tool):
    spec = ToolSpec(
        name="system.mouse_click",
        description="Click the mouse at a specific screen position.",
        requires_confirmation=True,
    )

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.click(
            x=int(kwargs["x"]),
            y=int(kwargs["y"]),
            button=str(kwargs.get("button", "left")),
            clicks=int(kwargs.get("clicks", 1)),
        )


class KeyboardTypeTool(Tool):
    spec = ToolSpec(
        name="system.keyboard_type",
        description="Type text into the active application.",
        requires_confirmation=True,
    )

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.type_text(
            text=str(kwargs["text"]),
            interval=float(kwargs.get("interval", 0.0)),
        )


class KeyboardPressTool(Tool):
    spec = ToolSpec(
        name="system.keyboard_press",
        description="Press a key or shortcut in the active application.",
        requires_confirmation=True,
    )

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        keys = kwargs.get("keys", [])
        return await context.system_controller.press_keys([str(key) for key in keys])


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
    registry.register(FileListTool())
    registry.register(FileReadTool())
    registry.register(ProcessesTool())
    registry.register(OpenPathTool())
    registry.register(StartupStatusTool())
    registry.register(DesktopStatusTool())
    registry.register(MouseMoveTool())
    registry.register(MouseClickTool())
    registry.register(KeyboardTypeTool())
    registry.register(KeyboardPressTool())
    registry.register(ShellTool())
    registry.register(FileWriteTool())
    registry.register(ScheduleReminderTool())
