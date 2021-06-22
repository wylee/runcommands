import enum
import subprocess


class Color(enum.Enum):

    default = "default"
    black = "black"
    red = "red"
    green = "green"
    yellow = "yellow"
    blue = "blue"
    magenta = "magenta"
    cyan = "cyan"
    white = "white"

    def __str__(self):
        return f"[{self.value}]"


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
