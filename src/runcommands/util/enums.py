import enum
import os
import subprocess
import sys

import blessings

from .misc import isatty


if isatty(sys.stdout) and os.getenv("TERM"):
    Terminal = blessings.Terminal
else:
    # XXX: Mock terminal that returns "" for all attributes
    class TerminalValue:
        registry = {}

        @classmethod
        def get(cls, name):
            if name not in cls.registry:
                cls.registry[name] = cls(name)
            return cls.registry[name]

        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return f"{self.__class__.__name__}({self.name})"

        def __str__(self):
            return ""

    class Terminal:
        def __getattr__(self, name):
            return TerminalValue.get(name)


TERM = Terminal()


class Color(enum.Enum):

    none = ""
    reset = TERM.normal
    black = TERM.black
    red = TERM.red
    green = TERM.green
    yellow = TERM.yellow
    blue = TERM.blue
    magenta = TERM.magenta
    cyan = TERM.cyan
    white = TERM.white

    def __str__(self):
        return str(self.value)


class StreamOptions(enum.Enum):

    """Choices for stream handling."""

    capture = "capture"
    hide = "hide"
    none = "none"

    @property
    def option(self):
        return {
            "capture": subprocess.PIPE,
            "hide": subprocess.DEVNULL,
            "none": None,
        }[self.value]
