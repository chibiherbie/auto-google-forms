import json
import re
from html import unescape

from src.errors import FormImportError
from src.models import Question, QuestionType

PUBLIC_DATA_MARKER = "var FB_PUBLIC_LOAD_DATA_ ="
SINGLE_CHOICE_ITEM_TYPES = {2, 3}
CHECKBOX_ITEM_TYPE = 4
GRID_ITEM_TYPE = 7
IGNORED_ITEM_TYPES = {6, 8, 11}


def extract_public_data(content: str) -> list[object]:
    marker_index = content.find(PUBLIC_DATA_MARKER)
    if marker_index < 0:
        raise FormImportError(
            "Form structure was not found. The form may require authorization "
            "or Google may have changed the page format"
        )

    payload = content[marker_index + len(PUBLIC_DATA_MARKER) :].lstrip()
    try:
        data, _ = json.JSONDecoder().raw_decode(payload)
    except json.JSONDecodeError as error:
        raise FormImportError("Could not parse Google Form structure") from error

    if not isinstance(data, list):
        raise FormImportError("Google Form returned an unknown data format")
    return data


def extract_title(data: list[object], content: str) -> str:
    title = _nested_value(data, 1, 8)
    if isinstance(title, str) and title.strip():
        return title.strip()

    match = re.search(r"<title>(.*?)</title>", content, flags=re.IGNORECASE | re.DOTALL)
    if match:
        html_title = unescape(match.group(1))
        return re.sub(r"\s*-\s*Google Forms\s*$", "", html_title).strip()

    raise FormImportError("Could not determine form title")


def extract_questions(data: list[object]) -> tuple[Question, ...]:
    items = _nested_value(data, 1, 1)
    if not isinstance(items, list):
        raise FormImportError("Google Form structure does not contain a question list")

    questions: list[Question] = []
    unsupported: list[str] = []

    for item in _valid_items(items):
        item_type = item[3]
        if item_type in SINGLE_CHOICE_ITEM_TYPES:
            questions.append(_decode_choice_question(item, "single_choice"))
        elif item_type == CHECKBOX_ITEM_TYPE:
            questions.append(_decode_choice_question(item, "checkbox"))
        elif item_type == GRID_ITEM_TYPE:
            questions.extend(_decode_grid_questions(item))
        elif item_type not in IGNORED_ITEM_TYPES:
            unsupported.append(_unsupported_label(item, item_type))

    if unsupported:
        raise FormImportError("Unsupported questions: " + ", ".join(unsupported))
    return tuple(questions)


def _valid_items(items: list[object]) -> tuple[list[object], ...]:
    return tuple(
        item
        for item in items
        if isinstance(item, list) and len(item) >= 5
    )


def _decode_choice_question(
    item: list[object],
    question_type: QuestionType,
) -> Question:
    title = _item_title(item)
    entry = _first_entry(item, title)
    if len(entry) < 3:
        raise FormImportError(f"Could not parse question settings for {title!r}")

    entry_id = entry[0]
    raw_options = entry[1]
    if not isinstance(entry_id, int) or not isinstance(raw_options, list):
        raise FormImportError(f"Could not parse question options for {title!r}")

    return Question(
        id=_entry_name(entry_id),
        title=title,
        type=question_type,
        required=bool(entry[2]),
        options=_options(raw_options, f"Question {title!r}"),
    )


def _decode_grid_questions(item: list[object]) -> tuple[Question, ...]:
    group_title = _grid_title(item)
    entries = item[4]
    if not isinstance(entries, list) or not entries:
        raise FormImportError(f"Grid {group_title!r} contains no rows")

    questions: list[Question] = []
    for entry in entries:
        if not isinstance(entry, list) or len(entry) < 3:
            raise FormImportError(f"Could not parse grid {group_title!r}")

        entry_id = entry[0]
        raw_options = entry[1]
        row_title = _grid_row_title(entry)
        if not isinstance(entry_id, int) or not isinstance(raw_options, list):
            raise FormImportError(f"Could not parse grid options for {group_title!r}")

        questions.append(
            Question(
                id=_entry_name(entry_id),
                title=row_title,
                type="single_choice",
                required=bool(entry[2]),
                options=_options(raw_options, f"Grid row {row_title!r}"),
                group_title=group_title,
            )
        )

    return tuple(questions)


def _item_title(item: list[object]) -> str:
    title = item[1]
    if not isinstance(title, str) or not title.strip():
        raise FormImportError("Question title is missing")
    return title.strip()


def _grid_title(item: list[object]) -> str:
    title = item[1]
    if not isinstance(title, str) or not title.strip():
        raise FormImportError("Grid title is missing")
    return title.strip()


def _first_entry(item: list[object], title: str) -> list[object]:
    entries = item[4]
    if not isinstance(entries, list) or not entries or not isinstance(entries[0], list):
        raise FormImportError(f"Could not parse question {title!r}")
    return entries[0]


def _grid_row_title(entry: list[object]) -> str:
    for value in reversed(entry[3:]):
        if isinstance(value, str) and value.strip():
            return value.strip()
        if (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], str)
            and value[0].strip()
        ):
            return value[0].strip()
    raise FormImportError("Could not determine grid row title")


def _options(raw_options: list[object], owner: str) -> tuple[str, ...]:
    options = tuple(
        option[0]
        for option in raw_options
        if isinstance(option, list)
        and option
        and isinstance(option[0], str)
        and option[0].strip()
    )
    if len(options) < 2:
        raise FormImportError(f"{owner} contains fewer than two answer options")
    return options


def _unsupported_label(item: list[object], item_type: object) -> str:
    title = item[1] if isinstance(item[1], str) else "?"
    return f"{title!r} (type {item_type})"


def _entry_name(entry_id: int) -> str:
    return f"entry.{entry_id}"


def _nested_value(value: object, *indexes: int) -> object | None:
    current = value
    for index in indexes:
        if not isinstance(current, list) or len(current) <= index:
            return None
        current = current[index]
    return current
