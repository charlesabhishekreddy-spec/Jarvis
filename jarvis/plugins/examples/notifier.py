from __future__ import annotations

from jarvis.core.events import Event
from jarvis.core.context import JarvisContext
from jarvis.plugins.base import JarvisPlugin


class NotifierPlugin(JarvisPlugin):
    name = "notifier"
    version = "1.0.0"
    description = "Example plugin that records automation events into memory."

    async def register(self, context: JarvisContext) -> None:
        api = self.api(context)

        async def on_event(event: Event) -> None:
            await api.log(
                category="plugin.notifier",
                message=f"Automation event: {event.topic}",
                details=event.payload,
            )

        await api.subscribe("automation.*", on_event)


PLUGIN_CLASS = NotifierPlugin
