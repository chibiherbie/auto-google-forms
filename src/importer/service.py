from pathlib import Path

from src.config import load_config, save_config
from src.errors import FormImportError
from src.form_configs import FormConfigs
from src.models import FormConfig

from src.importer.misc import empty_response_plan, merge_response_plan
from src.importer.types import FormParser, ImportResult


class FormImporter:
    def __init__(self, form_configs: FormConfigs, parser: FormParser) -> None:
        self._form_configs = form_configs
        self._parser = parser

    def add(self, source_url: str) -> ImportResult:
        form = self._parser.parse(source_url)
        existing = self._form_configs.find_by_form_id(form.id)
        if existing is not None:
            raise FormImportError(
                f"Form is already saved in {existing.path}. Use update instead."
            )

        config = FormConfig(
            schema_version=1,
            form=form,
            response_plan=empty_response_plan(form),
        )
        path = self._form_configs.available_path(form.id)
        save_config(config, path)
        return ImportResult(path=path, config=config)

    def update(self, path: Path) -> ImportResult:
        current = load_config(path)
        updated_form = self._parser.parse(current.form.source_url)
        if updated_form.id != current.form.id:
            raise FormImportError(
                "Fetched form has a different ID; config was not updated"
            )

        config = FormConfig(
            schema_version=current.schema_version,
            form=updated_form,
            response_plan=merge_response_plan(current, updated_form),
        )
        save_config(config, path)
        return ImportResult(path=path, config=config)
