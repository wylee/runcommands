import enum
import os
from functools import partial
from typing import Mapping

from rich.console import Console

from .enums import Color
from .misc import is_type


class ColorMap:
    def __init__(self, *color_maps):
        for color_map in color_maps:
            self.add_colors(color_map)

    def __getitem__(self, name: str):
        return getattr(self, name)

    def __setitem__(self, name: str, color: str):
        setattr(self, name, color)

    def add_colors(self, color_map: Mapping[str, str]):
        if is_type(color_map, enum.Enum):
            items = ((color.name, color) for color in color_map)
        else:
            items = color_map.items()
        for name, color in items:
            setattr(self, name, color)


class Printer:

    # Symbolic name => color
    color_map = {
        "none": Color.default,
        "header": Color.white,
        "info": Color.blue,
        "success": Color.green,
        "echo": Color.cyan,
        "warning": Color.yellow,
        "error": Color.red,
        "danger": Color.red,
        "debug": Color.cyan,
    }

    def __init__(
        self,
        colors: enum.Enum = Color,
        color_map: Mapping = None,
        default_color=None,
    ):
        self.is_posix = os.name == "posix"
        self.colors = colors
        self.color_map = ColorMap()
        if colors:
            self.color_map.add_colors(colors)
        if self.__class__.color_map:
            self.color_map.add_colors(self.__class__.color_map)
        if color_map:
            self.color_map.add_colors(color_map)
        self.default_color = self.get_color(default_color)
        self.stdout_console = Console()
        self.stderr_console = Console(stderr=True)

    def __call__(self, *args, **kwargs):
        self.print(*args, **kwargs)

    def __getattr__(self, color):
        # self.red("...")
        return partial(self.stdout_console.print, style=str(color))

    def get_color(self, color):
        if color is None:
            return None
        if isinstance(color, self.colors):
            return color
        try:
            return self.color_map[color]
        except KeyError:
            raise ValueError(f"Unknown color: {color}") from None

    def colorize(self, *args, color=None, sep=" "):
        if not args:
            return ""
        if color is not None:
            color = self.get_color(color)
            args = (color,) + args
        string = []
        for arg in args[:-1]:
            string.append(str(arg))
            if not isinstance(arg, self.colors):
                string.append(sep)
        string.append(str(args[-1]))
        string = "".join(string)
        return string

    def print(
        self,
        *args,
        color=None,
        sep=" ",
        highlight=False,
        stderr=False,
        **kwargs,
    ):
        string = self.colorize(*args, color=color, sep=sep)
        if "flush" in kwargs:
            del kwargs["flush"]
        console = self.stderr_console if stderr else self.stdout_console
        console.print(string, sep=sep, highlight=highlight, **kwargs)

    def header(self, *args, color=None, style="bold", **kwargs):
        if color is None:
            color = self.color_map.header
        self.hr()
        self.print(*args, color=color, style=style, **kwargs)
        self.print()

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

    def warning(self, *args, color=None, stderr=True, **kwargs):
        if color is None:
            color = self.color_map.warning
        self.print(*args, color=color, stderr=stderr, **kwargs)

    def error(self, *args, color=None, stderr=True, **kwargs):
        if color is None:
            color = self.color_map.error
        self.print(*args, color=color, stderr=stderr, **kwargs)

    def danger(self, *args, color=None, stderr=True, **kwargs):
        if color is None:
            color = self.color_map.danger
        self.print(*args, color=color, stderr=stderr, **kwargs)

    def debug(self, *args, color=None, stderr=True, **kwargs):
        if color is None:
            color = self.color_map.debug
        self.print(*args, color=color, stderr=stderr, **kwargs)

    def hr(self, *args, color=None, fill_char="─", align="center", **kwargs):
        """Print a horizontal with optional title"""
        kwargs["characters"] = fill_char
        kwargs["align"] = align
        if "end" in kwargs:
            end = kwargs.pop("end")
            args = args + (end,)
        if args:
            sep = kwargs.get("sep") or " "
            kwargs["title"] = sep.join(args)
        if color:
            kwargs["style"] = self.get_color(color).value
        self.stdout_console.rule(**kwargs)


printer = Printer()
