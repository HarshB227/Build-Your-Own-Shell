from app.navigation import *
from app.redirection import *
from app.complete import complete
from app.background_jobs import list_bg_jobs
from app.history import history_cmd, write_history_on_exit


BUILTINS = {
    "exit": lambda _, file=sys.stdout: exit_shell(),
    "echo": lambda args, outfile=sys.stdout, errfile=sys.stdout: echo(
        args, outfile, errfile
    ),
    "type": lambda args, outfile=sys.stdout, errfile=sys.stdout: print_command_type(
        args, outfile, errfile
    ),
    "pwd": lambda _, outfile=sys.stdout, errfile=sys.stdout: print(
        os.getcwd(), file=outfile
    ),
    "cd": lambda args, outfile=sys.stdout, errfile=sys.stdout: cwd(
        args, outfile, errfile
    ),
    "complete": lambda args, outfile=sys.stdout, errfile=sys.stderr: complete(args),
    "jobs": lambda args, outfile=sys.stdout, errfile=sys.stderr: list_bg_jobs(),
    "history": lambda args, outfile=sys.stdout, errfile=sys.stderr: history_cmd(args),
    "declare": lambda args, outfile=sys.stdout, errfile=sys.stderr: 0,
}

PATH = os.getenv("PATH")
if PATH:
    PATH = PATH.split(":")
else:
    PATH = []


def exit_shell():
    write_history_on_exit()
    sys.exit()


def echo(args, outfile=sys.stdout, errfile=sys.stdout):
    print(" ".join(args), file=outfile)


def print_executable(command, outfile=sys.stdout):
    for path in PATH:
        executable = os.path.join(path, command)
        if os.path.isfile(executable) and os.access(executable, os.X_OK):
            print(f"{command} is {executable}", file=outfile)
            return True
    return False


def return_executable_name(command):
    for path in PATH:
        executable = os.path.join(path, command)
        if os.path.isfile(executable) and os.access(executable, os.X_OK):
            return command
    return ""


def return_command_type(command):
    if command in BUILTINS:
        return "builtin"
    elif return_executable_name(command):
        return "exec"
    else:
        return "invalid"


def print_command_type(commands, outfile=sys.stdout, errfile=sys.stdout):
    for command in commands:
        if command in BUILTINS:
            print(f"{command} is a shell builtin", file=outfile)
        elif print_executable(command, outfile):
            pass
        else:
            print(f"{command}: not found", file=errfile)


def exe_redirect(
    command_name, executable_path, command_args, redirect_command, redirect_index
):
    match redirect_command:
        case ">" | "1>":
            out_redirect_exe(
                command_name,
                executable_path,
                command_args[1:redirect_index],
                " ".join(command_args[redirect_index + 1 :]),
            )

        case "2>":
            err_redirect_exe(
                command_name,
                executable_path,
                command_args[1:redirect_index],
                " ".join(command_args[redirect_index + 1 :]),
            )

        case ">>" | "1>>":
            append_out_exe(
                command_name,
                executable_path,
                command_args[1:redirect_index],
                " ".join(command_args[redirect_index + 1 :]),
            )

        case "2>>":
            append_err_exe(
                command_name,
                executable_path,
                command_args[1:redirect_index],
                " ".join(command_args[redirect_index + 1 :]),
            )

        case _:
            out_redirect_exe(command_name, executable_path, command_args[1:])


def builtin_redirect(exe_func, command_args, redirect_command, redirect_index):
    match redirect_command:
        case ">" | "1>":
            out_redirect_builtin(
                exe_func,
                command_args[1:redirect_index],
                " ".join(command_args[redirect_index + 1 :]),
            )

        case "2>":
            err_redirect_builtin(
                exe_func,
                command_args[1:redirect_index],
                " ".join(command_args[redirect_index + 1 :]),
            )

        case ">>" | "1>>":
            append_out_builtin(
                exe_func,
                command_args[1:redirect_index],
                " ".join(command_args[redirect_index + 1 :]),
            )

        case "2>>":
            append_err_builtin(
                exe_func,
                command_args[1:redirect_index],
                " ".join(command_args[redirect_index + 1 :]),
            )

        case _:
            out_redirect_builtin(exe_func, command_args[1:])
