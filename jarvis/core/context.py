from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .config import Settings
from .events import AsyncEventBus

if TYPE_CHECKING:
    from jarvis.brain.intelligence import IntelligenceService
    from jarvis.brain.learning import AdaptiveLearningService
    from jarvis.automation.scheduler import AutomationService
    from jarvis.memory.service import MemoryService
    from jarvis.plugins.loader import PluginLoader
    from jarvis.security.confirmations import ConfirmationService
    from jarvis.security.manager import SecurityManager
    from jarvis.system_control.os_controller import SystemController
    from jarvis.tools.registry import ToolRegistry
    from jarvis.vision.perception import VisionService
    from jarvis.voice.pipeline import VoicePipeline
    from jarvis.web_intelligence.search import WebIntelligenceService
    from .runtime import JarvisRuntime


@dataclass(slots=True)
class JarvisContext:
    settings: Settings
    bus: AsyncEventBus
    memory: "MemoryService"
    security: "SecurityManager"
    system_controller: "SystemController"
    automation: "AutomationService"
    web: "WebIntelligenceService"
    vision: "VisionService"
    tools: "ToolRegistry"
    plugins: "PluginLoader"
    intelligence: "IntelligenceService | None" = None
    learning: "AdaptiveLearningService | None" = None
    confirmations: "ConfirmationService | None" = None
    runtime: "JarvisRuntime | None" = None
    voice: "VoicePipeline | None" = None
