import os
import sys
import shutil
import subprocess
from .shell import Shell


class Pipe:
    def __init__(self):
        self.pipeout = None  # file object: read end of previous stage's output
        self.shell = Shell()

    def execute(self, pipe_list, stdout=None, stderr=None):
        self.pipeout = None
        processes = []  # list of Popen or None (builtins run synchronously)

        for index, cmd in enumerate(pipe_list):
            is_last = index == len(pipe_list) - 1
            stage_stdout = stdout if is_last else subprocess.PIPE

            proc = self.run(cmd, stage_stdout, stderr)
            if proc is not None:
                processes.append(proc)

        for proc in processes:
            proc.wait()

    def run(self, cmd, stdout_dest, stderr_dest):
        command, *args = cmd
        builtin = self.shell.builtin.get(command)

        if builtin:
            return self._run_builtin(builtin, args, stdout_dest, stderr_dest)
        else:
            return self._run_external(cmd, stdout_dest, stderr_dest)

    def _run_builtin(self, builtin, args, stdout_dest, stderr_dest):
        # Figure out where the builtin's output should go
        make_pipe = stdout_dest == subprocess.PIPE
        if make_pipe:
            read_fd, write_fd = os.pipe()
            out_file = os.fdopen(write_fd, "w")
        else:
            out_file = stdout_dest or sys.stdout

        in_file = self.pipeout if self.pipeout else sys.stdin

        try:
            builtin(args, stdout=out_file, stderr=stderr_dest or sys.stderr)
        finally:
            if out_file is not sys.stdout:
                out_file.close()
            if in_file is not sys.stdin:
                in_file.close()

        self.pipeout = os.fdopen(read_fd, "r") if make_pipe else None
        return None  # nothing to wait() on, it already ran synchronously

    def _run_external(self, cmd, stdout_dest, stderr_dest):
        command = cmd[0]
        if not shutil.which(command):
            print(f"{command}: command not found")
            return None

        proc = subprocess.Popen(
            cmd,
            stdin=self.pipeout if self.pipeout else None,
            stdout=stdout_dest,
            stderr=stderr_dest,
            text=True,
        )

        if self.pipeout:
            self.pipeout.close()

        self.pipeout = proc.stdout
        return proc
