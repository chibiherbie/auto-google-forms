from src.models import AnswerTarget, FormConfig, FormDefinition, ResponsePlan


def empty_response_plan(form: FormDefinition) -> ResponsePlan:
    return ResponsePlan(
        total_responses=0,
        answers={
            question.id: tuple(
                AnswerTarget(value=option, count=0) for option in question.options
            )
            for question in form.questions
        },
    )


def merge_response_plan(
    current: FormConfig,
    updated_form: FormDefinition,
) -> ResponsePlan:
    previous_answers = current.response_plan.answers
    answers: dict[str, tuple[AnswerTarget, ...]] = {}

    for question in updated_form.questions:
        previous_counts = {
            target.value: target.count
            for target in previous_answers.get(question.id, ())
        }
        answers[question.id] = tuple(
            AnswerTarget(value=option, count=previous_counts.get(option, 0))
            for option in question.options
        )

    return ResponsePlan(
        total_responses=current.response_plan.total_responses,
        answers=answers,
    )
