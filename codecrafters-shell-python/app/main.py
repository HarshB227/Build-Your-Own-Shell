import glob
import io
import os
import re
import readline
import shlex
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout

BUILTINS = [
    "echo",
    "exit",
    "type",
    "pwd",
    "cd",
    "complete",
    "jobs",
    "history",
    "declare",
]

VARIABLES = {}


class ShellCompleter:
    def __init__(self, commands: list[str]):
        self.commands = commands
        # Maps a command name to a rule tuple: e.g., {"git": ("-C", "my_script"), "type": ("-c", None)}
        self.custom_rules = {}

    def complete(self, text: str, state: int) -> str | None:
        if state == 0:
            full_line = readline.get_line_buffer()
            stripped_line = full_line.lstrip()
            if " " not in stripped_line:
                self.matches = [
                    cmd + " " for cmd in self.commands if cmd.startswith(text)
                ]
            else:
                parts = stripped_line.split()
                base_cmd = parts[0] if parts else ""
                rule_info = self.custom_rules.get(base_cmd)

                if rule_info:
                    flag, value = rule_info
                    if flag == "-c":
                        self.matches = [
                            cmd + " " for cmd in self.commands if cmd.startswith(text)
                        ]
                    elif flag == "-f":
                        self.matches = glob.glob(f"{text}*")
                        self.matches = [
                            f"{m}/" if os.path.isdir(m) else f"{m} "
                            for m in self.matches
                        ]
                    elif flag == "-C":
                        external_cmd = value
                        prev_word = parts[-2] if len(parts) > 1 else base_cmd
                        args = [external_cmd, base_cmd, text, prev_word]

                        comp_env = os.environ.copy()
                        comp_env["COMP_LINE"] = full_line.rstrip("\n")
                        comp_env["COMP_POINT"] = str(len(full_line))

                        try:
                            res = subprocess.run(
                                args,
                                capture_output=True,
                                text=True,
                                check=True,
                                env=comp_env,
                            )
                            self.matches = [
                                line.strip() + " "
                                for line in res.stdout.splitlines()
                                if line.strip()
                            ]
                        except Exception:
                            self.matches = []
                else:
                    self.matches = glob.glob(f"{text}*")
                    self.matches = [
                        f"{m}/" if os.path.isdir(m) else f"{m} " for m in self.matches
                    ]
        try:
            return self.matches[state]
        except IndexError:
            return None


def get_all_executables() -> list[str]:
    executables = []
    env_path = os.environ.get("PATH", "")
    for directory in env_path.split(os.pathsep):
        if not directory or not os.path.isdir(directory):
            continue
        try:
            for entry in os.scandir(directory):
                if entry.is_file() and os.access(entry.path, os.X_OK):
                    executables.append(entry.name)
        except OSError:
            continue
    return executables


def parse_redirection(
    cmd_parts: list[str],
) -> tuple[list[str], str | None, str | None, str]:
    for idx in range(len(cmd_parts) - 1, -1, -1):
        token = cmd_parts[idx]
        if token in (">", "1>", "2>", ">>", "1>>", "2>>"):
            if idx + 1 < len(cmd_parts):
                target_file = cmd_parts[idx + 1]
                cleaned_args = cmd_parts[:idx] + cmd_parts[idx + 2 :]
                file_mode = "a" if ">>" in token else "w"
                stream_type = "stderr" if token in ("2>", "2>>") else "stdout"
                return cleaned_args, target_file, stream_type, file_mode
    return cmd_parts, None, None, "w"


def find_in_path(command: str) -> str | None:
    env_path = os.environ.get("PATH", "")
    for directory in env_path.split(os.pathsep):
        full_path = os.path.join(directory, command)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None


def reap_zombie_jobs(bg_jobs: list[dict], print_only_done: bool = True) -> None:
    for job in bg_jobs:
        if job["status"] == "Running":
            if job["proc_obj"].poll() is not None:
                job["status"] = "Done"
            if job["cmd_str"].endswith(" &"):
                job["cmd_str"] = job["cmd_str"][:-2]

    num_jobs = len(bg_jobs)
    for idx, job in enumerate(bg_jobs):
        if not print_only_done or job["status"] == "Done":
            if idx == num_jobs - 1:
                marker = "+"
            elif idx == num_jobs - 2:
                marker = "-"
            else:
                marker = " "

            status_padded = f"{job['status']:<24}"
            print(f"[{job['job_num']}]{marker} {status_padded}{job['cmd_str']}")

    bg_jobs[:] = [job for job in bg_jobs if job["status"] != "Done"]


def save_history_to_file(history_list: list[str]) -> None:
    hist_file_path = os.environ.get("HISTFILE")
    if hist_file_path:
        try:
            with open(hist_file_path, "w") as f:
                for line in history_list:
                    f.write(line + "\n")
        except OSError:
            pass


def handle_builtin(
    base_command: str,
    cmd_parts: list[str],
    completer: ShellCompleter,
    bg_jobs: list[dict],
    history_list: list[str],
    history_state: dict[str, int],
) -> None:
    if base_command == "echo":
        print(" ".join(cmd_parts))
    elif base_command == "pwd":
        print(os.getcwd())
    elif base_command == "cd":
        if not cmd_parts:
            target_dir = os.environ.get("HOME", os.path.expanduser("~"))
        else:
            target_dir = os.path.expanduser(cmd_parts[0])
        try:
            os.chdir(target_dir)
        except FileNotFoundError:
            print(f"cd: {target_dir}: No such file or directory")
        except NotADirectoryError:
            print(f"cd: {target_dir}: Not a directory")
        except PermissionError:
            print(f"cd: {target_dir}: Permission denied")
    elif base_command == "type":
        if not cmd_parts:
            print("type: missing operand")
            return
        cmd_args = cmd_parts[0]
        if cmd_args in BUILTINS:
            print(f"{cmd_args} is a shell builtin")
        else:
            full_path = find_in_path(cmd_args)
            if full_path:
                print(f"{cmd_args} is {full_path}")
            else:
                print(f"{cmd_args}: not found")
    elif base_command == "complete":
        if not cmd_parts or (cmd_parts[0] == "-p" and len(cmd_parts) == 1):
            for cmd, rule_info in completer.custom_rules.items():
                flag, val = rule_info
                val_str = f" '{val}'" if val else ""
                print(f"complete {flag}{val_str} {cmd}")
            return

        if cmd_parts[0] == "-p" and len(cmd_parts) == 2:
            target_cmd = cmd_parts[1]
            if target_cmd in completer.custom_rules:
                flag, val = completer.custom_rules[target_cmd]
                val_str = f" '{val}'" if val else ""
                print(f"complete {flag}{val_str} {target_cmd}")
            else:
                print(f"complete: {target_cmd}: no completion specification")
            return

        if cmd_parts[0] == "-r":
            if len(cmd_parts) < 2:
                print("shell: complete: -r: option requires an argument")
                return

            target_cmd = cmd_parts[1]
            if target_cmd in completer.custom_rules:
                del completer.custom_rules[target_cmd]
            else:
                print(f"shell: complete: {target_cmd}: no completion specification")
            return

        flag = cmd_parts[0]

        if flag == "-C" and len(cmd_parts) >= 3:
            external_cmd = cmd_parts[1]
            target_cmd = cmd_parts[2]
            completer.custom_rules[target_cmd] = ("-C", external_cmd)
        elif flag in ("-c", "-f"):
            target_cmd = cmd_parts[1]
            completer.custom_rules[target_cmd] = (flag, None)
        else:
            print(f"shell: complete: {flag}: invalid option")
    elif base_command == "jobs":
        reap_zombie_jobs(bg_jobs, print_only_done=False)
    elif base_command == "history":
        if cmd_parts and cmd_parts[0] == "-a":
            if len(cmd_parts) < 2:
                print("shell: history: -a: option requires an argument")
                return
            history_file = cmd_parts[1]

            try:
                with open(history_file, "a") as f:
                    start_idx = history_state["index_written"]

                    for idx in range(start_idx, len(history_list)):
                        f.write(history_list[idx] + "\n")

                    history_state["index_written"] = len(history_list)
            except OSError as e:
                print(f"shell: history: {history_file}: {e.strerror}")
            return

        if cmd_parts and cmd_parts[0] == "-w":
            if len(cmd_parts) < 2:
                print("shell: history: -w: option requires an argument")
                return
            history_file = cmd_parts[1]

            try:
                with open(history_file, "w") as f:
                    for line in history_list:
                        f.write(line + "\n")
            except OSError as e:
                print(f"shell: history: {history_file}: {e.strerror}")
            return

        if cmd_parts and cmd_parts[0] == "-r":
            if len(cmd_parts) < 2:
                print("shell: history: -r: option requires an argument")
                return
            history_file = cmd_parts[1]

            try:
                with open(history_file, "r") as f:
                    for line in f:
                        cleaned_line = line.strip()
                        if cleaned_line:
                            history_list.append(cleaned_line)
            except OSError as e:
                print(f"shell: history: {history_file}: {e.strerror}")

            return

        display_list = history_list
        start_index = 1

        if cmd_parts:
            try:
                limit = int(cmd_parts[0])
                if limit > 0:
                    display_list = history_list[-limit:]
                    start_index = max(1, len(history_list) - limit + 1)
            except ValueError:
                print(f"shell: history: {cmd_parts[0]}: numeric argument required")
                return

        for idx, cmd in enumerate(display_list, start=start_index):
            print(f"{idx:>5} {cmd}")
    elif base_command == "declare":
        if not cmd_parts:
            return

        if cmd_parts[0] == "-p":
            if len(cmd_parts) >= 2:
                var_name = cmd_parts[1]
                if var_name in VARIABLES:
                    print(f'declare -- {var_name}="{VARIABLES[var_name]}"')
                else:
                    print(f"declare: {var_name}: not found")
            else:
                print("declare: -p: option requires an argument")
            return

        for part in cmd_parts:
            if "=" in part:
                var_name, _, var_value = part.partition("=")
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", var_name):
                    print(f"declare: `{part}': not a valid identifier")
                else:
                    VARIABLES[var_name] = var_value
            else:
                if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", part):
                    print(f"declare: `{part}': not a valid identifier")
        return


def execute_command(
    base_command: str,
    cmd_parts: list[str],
    file_handle,
    stream_type: str | None,
    completer: ShellCompleter,
    is_background: bool,
    bg_jobs: list[dict],
    history_list: list[str],
    history_state: dict[str, int],
    original_cmd_str: str = "",
) -> None:
    if base_command in BUILTINS:
        out_stream = file_handle if stream_type == "stdout" else sys.stdout
        err_stream = file_handle if stream_type == "stderr" else sys.stderr
        with redirect_stdout(out_stream), redirect_stderr(err_stream):
            handle_builtin(
                base_command, cmd_parts, completer, bg_jobs, history_list, history_state
            )
    else:
        full_path = find_in_path(base_command)

        if full_path:
            final_args = [base_command] + cmd_parts

            if is_background:
                if not bg_jobs:
                    assigned_job_num = 1
                else:
                    assigned_job_num = max(job["job_num"] for job in bg_jobs) + 1

                stdout_val = file_handle if stream_type == "stdout" else None
                stderr_val = file_handle if stream_type == "stderr" else None

                proc = subprocess.Popen(
                    final_args,
                    executable=full_path,
                    stdout=stdout_val,
                    stderr=stderr_val,
                )

                print(f"[{assigned_job_num}] {proc.pid}")

                bg_jobs.append(
                    {
                        "job_num": assigned_job_num,
                        "pid": proc.pid,
                        "cmd_str": original_cmd_str,
                        "status": "Running",
                        "proc_obj": proc,
                    }
                )

            else:
                if stream_type == "stdout":
                    subprocess.run(final_args, executable=full_path, stdout=file_handle)
                elif stream_type == "stderr":
                    subprocess.run(final_args, executable=full_path, stderr=file_handle)
                else:
                    subprocess.run(final_args, executable=full_path)
        else:
            print(f"{base_command}: command not found")


def execute_pipeline(
    stages: list[list[str]],
    file_handle,
    stream_type: str | None,
    completer: ShellCompleter,
    bg_jobs: list[dict],
    history_list: list[str],
    history_state: dict[str, int],
) -> None:
    num_stages = len(stages)
    pipes = [os.pipe() for _ in range(num_stages - 1)]
    procs = []

    for i, stage in enumerate(stages):
        base = stage[0]
        args = stage[1:]

        stdin_fd: int | None = None if i == 0 else pipes[i - 1][0]

        stdout_fd: int | None = None if i == num_stages - 1 else pipes[i][1]
        stderr_fd = (
            file_handle if (i == num_stages - 1 and stream_type == "stderr") else None
        )

        stdin_already_closed = False

        if base in BUILTINS:
            input_data = ""
            if i > 0 and stdin_fd is not None:
                try:
                    with os.fdopen(stdin_fd, "r") as f:
                        input_data = f.read()
                    stdin_already_closed = True
                except OSError:
                    pass

            pipe_buffer = io.StringIO()
            original_stdin = sys.stdin
            sys.stdin = io.StringIO(input_data)

            try:
                if i == num_stages - 1 and stream_type == "stdout" and file_handle:
                    out_stream = file_handle
                elif i < num_stages - 1:
                    out_stream = pipe_buffer
                else:
                    out_stream = sys.stdout

                with (
                    redirect_stdout(out_stream),
                    redirect_stderr(stderr_fd or sys.stderr),
                ):
                    handle_builtin(
                        base, args, completer, bg_jobs, history_list, history_state
                    )
            finally:
                sys.stdin = original_stdin

            if i < num_stages - 1 and stdout_fd is not None:
                try:
                    os.write(stdout_fd, pipe_buffer.getvalue().encode())
                except OSError:
                    pass
        else:
            path = find_in_path(base)
            if not path:
                print(f"{base}: command not found")
                for r, w in pipes[i:]:
                    try:
                        os.close(r)
                    except OSError:
                        pass
                    try:
                        os.close(w)
                    except OSError:
                        pass
                return

            final_stdout = (
                file_handle
                if (i == num_stages - 1 and stream_type == "stdout")
                else stdout_fd
            )

            proc = subprocess.Popen(
                [base] + args,
                executable=path,
                stdin=stdin_fd,
                stdout=final_stdout,
                stderr=stderr_fd,
            )
            procs.append(proc)

        if i > 0 and stdin_fd is not None and not stdin_already_closed:
            try:
                os.close(stdin_fd)
            except OSError:
                pass
        if i < num_stages - 1 and stdout_fd is not None:
            try:
                os.close(stdout_fd)
            except OSError:
                pass

    for proc in procs:
        proc.wait()


def expand_variables(token: str) -> str:
    pattern = r"\$\{([A-Za-z_][A-Za-z_0-9]*)\}|\$([A-Za-z_][A-Za-z_0-9]*)"
    return re.sub(
        pattern,
        lambda m: VARIABLES.get(
            m.group(1) or m.group(2),
            os.environ.get(m.group(1) or m.group(2), ""),
        ),
        token,
    )


def main() -> None:
    path_execs = get_all_executables()
    all_commands = list(set(BUILTINS + path_execs))

    readline.set_completer_delims(" \t\n")
    completer = ShellCompleter(all_commands)
    readline.set_completer(completer.complete)

    try:
        readline.parse_and_bind("tab: complete")
    except Exception:
        readline.parse_and_bind("bind ^I rl_complete")

    bg_jobs = []
    history_list = []
    history_state = {"index_written": 0}

    hist_file_path = os.environ.get("HISTFILE")
    if hist_file_path and os.path.isfile(hist_file_path):
        try:
            with open(hist_file_path, "r") as f:
                for line in f:
                    cleaned_line = line.strip()
                    if cleaned_line:
                        history_list.append(cleaned_line)
        except OSError:
            pass

    while True:
        reap_zombie_jobs(bg_jobs, print_only_done=True)
        try:
            command = input("$ ")
        except EOFError, KeyboardInterrupt:
            save_history_to_file(history_list)
            sys.exit(0)

        cleaned_input = command.strip()
        if not cleaned_input:
            continue

        history_list.append(cleaned_input)

        try:
            tokens = shlex.split(command)
        except ValueError as e:
            print(f"shell: {e}")
            continue

        if not tokens:
            continue

        expanded_tokens = []
        for t in tokens:
            expanded = expand_variables(t)
            if expanded != "":
                expanded_tokens.append(expanded)
        tokens = expanded_tokens

        if not tokens:
            continue

        if "|" in tokens:
            stages = []
            current_stage = []
            for token in tokens:
                if token == "|":
                    stages.append(current_stage)
                    current_stage = []
                else:
                    current_stage.append(token)
            stages.append(current_stage)

            if any(not stage for stage in stages):
                print("shell: syntax error near unexpected token |")
                continue

            right_tokens, redirect_file, stream_type, file_mode = parse_redirection(
                stages[-1]
            )
            stages[-1] = right_tokens

            file_handle = None
            if redirect_file:
                try:
                    file_handle = open(redirect_file, file_mode)
                except OSError as e:
                    print(f"shell: {redirect_file}: {e.strerror}")
                    continue

            try:
                execute_pipeline(
                    stages,
                    file_handle,
                    stream_type,
                    completer,
                    bg_jobs,
                    history_list,
                    history_state,
                )
            finally:
                if file_handle:
                    file_handle.close()
            continue

        base_command = tokens[0]
        cmd_parts = tokens[1:]

        if base_command == "exit":
            save_history_to_file(history_list)
            sys.exit(0)

        is_background = False
        if cmd_parts and cmd_parts[-1] == "&":
            is_background = True
            cmd_parts.pop()
        elif base_command == "&":
            continue

        cmd_parts, redirect_file, stream_type, file_mode = parse_redirection(cmd_parts)

        file_handle = None
        if redirect_file:
            try:
                file_handle = open(redirect_file, file_mode)
            except OSError as e:
                print(f"shell: {redirect_file}: {e.strerror}")
                continue
        try:
            execute_command(
                base_command,
                cmd_parts,
                file_handle,
                stream_type,
                completer,
                is_background,
                bg_jobs,
                history_list,
                history_state,
                cleaned_input,
            )
        finally:
            if file_handle:
                file_handle.close()


if __name__ == "__main__":
    main()
    