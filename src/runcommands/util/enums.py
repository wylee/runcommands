import enum
import subprocess


class Color(enum.Enum):

    default = "default"
    black = "black"
    red = "bright_red"
    green = "bright_green"
    yellow = "bright_yellow"
    blue = "bright_blue"
    magenta = "bright_magenta"
    cyan = "bright_cyan"
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
