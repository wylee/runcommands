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


class PrinterColor(enum.Enum):
    # Color
    default = Color.default.value
    black = Color.black.value
    red = Color.red.value
    green = Color.green.value
    yellow = Color.yellow.value
    blue = Color.blue.value
    magenta = Color.magenta.value
    cyan = Color.cyan.value
    white = Color.white.value

    # Colors by type
    none = Color.default.value
    header = Color.white.value
    info = Color.blue.value
    success = Color.green.value
    echo = Color.cyan.value
    warning = Color.yellow.value
    error = Color.red.value
    danger = Color.red.value
    debug = Color.cyan.value

    def open(self):
        return f"[{self.value}]"

    def close(self):
        return f"[/{self.value}]"


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
