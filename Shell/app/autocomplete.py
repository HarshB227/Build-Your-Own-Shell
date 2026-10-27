import readline

from app.executor.builtins import BUILTIN_NAMES


def completer(text: str, state: int) -> str | None:
    matches = [c + " " for c in BUILTIN_NAMES if c.startswith(text)]
    if state == 0 and not matches:
        print("\x07", end="", flush=True)
    return matches[state] if state < len(matches) else None


def setup() -> None:
    readline.set_completer(completer)
    # libedit (macOS default) uses different keybinding syntax than GNU Readline
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")