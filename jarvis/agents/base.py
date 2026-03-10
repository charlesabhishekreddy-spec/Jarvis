from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.models import CommandRequest, TaskPlan, TaskStep


class BaseAgent(ABC):
    name = "agent"
    description = "Generic JARVIS agent"
    keywords: tuple[str, ...] = ()

    def matches(self, step: TaskStep) -> bool:
        if step.agent_hint == self.name:
            return True
        haystack = f"{step.title} {step.description}".lower()
        return any(keyword in haystack for keyword in self.keywords)

    @abstractmethod
    async def handle(
        self,
        step: TaskStep,
        plan: TaskPlan,
        request: CommandRequest,
        context: JarvisContext,
    ) -> dict[str, Any]:
        raise NotImplementedError
