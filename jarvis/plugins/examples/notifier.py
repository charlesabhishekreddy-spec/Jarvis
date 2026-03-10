from __future__ import annotations

from jarvis.core.events import Event
from jarvis.core.context import JarvisContext
from jarvis.plugins.base import JarvisPlugin


class NotifierPlugin(JarvisPlugin):
    name = "notifier"
    version = "1.0.0"
    description = "Example plugin that records automation events into memory."

    async def register(self, context: JarvisContext) -> None:
        async def on_event(event: Event) -> None:
            await context.memory.log_activity(
                category="plugin.notifier",
                message=f"Automation event: {event.topic}",
                details=event.payload,
            )

        await context.bus.subscribe("automation.*", on_event)


PLUGIN_CLASS = NotifierPlugin
