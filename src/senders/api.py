import requests

from src.models import FormDefinition
from src.planner import PlannedResponse

from .base import ResponseSender, SendReceipt


class APISender(ResponseSender):
    def __init__(self) -> None:
        self._session: requests.Session | None = None

    def open(self, form: FormDefinition) -> None:
        headers = {
            "Referer": form.source_url + "/viewform",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/28.0.1500.52 Safari/537.36"
            ),
        }
        self._session = requests.Session()
        self._session.headers.update(headers)

    def send(
        self,
        form: FormDefinition,
        response: PlannedResponse,
    ) -> SendReceipt:
        if self._session is None:
            raise RuntimeError("APISender is not open")

        response_url = form.source_url + "/formResponse"
        http_response = self._session.post(response_url, data=response.answers)
        http_response.raise_for_status()
        return SendReceipt(external_id=str(response.number))

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None
