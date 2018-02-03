import argparse
import builtins
import re
from collections import OrderedDict
from enum import Enum
from inspect import Parameter

from .exc import CommandError
from .util import Hide


class ArgConfig:

    """Configuration for an arg.

    This can be used as a function parameter annotation to explicitly
    configure an arg, overriding default behavior.

    Args:

        short_option (str): A short option like -x to use instead of the
            default, which is derived from the first character of the
            arg name.
        type (type): A type to use instead of guessing based on the
            arg's default value.
        choices (sequence): A sequence of allowed choices for the arg.
        help (str): The help string for the arg.

    .. note:: For convenience, regular dicts can be used to annotate
        args instead instead; they will be converted to instances of
        this class automatically.

    """

    short_option_regex = re.compile(r'^-\w$')

    def __init__(self, *, short_option=None, type=None, choices=None, help=None):
        if short_option is not None:
            if not self.short_option_regex.search(short_option):
                message = 'Expected short option with form -x, not "{short_option}"'
                message = message.format_map(locals())
                raise ValueError(message)

        if type is not None:
            if not isinstance(type, builtins.type):
                message = 'Expected type, not {type.__class__.__name__}'.format_map(locals())
                raise ValueError(message)

        self.short_option = short_option
        self.type = type
        self.choices = choices
        self.help = help


class Arg:

    """Encapsulates an arg belonging to a command.

    Attributes:

        command (Command): The command this arg belongs to.
        parameter (Parameter): The function parameter this arg is
            derived from.
        name (str): The normalized arg name.
        type (type): The type of the arg. By default, a positional arg
            will be parsed as str and an optional/keyword arg will be
            parsed as the type of its default value (or as str if the
            default value is None).
        default (object): The default value for the arg.
        choices (sequence): A sequence of allowed choices for the arg.
        help (str): The help string for the arg.
        short_option (str): The short command line option.
        long_option (str): Long command line option.
        inverse_option (str): Inverse option for boolean args.

    """

    empty = Parameter.empty

    def __init__(self, *,
                 command,
                 parameter,
                 name,
                 type,
                 default,
                 choices,
                 help,
                 short_option,
                 long_option,
                 inverse_option):

        self.command = command

        self.parameter = parameter
        self.is_positional = default is self.empty
        self.is_optional = not self.is_positional
        self.is_keyword_only = parameter.kind is parameter.KEYWORD_ONLY

        self.name = name
        self.qualified_name = '{command.qualified_name}.{name}'.format_map(locals())
        self.defaults_path = 'defaults.{self.qualified_name}'.format_map(locals())
        self.short_defaults_path = 'defaults.{self.name}'.format_map(locals())

        if type is None:
            if name == 'hide' and self.is_optional:
                self.type = bool_or(Hide)
                self.is_bool = False
                self.is_dict = False
                self.is_enum = False
                self.is_list = False
                self.is_bool_or = True
            else:
                self.type = str if default in (None, self.empty) else default.__class__
                self.is_bool = isinstance(default, bool)
                self.is_dict = isinstance(default, dict)
                self.is_enum = isinstance(default, Enum)
                self.is_list = isinstance(default, (list, tuple))
                self.is_bool_or = False
        else:
            if not isinstance(type, builtins.type):
                message = 'Expect type, not {arg_type.__class__.__name__}'.format_map(locals())
                raise TypeError(message)
            self.type = type
            self.is_bool = issubclass(type, bool)
            self.is_dict = issubclass(type, dict)
            self.is_enum = issubclass(type, Enum)
            self.is_list = issubclass(type, (list, tuple))
            self.is_bool_or = issubclass(type, bool_or)

        self.takes_value = self.is_positional or (self.is_optional and not self.is_bool)

        self.default = default

        if not choices:
            if self.is_enum:
                choices = self.type
            elif self.is_bool_or and issubclass(self.type.type, Enum):
                choices = self.type.type

        self.choices = choices
        self.help = help

        self.short_option = short_option
        self.long_option = long_option
        self.inverse_option = inverse_option if (self.is_bool or self.is_bool_or) else None

        options = (self.short_option, self.long_option, self.inverse_option)
        self.options = tuple(option for option in options if option)

    def __str__(self):
        string = '{kind} arg: {self.name}{default} ({self.type.__name__})'
        kind = 'Positional' if self.is_positional else 'Optional'
        has_default = self.default not in (self.empty, None)
        default = '[={self.default}]'.format_map(locals()) if has_default else ''
        return string.format_map(locals())


class HelpArg(Arg):

    def __init__(self, *, command):
        parameter = Parameter('help', Parameter.POSITIONAL_OR_KEYWORD, default=False)
        super().__init__(
            command=command,
            parameter=parameter,
            name='help',
            type=bool,
            default=False,
            choices=None,
            help=None,
            short_option='-h',
            long_option='--help',
            inverse_option=None,
        )


class bool_or:

    """Used to indicate that an arg can be a flag or an option.

    Use like this::

        @command
        def local(config, cmd, hide: {'type': bool_or(str)} = False):
            "Run the specified command, possibly hiding its output."

    Allows for this::

        run local --hide all     # Hide everything
        run local --hide         # Hide everything with less effort
        run local --hide stdout  # Hide stdout only
        run local --no-hide      # Don't hide anything

    """

    type = None

    def __new__(cls, other_type):
        if not isinstance(other_type, type):
            message = 'Expected type, not {other_type.__class__.__name__}'.format_map(locals())
            raise TypeError(message)
        name = 'BoolOr{name}'.format(name=other_type.__name__.title())
        return type(name, (cls, ), {'type': other_type})


class BoolOrAction(argparse.Action):

    def __call__(self, parser, namespace, value, option_string=None):
        if value is None:
            value = True
        setattr(namespace, self.dest, value)


class DictAddAction(argparse.Action):

    def __call__(self, parser, namespace, item, option_string=None):
        from .config import JSONValue

        if not hasattr(namespace, self.dest):
            setattr(namespace, self.dest, OrderedDict())

        items = getattr(namespace, self.dest)

        try:
            name, value = item.split('=', 1)
        except ValueError:
            raise CommandError(
                'Bad format for {self.option_strings[0]}; expected: name=<value>; got: {item}'
                .format_map(locals()))

        if value:
            value = JSONValue(value, name=name).load(tolerant=True)
        else:
            value = None

        items[name] = value


class ListAppendAction(argparse.Action):

    def __call__(self, parser, namespace, value, option_string=None):
        from .config import JSONValue

        if not hasattr(namespace, self.dest):
            setattr(namespace, self.dest, [])
        items = getattr(namespace, self.dest)
        if value:
            name = str(len(items))
            value = JSONValue(value, name=name).load(tolerant=True)
        else:
            value = None
        items.append(value)
