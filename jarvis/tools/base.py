from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from jarvis.core.context import JarvisContext


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    requires_confirmation: bool = False


class Tool(ABC):
    spec: ToolSpec

    @abstractmethod
    async def execute(self, context: JarvisContext, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError
