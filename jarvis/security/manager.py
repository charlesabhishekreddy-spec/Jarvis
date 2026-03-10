from __future__ import annotations

from jarvis.core.config import SecuritySettings
from jarvis.core.models import RiskAssessment
from jarvis.core.service import Service

from .identity import VoiceIdentityVerifier
from .permissions import PermissionDecision, PermissionManager
from .policy import CommandSafetyPolicy
from .sandbox import SandboxPolicy


class SecurityManager(Service):
    def __init__(self, settings: SecuritySettings) -> None:
        super().__init__("jarvis.security")
        self.settings = settings
        self.policy = CommandSafetyPolicy()
        self.permissions = PermissionManager()
        self.identity = VoiceIdentityVerifier()
        self.sandbox = SandboxPolicy(settings.allowed_workdirs)

    def assess_command(self, text: str) -> RiskAssessment:
        return self.policy.assess(text, confirm_dangerous=self.settings.confirm_dangerous_commands)

    def authorize_tool(self, tool_name: str) -> PermissionDecision:
        return self.permissions.can_use_tool(tool_name)

    def is_path_allowed(self, path: str) -> bool:
        return self.sandbox.is_path_allowed(path)
