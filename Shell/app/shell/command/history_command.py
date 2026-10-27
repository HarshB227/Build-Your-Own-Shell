import readline
import sys
from typing import List

from .container import command_container

_last_append_line = 0


@command_container.register_command("history")
def execute_history(arguments: List[str]) -> None:
    no_items = readline.get_current_history_length()

    if len(arguments) == 3:
        histfile = arguments[2]
        match arguments[1]:
            case "-r":
                readline.read_history_file(histfile)
            case "-w":
                readline.write_history_file(histfile)
            case "-a":
                global _last_append_line
                readline.append_history_file(no_items - _last_append_line, histfile)
                _last_append_line = no_items
        return

    n = int(arguments[1]) if len(arguments) > 1 else no_items
    for i in range(no_items + 1 - n, no_items + 1):
        line = readline.get_history_item(i)
        sys.stdout.write(f"{i:>5}  {line}\n")