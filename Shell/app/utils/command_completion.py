import os
import readline


class Completer:
    def __init__(self, builtins: list[str], path=None):
        self.builtins = builtins
        self.path = path if path is not None else os.getenv("PATH")

    def _get_path_completer(self):
        executables = []
        for d in self.path.split(":"):
            if os.path.exists(d):
                for f in os.listdir(d):
                    executables.append(os.path.basename(f))
        return executables

    def completer(self, text: str, state: int):
        line = readline.get_line_buffer()
        parts = line.split()
        completing_command = (
            True
            if (len(parts) == 0) or (len(parts) == 1 and not line.endswith(" "))
            else False
        )

        if completing_command:
            executables = self._get_path_completer()
            executables.extend(self.builtins)
            matches = [c for c in executables if c.startswith(text)]

            if state >= len(matches):
                return None
            completion = matches[state]
        else:
            directory_parts = text.split(f"/")
            directory_path, sep, prefix = text.rpartition("/")
            directory_path = directory_path or "."

            try:
                entries = os.listdir(directory_path)
            except OSError as oe:
                print(oe)
                return None
            matches = [d for d in os.listdir(directory_path) if d.startswith(prefix)]
            if state >= len(matches):
                return None
            completion = f"{directory_path}/{matches[state]}" if sep else matches[state]

        return completion + "/" if os.path.isdir(completion) else completion + " "
