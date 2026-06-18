import sys
from pathlib import Path

from src.planner import ResponsePlanner
from src.errors import ConfigError, PlanBuildError
from src.execution import ExecutionEngine
from src.form_configs import FormConfigs
from src.google_forms import GoogleFormsHtmlParser
from src.importer import FormImporter
from src.interactive import InteractiveSession
from src.ui.questionary_ui import QuestionaryUi


def main() -> int:
    try:
        form_configs = FormConfigs(Path("configs"))
        return InteractiveSession(
            form_configs=form_configs,
            ui=QuestionaryUi(),
            importer=FormImporter(
                form_configs=form_configs,
                parser=GoogleFormsHtmlParser(),
            ),
            planner=ResponsePlanner(),
            executor=ExecutionEngine(),
        ).run()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        return 130
    except ConfigError as error:
        print(f"Configuration error:\n{error}", file=sys.stderr)
        return 2
    except PlanBuildError as error:
        print(f"Plan error:\n{error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"File error: {error}", file=sys.stderr)
        return 2
