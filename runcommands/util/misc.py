import importlib
import os
import sys


def abort(code=0, message='Aborted', color=True):
    from .printer import printer
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
    # injected into it using ``str.format_map(format_kwargs)``.
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
        args = args.format_map(format_kwargs)
    return args


def format_if(value, format_kwargs):
    """Apply format args to value if value or return value as is."""
    if not value:
        return value
    return value.format_map(format_kwargs)


def get_all_list(namespace, prefix=None):
    """Get __all__ list for module namespace & prefix.

    This gathers the names of all the commands in the namespace whose
    qualified names begin with the specified package prefix.

    By default, the package name of the module namespace is used as the
    prefix. Pass an empty string to select all commands in the namespace
    regardless of where they were defined.

    This is intended for use in command modules that are intended for
    export into other command modules to keep other imported names from
    being inadvertently exported.

    Usage::

        >>> __all__ = get_all_list(vars())

    """
    # XXX: Avoid circular import
    from runcommands.command import Command
    if prefix is None:
        prefix = namespace['__package__']
    if not prefix.endswith('.') and prefix != '':
        prefix += '.'
    return [
        name for name, obj in namespace.items()
        if isinstance(obj, Command) and obj.qualified_name.startswith(prefix)
    ]


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
