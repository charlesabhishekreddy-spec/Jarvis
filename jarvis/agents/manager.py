from __future__ import annotations

from .autonomous import AutonomousAgent
from .automation import AutomationAgent
from .base import BaseAgent
from .coder import CoderAgent
from .commander import CommanderAgent
from .memory import MemoryAgent
from .research import ResearchAgent
from .security import SecurityAgent
from .system import SystemAgent
from .vision import VisionAgent


class AgentManager:
    def __init__(self) -> None:
        self.agents: list[BaseAgent] = [
            ResearchAgent(),
            CoderAgent(),
            AutomationAgent(),
            MemoryAgent(),
            SecurityAgent(),
            SystemAgent(),
            VisionAgent(),
            AutonomousAgent(),
            CommanderAgent(),
        ]

    def select(self, agent_hint: str, step) -> BaseAgent:
        for agent in self.agents:
            if agent.name == agent_hint:
                return agent
        for agent in self.agents:
            if agent.matches(step):
                return agent
        return CommanderAgent()
