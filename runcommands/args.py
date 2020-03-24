import argparse
import builtins
import json
import re
from enum import Enum
from inspect import Parameter
from typing import Mapping, Sequence

from .exc import CommandError
from .util import cached_property


EMPTY = Parameter.empty
KEYWORD_ONLY = Parameter.KEYWORD_ONLY
POSITIONAL_OR_KEYWORD = Parameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = Parameter.VAR_POSITIONAL


class POSITIONAL_PLACEHOLDER:

    """Used as a placeholder for positionals."""


class ArgConfig:

    """Configuration for an arg.

    This can be used as a function parameter annotation to explicitly
    configure an arg, overriding default behavior.

    Args:

        container (type): Container type to collect args into. If this
            is passed, or if the ``default`` value is a container type,
            values for this arg will be collected into a container of
            the appropriate type.
        type (type): The arg's type. By default, a positional arg will
            be parsed as ``str`` and an optional/keyword arg will be
            parsed as the type of its default value (or as ``str`` if
            the default value is ``None``). If a ``container`` is
            specified, or if the ``default`` value for the arg is a
            container, the ``type`` will be applied to the container's
            values.
        choices (sequence): A sequence of allowed choices for the arg.
        help (str): Help string for the arg.
        inverse_help (str): Inverse help string for the arg (for the
            ``--no-xyz`` variation of boolean args).
        short_option (str): Short command line option.
        long_option (str): Long command line option.
        inverse_short_option (str): Inverse short option for boolean
            args.
        inverse_long_option (str): Inverse long option for boolean args.
        action (Action): ``argparse`` Action.
        nargs (int|str): Number of command line args to consume.
        mutual_exclusion_group (str): Name of mutual exclusion group to
            add this arg to.
        default: Default value for positional args.

    .. note:: For convenience, regular dicts can be used to annotate
        args instead; they will be converted to instances of this class
        automatically.

    """

    short_option_regex = re.compile(r'-\w')
    long_option_regex = re.compile(r'--\w+(-\w+)*')

    def __init__(self, *,
                 container=None,
                 type=None,
                 choices=None,
                 help=None,
                 inverse_help=None,
                 short_option=None,
                 long_option=None,
                 no_inverse=False,
                 inverse_short_option=None,
                 inverse_long_option=None,
                 inverse_option=None,  # XXX: Temporary alias for inverse_long_option
                 action=None,
                 nargs=None,
                 mutual_exclusion_group=None,
                 default=EMPTY):
        if short_option is not None:
            if not self.short_option_regex.fullmatch(short_option):
                message = 'Expected short option with form -x, not "{short_option}"'
                message = message.format_map(locals())
                raise CommandError(message)

        if long_option is not None:
            if not self.long_option_regex.fullmatch(long_option):
                message = 'Expected long option with form --option, not "{long_option}"'
                message = message.format_map(locals())
                raise CommandError(message)

        self.container = container
        self.type = type
        self.choices = choices
        self.help = help
        self.inverse_help = inverse_help
        self.short_option = short_option
        self.long_option = long_option
        self.no_inverse = no_inverse
        self.inverse_short_option = inverse_short_option
        self.inverse_long_option = inverse_long_option or inverse_option
        self.action = action
        self.nargs = nargs
        self.mutual_exclusion_group = mutual_exclusion_group
        self.default = default

    def __repr__(self):
        options = (
            self.short_option,
            self.long_option,
            self.inverse_short_option,
            self.inverse_long_option,
        )
        options = (option for option in options if option)
        options = ', '.join(options)
        return 'arg<{self.type.__name__}>({options})'.format_map(locals())


arg = ArgConfig


class Arg:

    """Encapsulates an arg belonging to a command.

    Attributes:

        command (Command): Command this arg belongs to.
        parameter (Parameter): Function parameter this arg is derived
            from.
        name (str): Normalized arg name.
        container (type): Container type to collect args into. If this
            is passed, or if the ``default`` value is a container type,
            values for this arg will be collected into a container of
            the appropriate type.
        type (type): The arg's type. By default, a positional arg will
            be parsed as ``str`` and an optional/keyword arg will be
            parsed as the type of its default value (or as ``str`` if
            the default value is ``None``). If a ``container`` is
            specified, or if the ``default`` value for the arg is a
            container, the ``type`` will be applied to the container's
            values.
        positional (bool): An arg will automatically be considered
            positional if it doesn't have a default value, so this
            doesn't usually need to be passed explicitly. It can be
            used to force an arg that would normally be optional to
            be positional.
        default (object): Default value for the arg.
        choices (sequence): A sequence of allowed choices for the arg.
        help (str): Help string for the arg.
        inverse_help (str): Inverse help string for the arg (for the
            ``--no-xyz`` variation of boolean args).
        short_option (str): Short command line option.
        long_option (str): Long command line option.
        inverse_short_option (str): Inverse short option for boolean
            args.
        inverse_long_option (str): Inverse long option for boolean args.
        action (Action): ``argparse`` Action.
        nargs (int|str): Number of command line args to consume.
        mutual_exclusion_group (str): Name of mutual exclusion group to
            add this arg to.

    """

    def __init__(self, *,
                 command,
                 parameter,
                 name,
                 container,
                 type,
                 positional,
                 default,
                 choices,
                 help,
                 inverse_help,
                 short_option,
                 long_option,
                 no_inverse,
                 inverse_short_option,
                 inverse_long_option,
                 action,
                 nargs,
                 mutual_exclusion_group):

        command = command

        is_keyword_only = parameter.kind is KEYWORD_ONLY and default is EMPTY
        is_var_positional = parameter.kind is VAR_POSITIONAL
        if default is EMPTY:
            is_positional = not (is_var_positional or is_keyword_only)
            is_optional = False
        else:
            is_positional = False
            is_optional = True

        if positional is not None:
            is_positional = positional

        metavar = name.upper().replace('-', '_')
        if container and len(name) > 1 and name.endswith('s'):
            metavar = metavar[:-1]

        if container is None:
            is_mapping = isinstance(default, Mapping)
            is_sequence = isinstance(default, Sequence) and not isinstance(default, str)
            if is_mapping or is_sequence:
                container = default.__class__
            elif is_var_positional:
                container = tuple

        if type is None:
            if isinstance(choices, builtins.type) and issubclass(choices, Enum):
                type = choices
            elif container is None:
                if default not in (None, EMPTY):
                    type = default.__class__
                else:
                    type = str
            else:
                type = str

        if isinstance(type, builtins.type):
            is_bool = issubclass(type, bool)
            is_bool_or = issubclass(type, bool_or)
            is_enum_bool_or = is_bool_or and issubclass(type, Enum)
            is_enum = issubclass(type, Enum)
        else:
            is_bool = False
            is_bool_or = False
            is_enum_bool_or = False
            is_enum = False

        if is_bool:
            type = None
            metavar = None
        elif is_bool_or:
            type = type.type

        if not choices:
            if is_enum:
                choices = type
            elif is_enum_bool_or:
                choices = type.type

        if is_positional or is_var_positional:
            options = (short_option, long_option, inverse_long_option)
            options = tuple(option for option in options if option is not None)
            if options:
                raise CommandError(
                    'Positional args cannot be specified with options: {options}'
                    .format(options=', '.join(options)))

        if action is None:
            if container:
                action = ContainerAction.from_container(container)
            elif is_bool:
                action = 'store_true'
            elif is_bool_or:
                action = BoolOrAction

        if nargs is None:
            if is_positional:
                if container:
                    nargs = '+'
                elif is_optional:
                    nargs = '?'
            elif is_var_positional:
                nargs = '*'
            elif is_bool_or:
                nargs = '?'
            elif is_optional:
                if container:
                    nargs = '*'

        options = tuple(opt for opt in (short_option, long_option) if opt is not None)
        all_options = options

        if no_inverse:
            inverse_options = ()
        else:
            inverse_options = tuple(
                opt for opt in (inverse_short_option, inverse_long_option) if opt is not None
            )
            all_options += inverse_options

        if is_var_positional and default is EMPTY:
            default = ()

        self.command = command
        self.parameter = parameter
        self.is_positional = is_positional
        self.is_var_positional = is_var_positional
        self.is_optional = is_optional
        self.takes_value = is_positional or (is_optional and not is_bool)
        self.dest = parameter.name
        self.name = name
        self.metavar = metavar
        self.container = container
        self.type = type
        self.is_bool = is_bool
        self.is_bool_or = is_bool_or
        self.default = default
        self.choices = choices
        self.help = help
        self.inverse_help = inverse_help
        self.short_option = short_option
        self.long_option = long_option
        self.options = options
        self.no_inverse = no_inverse
        self.inverse_short_option = inverse_short_option
        self.inverse_long_option = inverse_long_option
        self.inverse_options = inverse_options
        self.all_options = all_options
        self.action = action
        self.nargs = nargs
        self.mutual_exclusion_group = mutual_exclusion_group

    @cached_property
    def add_argument_args(self):
        args = self.options
        kwargs = {
            'action': self.action,
            'choices': self.choices,
            'dest': self.dest,
            'help': self.help,
            'metavar': self.metavar,
            'nargs': self.nargs,
            'type': self.type,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if self.is_positional and self.is_optional:
            kwargs['default'] = POSITIONAL_PLACEHOLDER
        return args, kwargs

    @cached_property
    def add_argument_inverse_args(self):
        if not (self.is_bool or self.is_bool_or) or self.no_inverse:
            return None

        args = self.inverse_options
        _, kwargs = self.add_argument_args

        if self.inverse_help:
            inverse_help = self.inverse_help
        elif self.help:
            help_ = kwargs['help']
            if help_.startswith('Don\'t '):
                inverse_help = help_[6:].capitalize()
            elif help_.startswith('Do not '):
                inverse_help = help_[7:].capitalize()
            else:
                first_letter = help_[0].lower()
                rest = help_[1:]
                inverse_help = 'Don\'t {first_letter}{rest}'.format_map(locals())
        else:
            inverse_help = self.help

        kwargs = kwargs.copy()
        kwargs['action'] = 'store_false'
        kwargs['help'] = inverse_help

        if self.is_bool_or:
            kwargs.pop('metavar')
            kwargs.pop('nargs')
            kwargs.pop('type')

        return args, kwargs

    def __str__(self):
        string = '{kind} arg: {self.name}{default}: type={type}'
        kind = 'Positional' if self.is_positional else 'Optional'
        has_default = self.default not in (EMPTY, None)
        default = '[={self.default}]'.format_map(locals()) if has_default else ''
        if self.is_bool:
            type = 'flag'
        elif self.is_bool_or:
            type = 'flag|{self.type.__name__}'.format_map(locals())
        elif self.type is None:
            type = None
        else:
            type = self.type.__name__
        return string.format_map(locals())


class HelpArg(Arg):

    def __init__(self, *, command):
        parameter = Parameter('help', POSITIONAL_OR_KEYWORD, default=False)
        super().__init__(
            command=command,
            parameter=parameter,
            name='help',
            container=None,
            type=bool,
            positional=None,
            default=False,
            choices=None,
            help=None,
            inverse_help=None,
            short_option='-h',
            long_option='--help',
            no_inverse=True,
            inverse_short_option=None,
            inverse_long_option=None,
            action=None,
            nargs=None,
            mutual_exclusion_group=None,
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

    def __new__(cls, type, *, _type_cache={}):
        if type not in _type_cache:
            name = 'BoolOr{name}'.format(name=type.__name__.title())
            _type_cache[type] = builtins.type(name, (cls,), {'type': type})
        return _type_cache[type]


class BoolOrAction(argparse.Action):

    def __call__(self, parser, namespace, value, option_string=None):
        if value is None:
            value = True
        setattr(namespace, self.dest, value)


class ContainerAction(argparse.Action):

    @classmethod
    def from_container(cls, container_type):
        return type('ContainerAction', (cls,), {'container_type': container_type})

    def __call__(self, parser, namespace, values, option_string=None):
        items_to_add = []
        items = getattr(namespace, self.dest, self.container_type())
        if isinstance(items, Mapping):
            if items is not None:
                items_to_add.extend(items.items())
            for value in values:
                try:
                    name, value = value.split(':', 1)
                except ValueError:
                    message = (
                        'Bad format for {self.option_strings[0]}; '
                        'expected name:<value> but got: {value}')
                    raise CommandError(message.format_map(locals()))
                value = self.type(value)
                items_to_add.append((name, value))
            items = self.container_type(items_to_add)
        else:  # Sequence
            if items is not None:
                items_to_add.extend(items)
            items_to_add.extend(self.type(value) for value in values)
            items = self.container_type(items_to_add)
        setattr(namespace, self.dest, items)


def json_value(string):
    """Convert string to JSON if possible; otherwise, return as is."""
    try:
        string = json.loads(string)
    except ValueError:
        pass
    return string
