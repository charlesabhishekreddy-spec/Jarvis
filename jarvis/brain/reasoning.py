from __future__ import annotations

from jarvis.agents.manager import AgentManager
from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, CommandResponse, TaskPlan, TaskStatus, utc_now

from .planning import TaskPlanner


class ReasoningEngine:
    def __init__(self, context: JarvisContext) -> None:
        self.context = context
        self.planner = TaskPlanner()
        self.agents = AgentManager()

    async def execute(self, request: CommandRequest) -> CommandResponse:
        assessment = self.context.security.assess_command(request.text)
        if assessment.requires_confirmation and not request.metadata.get("confirmed"):
            return CommandResponse(
                status=TaskStatus.REQUIRES_CONFIRMATION,
                message=assessment.reason,
                data={
                    "risk_level": assessment.level.value,
                    "recommended_action": assessment.recommended_action,
                },
            )

        plan = self.planner.create_plan(request)
        plan.status = TaskStatus.IN_PROGRESS
        await self.context.memory.save_task(plan)
        await self.context.bus.publish("task.created", plan.to_dict())

        for index, step in enumerate(plan.steps):
            step.status = TaskStatus.IN_PROGRESS
            if step.metadata.get("content_from_previous") and index > 0:
                step.metadata["content"] = plan.steps[index - 1].result or ""
            await self.context.bus.publish(
                "task.step.started",
                {"plan_id": plan.plan_id, "step_id": step.step_id, "title": step.title, "agent_hint": step.agent_hint},
            )
            agent = self.agents.select(step.agent_hint, step)
            result = await agent.handle(step, plan, request, self.context)
            step.result = result.get("message", "")
            step.status = TaskStatus.COMPLETED
            plan.updated_at = utc_now()
            await self.context.memory.log_activity(
                category="task.step",
                message=f"{agent.name} completed {step.title}",
                details={"plan_id": plan.plan_id, "step_id": step.step_id},
            )
            await self.context.bus.publish(
                "task.step.completed",
                {"plan_id": plan.plan_id, "step_id": step.step_id, "agent": agent.name, "result": step.result},
            )

        plan.status = TaskStatus.COMPLETED
        await self.context.memory.save_task(plan)
        await self.context.bus.publish("task.completed", plan.to_dict())

        final_message = plan.steps[-1].result or "Task completed."
        response = CommandResponse(
            status=TaskStatus.COMPLETED,
            message=final_message,
            task_id=plan.plan_id,
            data={"plan": plan.to_dict()},
        )
        return response
