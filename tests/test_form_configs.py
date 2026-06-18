import tempfile
import unittest
from pathlib import Path

from src.form_configs import FormConfigs


class FormConfigsTest(unittest.TestCase):
    def test_creates_examples_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            form_configs = FormConfigs(Path(directory))

            first = form_configs.create_example()
            second = form_configs.create_example()

            self.assertEqual(first.name, "example.json")
            self.assertEqual(second.name, "example-2.json")
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_lists_broken_json_as_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text("{", encoding="utf-8")

            entries = FormConfigs(Path(directory)).list_forms()

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].title, "broken")
            self.assertFalse(entries[0].is_ready)
            self.assertTrue(entries[0].validation_errors)


if __name__ == "__main__":
    unittest.main()
