import json
from pathlib import Path
from typing import TextIO

from src.models import FormDefinition
from src.planner import PlannedResponse

from .base import ResponseSender, SendReceipt


class JsonlSender(ResponseSender):
    """Reference sender that exports each planned response as one JSON line."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file: TextIO | None = None

    def open(self, form: FormDefinition) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8")

    def send(
        self,
        form: FormDefinition,
        response: PlannedResponse,
    ) -> SendReceipt:
        if self._file is None:
            raise RuntimeError("JsonlSender is not open")

        payload = {
            "form": {
                "id": form.id,
                "title": form.title,
                "source_url": form.source_url,
            },
            "response_number": response.number,
            "answers": {
                question_id: list(values)
                for question_id, values in response.grouped_answers().items()
            },
        }
        self._file.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return SendReceipt(external_id=str(response.number))

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
