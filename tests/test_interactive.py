import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence

from src.execution import ExecutionEngine
from src.form_configs import FormConfigs
from src.google_forms import GoogleFormsHtmlParser
from src.importer import FormImporter
from src.interactive import (
    BACK,
    CREATE_EXAMPLE,
    EXIT,
    LIST_FORMS,
    VALIDATE,
    InteractiveSession,
)
from src.planner import ResponsePlanner


class FakeUi:
    def __init__(self, answers: Sequence[Any]) -> None:
        self.answers = iter(answers)
        self.output: list[str] = []
        self.clear_count = 0
        self.pause_count = 0

    def choose(
        self, message: str, choices: Sequence[tuple[str, Any]]
    ) -> Any | None:
        answer = next(self.answers)
        if answer == "<first-form>":
            return next(value for _, value in choices if hasattr(value, "path"))
        return answer

    def ask_text(self, message: str) -> str | None:
        return next(self.answers)

    def print(self, message: str = "") -> None:
        self.output.append(message)

    def clear(self) -> None:
        self.clear_count += 1

    def pause(self, message: str = "Press any key to continue") -> None:
        self.pause_count += 1


class InteractiveSessionTest(unittest.TestCase):
    @staticmethod
    def _session(form_configs: FormConfigs, ui: FakeUi) -> InteractiveSession:
        parser = GoogleFormsHtmlParser(
            fetcher=lambda _: (_ for _ in ()).throw(
                AssertionError("Network fetch is not expected in this test")
            )
        )
        return InteractiveSession(
            form_configs=form_configs,
            ui=ui,
            importer=FormImporter(form_configs, parser),
            planner=ResponsePlanner(),
            executor=ExecutionEngine(),
        )

    def test_creates_example_from_menu(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            form_configs = FormConfigs(Path(directory))
            ui = FakeUi((CREATE_EXAMPLE, EXIT))

            result = self._session(form_configs, ui).run()

            self.assertEqual(result, 0)
            self.assertTrue((Path(directory) / "example.json").exists())
            self.assertEqual(ui.pause_count, 1)
            self.assertGreaterEqual(ui.clear_count, 3)

    def test_selects_and_validates_form(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            form_configs = FormConfigs(Path(directory))
            form_configs.create_example()
            ui = FakeUi((LIST_FORMS, "<first-form>", VALIDATE, BACK, EXIT))

            result = self._session(form_configs, ui).run()

            self.assertEqual(result, 0)
            self.assertTrue(
                any("Config is valid" in line for line in ui.output)
            )
            self.assertEqual(ui.pause_count, 1)
            self.assertGreaterEqual(ui.clear_count, 5)

    def test_back_from_form_list_returns_to_main_menu(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            form_configs = FormConfigs(Path(directory))
            form_configs.create_example()
            ui = FakeUi((LIST_FORMS, BACK, EXIT))

            result = self._session(form_configs, ui).run()

            self.assertEqual(result, 0)
            self.assertEqual(ui.pause_count, 0)


if __name__ == "__main__":
    unittest.main()
