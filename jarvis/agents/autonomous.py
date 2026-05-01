from __future__ import annotations

import json
from typing import Any

from jarvis.brain.intelligence import ToolCall
from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep

from .base import BaseAgent


class AutonomousAgent(BaseAgent):
    name = "autonomous"
    description = "Uses tool planning to fulfill generic workspace and system requests."
    keywords = ("file", "folder", "workspace", "process", "read", "open", "lookup")

    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        memories = await context.memory.recall(request.text, limit=3)
        projects = await context.memory.project_contexts(limit=3)
        goals = await context.memory.goals(status="active", limit=3)
        tool_calls = await context.intelligence.plan_tool_usage(
            request.text,
            context.tools.list_tools(),
            context={"memories": memories, "projects": projects, "goals": goals, "plan": plan.to_dict()},
            max_calls=step.metadata.get("max_calls", 3),
        )
        if not tool_calls:
            response = await context.intelligence.respond(
                prompt=request.text,
                context={"memories": memories, "projects": projects, "goals": goals, "plan": plan.to_dict()},
            )
            return {"message": response.text, "provider": response.provider, "tool_calls": []}

        outputs: list[dict[str, Any]] = []
        fragments: list[str] = []
        for call in tool_calls:
            result = await context.tools.execute(
                call.name,
                context,
                confirmed=bool(request.metadata.get("confirmed", False)),
                **call.arguments,
            )
            outputs.append({"tool": call.name, "arguments": call.arguments, "reason": call.reason, "result": result})
            fragments.append(self._result_fragment(call, result))
            if not result.get("ok", False):
                break

        summary = await context.intelligence.respond(
            prompt=f"Summarize the tool-assisted result for: {request.text}",
            context={"memories": memories, "projects": projects, "goals": goals, "results": fragments, "plan": plan.to_dict()},
        )
        return {
            "message": summary.text if summary.text.strip() else "\n".join(fragments),
            "provider": summary.provider,
            "tool_calls": outputs,
        }

    def _result_fragment(self, call: ToolCall, result: dict[str, Any]) -> str:
        if not result.get("ok", False):
            return f"{call.name} failed: {result.get('error', result)}"
        if call.name == "system.list_files":
            files = result.get("files", [])[:10]
            directories = result.get("directories", [])[:10]
            return f"Listed path {result.get('path')}. Files: {files}. Directories: {directories}."
        if call.name == "system.read_file":
            return f"Read file {result.get('path')}: {result.get('content', '')[:500]}"
        if call.name == "system.processes":
            return f"Running processes: {json.dumps(result.get('processes', [])[:10])}"
        if call.name == "system.terminate_process":
            return result.get("message", json.dumps(result))
        if call.name == "system.windows":
            return f"Windows: {json.dumps(result.get('windows', [])[:10])}"
        if call.name in {"system.window_focus", "system.window_minimize", "system.window_maximize"}:
            return result.get("message", json.dumps(result))
        if call.name == "web.search":
            return f"Web search results: {json.dumps(result.get('results', [])[:5])}"
        if call.name == "memory.recall":
            return f"Memory recall results: {json.dumps(result.get('results', [])[:5])}"
        if call.name == "memory.remember":
            return f"Stored memory: {result.get('content')}"
        if call.name == "system.open_path":
            return result.get("message", "Opened path.")
        return json.dumps(result)
