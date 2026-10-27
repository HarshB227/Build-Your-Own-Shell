import os
from functools import wraps
from typing import TYPE_CHECKING, Callable, cast

from app.commands import BuiltinCommandRegistry, builtin_registry
from app.completion import CommandCompletionRegistry, external_command_registry
from app.engine import JobManager

from .backends.readline_impl import ReadlineBackend

if TYPE_CHECKING:
    from app.core import Completer, TerminalBackendProtocol

from app.core import (
    ShellContext,
    reset_backend_context,
    reset_terminal_manager,
    set_backend_context,
    set_terminal_manager,
)


class TerminalManager:
    def __init__(
        self,
        completer: Completer,
        histfile: str = "~/.shell_history",
        backend: TerminalBackendProtocol | None = None,
        builtin_command_registry: BuiltinCommandRegistry | None = None,
        command_completion_registry: CommandCompletionRegistry | None = None,
        job_manager: JobManager | None = None,
    ):
        self.completer = completer
        self.histfile = os.environ.get("HISTFILE") or os.path.expanduser(histfile)

        self.backend: TerminalBackendProtocol = (
            backend if backend else cast("TerminalBackendProtocol", ReadlineBackend())
        )
        self.builtin_registry = (
            builtin_command_registry if builtin_command_registry else builtin_registry
        )
        self.completion_registry = (
            command_completion_registry
            if command_completion_registry
            else external_command_registry
        )
        self.job_manager = job_manager if job_manager else JobManager()
        self.shell_context = ShellContext(
            self.builtin_registry,
            self.completion_registry,
            self.job_manager,
            self.backend,
        )

    def __enter__(self):
        self._token = set_backend_context(self.backend)
        self._manager_token = set_terminal_manager(self)

        self.backend.init_terminal()

        self.backend.bind_completer(self.completer)

        self.backend.history.read_history_file(self.histfile)

        self.backend.history.last_append_line = (
            self.backend.history.get_current_history_length()
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.backend.history.write_history_file(self.histfile)

        self.backend.unbind_completer()
        self.backend.restore_terminal()

        reset_backend_context(self._token)
        reset_terminal_manager(self._manager_token)

    def __call__(self, func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper
        