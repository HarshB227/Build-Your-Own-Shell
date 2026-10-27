import sys
import readline
import subprocess
import os

from app.commands import APPLICABLE_COMMANDS
from app.utils import get_all_executable_files
from app.instance_cache import instance_cache
from app.constants import COMPLETER_CACHE_SUFFIX_PATH
from functools import lru_cache

_prev_text = [None]
_lcp_mode = [False]


@lru_cache(maxsize=None)
def _get_all_commands():
    builtin = [c.get_command() for c in APPLICABLE_COMMANDS]
    executables = get_all_executable_files()
    return list(dict.fromkeys(builtin + executables))


def _get_matches(text: str) -> list:
    from app.commands.command import Command

    line = readline.get_line_buffer()
    if _is_completer_registered(line):
        specific_completer = _run_specific_completer(line, text)
        return [specific_completer] if specific_completer else None
    if " " in line:
        return Command.get_completions(text)
    return [c + " " for c in _get_all_commands() if c.startswith(text)]


def _is_completer_registered(line: str) -> bool:
    from app.commands.complete_command import CompleteCommand
    from app.commands.dummy_command import DummyCommand

    command = DummyCommand(line)
    command_name = command.command_properties.input_command
    return (
        True
        if instance_cache.get_memory(
            CompleteCommand.get_command(),
            f"{COMPLETER_CACHE_SUFFIX_PATH}{command_name}",
        )
        else False
    )


def _run_specific_completer(line: str, text: str) -> str:
    from app.commands.complete_command import CompleteCommand
    from app.commands.dummy_command import DummyCommand

    parts = line.strip().split()
    if text:
        previous_word = parts[-2] if len(parts) >= 2 else ""
    else:
        previous_word = parts[-1] if parts else ""
    command = DummyCommand(line)
    command_name = command.command_properties.input_command
    incomplete_word = text
    completer_path = instance_cache.get_memory(
        CompleteCommand.get_command(), f"{COMPLETER_CACHE_SUFFIX_PATH}{command_name}"
    )
    result = subprocess.run(
        [completer_path, command_name, incomplete_word, previous_word],
        capture_output=True,
        text=True,
        env={**os.environ, "COMP_LINE": line, "COMP_POINT": str(len(line))},
    )
    if not result.stdout or result.stdout.strip() == "":
        sys.stdout.write("\x07")
        sys.stdout.flush()
        return None
    return result.stdout.strip() + " "


def _completer(text, state):
    matches = _get_matches(text)
    longest_common_prefix = _get_longest_common_prefix(text, matches)

    if state == 0:
        _lcp_mode[0] = False

        if not matches:
            sys.stdout.write("\x07")
            sys.stdout.flush()
            _prev_text[0] = None
            return None

        if len(matches) == 1:
            _prev_text[0] = None
            return matches[0]

        if _prev_text[0] != longest_common_prefix:
            _prev_text[0] = longest_common_prefix
            if longest_common_prefix != text:
                _lcp_mode[0] = True
                return longest_common_prefix
            sys.stdout.write("\x07")
            sys.stdout.flush()
            return None
        else:
            _prev_text[0] = None

    if _lcp_mode[0]:
        return None

    return matches[state] if state < len(matches) else None


def _get_longest_common_prefix(text: str, matches: list):
    if not matches:
        return text
    longest_common_prefix = matches[0]
    for match in matches[1:]:
        temp_lcp = ""
        for i in range(min(len(match), len(longest_common_prefix))):
            if match[i] == longest_common_prefix[i]:
                temp_lcp += match[i]
            else:
                break
        longest_common_prefix = temp_lcp
    return longest_common_prefix


def setup():
    readline.set_completer(_completer)
    readline.set_completer_delims(" \t\n")
    if "libedit" in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set show-all-if-ambiguous off")
        readline.parse_and_bind("set show-all-if-unmodified on")
