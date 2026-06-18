import unittest
from dataclasses import replace

from src.config import example_config
from src.models import (
    AnswerTarget,
    FormDefinition,
    Question,
    ResponsePlan,
)
from src.planner import ResponsePlanner


def mixed_config():
    config = example_config()
    form = FormDefinition(
        id=config.form.id,
        title=config.form.title,
        source_url=config.form.source_url,
        questions=(
            Question(
                id="single",
                title="Choose one",
                type="single_choice",
                required=True,
                options=("A", "B"),
            ),
            Question(
                id="multiple",
                title="Choose several",
                type="checkbox",
                required=True,
                options=("X", "Y", "Z"),
            ),
        ),
    )
    plan = ResponsePlan(
        total_responses=5,
        answers={
            "single": (
                AnswerTarget(value="A", count=3),
                AnswerTarget(value="B", count=2),
            ),
            "multiple": (
                AnswerTarget(value="X", count=5),
                AnswerTarget(value="Y", count=2),
                AnswerTarget(value="Z", count=1),
            ),
        },
    )
    return replace(config, form=form, response_plan=plan)


class ResponsePlannerTest(unittest.TestCase):
    def test_builds_exact_target_counts(self) -> None:
        batch = ResponsePlanner().build(mixed_config(), seed=42)

        self.assertEqual(len(batch.responses), 5)
        actual = {
            statistic.question_id: {
                answer.value: answer.count for answer in statistic.answers
            }
            for statistic in batch.statistics
        }
        self.assertEqual(actual["single"], {"A": 3, "B": 2})
        self.assertEqual(actual["multiple"], {"X": 5, "Y": 2, "Z": 1})
        self.assertTrue(
            all(response.values_for("multiple") for response in batch.responses)
        )

    def test_same_seed_is_reproducible(self) -> None:
        planner = ResponsePlanner()

        first = planner.build(mixed_config(), seed=123)
        second = planner.build(mixed_config(), seed=123)

        self.assertEqual(first, second)

    def test_different_seed_changes_assignments(self) -> None:
        planner = ResponsePlanner()

        first = planner.build(mixed_config(), seed=1)
        second = planner.build(mixed_config(), seed=2)

        self.assertNotEqual(first.responses, second.responses)

    def test_optional_checkbox_can_be_empty(self) -> None:
        config = mixed_config()
        checkbox = replace(config.form.questions[1], required=False)
        form = replace(config.form, questions=(config.form.questions[0], checkbox))
        plan = replace(
            config.response_plan,
            answers={
                **config.response_plan.answers,
                "multiple": (
                    AnswerTarget(value="X", count=1),
                    AnswerTarget(value="Y", count=0),
                    AnswerTarget(value="Z", count=0),
                ),
            },
        )

        batch = ResponsePlanner().build(
            replace(config, form=form, response_plan=plan),
            seed=0,
        )

        empty_count = sum(
            not response.values_for("multiple") for response in batch.responses
        )
        self.assertEqual(empty_count, 4)

    def test_checkbox_is_represented_as_repeated_form_fields(self) -> None:
        batch = ResponsePlanner().build(mixed_config(), seed=42)
        response = next(
            item
            for item in batch.responses
            if len(item.values_for("multiple")) > 1
        )

        repeated_fields = [
            field
            for field in response.answers
            if field[0] == "multiple"
        ]

        self.assertGreater(len(repeated_fields), 1)
        self.assertTrue(all(name == "multiple" for name, _ in repeated_fields))


if __name__ == "__main__":
    unittest.main()
