import enum
import subprocess


class Color(enum.Enum):

    none = ''
    reset = '\033[0m'
    black = '\033[90m'
    red = '\033[91m'
    green = '\033[92m'
    yellow = '\033[93m'
    blue = '\033[94m'
    magenta = '\033[95m'
    cyan = '\033[96m'
    white = '\033[97m'

    def __str__(self):
        return self.value


class StreamOptions(enum.Enum):

    """Choices for stream handling."""

    capture = 'capture'
    hide = 'hide'
    none = 'none'

    @property
    def option(self):
        return {
            'capture': subprocess.PIPE,
            'hide': subprocess.DEVNULL,
            'none': None,
        }[self.value]
