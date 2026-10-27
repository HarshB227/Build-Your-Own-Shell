import os
import shutil
import sys
from typing import Any, Callable, Never, TypeAlias, TypeVar

FuncType: TypeAlias = Callable[[list[str]], Any]
F = TypeVar("F", bound=FuncType)

BuiltinFunctionsTable: dict[str, FuncType] = {}


def builtin(fun_name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        BuiltinFunctionsTable[fun_name] = func
        return func

    return decorator


@builtin("exit")
def _(args: list[str]) -> Never:
    code = args[0] if args else 0
    sys.exit(code)


@builtin("echo")
def _(texts: list[str]) -> None:
    print(" ".join(texts))


@builtin("type")
def _(commands: list[str]) -> None:
    if not commands:
        return

    command = commands[0]

    if command in BuiltinFunctionsTable:
        print(f"{command} is a shell builtin")
    elif cmd_path := shutil.which(command):
        print(f"{command} is {cmd_path}")
    else:
        print(f"{command}: not found")


@builtin("pwd")
def _(args: list[str]) -> None:
    print(os.getcwd())


@builtin("cd")
def _(paths: list[str]) -> None:
    path = paths[0]

    try:
        os.chdir(os.path.expanduser(path))
    except OSError as e:
        print(f"cd: {path}: {e.strerror}")


@builtin("complete")
def _(args: list[str]) -> None:
    from app.autocomplete import ExternalCommandCompleter, RegisteredCommandCompletion

    flag, *cmds = args
    if flag == "-p":
        cmd = cmds[0]
        completer = RegisteredCommandCompletion.get(cmd)
        if completer:
            print(f"complete -C '{completer.command_path}' {cmd}")
        else:
            print(f"complete: {cmd}: no completion specification")
    elif flag == "-C":
        path, cmd = cmds
        RegisteredCommandCompletion[cmd] = ExternalCommandCompleter(path)
    elif flag == "-r":
        RegisteredCommandCompletion.pop(cmds[0], None)


@builtin("jobs")
def _(args: list[str]) -> None:
    from app.jobs import BackgroundJobs

    for job in BackgroundJobs.values():
        print(
            f"[{job.id}]{'+' if job.id == next(reversed(BackgroundJobs.keys())) else ''}  {'Running':<24}{job.command}"
        )
