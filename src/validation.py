from urllib.parse import urlparse

from .errors import ConfigValidationError
from .models import FormConfig

MAX_TOTAL_RESPONSES = 10_000


def validate_config(config: FormConfig) -> None:
    errors: list[str] = []

    if config.schema_version != 1:
        errors.append(
            f"schema_version: expected 1, got {config.schema_version}"
        )

    if not config.form.id.strip():
        errors.append("form.id: must not be empty")
    if not config.form.title.strip():
        errors.append("form.title: must not be empty")
    if not _is_http_url(config.form.source_url):
        errors.append("form.source_url: must be an absolute HTTP(S) URL")
    if not config.form.questions:
        errors.append("form.questions: at least one question is required")

    question_ids: set[str] = set()
    for question in config.form.questions:
        prefix = f"question[{question.id or '?'}]"
        if not question.id.strip():
            errors.append(f"{prefix}.id: must not be empty")
        elif question.id in question_ids:
            errors.append(f"{prefix}.id: duplicate question id")
        question_ids.add(question.id)

        if not question.title.strip():
            errors.append(f"{prefix}.title: must not be empty")
        if question.group_title is not None and not question.group_title.strip():
            errors.append(f"{prefix}.group_title: must not be empty")
        if len(question.options) < 2:
            errors.append(f"{prefix}.options: at least two options are required")
        if len(set(question.options)) != len(question.options):
            errors.append(f"{prefix}.options: values must be unique")
        if any(not option.strip() for option in question.options):
            errors.append(f"{prefix}.options: values must not be empty")

    total = config.response_plan.total_responses
    if total <= 0:
        errors.append("response_plan.total_responses: must be greater than zero")
    if total > MAX_TOTAL_RESPONSES:
        errors.append(
            "response_plan.total_responses: "
            f"must not exceed {MAX_TOTAL_RESPONSES}"
        )

    planned_ids = set(config.response_plan.answers)
    for missing_id in sorted(question_ids - planned_ids):
        errors.append(f"response_plan.answers: missing question {missing_id}")
    for unknown_id in sorted(planned_ids - question_ids):
        errors.append(f"response_plan.answers: unknown question {unknown_id}")

    questions_by_id = {question.id: question for question in config.form.questions}
    for question_id, targets in config.response_plan.answers.items():
        question = questions_by_id.get(question_id)
        if question is None:
            continue

        prefix = f"response_plan.answers.{question_id}"
        if not targets:
            errors.append(f"{prefix}: at least one target is required")
            continue

        values = [target.value for target in targets]
        if len(set(values)) != len(values):
            errors.append(f"{prefix}: target values must be unique")

        for target in targets:
            if target.value not in question.options:
                errors.append(
                    f"{prefix}: {target.value!r} is not a valid question option"
                )
            if target.count < 0:
                errors.append(f"{prefix}.{target.value}: count must not be negative")
            if target.count > total:
                errors.append(
                    f"{prefix}.{target.value}: count must not exceed {total}"
                )

        target_total = sum(target.count for target in targets)
        if question.type == "single_choice" and target_total != total:
            errors.append(
                f"{prefix}: counts sum to {target_total}, expected {total}"
            )
        if (
            question.type == "checkbox"
            and question.required
            and target_total < total
        ):
            errors.append(
                f"{prefix}: required checkbox counts sum to {target_total}, "
                f"expected at least {total}"
            )

    if errors:
        raise ConfigValidationError(errors)


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
