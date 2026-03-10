from __future__ import annotations

from pathlib import Path
from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class SystemAgent(BaseAgent):
    name = "system"
    description = "Interacts with the operating system and local files."
    keywords = ("open", "launch", "terminal", "file", "save", "application")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        action = step.metadata.get("action", "resource_usage")
        confirmed = bool(request.metadata.get("confirmed", False))
        if action == "write_file":
            result = await context.tools.execute(
                "system.write_file",
                context,
                confirmed=confirmed,
                path=step.metadata["path"],
                content=step.metadata["content"],
            )
            if not result.get("ok", False):
                return {"message": result.get("error", f"Failed to save file to {step.metadata['path']}."), "result": result}
            return {"message": f"Saved file to {result.get('path', step.metadata['path'])}.", "result": result}
        if action == "shell":
            result = await context.tools.execute(
                "system.shell",
                context,
                confirmed=confirmed,
                command=step.metadata["command"],
                workdir=step.metadata.get("workdir"),
            )
            if not result.get("ok", False):
                return {"message": result.get("error", "Shell execution failed."), "result": result}
            return {"message": result["result"]["stdout"] or result["result"]["stderr"], "result": result}
        if action == "desktop_status":
            result = await context.tools.execute("system.desktop_status", context, confirmed=confirmed)
            return {"message": result.get("message", result.get("error", "Desktop status unavailable.")), "result": result}
        if action == "mouse_move":
            result = await context.tools.execute(
                "system.mouse_move",
                context,
                confirmed=confirmed,
                x=step.metadata["x"],
                y=step.metadata["y"],
                duration=step.metadata.get("duration", 0.0),
            )
            return {"message": result.get("message", result.get("error", "Mouse move failed.")), "result": result}
        if action == "mouse_click":
            result = await context.tools.execute(
                "system.mouse_click",
                context,
                confirmed=confirmed,
                x=step.metadata["x"],
                y=step.metadata["y"],
                button=step.metadata.get("button", "left"),
                clicks=step.metadata.get("clicks", 1),
            )
            return {"message": result.get("message", result.get("error", "Mouse click failed.")), "result": result}
        if action == "keyboard_type":
            result = await context.tools.execute(
                "system.keyboard_type",
                context,
                confirmed=confirmed,
                text=step.metadata["text"],
                interval=step.metadata.get("interval", 0.0),
            )
            return {"message": result.get("message", result.get("error", "Keyboard typing failed.")), "result": result}
        if action == "keyboard_press":
            result = await context.tools.execute(
                "system.keyboard_press",
                context,
                confirmed=confirmed,
                keys=step.metadata["keys"],
            )
            return {"message": result.get("message", result.get("error", "Keyboard key press failed.")), "result": result}
        if action == "startup_status":
            result = await context.system_controller.startup_status(mode=step.metadata.get("mode"))
            state = "installed" if result.get("installed") else "not installed"
            return {"message": f"Startup registration is {state}. {result.get('message', '')}".strip(), "result": result}
        if action == "install_startup":
            result = await context.system_controller.install_startup(mode=step.metadata.get("mode"))
            return {"message": result.get("message", "Startup installation attempted."), "result": result}
        if action == "uninstall_startup":
            result = await context.system_controller.uninstall_startup()
            return {"message": result.get("message", "Startup removal attempted."), "result": result}
        if action == "open_path":
            result = await context.system_controller.open_path(step.metadata["path"])
            return {"message": result}
        if action == "launch_application":
            result = await context.system_controller.launch_application(step.metadata["application"])
            return {"message": result}
        usage = await context.system_controller.resource_usage()
        return {"message": f"CPU {usage['cpu_percent']}%, memory {usage['memory_percent']}%.", "usage": usage}
