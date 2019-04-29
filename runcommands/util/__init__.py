import importlib
import inspect
import os
import pathlib
from collections import OrderedDict

from .decorators import cached_property
from .enums import Color, StreamOptions
from .misc import abort, flatten_args, format_if, isatty, load_object, merge_dicts
from .path import abs_path, asset_path, paths_to_str
from .printer import get_hr, printer
from .prompt import confirm, prompt
from .string import camel_to_underscore


__all__ = [
    'collect_commands', 'get_commands_in_namespace',
    'cached_property',
    'Color', 'StreamOptions',
    'abort', 'flatten_args', 'format_if', 'isatty', 'load_object', 'merge_dicts',
    'abs_path', 'asset_path', 'paths_to_str',
    'get_hr', 'printer',
    'confirm', 'prompt',
    'camel_to_underscore',
]


def collect_commands(package_name=None, in_place=False, level=1):
    """Collect commands from package and its subpackages.

    This replaces the tedium of adding and maintaining a bunch of
    imports like ``from .xyz import x, y, z`` in modules that are used
    to collect all of the commands in a package.

    Args:
        package_name (str): Package to collect from. If not passed, the
            package containing the module of the call site will be used.
        in_place (bool): If set, the call site's globals will be updated
            in place (using some frame magic).
        level (int): If not called from the global scope, set this
            appropriately to account for the call stack.

    Returns:
        OrderedDict: The commands found in the package, ordered by name.

    Example usage::

        # mypackage.commands
        __all__ = list(collect_commands(in_place=True))

    Less magical usage::

        # mypackage.commands
        commands = collect_commands()
        globals().update(commands)
        __all__ = list(commands)

    .. note:: If ``package_name`` is passed and refers to a namespace
        package, all corresponding namespace package directories will be
        searched for commands.

    """
    commands = {}

    frame = inspect.stack()[level][0]
    f_globals = frame.f_globals

    if package_name is None:
        # Collect from package containing module of call site
        package_name = f_globals['__name__'].rsplit('.', 1)[0]
        package_paths = [os.path.dirname(f_globals['__file__'])]
    else:
        # Collect from named package
        package = importlib.import_module(package_name)
        package_name = package.__name__
        package_paths = package.__path__

    for package_path in package_paths:
        package_path = pathlib.Path(package_path)
        for file in package_path.rglob('*.py'):
            rel_path = str(file.relative_to(package_path))
            rel_path = rel_path[:-3]
            module_name = rel_path.replace(os.sep, '.')
            module_name = '.'.join((package_name, module_name))
            module = importlib.import_module(module_name)
            module_commands = get_commands_in_namespace(module)
            commands.update(module_commands)

    commands = OrderedDict((name, commands[name]) for name in sorted(commands))

    if in_place:
        f_globals.update(commands)

    return commands


def get_commands_in_namespace(namespace=None, level=1):
    """Get commands in namespace.

    Args:
        namespace (dict|module): Typically a module. If not passed, the
            globals from the call site will be used.
        level (int): If not called from the global scope, set this
            appropriately to account for the call stack.

    Returns:
        OrderedDict: The commands found in the namespace, ordered by
            name.

    Can be used to create ``__all__`` lists::

        __all__ = list(get_commands_in_namespace())

    """
    from ..command import Command  # noqa: Avoid circular import
    commands = {}
    if namespace is None:
        frame = inspect.stack()[level][0]
        namespace = frame.f_globals
    elif inspect.ismodule(namespace):
        namespace = vars(namespace)
    for name in namespace:
        obj = namespace[name]
        if isinstance(obj, Command):
            commands[name] = obj
    return OrderedDict((name, commands[name]) for name in sorted(commands))
