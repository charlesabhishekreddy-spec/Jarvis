from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PermissionDecision:
    allowed: bool
    reason: str


class PermissionManager:
    def can_use_tool(self, tool_name: str) -> PermissionDecision:
        return PermissionDecision(allowed=True, reason=f"Tool {tool_name} is permitted.")
