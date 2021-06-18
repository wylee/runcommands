import inspect
from collections import OrderedDict

from .data import Data
from .enums import Color, StreamOptions
from .misc import (
    abort,
    flatten_args,
    format_if,
    is_mapping,
    is_sequence,
    is_type,
    isatty,
    load_object,
    merge_dicts,
)
from .path import (
    abs_path,
    asset_path,
    find_project_root,
    is_project_root,
    module_from_path,
    paths_to_str,
)
from .printer import printer
from .prompt import confirm, prompt
from .string import camel_to_underscore, invert_string


__all__ = [
    "get_commands_in_namespace",
    "Data",
    "Color",
    "StreamOptions",
    "abort",
    "flatten_args",
    "format_if",
    "isatty",
    "is_mapping",
    "is_sequence",
    "is_type",
    "load_object",
    "merge_dicts",
    "abs_path",
    "asset_path",
    "find_project_root",
    "is_project_root",
    "module_from_path",
    "paths_to_str",
    "printer",
    "confirm",
    "prompt",
    "camel_to_underscore",
    "invert_string",
]


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
