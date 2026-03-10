from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ServiceState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(slots=True)
class Event:
    topic: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=utc_now)
    event_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class CommandRequest:
    text: str
    source: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class CommandResponse:
    status: TaskStatus
    message: str
    task_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class RiskAssessment:
    level: RiskLevel
    reason: str
    requires_confirmation: bool
    recommended_action: str


@dataclass(slots=True)
class TaskStep:
    title: str
    description: str
    agent_hint: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    step_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class TaskPlan:
    goal: str
    steps: list[TaskStep]
    status: TaskStatus = TaskStatus.PENDING
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "steps": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "description": step.description,
                    "agent_hint": step.agent_hint,
                    "metadata": step.metadata,
                    "status": step.status.value,
                    "result": step.result,
                }
                for step in self.steps
            ],
        }


@dataclass(slots=True)
class ActivityRecord:
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utc_now)
