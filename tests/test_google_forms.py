import json
import unittest

from src.errors import FormImportError
from src.google_forms import FetchedPage, GoogleFormsHtmlParser

FORM_URL = "https://docs.google.com/forms/d/e/test-form-id/viewform"
CANONICAL_FORM_URL = "https://docs.google.com/forms/d/e/test-form-id"


def form_html(items: list[object], title: str = "Test survey") -> str:
    form_data: list[object] = [
        None,
        [
            None,
            items,
            None,
            None,
            None,
            None,
            None,
            None,
            title,
        ],
    ]
    return (
        "<html><head><title>Fallback - Google Forms</title></head>"
        f"<script>var FB_PUBLIC_LOAD_DATA_ = {json.dumps(form_data)};</script>"
        "</html>"
    )


class GoogleFormsHtmlParserTest(unittest.TestCase):
    def test_parses_single_choice_and_dropdown(self) -> None:
        html = form_html(
            [
                [
                    11,
                    "Choose a color",
                    None,
                    2,
                    [[123, [["Red"], ["Blue"]], 1]],
                ],
                [
                    12,
                    "Choose a country",
                    None,
                    3,
                    [[456, [["Russia"], ["Japan"]], 0]],
                ],
            ]
        )
        parser = GoogleFormsHtmlParser(
            fetcher=lambda _: FetchedPage(url=FORM_URL, content=html)
        )

        form = parser.parse(FORM_URL)

        self.assertEqual(form.id, "test-form-id")
        self.assertEqual(form.title, "Test survey")
        self.assertEqual(form.source_url, CANONICAL_FORM_URL)
        self.assertEqual(len(form.questions), 2)
        self.assertEqual(form.questions[0].id, "entry.123")
        self.assertEqual(form.questions[0].options, ("Red", "Blue"))
        self.assertTrue(form.questions[0].required)
        self.assertFalse(form.questions[1].required)

    def test_parses_checkboxes(self) -> None:
        html = form_html(
            [
                [
                    11,
                    "What is included?",
                    None,
                    4,
                    [[123, [["Cooking"], ["Cleaning"], ["Shopping"]], 1]],
                ]
            ]
        )
        parser = GoogleFormsHtmlParser(
            fetcher=lambda _: FetchedPage(url=FORM_URL, content=html)
        )

        form = parser.parse(FORM_URL)

        self.assertEqual(len(form.questions), 1)
        self.assertEqual(form.questions[0].type, "checkbox")
        self.assertEqual(
            form.questions[0].options,
            ("Cooking", "Cleaning", "Shopping"),
        )

    def test_parses_grid_rows_as_questions(self) -> None:
        html = form_html(
            [
                [
                    11,
                    "Rate the statements",
                    None,
                    7,
                    [
                        [
                            123,
                            [["Disagree"], ["Neutral"], ["Agree"]],
                            1,
                            None,
                            ["Statement one"],
                        ],
                        [
                            456,
                            [["Disagree"], ["Neutral"], ["Agree"]],
                            0,
                            None,
                            ["Statement two"],
                        ],
                    ],
                ]
            ]
        )
        parser = GoogleFormsHtmlParser(
            fetcher=lambda _: FetchedPage(url=FORM_URL, content=html)
        )

        form = parser.parse(FORM_URL)

        self.assertEqual(len(form.questions), 2)
        self.assertEqual(form.questions[0].id, "entry.123")
        self.assertEqual(form.questions[0].title, "Statement one")
        self.assertEqual(form.questions[0].group_title, "Rate the statements")
        self.assertEqual(form.questions[1].id, "entry.456")
        self.assertFalse(form.questions[1].required)

    def test_rejects_non_google_url_before_fetch(self) -> None:
        parser = GoogleFormsHtmlParser(
            fetcher=lambda _: (_ for _ in ()).throw(
                AssertionError("Fetcher must not be called")
            )
        )

        with self.assertRaisesRegex(FormImportError, "Expected an HTTPS URL"):
            parser.parse("https://example.com/form")

    def test_accepts_saved_base_url_for_update(self) -> None:
        html = form_html(
            [
                [
                    11,
                    "Choose a color",
                    None,
                    2,
                    [[123, [["Red"], ["Blue"]], 1]],
                ]
            ]
        )
        fetched_urls: list[str] = []

        def fetcher(source_url: str) -> FetchedPage:
            fetched_urls.append(source_url)
            return FetchedPage(url=FORM_URL, content=html)

        form = GoogleFormsHtmlParser(fetcher=fetcher).parse(CANONICAL_FORM_URL)

        self.assertEqual(fetched_urls, [CANONICAL_FORM_URL])
        self.assertEqual(form.source_url, CANONICAL_FORM_URL)

    def test_reports_unsupported_question_type(self) -> None:
        html = form_html(
            [
                [
                    11,
                    "Free text",
                    None,
                    0,
                    [[123, None, 1]],
                ]
            ]
        )
        parser = GoogleFormsHtmlParser(
            fetcher=lambda _: FetchedPage(url=FORM_URL, content=html)
        )

        with self.assertRaisesRegex(FormImportError, "Free text"):
            parser.parse(FORM_URL)


if __name__ == "__main__":
    unittest.main()
