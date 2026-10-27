import selectors
import subprocess
from typing import Dict, Optional, Set
from .parser import LineParser

registered: Dict[str, str] = {}


def register(program: str, handler_path: str):
    registered[program] = handler_path


def get_handler(program: str) -> Optional[str]:
    return registered.get(program)


def collect(program: str, line: str) -> Optional[Set[str]]:
    handler_path = get_handler(program)
    if not handler_path:
        return None

    command = LineParser(line).parse()[-1]
    last_argument = command.arguments[-1]
    previous_argument = command.arguments[-2] if len(command.arguments) > 1 else ""

    process = subprocess.Popen(
        [handler_path, program, last_argument, previous_argument],
        bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    candidates: Set[str] = set()

    def handle_output(stream, mask):
        line = stream.readline().rstrip("\n")

        if not line:
            return

        candidates.add(line)

    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ, handle_output)

        while process.poll() is None:
            events = selector.select()

            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

        process.wait()

    return candidates
