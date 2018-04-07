import functools
import importlib
import os

from ..exc import RunAborted


def abort(return_code=0, message='Aborted', color=True):
    from .printer import printer
    if message:
        if color is True:
            color = 'error' if return_code else 'warning'
        if color:
            message = printer.colorize(message, color=color)
    raise RunAborted(return_code, message)


def flatten_args(args: list, join=False, *, empty=(None, [], (), '')) -> list:
    """Flatten args and remove empty items.

    Args:
        args: A list of items (typically but not necessarily strings),
            which may contain sub-lists, that will be flattened into
            a single list with empty items removed. Empty items include
            ``None`` and empty lists, tuples, and strings.
        join: If ``True`` or a string, the final flattened list will be
            joined into a single string. The default join string is
            a space.
        empty: Items that are considered empty.

    Returns:
        list|str: The list of args flattened with empty items removed
            and the remaining items converted to strings. If ``join`` is
            specified, the list of flattened args will be joined into
            a single string.

    Examples::

        >>> flatten_args([])
        []
        >>> flatten_args(())
        []
        >>> flatten_args([(), (), [(), ()]])
        []
        >>> flatten_args(['executable', '--flag' if True else None, ('--option', 'value'), [None]])
        ['executable', '--flag', '--option', 'value']
        >>> flatten_args(['executable', '--option', 0])
        ['executable', '--option', '0']

    """
    flat_args = []
    non_empty_args = (arg for arg in args if arg not in empty)
    for arg in non_empty_args:
        if isinstance(arg, (list, tuple)):
            flat_args.extend(flatten_args(arg))
        else:
            flat_args.append(str(arg))
    if join:
        join = ' ' if join is True else join
        flat_args = join.join(flat_args)
    return flat_args


def format_if(value, format_kwargs):
    """Apply format args to value if value or return value as is."""
    if not value:
        return value
    return value.format_map(format_kwargs)


def isatty(stream):
    try:
        return stream.isatty()
    except Exception:
        pass

    try:
        fileno = stream.fileno()
    except Exception:
        pass
    else:
        return os.isatty(fileno)

    return False


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


def merge_dicts(*dicts):
    """Merge all dicts.

    Dicts later in the list take precedence over dicts earlier in the
    list.

    """
    return functools.reduce(_merge_dicts, dicts, {})


def _merge_dicts(a, b):
    # Merge dict b into dict a
    a = a.copy()
    if not isinstance(a, dict) and isinstance(b, dict):
        raise TypeError(
            'Expected two dicts; got {a.__class__} and {b.__class__}'
            .format_map(locals()))
    for k, v in b.items():
        if k in a and isinstance(a[k], dict):
            v = merge_dicts(a[k], v)
        a[k] = v
    return a
