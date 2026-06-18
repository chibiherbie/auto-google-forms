import re
from urllib.parse import urlparse

from src.errors import FormImportError

FORM_PATH_RE = re.compile(r"^/forms/d/(?:e/)?([^/]+)(?:/viewform)?/?$")


def validate_google_form_url(source_url: str) -> None:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()

    is_short_url = host == "forms.gle" and bool(parsed.path.strip("/"))
    is_docs_url = (
        host == "docs.google.com"
        and parsed.path.startswith("/forms/")
        and _extract_form_id_or_none(source_url) is not None
    )
    if parsed.scheme != "https" or not (is_short_url or is_docs_url):
        raise FormImportError(
            "Expected an HTTPS URL from forms.gle or docs.google.com/forms/d/... "
            "with an optional /viewform suffix"
        )


def view_form_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    if (parsed.hostname or "").lower() == "forms.gle":
        return source_url
    return f"{canonical_form_url(source_url)}/viewform"


def canonical_form_url(source_url: str) -> str:
    return f"https://docs.google.com/forms/d/e/{extract_form_id(source_url)}"


def extract_form_id(source_url: str) -> str:
    form_id = _extract_form_id_or_none(source_url)
    if form_id is None:
        raise FormImportError("Could not determine form ID from URL")
    return form_id


def _extract_form_id_or_none(source_url: str) -> str | None:
    match = FORM_PATH_RE.search(urlparse(source_url).path)
    return match.group(1) if match else None
