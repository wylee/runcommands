import enum
import os
import subprocess
import sys

import blessings

from .misc import isatty


if isatty(sys.stdout) and os.getenv("TERM"):
    Terminal = blessings.Terminal
else:

    class Terminal:
        def __getattr__(self, name):
            return ""


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
        return self.value


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
