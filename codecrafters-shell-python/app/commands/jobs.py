from app.commands.base import BackgroundQueue, Command
from app.outputStreams import StreamHandler


class JobsCommand(Command):
    def __init__(self, background_queue: BackgroundQueue) -> None:
        super().__init__()
        self._background_queue = background_queue

    def execute(self, args: list[str], stream_handler: StreamHandler) -> None:
        for idx, val in enumerate(self._background_queue):
            marker = " "
            if idx == len(self._background_queue) - 1:
                marker = "+"
            elif idx == len(self._background_queue) - 2:
                marker = "-"

            stream_handler.stdout.write(
                f"[{val.job_num}]{marker}  {val.parse_status()}{val.command}\n"
            )
