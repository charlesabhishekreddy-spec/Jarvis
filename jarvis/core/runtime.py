from __future__ import annotations

from pathlib import Path

from jarvis.brain.intelligence import IntelligenceService
from jarvis.brain.learning import AdaptiveLearningService
from jarvis.brain.proactive import ProactiveReviewService
from jarvis.automation.orchestration import OrchestrationService
from jarvis.automation.scheduler import AutomationService
from jarvis.brain.reasoning import ReasoningEngine
from jarvis.memory.service import MemoryService
from jarvis.plugins.loader import PluginLoader
from jarvis.security.confirmations import ConfirmationService
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
from .models import CommandRequest, CommandResponse, TaskStatus
from .service import Service
from .task_queue import BackgroundCommandService


class JarvisRuntime(Service):
    def __init__(self, settings: Settings) -> None:
        super().__init__("jarvis.runtime")
        self.settings = settings
        self.bus = AsyncEventBus()
        self.memory = MemoryService(settings.memory.sqlite_path, settings.memory.semantic_index_path)
        self.security = SecurityManager(settings.security)
        self.system_controller = SystemController(self.security, settings)
        self.automation = AutomationService(self.bus, self.memory)
        self.command_queue = BackgroundCommandService(self.bus, self._execute_request_now)
        self.orchestration = OrchestrationService(
            bus=self.bus,
            memory=self.memory,
            submit_request=self.command_queue.submit,
            lookup_execution=self.command_queue.get,
            cancel_execution=self.command_queue.cancel,
        )
        self.confirmations = ConfirmationService(self.memory, self.bus, self.command_queue.submit)
        self.intelligence = IntelligenceService(
            settings.intelligence,
            gemini_api_key=settings.api_keys.gemini_api_key,
        )
        self.learning = AdaptiveLearningService(
            memory=self.memory,
            intelligence=self.intelligence,
            enabled=settings.learning.enabled,
            workspace_root=settings.security.allowed_workdirs[0] if settings.security.allowed_workdirs else None,
        )
        self.proactive = ProactiveReviewService(
            memory=self.memory,
            intelligence=self.intelligence,
            bus=self.bus,
            enabled=settings.learning.proactive_review_enabled,
            interval_seconds=settings.learning.proactive_review_interval_seconds,
        )
        self.web = WebIntelligenceService(
            news_api_key=settings.api_keys.news_api_key,
            weather_api_key=settings.api_keys.weather_api_key,
        )
        self.vision = VisionService(
            data_dir=settings.runtime.data_dir,
            bus=self.bus,
            memory=self.memory,
        )
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
            orchestration=self.orchestration,
            web=self.web,
            vision=self.vision,
            tools=self.tools,
            plugins=self.plugins,
            intelligence=self.intelligence,
            learning=self.learning,
            proactive=self.proactive,
            confirmations=self.confirmations,
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
            self.command_queue,
            self.orchestration,
            self.confirmations,
            self.intelligence,
            self.learning,
            self.proactive,
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
        return await self._execute_request_now(request)

    async def _execute_request_now(self, request: CommandRequest) -> CommandResponse:
        await self.bus.publish("command.received", {"request_id": request.request_id, "text": request.text, "source": request.source})
        response = await self.reasoning.execute(request)
        if response.status == TaskStatus.REQUIRES_CONFIRMATION:
            confirmation = await self.confirmations.create(
                request=request,
                risk_level=str(response.data.get("risk_level", "unknown")),
                reason=response.message,
                recommended_action=str(response.data.get("recommended_action", "")),
            )
            response.data["confirmation_id"] = confirmation.confirmation_id
            response.data["confirmation"] = confirmation.to_dict()
        await self.memory.save_exchange(request, response)
        await self.learning.capture_interaction(request, response)
        await self.memory.log_activity(
            category="command",
            message=response.message,
            details={"request_id": request.request_id, "status": response.status.value},
        )
        return response

    async def execute_text(self, text: str, source: str = "text", confirmed: bool = False) -> CommandResponse:
        request = CommandRequest(text=text, source=source, metadata={"confirmed": confirmed})
        return await self.execute_request(request)

    async def submit_text(self, text: str, source: str = "text", confirmed: bool = False) -> dict:
        request = CommandRequest(text=text, source=source, metadata={"confirmed": confirmed})
        record = await self.command_queue.submit(request)
        return record.to_dict()

    async def status_snapshot(self) -> dict:
        resources = await self.system_controller.resource_usage()
        processes = await self.system_controller.list_processes(limit=15)
        windows = await self.system_controller.list_windows(limit=12)
        startup = await self.system_controller.startup_status()
        return {
            "runtime": {"state": self.state.value, "env": self.settings.runtime.env},
            "services": [service.status() for service in self.services],
            "intelligence": self.intelligence.snapshot(),
            "plugins": self.plugins.list_plugins(),
            "tools": self.tools.list_tools(),
            "startup": startup,
            "voice": self.voice.status_snapshot(),
            "vision": self.vision.status_snapshot(),
            "jobs": await self.automation.snapshot_jobs(),
            "workflows": await self.orchestration.workflows(limit=10),
            "orchestration": self.orchestration.snapshot(),
            "command_queue": self.command_queue.snapshot(),
            "confirmations": {"pending": await self.confirmations.list(status="pending", limit=20)},
            "insights": await self.learning.insights(),
            "goals": await self.memory.goals(limit=10),
            "proactive_review": self.proactive.snapshot(),
            "processes": processes,
            "windows": windows,
            "resources": resources,
        }

    async def dashboard_snapshot(self) -> dict:
        return {
            "status": await self.status_snapshot(),
            "activities": await self.memory.recent_activities(25),
            "tasks": await self.memory.recent_tasks(10),
            "conversations": await self.memory.recent_conversations(10),
            "events": self.bus.recent_events(25),
            "executions": self.command_queue.list(20),
            "confirmations": await self.confirmations.list(limit=20),
        }
