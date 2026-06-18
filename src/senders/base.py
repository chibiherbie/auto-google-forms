from dataclasses import dataclass
from typing import Protocol

from src.models import FormDefinition
from src.planner import PlannedResponse


@dataclass(frozen=True, slots=True)
class SendReceipt:
    external_id: str | None = None


class SendError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        self.retryable = retryable
        super().__init__(message)


class ResponseSender(Protocol):
    def open(self, form: FormDefinition) -> None: ...

    def send(
        self,
        form: FormDefinition,
        response: PlannedResponse,
    ) -> SendReceipt: ...

    def close(self) -> None: ...
