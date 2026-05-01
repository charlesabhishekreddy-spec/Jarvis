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


class ProjectContextsTool(Tool):
    spec = ToolSpec(name="memory.projects", description="List recent project context records.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        results = await context.memory.project_contexts(status=kwargs.get("status"), limit=kwargs.get("limit", 5))
        return {"ok": True, "results": results}


class SuggestionsTool(Tool):
    spec = ToolSpec(name="memory.suggestions", description="List proactive suggestions derived from recent work.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        results = await context.memory.proactive_suggestions(status=kwargs.get("status"), limit=kwargs.get("limit", 5))
        return {"ok": True, "results": results}


class GoalsTool(Tool):
    spec = ToolSpec(name="memory.goals", description="List persistent goals and their next actions.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        results = await context.memory.goals(status=kwargs.get("status"), limit=kwargs.get("limit", 5))
        return {"ok": True, "results": results}


class GoalCreateTool(Tool):
    spec = ToolSpec(name="memory.goal_create", description="Create a persistent goal with priority and next action.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        goal = await context.memory.create_goal(
            title=kwargs["title"],
            detail=kwargs.get("detail", kwargs["title"]),
            priority=kwargs.get("priority", 50),
            project_id=kwargs.get("project_id"),
            next_action=kwargs.get("next_action"),
            metadata=kwargs.get("metadata", {}),
        )
        return {"ok": True, "goal": goal.to_dict()}


class GoalUpdateTool(Tool):
    spec = ToolSpec(name="memory.goal_update", description="Update a goal status, priority, or next action.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        goal_id = kwargs.get("goal_id")
        if not goal_id and kwargs.get("title"):
            existing = await context.memory.find_goal(kwargs["title"], statuses=kwargs.get("statuses"))
            if existing is not None:
                goal_id = existing["goal_id"]
        if not goal_id:
            return {"ok": False, "error": "Goal not found."}
        updated = await context.memory.update_goal(
            goal_id,
            status=kwargs.get("status"),
            priority=kwargs.get("priority"),
            next_action=kwargs.get("next_action"),
            metadata=kwargs.get("metadata"),
        )
        if updated is None:
            return {"ok": False, "error": "Goal not found."}
        return {"ok": True, "goal": updated}


class WebSearchTool(Tool):
    spec = ToolSpec(name="web.search", description="Research the web, news, and public knowledge sources.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        query = kwargs["query"]
        results = await context.web.search(query)
        return {"ok": True, "results": results}


class VisionStatusTool(Tool):
    spec = ToolSpec(name="vision.status", description="Inspect camera, screen capture, and OCR provider availability.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "vision": context.vision.status_snapshot()}


class VisionScreenTool(Tool):
    spec = ToolSpec(name="vision.inspect_screen", description="Capture the current screen and optionally run OCR.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.vision.inspect_screen(
            save_artifact=bool(kwargs.get("save_artifact", True)),
            include_ocr=bool(kwargs.get("include_ocr", True)),
            label=kwargs.get("label"),
        )


class VisionCameraTool(Tool):
    spec = ToolSpec(name="vision.inspect_camera", description="Capture a webcam frame and optionally run OCR.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.vision.inspect_camera(
            save_artifact=bool(kwargs.get("save_artifact", True)),
            include_ocr=bool(kwargs.get("include_ocr", False)),
            label=kwargs.get("label"),
        )


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
        return await context.system_controller.list_processes(limit=kwargs.get("limit", 20), query=kwargs.get("query"))


class TerminateProcessTool(Tool):
    spec = ToolSpec(
        name="system.terminate_process",
        description="Terminate a running process by pid or exact name.",
        requires_confirmation=True,
    )

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        pid = kwargs.get("pid")
        return await context.system_controller.terminate_process(
            pid=int(pid) if pid is not None else None,
            name=kwargs.get("process_name"),
        )


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


class WindowListTool(Tool):
    spec = ToolSpec(name="system.windows", description="List visible desktop windows and their titles.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.list_windows(limit=kwargs.get("limit", 20), query=kwargs.get("query"))


class WindowFocusTool(Tool):
    spec = ToolSpec(name="system.window_focus", description="Focus a matching desktop window by title.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.focus_window(str(kwargs["title"]))


class WindowMinimizeTool(Tool):
    spec = ToolSpec(name="system.window_minimize", description="Minimize a matching desktop window by title.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.minimize_window(str(kwargs["title"]))


class WindowMaximizeTool(Tool):
    spec = ToolSpec(name="system.window_maximize", description="Maximize a matching desktop window by title.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        return await context.system_controller.maximize_window(str(kwargs["title"]))


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
    registry.register(ProjectContextsTool())
    registry.register(SuggestionsTool())
    registry.register(GoalsTool())
    registry.register(GoalCreateTool())
    registry.register(GoalUpdateTool())
    registry.register(WebSearchTool())
    registry.register(VisionStatusTool())
    registry.register(VisionScreenTool())
    registry.register(VisionCameraTool())
    registry.register(FileListTool())
    registry.register(FileReadTool())
    registry.register(ProcessesTool())
    registry.register(TerminateProcessTool())
    registry.register(OpenPathTool())
    registry.register(StartupStatusTool())
    registry.register(DesktopStatusTool())
    registry.register(WindowListTool())
    registry.register(WindowFocusTool())
    registry.register(WindowMinimizeTool())
    registry.register(WindowMaximizeTool())
    registry.register(MouseMoveTool())
    registry.register(MouseClickTool())
    registry.register(KeyboardTypeTool())
    registry.register(KeyboardPressTool())
    registry.register(ShellTool())
    registry.register(FileWriteTool())
    registry.register(ScheduleReminderTool())
