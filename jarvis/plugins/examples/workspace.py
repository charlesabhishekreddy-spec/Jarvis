from __future__ import annotations

from pathlib import Path
from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.plugins.base import JarvisPlugin
from jarvis.tools.base import Tool, ToolSpec


class WorkspaceInventoryTool(Tool):
    spec = ToolSpec(name="plugin.workspace_inventory", description="List files from the current JARVIS workspace.")

    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        limit = int(kwargs.get("limit", 25))
        root = Path.cwd()
        files = [str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()][:limit]
        return {"ok": True, "files": files, "root": str(root)}


class WorkspacePlugin(JarvisPlugin):
    name = "workspace"
    version = "1.0.0"
    description = "Example plugin that exposes workspace inventory as a tool."

    async def register(self, context: JarvisContext) -> None:
        api = self.api(context)
        api.register_tool(WorkspaceInventoryTool())
        await api.log("plugin.workspace", "Workspace inventory tool registered.")


PLUGIN_CLASS = WorkspacePlugin
