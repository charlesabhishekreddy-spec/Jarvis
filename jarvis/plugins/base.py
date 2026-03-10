from __future__ import annotations

from abc import ABC, abstractmethod

from jarvis.core.context import JarvisContext


class JarvisPlugin(ABC):
    name = "plugin"
    version = "0.0.0"
    description = "Generic JARVIS plugin"

    @abstractmethod
    async def register(self, context: JarvisContext) -> None:
        raise NotImplementedError
