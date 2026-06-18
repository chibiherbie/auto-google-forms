import json
from pathlib import Path
from typing import Any

from .errors import ConfigDecodeError
from .models import AnswerTarget, FormConfig, FormDefinition, Question, ResponsePlan


def load_config(path: Path) -> FormConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigDecodeError(f"Config file does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ConfigDecodeError(
            f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error

    try:
        return _decode_config(raw)
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigDecodeError(f"Invalid config structure: {error}") from error


def save_config(config: FormConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config_to_dict(config), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def config_to_dict(config: FormConfig) -> dict[str, Any]:
    return {
        "schema_version": config.schema_version,
        "form": {
            "id": config.form.id,
            "title": config.form.title,
            "source_url": config.form.source_url,
            "questions": [
                _question_to_dict(question)
                for question in config.form.questions
            ],
        },
        "response_plan": {
            "total_responses": config.response_plan.total_responses,
            "answers": {
                question_id: [
                    {"value": target.value, "count": target.count}
                    for target in targets
                ]
                for question_id, targets in config.response_plan.answers.items()
            },
        },
    }


def _question_to_dict(question: Question) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": question.id,
        "title": question.title,
        "type": question.type,
        "required": question.required,
        "options": list(question.options),
    }
    if question.group_title is not None:
        result["group_title"] = question.group_title
    return result


def example_config() -> FormConfig:
    return FormConfig(
        schema_version=1,
        form=FormDefinition(
            id="example-form-id",
            title="Example survey",
            source_url="https://docs.google.com/forms/d/e/example",
            questions=(
                Question(
                    id="entry.123456",
                    title="Choose one",
                    type="single_choice",
                    required=True,
                    options=("A", "B"),
                ),
            ),
        ),
        response_plan=ResponsePlan(
            total_responses=10,
            answers={
                "entry.123456": (
                    AnswerTarget(value="A", count=6),
                    AnswerTarget(value="B", count=4),
                )
            },
        ),
    )


def _decode_config(raw: Any) -> FormConfig:
    if not isinstance(raw, dict):
        raise TypeError("root value must be an object")

    form_raw = _object(raw["form"], "form")
    questions_raw = _list(form_raw["questions"], "form.questions")
    plan_raw = _object(raw["response_plan"], "response_plan")
    answers_raw = _object(plan_raw["answers"], "response_plan.answers")

    questions = tuple(
        _decode_question(_object(question, f"form.questions[{index}]"))
        for index, question in enumerate(questions_raw)
    )
    answers = {
        str(question_id): tuple(
            _decode_target(
                _object(target, f"response_plan.answers.{question_id}[{index}]")
            )
            for index, target in enumerate(
                _list(targets, f"response_plan.answers.{question_id}")
            )
        )
        for question_id, targets in answers_raw.items()
    }

    return FormConfig(
        schema_version=_integer(raw["schema_version"], "schema_version"),
        form=FormDefinition(
            id=_string(form_raw["id"], "form.id"),
            title=_string(form_raw["title"], "form.title"),
            source_url=_string(form_raw["source_url"], "form.source_url"),
            questions=questions,
        ),
        response_plan=ResponsePlan(
            total_responses=_integer(
                plan_raw["total_responses"], "response_plan.total_responses"
            ),
            answers=answers,
        ),
    )


def _decode_question(raw: dict[str, Any]) -> Question:
    question_type = _string(raw["type"], "question.type")
    if question_type not in {"single_choice", "checkbox"}:
        raise ValueError(f"unsupported question type: {question_type}")

    required = raw["required"]
    if not isinstance(required, bool):
        raise TypeError("question.required must be a boolean")

    group_title = raw.get("group_title")
    if group_title is not None:
        group_title = _string(group_title, "question.group_title")

    return Question(
        id=_string(raw["id"], "question.id"),
        title=_string(raw["title"], "question.title"),
        type=question_type,
        required=required,
        options=tuple(
            _string(option, "question.options[]")
            for option in _list(raw["options"], "question.options")
        ),
        group_title=group_title,
    )


def _decode_target(raw: dict[str, Any]) -> AnswerTarget:
    return AnswerTarget(
        value=_string(raw["value"], "answer.value"),
        count=_integer(raw["count"], "answer.count"),
    )


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{path} must be an array")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{path} must be a string")
    return value


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{path} must be an integer")
    return value
