import importlib
import os
import shutil
import sys

import enum


class Hide(enum.Enum):

    none = 'none'
    stdout = 'stdout'
    stderr = 'stderr'
    all = 'all'

    @classmethod
    def hide_stdout(cls, value):
        if value is None:
            return False
        return cls(value) in (cls.stdout, cls.all)

    @classmethod
    def hide_stderr(cls, value):
        if value is None:
            return False
        return cls(value) in (cls.stderr, cls.all)


class cached_property:

    def __init__(self, fget):
        self.fget = fget
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def __get__(self, obj, cls=None):
        if obj is None:  # Property accessed via class
            return self
        obj.__dict__[self.__name__] = self.fget(obj)
        return obj.__dict__[self.__name__]


def isatty(stream):
    try:
        return stream.isatty()
    except:
        pass

    try:
        fileno = stream.fileno()
    except:
        pass
    else:
        return os.isatty(fileno)

    return False


def abort(code=0, message='Aborted', color=True):
    if message:
        if color is True:
            color = 'error' if code else 'warning'
        if color:
            message = printer.colorize(message, color=color)
        if code != 0:
            print(message, file=sys.stderr)
        else:
            print(message)
    sys.exit(code)


def abs_path(path, format_kwargs={}):
    """Get abs. path for ``path``.

    ``path`` may be a relative or absolute file system path or an asset
    path. If ``path`` is already an abs. path, it will be returned as
    is. Otherwise, it will be converted into a normalized abs. path.

    """
    if format_kwargs:
        path = path.format(**format_kwargs)
    if not os.path.isabs(path):
        if ':' in path:
            path = asset_path(path)
        else:
            path = os.path.expanduser(path)
            path = os.path.normpath(os.path.abspath(path))
    return path


def asset_path(path, format_kwargs={}):
    """Get absolute path to asset in package.

    ``path`` can be just a package name like 'package' or it can be
    a package name and a relative file system path like 'package:util'.

    """
    if ':' in path:
        package_name, *rel_path = path.split(':', 1)
    else:
        package_name, rel_path = path, ()
    package = importlib.import_module(package_name)
    if not hasattr(package, '__file__'):
        raise ValueError("Can't compute path relative to namespace package")
    package_path = os.path.dirname(package.__file__)
    path = os.path.join(package_path, *rel_path)
    path = os.path.normpath(os.path.abspath(path))
    if format_kwargs:
        path = path.format(**format_kwargs)
    return path


def args_to_str(args, joiner=' ', format_kwargs={}):
    # If ``args`` is a list or tuple, it will first be joined into a string
    # using the join string specified by ``joiner``. Empty strings will be
    # removed.
    #
    # ``args`` may contain nested lists and tuples, which will be joined
    # recursively.
    #
    # After ``args`` has been joined into a single string, its leading and
    # trailing whitespace will be stripped and then ``format_args`` will be
    # injected into it using ``str.format(**format_kwargs)``.
    if args is None:
        return ''
    if not isinstance(args, str):
        if isinstance(args, (list, tuple)):
            args_to_join = (args_to_str(a, joiner, None) for a in args)
            args = joiner.join(a for a in args_to_join if a)
        else:
            raise TypeError('args must be a str, list, or tuple')
    args = args.strip()
    if format_kwargs:
        args = args.format(**format_kwargs)
    return args


def as_list(items, sep=','):
    # Convert ``items`` to list.
    #
    # - None -> []
    # - '' -> []
    # - non-empty str -> items split on comma
    # - list -> items
    # - any other type -> items
    if items is None:
        items = []
    elif isinstance(items, str):
        if items == '':
            items = []
        else:
            items = items.strip().split(sep)
            items = [item.strip() for item in items]
    return items


def as_tuple(items, sep=','):
    # Same as ``as_list`` with ``items`` converted to tuple.
    return tuple(as_list(items, sep))


def confirm(config, prompt='Really?', color='warning', yes_values=('y', 'yes'),
            abort_on_unconfirmed=False, abort_options=None):
    prompt = prompt.format(**config)
    prompt = '{prompt} [{yes_value}/N] '.format(prompt=prompt, yes_value=yes_values[0])
    if isinstance(yes_values, str):
        yes_values = (yes_values,)
    if color is not None:
        prompt = printer.colorize(prompt, color=color)
    try:
        answer = input(prompt)
    except KeyboardInterrupt:
        print()
        confirmed = False
    else:
        answer = answer.strip().lower()
        confirmed = answer in yes_values
    if not confirmed and abort_on_unconfirmed:
        abort(**(abort_options or {}))
    return confirmed


def load_object(obj) -> object:
    """Load an object.

    Args:
        obj (str|object): Load the indicated object if this is a string;
            otherwise, return the object as is.

            To load a module, pass a dotted path like 'package.module';
            to load an an object from a module pass a path like
            'package.module:name'.

    Returns:
        object

    """
    if isinstance(obj, str):
        if ':' in obj:
            module_name, obj_name = obj.split(':')
            if not module_name:
                module_name = '.'
        else:
            module_name = obj
        obj = importlib.import_module(module_name)
        if obj_name:
            attrs = obj_name.split('.')
            for attr in attrs:
                obj = getattr(obj, attr)
    return obj


def prompt(message, default=None, color=True):
    message = message.rstrip()
    if default is not None:
        default = default.rstrip()
        message = '%s [%s]' % (message, default)
    message = '%s ' % message
    if color is True:
        color = 'warning'
    if color:
        message = printer.colorize(message, color=color)
    try:
        value = input(message)
    except KeyboardInterrupt:
        print()
        abort()
    value = value.strip()
    if not value and default is not None:
        return default
    return value


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
            string = '{string}{end}'.format(**locals())
        return string

    def print(self, *args, color=Color.none, file=sys.stdout, **kwargs):
        if isatty(file):
            colorize_kwargs = kwargs.copy()
            colorize_kwargs.pop('end', None)
            string = self.colorize(*args, color=color, **colorize_kwargs)
            print(string, **kwargs)
        else:
            args = [a for a in args if not isinstance(a, Color)]
            print(*args, **kwargs)

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
