import shutil
import subprocess
import shlex
import os
import io
import re
from contextlib import redirect_stdout, redirect_stderr

from app.state import BUILTINS, BACKGROUND_JOBS, VARIABLES
from app.shell_builtins import COMMANDS


def extract_background(parts: list[str]) -> tuple[list[str], bool]:
    if parts and "&" in parts[-1]:
        return parts[:-1], True

    return parts, False


def extract_redirection(parts: list[str]) -> tuple[list[str], str | None, str, str]:
    redirs = {
        ">": ("std", "w"),
        "1>": ("std", "w"),
        ">>": ("std", "a"),
        "1>>": ("std", "a"),
        "2>": ("err", "w"),
        "2>>": ("err", "a"),
    }

    for i, part in enumerate(parts):
        if part in redirs:
            file_name = parts[i + 1]
            output_type, mode = redirs[part]

            clean_parts = parts[:i] + parts[i + 2 :]
            return clean_parts, file_name, output_type, mode

    return parts, None, "std", "w"


def process_variables(parts: list[str]) -> list[str]:
    pattern = re.compile(r"\$\{(.+?)\}|\$([a-zA-Z0-9_]+)")

    def replacer(match) -> str:
        var_name = match.group(1) or match.group(2)

        return VARIABLES.get(var_name, "")

    for i, part in enumerate(parts):
        parts[i] = pattern.sub(replacer, part)

    return parts


def execute_single_command(
    parts: list[str], file_name: str | None, output_type: str, mode: str, bg: bool
) -> bool:
    command, *arguments = parts
    output_file = None

    try:
        if file_name:
            output_file = open(file_name, mode, encoding="utf-8")

        stdout_target = output_file if (output_file and output_type == "std") else None
        stderr_target = output_file if (output_file and output_type == "err") else None

        if builtin := COMMANDS.get(command):
            if stdout_target:
                with redirect_stdout(stdout_target):
                    return builtin(arguments)
            elif stderr_target:
                with redirect_stderr(stderr_target):
                    return builtin(arguments)
            else:
                return builtin(arguments)

        elif shutil.which(command):
            kwargs = {}
            if stdout_target:
                kwargs["stdout"] = stdout_target
            if stderr_target:
                kwargs["stderr"] = stderr_target

            if bg:
                process = subprocess.Popen(parts, **kwargs)
                new_id = max(BACKGROUND_JOBS.keys(), default=0) + 1
                BACKGROUND_JOBS[new_id] = process
                print(f"[{new_id}] {process.pid}")
            else:
                subprocess.run(parts, **kwargs)

            return True

        else:
            print(f"{command}: command not found")
            return True

    except FileNotFoundError:
        print(f"bash: {file_name}: No such file or directory")
        return True

    finally:
        if output_file:
            output_file.close()


def run_multi_pipeline(command_list: list[list[str]]) -> bool:
    processes = []
    actual_input = None

    for i, cmd_parts in enumerate(command_list):
        is_last = i == len(command_list) - 1
        output_destiny = None if is_last else subprocess.PIPE

        base_cmd = cmd_parts[0]

        if base_cmd in BUILTINS:
            if actual_input is not None:
                if hasattr(actual_input, "close"):
                    actual_input.close()
                elif isinstance(actual_input, int):
                    os.close(actual_input)
                actual_input = None

            builtin = COMMANDS.get(base_cmd)
            args = cmd_parts[1:]

            if is_last:
                if builtin:
                    builtin(args)
            else:
                memory_buffer = io.StringIO()
                with redirect_stdout(memory_buffer):
                    if builtin:
                        builtin(args)

                text = memory_buffer.getvalue()

                read_fd, write_fd = os.pipe()
                os.write(write_fd, text.encode("utf-8"))
                os.close(write_fd)

                actual_input = read_fd

        else:
            try:
                p = subprocess.Popen(
                    cmd_parts, stdin=actual_input, stdout=output_destiny
                )
                processes.append(p)

                if isinstance(actual_input, int):
                    os.close(actual_input)

                actual_input = p.stdout

            except FileNotFoundError as e:
                print(f"bash: command not found: {e.filename}", file=sys.stderr)
                break

    for p in processes[:-1]:
        if p.stdout:
            p.stdout.close()

    for p in processes:
        p.wait()

    return True


def run_command(line: str) -> bool:
    try:
        parts = shlex.split(line)
    except ValueError:
        print("bash: syntax error")
        return True

    if not parts:
        return True

    parts = process_variables(parts)

    if "|" in parts:
        commands = []
        sub_cmd = []
        for token in parts:
            if token == "|":
                commands.append(sub_cmd)
                sub_cmd = []
            else:
                sub_cmd.append(token)

        if sub_cmd:
            commands.append(sub_cmd)

        return run_multi_pipeline(commands)

    parts, is_background = extract_background(parts)
    parts, file_name, output_type, mode = extract_redirection(parts)

    if not parts:
        return True

    return execute_single_command(parts, file_name, output_type, mode, is_background)
    