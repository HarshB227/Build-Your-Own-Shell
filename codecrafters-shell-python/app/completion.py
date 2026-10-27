import readline

from app.commands import out, list_entries
from app.commands.executable import list_executables


def completer(text, state):
    line = readline.get_line_buffer()
    if " " in line:
        matches = match_entry(text)
    else:
        matches = [cmd + " " for cmd in ["echo", "exit"] if cmd.startswith(text)]
        if not matches or state > 0:
            matches = [exe + " " for exe in list_executables() if exe.startswith(text)]

    if state == 0 and not matches:
        out.write("\x07")

    return matches[state] if state < len(matches) else None


def match_entry(text):
    if "/" in text:
        prefix, partial = text.rsplit("/", 1)
    else:
        prefix, partial = ".", text

    matches = [
        (name if prefix == "." else f"{prefix}/{name}") + (" " if is_file else "/")
        for name, is_file in list_entries(prefix)
        if name.startswith(partial)
    ][:1]

    return matches