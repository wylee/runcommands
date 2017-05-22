import shutil
import sys

from .enums import Color
from .misc import isatty


class Printer:

    color_map = {
        'header': Color.magenta,
        'info': Color.blue,
        'success': Color.green,
        'echo': Color.cyan,
        'warning': Color.yellow,
        'error': Color.red,
        'danger': Color.red,
        'debug': Color.cyan,
    }

    def __init__(self, color_map=None):
        if color_map is not None:
            self.color_map = color_map

    def colorize(self, *args, color=Color.none, sep=' ', end=Color.reset):
        if not isinstance(color, Color):
            if color in self.color_map:
                color = self.color_map[color]
            else:
                try:
                    color = Color[color]
                except KeyError:
                    raise ValueError('Unknown color: {color}'.format(color=color))
        args = (color,) + args
        string = []
        for arg in args[:-1]:
            string.append(str(arg))
            if not isinstance(arg, Color):
                string.append(sep)
        string.append(str(args[-1]))
        string = ''.join(string)
        if end:
            string = '{string}{end}'.format_map(locals())
        return string

    def print(self, *args, color=Color.none, file=sys.stdout, **kwargs):
        if isatty(file):
            colorize_kwargs = kwargs.copy()
            colorize_kwargs.pop('end', None)
            colorize_kwargs.pop('flush', None)
            string = self.colorize(*args, color=color, **colorize_kwargs)
            print(string, file=file, **kwargs)
        else:
            args = [a for a in args if not isinstance(a, Color)]
            print(*args, file=file, **kwargs)

    def header(self, *args, color=color_map['header'], **kwargs):
        self.print(*args, color=color, **kwargs)

    def info(self, *args, color=color_map['info'], **kwargs):
        self.print(*args, color=color, **kwargs)

    def success(self, *args, color=color_map['success'], **kwargs):
        self.print(*args, color=color, **kwargs)

    def echo(self, *args, color=color_map['echo'], **kwargs):
        self.print(*args, color=color, **kwargs)

    def warning(self, *args, color=color_map['warning'], file=sys.stderr, **kwargs):
        self.print(*args, color=color, file=file, **kwargs)

    def error(self, *args, color=color_map['error'], file=sys.stderr, **kwargs):
        self.print(*args, color=color, file=file, **kwargs)

    def danger(self, *args, color=color_map['danger'], file=sys.stderr, **kwargs):
        self.print(*args, color=color, file=file, **kwargs)

    def debug(self, *args, color=color_map['debug'], file=sys.stderr, **kwargs):
        self.print(*args, color=color, file=file, **kwargs)

    def hr(self, color=color_map['info']):
        self.print(get_hr(), color=color)


printer = Printer()


def get_hr():
    term_size = shutil.get_terminal_size((80, 25))
    hr = '=' * term_size.columns
    return hr
