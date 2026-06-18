import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.config import load_config, save_config
from src.form_configs import FormConfigs
from src.importer import FormImporter
from src.models import (
    AnswerTarget,
    FormDefinition,
    Question,
    ResponsePlan,
)

FORM_URL = "https://docs.google.com/forms/d/e/test-form/viewform"


class SequenceParser:
    def __init__(self, *forms: FormDefinition) -> None:
        self.forms = iter(forms)

    def parse(self, source_url: str) -> FormDefinition:
        return next(self.forms)


def form(options: tuple[str, ...]) -> FormDefinition:
    return FormDefinition(
        id="test-form",
        title="Survey",
        source_url=FORM_URL,
        questions=(
            Question(
                id="123",
                title="Question",
                type="single_choice",
                required=True,
                options=options,
            ),
        ),
    )


class FormImporterTest(unittest.TestCase):
    def test_add_creates_editable_zero_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            form_configs = FormConfigs(Path(directory))
            importer = FormImporter(form_configs, SequenceParser(form(("A", "B"))))

            result = importer.add(FORM_URL)

            config = load_config(result.path)
            self.assertEqual(config.response_plan.total_responses, 0)
            self.assertEqual(
                config.response_plan.answers["123"],
                (
                    AnswerTarget(value="A", count=0),
                    AnswerTarget(value="B", count=0),
                ),
            )

    def test_update_preserves_matching_option_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            form_configs = FormConfigs(Path(directory))
            importer = FormImporter(
                form_configs,
                SequenceParser(form(("A", "B")), form(("A", "C"))),
            )
            result = importer.add(FORM_URL)
            configured = replace(
                result.config,
                response_plan=ResponsePlan(
                    total_responses=10,
                    answers={
                        "123": (
                            AnswerTarget(value="A", count=6),
                            AnswerTarget(value="B", count=4),
                        )
                    },
                ),
            )
            save_config(configured, result.path)

            importer.update(result.path)

            updated = load_config(result.path)
            self.assertEqual(updated.response_plan.total_responses, 10)
            self.assertEqual(
                updated.response_plan.answers["123"],
                (
                    AnswerTarget(value="A", count=6),
                    AnswerTarget(value="C", count=0),
                ),
            )


if __name__ == "__main__":
    unittest.main()
