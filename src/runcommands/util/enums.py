import enum
import subprocess

from blessings import Terminal


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
