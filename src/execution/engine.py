import time
from typing import Callable

from src.models import FormDefinition
from src.planner import PlannedResponse, ResponseBatch
from src.senders.base import ResponseSender, SendError

from src.execution.policy import ExecutionPolicy
from src.execution.report import ExecutionItem, ExecutionProgress, ExecutionReport, ExecutionStatus

ProgressCallback = Callable[[ExecutionProgress], None]
Sleep = Callable[[float], None]
Clock = Callable[[], float]


class ExecutionEngine:
    def __init__(
        self,
        *,
        sleep: Sleep = time.sleep,
        clock: Clock = time.monotonic,
    ) -> None:
        self._sleep = sleep
        self._clock = clock

    def execute(
        self,
        *,
        form: FormDefinition,
        batch: ResponseBatch,
        sender: ResponseSender,
        policy: ExecutionPolicy | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> ExecutionReport:
        if form.id != batch.form_id:
            raise ValueError("Form ID does not match response batch")

        active_policy = policy or ExecutionPolicy()
        started_at = self._clock()
        items: list[ExecutionItem] = []

        sender.open(form)
        try:
            for index, response in enumerate(batch.responses):
                self._sleep_between_responses(index, active_policy)
                item = self._send_one(
                    form=form,
                    response=response,
                    sender=sender,
                    policy=active_policy,
                )
                items.append(item)
                self._notify_progress(on_progress, item, items, batch)

                if item.status == "failed" and not active_policy.continue_on_error:
                    break
        finally:
            sender.close()

        return _build_report(
            form=form,
            batch=batch,
            items=items,
            duration_seconds=max(0.0, self._clock() - started_at),
        )

    def _send_one(
        self,
        *,
        form: FormDefinition,
        response: PlannedResponse,
        sender: ResponseSender,
        policy: ExecutionPolicy,
    ) -> ExecutionItem:
        for attempt in range(1, policy.max_attempts + 1):
            try:
                receipt = sender.send(form, response)
            except SendError as error:
                if self._should_retry(error, attempt, policy):
                    self._sleep_retry_delay(attempt, policy)
                    continue

                return ExecutionItem(
                    response_number=response.number,
                    status="failed",
                    attempts=attempt,
                    error=str(error),
                )

            return ExecutionItem(
                response_number=response.number,
                status="succeeded",
                attempts=attempt,
                external_id=receipt.external_id,
            )

        raise AssertionError("Execution attempt loop finished unexpectedly")

    def _sleep_between_responses(
        self,
        response_index: int,
        policy: ExecutionPolicy,
    ) -> None:
        if response_index > 0 and policy.delay_seconds:
            self._sleep(policy.delay_seconds)

    def _sleep_retry_delay(
        self,
        attempt: int,
        policy: ExecutionPolicy,
    ) -> None:
        retry_delay = (
            policy.retry_delay_seconds
            * policy.backoff_multiplier ** (attempt - 1)
        )
        if retry_delay:
            self._sleep(retry_delay)

    @staticmethod
    def _should_retry(
        error: SendError,
        attempt: int,
        policy: ExecutionPolicy,
    ) -> bool:
        return error.retryable and attempt < policy.max_attempts

    @staticmethod
    def _notify_progress(
        on_progress: ProgressCallback | None,
        current: ExecutionItem,
        items: list[ExecutionItem],
        batch: ResponseBatch,
    ) -> None:
        if on_progress is None:
            return

        on_progress(
            ExecutionProgress(
                completed=len(items),
                total=len(batch.responses),
                succeeded=_count_status(items, "succeeded"),
                failed=_count_status(items, "failed"),
                current=current,
            )
        )


def _build_report(
    *,
    form: FormDefinition,
    batch: ResponseBatch,
    items: list[ExecutionItem],
    duration_seconds: float,
) -> ExecutionReport:
    return ExecutionReport(
        form_id=form.id,
        total=len(batch.responses),
        succeeded=_count_status(items, "succeeded"),
        failed=_count_status(items, "failed"),
        duration_seconds=duration_seconds,
        items=tuple(items),
    )


def _count_status(items: list[ExecutionItem], status: ExecutionStatus) -> int:
    return sum(item.status == status for item in items)
