from __future__ import annotations

from typing import Any

from jarvis.core.context import JarvisContext

from .base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.spec.name,
                "description": tool.spec.description,
                "requires_confirmation": tool.spec.requires_confirmation,
            }
            for tool in self._tools.values()
        ]

    async def execute(self, name: str, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        tool = self._tools[name]
        decision = context.security.authorize_tool(name)
        if not decision.allowed:
            return {"ok": False, "error": decision.reason}
        return await tool.execute(context, **kwargs)
