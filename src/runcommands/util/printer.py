from functools import partial

from rich.console import Console

from .enums import PrinterColor


class Printer:
    colors: type[PrinterColor]
    stdout_console: Console
    stderr_console: Console

    def __init__(self, colors: type[PrinterColor] = PrinterColor):
        self.colors = colors
        self.stdout_console = Console()
        self.stderr_console = Console(stderr=True)

    def __call__(self, *args, **kwargs):
        self.print(*args, **kwargs)

    def __getattr__(self, color):
        # self.red("...")
        return partial(self.print, color=color)

    def get_color(self, color: PrinterColor | str | None) -> PrinterColor | None:
        if color is None:
            return None
        if isinstance(color, str):
            try:
                return self.colors[color]
            except KeyError:
                raise ValueError(f"Unknown color: {color}") from None
        return color

    def colorize(self, *args, color: PrinterColor | str | None = None, sep=" "):
        if not args:
            return ""

        color_entry = self.get_color(color)
        string = []

        if color_entry is not None:
            string.append(color_entry.open())

        for arg in args[:-1]:
            if isinstance(arg, PrinterColor):
                string.append(arg.open())
            else:
                string.append(str(arg))
                string.append(sep)

        string.append(str(args[-1]))

        if color_entry is not None:
            string.append(color_entry.close())

        return "".join(string)

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
            color = self.colors.header
        self.hr()
        self.print(*args, color=color, style=style, **kwargs)
        self.print()

    def info(self, *args, color=None, **kwargs):
        if color is None:
            color = self.colors.info
        self.print(*args, color=color, **kwargs)

    def success(self, *args, color=None, **kwargs):
        if color is None:
            color = self.colors.success
        self.print(*args, color=color, **kwargs)

    def echo(self, *args, color=None, **kwargs):
        if color is None:
            color = self.colors.echo
        self.print(*args, color=color, **kwargs)

    def warning(self, *args, color=None, stderr=True, **kwargs):
        if color is None:
            color = self.colors.warning
        self.print(*args, color=color, stderr=stderr, **kwargs)

    def error(self, *args, color=None, stderr=True, **kwargs):
        if color is None:
            color = self.colors.error
        self.print(*args, color=color, stderr=stderr, **kwargs)

    def danger(self, *args, color=None, stderr=True, **kwargs):
        if color is None:
            color = self.colors.danger
        self.print(*args, color=color, stderr=stderr, **kwargs)

    def debug(self, *args, color=None, stderr=True, **kwargs):
        if color is None:
            color = self.colors.debug
        self.print(*args, color=color, stderr=stderr, **kwargs)

    def hr(self, *args, color=None, fill_char="─", align="center", **kwargs):
        """Print horizontal rule with optional title"""
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
