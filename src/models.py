from dataclasses import dataclass
from typing import Literal

QuestionType = Literal["single_choice", "checkbox"]


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    title: str
    type: QuestionType
    required: bool
    options: tuple[str, ...]
    group_title: str | None = None


@dataclass(frozen=True, slots=True)
class FormDefinition:
    id: str
    title: str
    source_url: str
    questions: tuple[Question, ...]


@dataclass(frozen=True, slots=True)
class AnswerTarget:
    value: str
    count: int


@dataclass(frozen=True, slots=True)
class ResponsePlan:
    total_responses: int
    answers: dict[str, tuple[AnswerTarget, ...]]


@dataclass(frozen=True, slots=True)
class FormConfig:
    schema_version: int
    form: FormDefinition
    response_plan: ResponsePlan
