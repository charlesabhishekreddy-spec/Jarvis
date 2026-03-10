from __future__ import annotations

import logging
from abc import ABC

from .models import ServiceState


class Service(ABC):
    """Shared lifecycle contract for runtime services."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.state = ServiceState.STOPPED
        self.logger = logging.getLogger(name)

    async def start(self) -> None:
        self.state = ServiceState.RUNNING

    async def stop(self) -> None:
        self.state = ServiceState.STOPPED

    def status(self) -> dict[str, str]:
        return {"name": self.name, "state": self.state.value}
