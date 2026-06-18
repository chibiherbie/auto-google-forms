import unittest
from dataclasses import replace

from src.config import example_config
from src.errors import ConfigValidationError
from src.models import (
    AnswerTarget,
    FormDefinition,
    Question,
    ResponsePlan,
)
from src.validation import validate_config


class ValidationTest(unittest.TestCase):
    def test_example_is_valid(self) -> None:
        validate_config(example_config())

    def test_rejects_wrong_target_total(self) -> None:
        config = example_config()
        invalid_plan = ResponsePlan(
            total_responses=10,
            answers={
                "entry.123456": (
                    AnswerTarget(value="A", count=3),
                    AnswerTarget(value="B", count=4),
                )
            },
        )

        with self.assertRaisesRegex(
            ConfigValidationError, "counts sum to 7, expected 10"
        ):
            validate_config(replace(config, response_plan=invalid_plan))

    def test_reports_missing_and_unknown_questions(self) -> None:
        config = example_config()
        invalid_plan = ResponsePlan(
            total_responses=10,
            answers={"unknown": (AnswerTarget(value="A", count=10),)},
        )

        with self.assertRaises(ConfigValidationError) as raised:
            validate_config(replace(config, response_plan=invalid_plan))

        self.assertIn(
            "response_plan.answers: missing question entry.123456",
            raised.exception.errors,
        )
        self.assertIn(
            "response_plan.answers: unknown question unknown",
            raised.exception.errors,
        )

    def test_allows_checkbox_counts_above_single_choice_total_sum(self) -> None:
        config = example_config()
        checkbox = Question(
            id="123456",
            title="Select all",
            type="checkbox",
            required=True,
            options=("A", "B"),
        )
        form = FormDefinition(
            id=config.form.id,
            title=config.form.title,
            source_url=config.form.source_url,
            questions=(checkbox,),
        )
        plan = ResponsePlan(
            total_responses=10,
            answers={
                "123456": (
                    AnswerTarget(value="A", count=8),
                    AnswerTarget(value="B", count=7),
                )
            },
        )

        validate_config(replace(config, form=form, response_plan=plan))

    def test_rejects_checkbox_count_above_total_responses(self) -> None:
        config = example_config()
        checkbox = Question(
            id="123456",
            title="Select all",
            type="checkbox",
            required=False,
            options=("A", "B"),
        )
        form = replace(config.form, questions=(checkbox,))
        plan = ResponsePlan(
            total_responses=10,
            answers={
                "123456": (
                    AnswerTarget(value="A", count=11),
                    AnswerTarget(value="B", count=0),
                )
            },
        )

        with self.assertRaisesRegex(
            ConfigValidationError, "count must not exceed 10"
        ):
            validate_config(replace(config, form=form, response_plan=plan))

    def test_required_checkbox_needs_at_least_one_mark_per_response(self) -> None:
        config = example_config()
        checkbox = Question(
            id="123456",
            title="Select all",
            type="checkbox",
            required=True,
            options=("A", "B"),
        )
        form = replace(config.form, questions=(checkbox,))
        plan = ResponsePlan(
            total_responses=10,
            answers={
                "123456": (
                    AnswerTarget(value="A", count=3),
                    AnswerTarget(value="B", count=4),
                )
            },
        )

        with self.assertRaisesRegex(
            ConfigValidationError, "expected at least 10"
        ):
            validate_config(replace(config, form=form, response_plan=plan))

    def test_rejects_excessive_batch_size(self) -> None:
        config = example_config()
        plan = ResponsePlan(
            total_responses=10_001,
            answers={
                "entry.123456": (
                    AnswerTarget(value="A", count=10_001),
                    AnswerTarget(value="B", count=0),
                )
            },
        )

        with self.assertRaisesRegex(
            ConfigValidationError, "must not exceed 10000"
        ):
            validate_config(replace(config, response_plan=plan))


if __name__ == "__main__":
    unittest.main()
