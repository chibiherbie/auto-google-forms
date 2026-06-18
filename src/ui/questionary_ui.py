from typing import Sequence, TypeVar

import questionary
from prompt_toolkit.shortcuts import clear as clear_screen
from questionary import Choice

from .terminal import TerminalUi

T = TypeVar("T")


class QuestionaryUi(TerminalUi):
    def choose(self, message: str, choices: Sequence[tuple[str, T]]) -> T | None:
        return questionary.select(
            message,
            choices=[Choice(title=title, value=value) for title, value in choices],
            qmark="",
            pointer=">",
        ).ask()

    def ask_text(self, message: str) -> str | None:
        return questionary.text(message, qmark="").ask()

    def print(self, message: str = "") -> None:
        questionary.print(message)

    def clear(self) -> None:
        clear_screen()

    def pause(self, message: str = "Press any key to continue") -> None:
        questionary.press_any_key_to_continue(message).ask()
