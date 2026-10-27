import pathlib
import sys

from .working_dir import get_cur_dir, set_cur_dir


def builtin_cd(args: list[str]):
    if len(args) < 2:
        sys.stdout.write("cd: : No such file or directory\n")
        return

    path = pathlib.Path(get_cur_dir() / args[1]).resolve()
    if not path.exists():
        sys.stdout.write(f"cd: {path}: No such file or directory\n")
        return

    set_cur_dir(path)