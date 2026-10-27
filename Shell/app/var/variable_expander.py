from typing import List

from app.etc.char_by_char_reader import CharByCharReader
from app.parse.parsed_command import ParsedCommand
from app.var.variable_manager import VariableManager


class VariableParser:
    def parse(self, s: str):
        reader = CharByCharReader(s)
        ret = []
        curr = ""
        while reader.has_next():
            c = reader.peek()
            if c != "$":
                curr += reader.next()
                continue

            reader.next()
            ret.append(curr)
            curr = "$"
            if reader.peek() == "{":
                curr += self.parse_with_braces(reader)
                ret.append(curr)
                curr = ""
            else:
                curr += self.parse_without_braces(reader)
                ret.append(curr)
                curr = ""
        if curr != "":
            ret.append(curr)
        return ret

    def parse_with_braces(self, reader):
        reader.next()
        curr = ""
        while reader.peek() != "}":
            curr += reader.next()
        reader.next()
        return curr

    def parse_without_braces(self, reader):
        curr = ""
        while reader.has_next() and reader.peek() != "$":
            curr += reader.next()

        return curr


class VariableExpander:
    def __init__(
        self,
        variableManager: VariableManager,
    ):
        self.variableManager = variableManager
        self.parser = VariableParser()

    def expand(self, args: List[str]):
        ret = []
        for var in args:
            if not "$" in var:
                ret.append(var)
                continue

            fragments = self.parser.parse(var)
            curr = ""
            for fragment in fragments:
                if not fragment.startswith("$"):
                    curr += fragment
                value = self.variableManager.get_variable(fragment[1:])
                curr += value if value != None else ""
                continue
            if curr != "":
                ret.append(curr)

        return ret

    def expand_command(self, command: ParsedCommand):
        command.args = self.expand(command.args)
        return command

    def expand_pipeline(self, pipeline: List[ParsedCommand]):
        return [self.expand_command(c) for c in pipeline]
        