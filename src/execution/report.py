from dataclasses import dataclass
from typing import Literal

ExecutionStatus = Literal["succeeded", "failed"]


@dataclass(frozen=True, slots=True)
class ExecutionItem:
    response_number: int
    status: ExecutionStatus
    attempts: int
    external_id: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionProgress:
    completed: int
    total: int
    succeeded: int
    failed: int
    current: ExecutionItem


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    form_id: str
    total: int
    succeeded: int
    failed: int
    duration_seconds: float
    items: tuple[ExecutionItem, ...]

    @property
    def is_successful(self) -> bool:
        return self.failed == 0

    @property
    def processed(self) -> int:
        return len(self.items)
