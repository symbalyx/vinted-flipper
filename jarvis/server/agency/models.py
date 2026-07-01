"""Modèles légers du moteur de missions JARVIS Agency."""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class MissionStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    VERIFYING = "verifying"
    RETRY_WAIT = "retry_wait"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MissionStep:
    id: str
    seq: int
    role: str
    title: str
    instructions: str
    depends_on: list[str] = field(default_factory=list)
    status: str = StepStatus.PENDING.value
    result: str = ""
    error: str = ""
    started_at: float | None = None
    finished_at: float | None = None
    max_attempts: int = 4
    attempt: int = 0
    next_run_at: float = 0
    checkpoint: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MissionPlan:
    summary: str
    steps: list[MissionStep]

    def to_dict(self) -> dict[str, Any]:
        return {"summary": self.summary, "steps": [s.to_dict() for s in self.steps]}
