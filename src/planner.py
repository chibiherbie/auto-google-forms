import random
from dataclasses import dataclass
from typing import Iterable

from .errors import PlanBuildError
from .models import FormConfig, Question
from .validation import validate_config


@dataclass(frozen=True, slots=True)
class PlannedResponse:
    number: int
    answers: tuple[tuple[str, str], ...]

    def values_for(self, question_id: str) -> tuple[str, ...]:
        return tuple(
            value
            for field_name, value in self.answers
            if field_name == question_id
        )

    def grouped_answers(self) -> dict[str, tuple[str, ...]]:
        grouped: dict[str, list[str]] = {}
        for field_name, value in self.answers:
            grouped.setdefault(field_name, []).append(value)
        return {
            field_name: tuple(values)
            for field_name, values in grouped.items()
        }


@dataclass(frozen=True, slots=True)
class AnswerStatistic:
    value: str
    count: int


@dataclass(frozen=True, slots=True)
class QuestionStatistic:
    question_id: str
    title: str
    answers: tuple[AnswerStatistic, ...]


@dataclass(frozen=True, slots=True)
class ResponseBatch:
    form_id: str
    seed: int | None
    responses: tuple[PlannedResponse, ...]
    statistics: tuple[QuestionStatistic, ...]


class ResponsePlanner:
    def build(self, config: FormConfig, seed: int | None = None) -> ResponseBatch:
        validate_config(config)

        randomizer = random.Random(seed)
        total = config.response_plan.total_responses
        response_answers: list[dict[str, tuple[str, ...]]] = [
            {} for _ in range(total)
        ]

        for question in config.form.questions:
            targets = config.response_plan.answers[question.id]
            if question.type == "single_choice":
                assignments = self._single_choice_assignments(
                    targets=((target.value, target.count) for target in targets),
                    total=total,
                    randomizer=randomizer,
                )
            elif question.type == "checkbox":
                assignments = self._checkbox_assignments(
                    question=question,
                    targets=((target.value, target.count) for target in targets),
                    total=total,
                    randomizer=randomizer,
                )
            else:
                raise PlanBuildError(
                    f"Unsupported question type: {question.type}"
                )

            for index, values in enumerate(assignments):
                if values or question.required:
                    response_answers[index][question.id] = values

        responses = tuple(
            PlannedResponse(
                number=index + 1,
                answers=tuple(
                    (question_id, value)
                    for question_id, values in answers.items()
                    for value in values
                ),
            )
            for index, answers in enumerate(response_answers)
        )
        statistics = calculate_statistics(config, responses)
        _assert_targets(config, statistics)

        return ResponseBatch(
            form_id=config.form.id,
            seed=seed,
            responses=responses,
            statistics=statistics,
        )

    @staticmethod
    def _single_choice_assignments(
        targets: Iterable[tuple[str, int]],
        total: int,
        randomizer: random.Random,
    ) -> list[tuple[str, ...]]:
        pool = [
            value
            for value, count in targets
            for _ in range(count)
        ]
        if len(pool) != total:
            raise PlanBuildError(
                f"Single-choice pool contains {len(pool)} answers, expected {total}"
            )

        randomizer.shuffle(pool)
        return [(value,) for value in pool]

    @staticmethod
    def _checkbox_assignments(
        question: Question,
        targets: Iterable[tuple[str, int]],
        total: int,
        randomizer: random.Random,
    ) -> list[tuple[str, ...]]:
        selections: list[list[str]] = [[] for _ in range(total)]

        for value, count in targets:
            indexes = list(range(total))
            randomizer.shuffle(indexes)
            indexes.sort(key=lambda index: len(selections[index]))
            for index in indexes[:count]:
                selections[index].append(value)

        if question.required and any(not values for values in selections):
            raise PlanBuildError(
                f"Could not fill required checkbox {question.id}"
            )

        return [tuple(values) for values in selections]


def calculate_statistics(
    config: FormConfig,
    responses: tuple[PlannedResponse, ...],
) -> tuple[QuestionStatistic, ...]:
    result: list[QuestionStatistic] = []

    for question in config.form.questions:
        counts = {option: 0 for option in question.options}
        for response in responses:
            for value in response.values_for(question.id):
                if value not in counts:
                    raise PlanBuildError(
                        f"Answer {value!r} is not present in question {question.id}"
                    )
                counts[value] += 1

        result.append(
            QuestionStatistic(
                question_id=question.id,
                title=question.title,
                answers=tuple(
                    AnswerStatistic(value=option, count=counts[option])
                    for option in question.options
                ),
            )
        )

    return tuple(result)


def _assert_targets(
    config: FormConfig,
    statistics: tuple[QuestionStatistic, ...],
) -> None:
    actual = {
        statistic.question_id: {
            answer.value: answer.count for answer in statistic.answers
        }
        for statistic in statistics
    }

    for question_id, targets in config.response_plan.answers.items():
        for target in targets:
            actual_count = actual[question_id][target.value]
            if actual_count != target.count:
                raise PlanBuildError(
                    f"Planner produced {actual_count} for "
                    f"{question_id}/{target.value!r}, expected {target.count}"
                )
