import textwrap
from pathlib import Path

from src import FormConfig
from src.config import load_config
from src.errors import ConfigError, FormImportError
from src.execution import ExecutionEngine, ExecutionPolicy
from src.form_configs import FormConfigs, FormEntry
from src.importer import FormImporter
from src.planner import ResponseBatch, ResponsePlanner
from src.senders import JsonlSender, APISender
from src.ui.terminal import TerminalUi
from src.validation import validate_config

ADD_FORM = "add_form"
LIST_FORMS = "list_forms"
CREATE_EXAMPLE = "create_example"
EXIT = "exit"

SHOW_INFO = "show_info"
VALIDATE = "validate"
UPDATE = "update"
RUN = "run"
EXPORT = "export"
REAL_RUN = "real_run"
BACK = "back"


class InteractiveSession:
    def __init__(
        self,
        form_configs: FormConfigs,
        ui: TerminalUi,
        importer: FormImporter,
        planner: ResponsePlanner,
        executor: ExecutionEngine,
    ) -> None:
        self._form_configs = form_configs
        self._ui = ui
        self._importer = importer
        self._planner = planner
        self._executor = executor

    def run(self) -> int:
        while True:
            self._show_screen()
            action = self._ui.choose(
                "Choose an action:",
                (
                    ("Add a form by URL", ADD_FORM),
                    ("My forms", LIST_FORMS),
                    ("Create an example config", CREATE_EXAMPLE),
                    ("Exit", EXIT),
                ),
            )

            if action in {None, EXIT}:
                self._ui.clear()
                self._ui.print("Exiting.")
                return 0
            if action == ADD_FORM:
                self._show_screen("Add form")
                self._add_form()
                self._ui.pause()
            elif action == LIST_FORMS:
                self._select_form()
            elif action == CREATE_EXAMPLE:
                self._show_screen("Create example")
                self._create_example()
                self._ui.pause()

    def _show_screen(self, title: str | None = None) -> None:
        self._ui.clear()
        self._ui.print("Auto Google Forms")
        if title is not None:
            self._ui.print(textwrap.shorten(title, width=72, placeholder="..."))
        self._ui.print(f"Config directory: {self._form_configs.directory.resolve()}")
        self._ui.print()

    def _add_form(self) -> None:
        source_url = self._ui.ask_text("Google Form URL:")
        if not source_url:
            return

        self._ui.print("Loading form structure...")
        try:
            result = self._importer.add(source_url.strip())
        except (FormImportError, OSError) as error:
            self._ui.print(f"Could not add form: {error}")
            return

        self._ui.print(f"Form added: {result.config.form.title}")
        self._ui.print(f"Config: {result.path}")
        self._ui.print(
            "Set total_responses and answer option counts, "
            "then validate the config from the menu."
        )

    def _create_example(self) -> None:
        try:
            path = self._form_configs.create_example()
        except OSError as error:
            self._ui.print(f"Could not create config: {error}")
            return

        self._ui.print(f"Config created: {path}")

    def _select_form(self) -> None:
        entries = self._form_configs.list_forms()
        if not entries:
            self._show_screen("My forms")
            self._ui.print(
                "No forms found. Add a form or create an example config."
            )
            self._ui.pause()
            return

        self._show_screen("My forms")
        choices = [(self._entry_label(entry), entry) for entry in entries]
        choices.append(("Back", BACK))
        entry = self._ui.choose("Choose a form:", choices)
        if entry is None or entry == BACK:
            return
        if not isinstance(entry, FormEntry):
            raise TypeError(f"Unexpected form selection: {entry!r}")

        self._form_menu(entry)

    def _form_menu(self, entry: FormEntry) -> None:
        while True:
            self._show_screen(entry.title)
            action = self._ui.choose(
                "Choose an action:",
                (
                    ("Information", SHOW_INFO),
                    ("Validate config", VALIDATE),
                    ("Update form structure", UPDATE),
                    ("Build dry run", RUN),
                    ("Run", REAL_RUN),
                    # ("Export JSONL", EXPORT),
                    ("Back", BACK),
                ),
            )

            if action in {None, BACK}:
                return

            self._show_screen(entry.title)
            if action == SHOW_INFO:
                self._show_info(entry)
            elif action == VALIDATE:
                self._validate(entry.path)
            elif action == UPDATE:
                self._update_form(entry.path)
            elif action == RUN:
                self._run_form(entry.path)
            elif action == REAL_RUN:
                self._real_run_form(entry.path)
            elif action == EXPORT:
                self._export_form(entry.path)
            self._ui.pause()

    def _show_info(self, entry: FormEntry) -> None:
        status = "ready to run" if entry.is_ready else "needs configuration"
        self._ui.print(f"Title: {entry.title}")
        self._ui.print(f"ID: {entry.form_id or 'not detected'}")
        self._ui.print(f"File: {entry.path}")
        self._ui.print(f"Status: {status}")

    def _validate(self, path: Path) -> bool:
        try:
            config = load_config(path)
            validate_config(config)
        except (ConfigError, OSError) as error:
            self._ui.print(f"Config error:\n{error}")
            return False

        self._ui.print(
            f"Config is valid: {config.form.title}, "
            f"planned responses: {config.response_plan.total_responses}."
        )
        return True

    def _run_form(self, path: Path) -> None:
        try:
            config = load_config(path)
            batch = self._planner.build(config, seed=0)
        except (ConfigError, OSError, ValueError) as error:
            self._ui.print(f"Dry run was not built:\n{error}")
            return

        self._show_dry_run(batch)

    def _show_dry_run(self, batch: ResponseBatch) -> None:
        self._ui.print(
            f"Dry run ready: {len(batch.responses)} responses, "
            f"{len(batch.statistics)} questions, seed={batch.seed}."
        )
        self._ui.print("Target counts were reproduced exactly.")

        for response in batch.responses[:3]:
            question_count = len(response.grouped_answers())
            self._ui.print(
                f"Response #{response.number}: "
                f"{question_count} questions, {len(response.answers)} marks."
            )

        self._ui.print("No network requests were sent.")

    def _update_form(self, path: Path) -> None:
        self._ui.print("Loading the current form structure...")
        try:
            result = self._importer.update(path)
        except (ConfigError, FormImportError, OSError) as error:
            self._ui.print(f"Could not update form: {error}")
            return

        self._ui.print(
            f"Form updated: {result.config.form.title}, "
            f"questions: {len(result.config.form.questions)}."
        )
        self._validate(result.path)

    def _real_run_form(self, path: Path) -> None:
        try:
            config = load_config(path)
            batch = self._planner.build(config, seed=0)
        except (ConfigError, OSError, ValueError) as error:
            self._ui.print(f"Dry run was not built:\n{error}")
            return

        self._start_real_run(config, batch)

    def _start_real_run(self, config: FormConfig,  batch: ResponseBatch) -> None:
        self._ui.print("Starting real run.")
        report = self._executor.execute(
            form=config.form,
            batch=batch,
            sender=APISender(),
            policy=ExecutionPolicy(
                max_attempts=3,
                delay_seconds=1.0,
                retry_delay_seconds=2.0,
                backoff_multiplier=2.0,
                continue_on_error=True,
            ),
            on_progress=lambda progress: self._ui.print(
                f"{progress.completed} {progress.total} {progress.failed}"
            ),
        )
        self._ui.print("Run finished.")

    def _export_form(self, path: Path) -> None:
        default_path = path.with_suffix(".responses.jsonl")
        raw_path = self._ui.ask_text(
            f"Export file [{default_path}]:"
        )
        output = Path(raw_path.strip()) if raw_path and raw_path.strip() else default_path
        if output.exists():
            self._ui.print(f"File already exists: {output}")
            return

        try:
            config = load_config(path)
            batch = self._planner.build(config, seed=0)
            report = self._executor.execute(
                form=config.form,
                batch=batch,
                sender=JsonlSender(output),
            )
        except (ConfigError, OSError, ValueError) as error:
            self._ui.print(f"Export failed:\n{error}")
            return

        self._ui.print(
            f"Export finished: {report.succeeded}/{report.total}, "
            f"errors: {report.failed}."
        )
        self._ui.print(f"File: {output}")

    @staticmethod
    def _entry_label(entry: FormEntry) -> str:
        status = "ready" if entry.is_ready else "needs configuration"
        title = textwrap.shorten(entry.title, width=52, placeholder="...")
        return f"{title} [{status}]"
