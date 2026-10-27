import os
from pathlib import Path


def cd(input):
    path = Path(input).expanduser()
    if not path.is_dir() and path.name[0] != "~":
        print(f"cd: /{path.name}: No such file or directory")
        return
    else:
        os.chdir(path)  