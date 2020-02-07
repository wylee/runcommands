import enum
import shutil
import sys
from typing import Mapping

from .enums import Color
from .misc import isatty


class ColorMap:

    def __init__(self, color_map: Mapping[str, str]):
        self.add_colors(color_map)

    def __getitem__(self, name: str):
        return getattr(self, name)

    def __setitem__(self, name: str, color: str):
        setattr(self, name, color)

    def add_colors(self, color_map: Mapping[str, str]):
        for name, color in color_map.items():
            setattr(self, name, color)


class Printer:

    # Symbolic name => color
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

    def __init__(self, colors: enum.Enum = Color, color_map: Mapping = None, default_color=None):
        self.colors = colors
        self.color_map = ColorMap({color.name: color for color in colors})
        self.color_map.add_colors(self.__class__.color_map)
        if color_map:
            self.color_map.add_colors(color_map)
        self.default_color = self.get_color(default_color)

    def __call__(self, *args, **kwargs):
        self.print(*args, **kwargs)

    def get_color(self, color):
        if color is None:
            return self.color_map.none
        if isinstance(color, self.colors):
            return color
        try:
            return self.color_map[color]
        except KeyError:
            raise ValueError('Unknown color: {color}'.format(color=color)) from None

    def colorize(self, *args, color=None, sep=' ', end='reset'):
        color = self.get_color(color)
        args = (color,) + args
        string = []
        for arg in args[:-1]:
            string.append(str(arg))
            if not isinstance(arg, self.colors):
                string.append(sep)
        string.append(str(args[-1]))
        string = ''.join(string)
        if end:
            end = self.get_color(end)
            string = '{string}{end}'.format_map(locals())
        return string

    def print(self, *args, color=None, file=sys.stdout, **kwargs):
        if color is None:
            color = self.default_color
        if isatty(file):
            colorize_kwargs = kwargs.copy()
            colorize_kwargs.pop('end', None)
            colorize_kwargs.pop('flush', None)
            string = self.colorize(*args, color=color, **colorize_kwargs)
            print(string, file=file, **kwargs)
        else:
            args = [a for a in args if not isinstance(a, self.colors)]
            print(*args, file=file, **kwargs)

    def header(self, *args, color=None, **kwargs):
        if color is None:
            color = self.color_map.header
        self.print(*args, color=color, **kwargs)

    def info(self, *args, color=None, **kwargs):
        if color is None:
            color = self.color_map.info
        self.print(*args, color=color, **kwargs)

    def success(self, *args, color=None, **kwargs):
        if color is None:
            color = self.color_map.success
        self.print(*args, color=color, **kwargs)

    def echo(self, *args, color=None, **kwargs):
        if color is None:
            color = self.color_map.echo
        self.print(*args, color=color, **kwargs)

    def warning(self, *args, color=None, file=sys.stderr, **kwargs):
        if color is None:
            color = self.color_map.warning
        self.print(*args, color=color, file=file, **kwargs)

    def error(self, *args, color=None, file=sys.stderr, **kwargs):
        if color is None:
            color = self.color_map.error
        self.print(*args, color=color, file=file, **kwargs)

    def danger(self, *args, color=None, file=sys.stderr, **kwargs):
        if color is None:
            color = self.color_map.danger
        self.print(*args, color=color, file=file, **kwargs)

    def debug(self, *args, color=None, file=sys.stderr, **kwargs):
        if color is None:
            color = self.color_map.debug
        self.print(*args, color=color, file=file, **kwargs)

    def hr(self, *args, color=None, **kwargs):
        if color is None:
            color = self.color_map.header
        hr = get_hr()
        if args:
            sep = kwargs.get('sep') or ' '
            hr = hr[len(sep.join(args)) + len(sep):]
            prefix_kwargs = kwargs.copy()
            prefix_kwargs['sep'] = sep
            prefix_kwargs['end'] = sep
            self.print(*args, color=color, **prefix_kwargs)
        self.print(hr, color=color, **kwargs)


printer = Printer()


def get_hr():
    term_size = shutil.get_terminal_size((80, 25))
    hr = '=' * term_size.columns
    return hr
