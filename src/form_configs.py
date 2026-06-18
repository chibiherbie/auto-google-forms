from dataclasses import dataclass
from pathlib import Path

from src.config import example_config, load_config, save_config
from src.errors import ConfigError
from src.validation import validate_config


@dataclass(frozen=True, slots=True)
class FormEntry:
    path: Path
    title: str
    form_id: str | None
    validation_errors: tuple[str, ...]

    @property
    def is_ready(self) -> bool:
        return not self.validation_errors


class FormConfigs:
    """Helper for working with form config files."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @property
    def directory(self) -> Path:
        return self._directory

    def list_forms(self) -> tuple[FormEntry, ...]:
        if not self._directory.exists():
            return ()

        return tuple(
            self._read_entry(path)
            for path in sorted(self._directory.glob("*.json"))
            if path.is_file()
        )

    def create_example(self) -> Path:
        path = self.available_path("example")
        save_config(example_config(), path)
        return path

    def find_by_form_id(self, form_id: str) -> FormEntry | None:
        return next(
            (entry for entry in self.list_forms() if entry.form_id == form_id),
            None,
        )

    def available_path(self, stem: str) -> Path:
        safe_stem = "".join(
            character if character.isalnum() or character in "-_" else "-"
            for character in stem
        ).strip("-_")
        if not safe_stem:
            safe_stem = "form"

        candidate = self._directory / f"{safe_stem}.json"
        suffix = 2
        while candidate.exists():
            candidate = self._directory / f"{safe_stem}-{suffix}.json"
            suffix += 1
        return candidate

    def _read_entry(self, path: Path) -> FormEntry:
        try:
            config = load_config(path)
        except (ConfigError, OSError) as error:
            return FormEntry(
                path=path,
                title=path.stem,
                form_id=None,
                validation_errors=(str(error),),
            )

        errors: tuple[str, ...] = ()
        try:
            validate_config(config)
        except ConfigError as error:
            errors = tuple(getattr(error, "errors", (str(error),)))

        return FormEntry(
            path=path,
            title=config.form.title,
            form_id=config.form.id,
            validation_errors=errors,
        )
