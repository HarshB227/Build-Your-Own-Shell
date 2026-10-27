import os
from collections import defaultdict

command_list = {
    "echo": lambda something: (" ".join(something) + "\n", False),
    "exit": lambda something: ("", True),
    "not found": lambda something: (f"{something}: command not found\n", False),
    "type": lambda something: (find_type(something), False),
    "pwd": lambda something: (f"{os.getcwd()}\n", False),
}