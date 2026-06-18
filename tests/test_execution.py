import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.config import example_config
from src.execution import (
    ExecutionEngine,
    ExecutionPolicy,
    SendError,
    SendReceipt,
)
from src.models import AnswerTarget, ResponsePlan
from src.planner import ResponsePlanner
from src.senders import JsonlSender


def configured_example(total: int = 3):
    config = example_config()
    return replace(
        config,
        response_plan=ResponsePlan(
            total_responses=total,
            answers={
                "entry.123456": (
                    AnswerTarget(value="A", count=total),
                    AnswerTarget(value="B", count=0),
                )
            },
        ),
    )


class FakeSender:
    def __init__(self, outcomes=None) -> None:
        self.outcomes = list(outcomes or [])
        self.opened = False
        self.closed = False
        self.calls: list[int] = []

    def open(self, form) -> None:
        self.opened = True

    def send(self, form, response):
        self.calls.append(response.number)
        if self.outcomes:
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return SendReceipt(external_id=f"result-{response.number}")

    def close(self) -> None:
        self.closed = True


class ExecutionEngineTest(unittest.TestCase):
    def test_executes_batch_and_reports_progress(self) -> None:
        config = configured_example()
        batch = ResponsePlanner().build(config, seed=0)
        sender = FakeSender()
        progress = []
        clock_values = iter((10.0, 12.5))
        engine = ExecutionEngine(clock=lambda: next(clock_values))

        report = engine.execute(
            form=config.form,
            batch=batch,
            sender=sender,
            on_progress=progress.append,
        )

        self.assertTrue(sender.opened)
        self.assertTrue(sender.closed)
        self.assertEqual(sender.calls, [1, 2, 3])
        self.assertEqual(report.succeeded, 3)
        self.assertEqual(report.failed, 0)
        self.assertEqual(report.duration_seconds, 2.5)
        self.assertEqual(progress[-1].completed, 3)
        self.assertEqual(progress[-1].succeeded, 3)

    def test_retries_only_retryable_send_errors_with_backoff(self) -> None:
        config = configured_example(total=1)
        batch = ResponsePlanner().build(config, seed=0)
        sender = FakeSender(
            outcomes=[
                SendError("temporary", retryable=True),
                SendError("temporary", retryable=True),
                SendReceipt(external_id="ok"),
            ]
        )
        sleeps = []

        report = ExecutionEngine(sleep=sleeps.append).execute(
            form=config.form,
            batch=batch,
            sender=sender,
            policy=ExecutionPolicy(
                max_attempts=3,
                retry_delay_seconds=0.5,
                backoff_multiplier=2,
            ),
        )

        self.assertEqual(sleeps, [0.5, 1.0])
        self.assertEqual(report.items[0].attempts, 3)
        self.assertEqual(report.items[0].external_id, "ok")

    def test_non_retryable_error_is_recorded_once(self) -> None:
        config = configured_example(total=1)
        batch = ResponsePlanner().build(config, seed=0)
        sender = FakeSender(
            outcomes=[SendError("rejected", retryable=False)]
        )

        report = ExecutionEngine().execute(
            form=config.form,
            batch=batch,
            sender=sender,
            policy=ExecutionPolicy(max_attempts=3),
        )

        self.assertEqual(sender.calls, [1])
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.items[0].error, "rejected")

    def test_rate_limit_and_stop_on_error(self) -> None:
        config = configured_example()
        batch = ResponsePlanner().build(config, seed=0)
        sender = FakeSender(
            outcomes=[
                SendReceipt(),
                SendError("stop", retryable=False),
            ]
        )
        sleeps = []

        report = ExecutionEngine(sleep=sleeps.append).execute(
            form=config.form,
            batch=batch,
            sender=sender,
            policy=ExecutionPolicy(
                delay_seconds=0.25,
                continue_on_error=False,
            ),
        )

        self.assertEqual(sender.calls, [1, 2])
        self.assertEqual(sleeps, [0.25])
        self.assertEqual(report.processed, 2)
        self.assertEqual(report.total, 3)

    def test_closes_sender_after_unexpected_exception(self) -> None:
        config = configured_example(total=1)
        batch = ResponsePlanner().build(config, seed=0)
        sender = FakeSender(outcomes=[RuntimeError("bug")])

        with self.assertRaisesRegex(RuntimeError, "bug"):
            ExecutionEngine().execute(
                form=config.form,
                batch=batch,
                sender=sender,
            )

        self.assertTrue(sender.closed)

    def test_jsonl_sender_exports_one_line_per_response(self) -> None:
        config = configured_example(total=2)
        batch = ResponsePlanner().build(config, seed=0)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "responses.jsonl"
            report = ExecutionEngine().execute(
                form=config.form,
                batch=batch,
                sender=JsonlSender(path),
            )

            lines = path.read_text(encoding="utf-8").splitlines()

        self.assertTrue(report.is_successful)
        self.assertEqual(len(lines), 2)
        payload = json.loads(lines[0])
        self.assertEqual(payload["form"]["id"], config.form.id)
        self.assertEqual(payload["answers"]["entry.123456"], ["A"])


if __name__ == "__main__":
    unittest.main()
