from __future__ import annotations
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.command import Command


if TYPE_CHECKING:
    from app.shell import Shell


class CommandRegister(object):
    def __init__(self):
        self.command_lookup: dict[str, Command] = {}

    def register(self, command_t: type[Command], shell: Shell) -> None:
        if self.get(command_t.name):
            raise ValueError(f"Command '{command_t.name}' already exists")

        command = command_t(shell)
        self.command_lookup[command.name] = command

    def get(self, command_name: str) -> Command | None:
        return self.command_lookup.get(command_name)


class ExecutableRegister(object):
    def __init__(self):
        self.executable_lookup: dict[str, str] = {}

    def register(self, executeable_name: str, executeable_path: str) -> None:
        if self.executable_lookup.get(executeable_name):
            return
        self.executable_lookup[executeable_name] = executeable_path

    def get(self, executable_name: str) -> str | None:
        return self.executable_lookup.get(executable_name)


class CompleteRegister(object):
    def __init__(self):
        self.complete_lookup: dict[str, str] = {}

    def register(self, executeable_name: str, script_path: str) -> None:
        self.complete_lookup[executeable_name] = script_path

    def unregister(self, executeable_name: str):
        if self.complete_lookup.get(executeable_name):
            self.complete_lookup.pop(executeable_name)

    def get(self, executeable_name: str) -> str | None:
        return self.complete_lookup.get(executeable_name)


@dataclass
class Job:
    number: int
    pid: int
    command: str
    process: subprocess.Popen
    status: str = "Running"


class JobRegister(object):
    def __init__(self):
        self.job_lookup: list[Job] = []
        self._counter: int = 1

    def register(self, pid: int, command: str, process: subprocess.Popen):
        job = Job(self._counter, pid, command, process)
        self.job_lookup.append(job)
        self._counter += 1

    def count(self) -> int:
        return len(self.job_lookup)

    def get_all(self) -> list[Job]:
        for job in self.job_lookup:
            if job.process.poll() is not None:
                job.status = "Done"
        result = self.job_lookup.copy()
        self.job_lookup = [j for j in self.job_lookup if j.status != "Done"]
        return result
