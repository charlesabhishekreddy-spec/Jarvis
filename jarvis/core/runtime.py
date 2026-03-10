from __future__ import annotations

from pathlib import Path

from jarvis.automation.scheduler import AutomationService
from jarvis.brain.reasoning import ReasoningEngine
from jarvis.memory.service import MemoryService
from jarvis.plugins.loader import PluginLoader
from jarvis.security.manager import SecurityManager
from jarvis.system_control.os_controller import SystemController
from jarvis.tools.builtin import register_builtin_tools
from jarvis.tools.registry import ToolRegistry
from jarvis.vision.perception import VisionService
from jarvis.voice.pipeline import VoicePipeline
from jarvis.web_intelligence.search import WebIntelligenceService

from .config import Settings
from .context import JarvisContext
from .events import AsyncEventBus
from .models import CommandRequest, CommandResponse
from .service import Service


class JarvisRuntime(Service):
    def __init__(self, settings: Settings) -> None:
        super().__init__("jarvis.runtime")
        self.settings = settings
        self.bus = AsyncEventBus()
        self.memory = MemoryService(settings.memory.sqlite_path, settings.memory.semantic_index_path)
        self.security = SecurityManager(settings.security)
        self.system_controller = SystemController(self.security)
        self.automation = AutomationService(self.bus)
        self.web = WebIntelligenceService(
            news_api_key=settings.api_keys.news_api_key,
            weather_api_key=settings.api_keys.weather_api_key,
        )
        self.vision = VisionService()
        self.tools = ToolRegistry()
        register_builtin_tools(self.tools)
        plugin_dir = Path(__file__).resolve().parents[1] / "plugins" / "examples"
        self.plugins = PluginLoader(str(plugin_dir))
        self.context = JarvisContext(
            settings=settings,
            bus=self.bus,
            memory=self.memory,
            security=self.security,
            system_controller=self.system_controller,
            automation=self.automation,
            web=self.web,
            vision=self.vision,
            tools=self.tools,
            plugins=self.plugins,
            runtime=self,
        )
        self.voice = VoicePipeline(self.context)
        self.context.voice = self.voice
        self.reasoning = ReasoningEngine(self.context)
        self.services: list[Service] = [
            self.memory,
            self.security,
            self.system_controller,
            self.automation,
            self.web,
            self.vision,
            self.plugins,
            self.voice,
        ]

    async def start(self) -> None:
        for service in self.services:
            await service.start()
        await self.plugins.load_all(self.context)
        await self.memory.log_activity(category="system", message="JARVIS runtime started.")
        await self.bus.publish("system.started", {"status": "running"})
        await super().start()

    async def stop(self) -> None:
        await self.bus.publish("system.stopping", {"status": "stopping"})
        for service in reversed(self.services):
            await service.stop()
        await super().stop()

    async def execute_request(self, request: CommandRequest) -> CommandResponse:
        await self.bus.publish("command.received", {"request_id": request.request_id, "text": request.text, "source": request.source})
        response = await self.reasoning.execute(request)
        await self.memory.save_exchange(request, response)
        await self.memory.log_activity(
            category="command",
            message=response.message,
            details={"request_id": request.request_id, "status": response.status.value},
        )
        return response

    async def execute_text(self, text: str, source: str = "text", confirmed: bool = False) -> CommandResponse:
        request = CommandRequest(text=text, source=source, metadata={"confirmed": confirmed})
        return await self.execute_request(request)

    async def status_snapshot(self) -> dict:
        resources = await self.system_controller.resource_usage()
        return {
            "runtime": {"state": self.state.value, "env": self.settings.runtime.env},
            "services": [service.status() for service in self.services],
            "plugins": self.plugins.list_plugins(),
            "tools": self.tools.list_tools(),
            "jobs": self.automation.list_jobs(),
            "resources": resources,
        }

    async def dashboard_snapshot(self) -> dict:
        return {
            "status": await self.status_snapshot(),
            "activities": await self.memory.recent_activities(25),
            "tasks": await self.memory.recent_tasks(10),
            "conversations": await self.memory.recent_conversations(10),
            "events": self.bus.recent_events(25),
        }
