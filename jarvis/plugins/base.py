from __future__ import annotations

from abc import ABC, abstractmethod

from jarvis.core.context import JarvisContext
from jarvis.plugins.sdk import PluginAPI


class JarvisPlugin(ABC):
    name = "plugin"
    version = "0.0.0"
    description = "Generic JARVIS plugin"

    def api(self, context: JarvisContext) -> PluginAPI:
        return PluginAPI(context)

    @abstractmethod
    async def register(self, context: JarvisContext) -> None:
        raise NotImplementedError
