from enum import StrEnum, auto
from dataclasses import dataclass

BUILTINS = {"exit", "echo", "type", "complete"}

COMPLETIONS: dict[str, str] = dict()


class RedirectionType(StrEnum):
    STDOUT = auto()
    STDERR = auto()
    STDOUTA = auto()  # stdout append
    STDERRA = auto()  # stderr append


@dataclass
class Redirection:
    path: str
    type: RedirectionType