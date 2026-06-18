from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.errors import FormImportError

from .urls import validate_google_form_url, view_form_url

MAX_FORM_SIZE = 5 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (compatible; AutoGoogleForms/0.1; +https://github.com/)"


@dataclass(frozen=True, slots=True)
class FetchedPage:
    url: str
    content: str


PageFetcher = Callable[[str], FetchedPage]


def fetch_public_form(source_url: str) -> FetchedPage:
    request = Request(
        view_form_url(source_url),
        headers={"User-Agent": USER_AGENT},
    )

    try:
        with urlopen(request, timeout=15) as response:
            final_url = response.geturl()
            validate_google_form_url(final_url)
            raw_content = response.read(MAX_FORM_SIZE + 1)
            charset = response.headers.get_content_charset() or "utf-8"
    except HTTPError as error:
        raise FormImportError(f"Google Forms returned HTTP {error.code}") from error
    except URLError as error:
        raise FormImportError(f"Could not load form: {error.reason}") from error
    except TimeoutError as error:
        raise FormImportError("Timed out while waiting for Google Forms") from error

    if len(raw_content) > MAX_FORM_SIZE:
        raise FormImportError("Form page exceeds the 5 MB size limit")

    try:
        content = raw_content.decode(charset)
    except (LookupError, UnicodeDecodeError) as error:
        raise FormImportError("Could not decode form page") from error

    return FetchedPage(url=final_url, content=content)
