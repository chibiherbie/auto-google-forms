import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.config import example_config, load_config, save_config
from src.errors import ConfigDecodeError
from src.models import FormDefinition, Question


class ConfigTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            expected = example_config()

            save_config(expected, path)

            self.assertEqual(load_config(path), expected)

    def test_rejects_boolean_as_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            raw = {
                "schema_version": 1,
                "form": {
                    "id": "form",
                    "title": "Survey",
                    "source_url": "https://example.com/form",
                    "questions": [
                        {
                            "id": "q1",
                            "title": "Question",
                            "type": "single_choice",
                            "required": True,
                            "options": ["A", "B"],
                        }
                    ],
                },
                "response_plan": {
                    "total_responses": 1,
                    "answers": {"q1": [{"value": "A", "count": True}]},
                },
            }
            path.write_text(json.dumps(raw), encoding="utf-8")

            with self.assertRaisesRegex(ConfigDecodeError, "must be an integer"):
                load_config(path)

    def test_round_trip_checkbox_and_group_title(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            config = example_config()
            form = FormDefinition(
                id=config.form.id,
                title=config.form.title,
                source_url=config.form.source_url,
                questions=(
                    Question(
                        id="grid-row",
                        title="Statement",
                        type="single_choice",
                        required=True,
                        options=("No", "Yes"),
                        group_title="Agreement",
                    ),
                    Question(
                        id="checkbox",
                        title="Select all",
                        type="checkbox",
                        required=False,
                        options=("A", "B"),
                    ),
                ),
            )
            config = replace(config, form=form)

            save_config(config, path)
            loaded = load_config(path)

            self.assertEqual(loaded.form.questions, form.questions)


if __name__ == "__main__":
    unittest.main()
