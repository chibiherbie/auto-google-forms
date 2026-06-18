from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.models import FormConfig, FormDefinition


class FormParser(Protocol):
    def parse(self, source_url: str) -> FormDefinition: ...


@dataclass(frozen=True, slots=True)
class ImportResult:
    path: Path
    config: FormConfig
