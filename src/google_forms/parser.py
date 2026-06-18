from src.errors import FormImportError
from src.models import FormDefinition

from src.google_forms.decoder import extract_public_data, extract_questions, extract_title
from src.google_forms.fetch import PageFetcher, fetch_public_form
from src.google_forms.urls import canonical_form_url, extract_form_id, validate_google_form_url


class GoogleFormsHtmlParser:
    def __init__(self, fetcher: PageFetcher | None = None) -> None:
        self._fetcher = fetcher or fetch_public_form

    def parse(self, source_url: str) -> FormDefinition:
        validate_google_form_url(source_url)
        page = self._fetcher(source_url)
        validate_google_form_url(page.url)

        data = extract_public_data(page.content)
        questions = extract_questions(data)
        if not questions:
            raise FormImportError("The form contains no supported questions")

        return FormDefinition(
            id=extract_form_id(page.url),
            title=extract_title(data, page.content),
            source_url=canonical_form_url(page.url),
            questions=questions,
        )
