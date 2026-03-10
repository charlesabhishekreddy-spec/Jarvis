from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from jarvis.core.context import JarvisContext
from jarvis.core.service import Service

from .base import JarvisPlugin


class PluginLoader(Service):
    def __init__(self, plugin_dir: str) -> None:
        super().__init__("jarvis.plugins")
        self.plugin_dir = Path(plugin_dir)
        self.loaded_plugins: list[JarvisPlugin] = []

    async def start(self) -> None:
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        await super().start()

    async def load_all(self, context: JarvisContext) -> None:
        for path in sorted(self.plugin_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            plugin = self._load_from_path(path)
            if plugin is None:
                continue
            await plugin.register(context)
            self.loaded_plugins.append(plugin)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {"name": plugin.name, "version": plugin.version, "description": plugin.description}
            for plugin in self.loaded_plugins
        ]

    def _load_from_path(self, path: Path) -> JarvisPlugin | None:
        spec = importlib.util.spec_from_file_location(f"jarvis_plugin_{path.stem}", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugin_class = getattr(module, "PLUGIN_CLASS", None)
        if plugin_class is None:
            return None
        plugin = plugin_class()
        if not isinstance(plugin, JarvisPlugin):
            return None
        return plugin
