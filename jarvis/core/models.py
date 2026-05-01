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
    QUEUED = "queued"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REQUIRES_CONFIRMATION = "requires_confirmation"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfirmationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"


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
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    step_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass(slots=True)
class TaskPlan:
    goal: str
    steps: list[TaskStep]
    metadata: dict[str, Any] = field(default_factory=dict)
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
            "metadata": self.metadata,
            "steps": [
                {
                    "step_id": step.step_id,
                    "title": step.title,
                    "description": step.description,
                    "agent_hint": step.agent_hint,
                    "metadata": step.metadata,
                    "depends_on": step.depends_on,
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


@dataclass(slots=True)
class ExecutionRecord:
    request_id: str
    text: str
    source: str
    status: TaskStatus = TaskStatus.QUEUED
    queued_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    task_id: str | None = None
    message: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    response_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "text": self.text,
            "source": self.source,
            "status": self.status.value,
            "queued_at": self.queued_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "task_id": self.task_id,
            "message": self.message,
            "error": self.error,
            "metadata": self.metadata,
            "response_data": self.response_data,
        }


@dataclass(slots=True)
class ConfirmationRecord:
    request_id: str
    text: str
    source: str
    risk_level: str
    reason: str
    recommended_action: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    confirmation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None
    decision_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "confirmation_id": self.confirmation_id,
            "request_id": self.request_id,
            "text": self.text,
            "source": self.source,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "recommended_action": self.recommended_action,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "decision_note": self.decision_note,
        }


@dataclass(slots=True)
class GoalRecord:
    title: str
    detail: str
    priority: int = 50
    status: GoalStatus = GoalStatus.ACTIVE
    project_id: str | None = None
    next_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    goal_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "detail": self.detail,
            "priority": self.priority,
            "status": self.status.value,
            "project_id": self.project_id,
            "next_action": self.next_action,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass(slots=True)
class WorkflowStepRecord:
    title: str
    command_text: str
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    request_id: str | None = None
    step_id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "command_text": self.command_text,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": self.result,
            "request_id": self.request_id,
        }


@dataclass(slots=True)
class WorkflowRecord:
    title: str
    steps: list[WorkflowStepRecord]
    goal_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "title": self.title,
            "goal_id": self.goal_id,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "steps": [step.to_dict() for step in self.steps],
        }
