import os
import sys


HOME = os.getenv("HOME")
original_stdout = sys.stdout
original_stderr = sys.stderr

BUILTINS = {"exit", "echo", "type", "pwd", "cd", "complete", "jobs", "history"}
COMPLETION_RULES = {}
BACKGROUND_JOBS = {}