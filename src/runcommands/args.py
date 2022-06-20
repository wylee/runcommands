import argparse
import builtins
import json
import re
from enum import Enum
from functools import update_wrapper
from inspect import Parameter as BaseParameter

from cached_property import cached_property

from .exc import CommandError
from .util import invert_string, is_mapping, is_sequence, is_type

EMPTY = BaseParameter.empty
KEYWORD_ONLY = BaseParameter.KEYWORD_ONLY
POSITIONAL_ONLY = BaseParameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = BaseParameter.POSITIONAL_OR_KEYWORD
VAR_KEYWORD = BaseParameter.VAR_KEYWORD
VAR_POSITIONAL = BaseParameter.VAR_POSITIONAL


class POSITIONAL_PLACEHOLDER:

    """Used as a placeholder for positionals."""


class Parameter:

    """Wrapper for :class:`inspect.Parameter`.

    Adds convenience methods for our typical use cases.

    """

    empty = EMPTY
    KEYWORD_ONLY = KEYWORD_ONLY
    POSITIONAL_ONLY = POSITIONAL_ONLY
    POSITIONAL_OR_KEYWORD = POSITIONAL_OR_KEYWORD
    VAR_KEYWORD = VAR_KEYWORD
    VAR_POSITIONAL = VAR_POSITIONAL

    def __init__(self, parameter):
        self.parameter = parameter

    @cached_property
    def is_positional(self):
        kind = self.parameter.kind
        default = self.parameter.default
        return (kind is POSITIONAL_ONLY) or (
            kind is POSITIONAL_OR_KEYWORD and default is EMPTY
        )

    @cached_property
    def is_var_positional(self):
        return self.parameter.kind is VAR_POSITIONAL

    @cached_property
    def is_var_keyword(self):
        return self.parameter.kind is VAR_KEYWORD

    @cached_property
    def is_optional(self):
        kind = self.parameter.kind
        default = self.parameter.default
        return (
            (kind is POSITIONAL_OR_KEYWORD) or (kind is KEYWORD_ONLY)
        ) and default is not EMPTY

    @cached_property
    def is_required_keyword_only(self):
        kind = self.parameter.kind
        default = self.parameter.default
        return kind is KEYWORD_ONLY and default is EMPTY

    @cached_property
    def is_bool(self):
        return isinstance(self.parameter.default, bool)

    def __getattr__(self, name):
        """Proxy to wrapped :class:`inspect.Parameter`."""
        return getattr(self.parameter, name)


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
        envvar(str): Environment variable containing a default value to
            use when the arg isn't specified on the command line.
        default: Default value for positional args.

    .. note:: For convenience, regular dicts can be used to annotate
        args instead; they will be converted to instances of this class
        automatically.

    """

    short_option_regex = re.compile(r"-\w")
    long_option_regex = re.compile(r"--\w+(-\w+)*")

    def __init__(
        self,
        *,
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
        envvar=None,
        default=EMPTY,
    ):
        if short_option is not None:
            if not self.short_option_regex.fullmatch(short_option):
                raise CommandError(
                    f'Expected short option with form -x, not "{short_option}"'
                )

        if long_option is not None:
            if not self.long_option_regex.fullmatch(long_option):
                raise CommandError(
                    f'Expected long option with form --option, not "{long_option}"'
                )

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
        self.envvar = envvar
        self.default = default

    def __repr__(self):
        type_name = self.type.__name__ if self.type is not None else "None"
        options = (
            self.short_option,
            self.long_option,
            self.inverse_short_option,
            self.inverse_long_option,
        )
        options = (option for option in options if option)
        options = ", ".join(options)
        return f"arg<{type_name}>({options})"


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
        envvar(str): Environment variable containing a default value to
            use when the arg isn't specified on the command line.

    """

    def __init__(
        self,
        *,
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
        mutual_exclusion_group,
        envvar,
    ):
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

        metavar = name.upper().replace("-", "_")
        if container and len(name) > 1 and name.endswith("s"):
            metavar = metavar[:-1]

        if container is None:
            if is_mapping(default) or is_sequence(default):
                container = default.__class__
            elif is_var_positional:
                container = tuple

        if type is None:
            if is_type(choices, Enum):
                type = choices
            elif container is not None:
                if default and default is not EMPTY:
                    type = default[0].__class__
                else:
                    type = str
            elif default not in (None, EMPTY):
                type = default.__class__
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
                    f"Positional args cannot be specified with "
                    f"options: {', '.join(options)}"
                )

        if action is None:
            if container:
                if is_bool_or:
                    action = BoolOrContainerAction.make(container, type)
                    # XXX: Type conversion handled in action
                    type = str
                else:
                    action = ContainerAction.make(container)
            elif is_bool:
                action = "store_true"
            elif is_bool_or:
                action = BoolOrAction

        if nargs is None:
            if is_positional:
                if container:
                    nargs = "+"
                elif is_optional:
                    nargs = "?"
            elif is_var_positional:
                nargs = "*"
            elif is_bool_or:
                if container:
                    nargs = "*"
                else:
                    nargs = "?"
            elif is_optional:
                if container:
                    nargs = "*"

        options = tuple(opt for opt in (short_option, long_option) if opt is not None)
        all_options = options

        if no_inverse:
            inverse_options = ()
        else:
            inverse_options = tuple(
                opt
                for opt in (inverse_short_option, inverse_long_option)
                if opt is not None
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
        self.envvar = envvar

    @cached_property
    def add_argument_args(self, *, _type_wrapper_cache={}):
        args = self.options
        if self.is_optional and not self.is_bool:
            if self.type not in _type_wrapper_cache:
                type = lambda v: (None if v == "" else self.type(v))  # noqa: E731
                type = update_wrapper(type, self.type)
                _type_wrapper_cache[self.type] = type
            type = _type_wrapper_cache[self.type]
        else:
            type = self.type
        kwargs = {
            "action": self.action,
            "choices": self.choices,
            "dest": self.dest,
            "help": self.help,
            "metavar": self.metavar,
            "nargs": self.nargs,
            "type": type,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if self.is_positional and self.is_optional:
            kwargs["default"] = POSITIONAL_PLACEHOLDER
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
            inverse_help = invert_string(self.help)
        else:
            inverse_help = self.help

        kwargs = kwargs.copy()
        kwargs["action"] = "store_false"
        kwargs["help"] = inverse_help

        if self.is_bool_or:
            kwargs.pop("metavar")
            kwargs.pop("nargs")
            kwargs.pop("type")

        return args, kwargs

    def convert_value(self, value: str):
        """Convert string value to this arg's type."""
        if not isinstance(value, str):
            return value
        if self.is_bool or self.is_bool_or:
            if value in ("1", "true"):
                return True
            elif value in ("0", "false"):
                return False
            if self.is_bool:
                raise ValueError(f"Bool value must be one of 1, true, 0, or false")
        converter = self.add_argument_args[1]["type"]
        value = converter(value)
        return value

    def __str__(self):
        kind = "Positional" if self.is_positional else "Optional"
        has_default = self.default not in (EMPTY, None)
        default = f"[={self.default}]" if has_default else ""
        if self.is_bool:
            type = "flag"
        elif self.is_bool_or:
            type = f"flag|{self.type.__name__}"
        elif self.type is None:
            type = None
        else:
            type = self.type.__name__
        return f"{kind} arg: {self.name}{default}: type={type}"


class HelpArg(Arg):
    def __init__(self, *, command):
        parameter = Parameter(
            BaseParameter("help", POSITIONAL_OR_KEYWORD, default=False),
        )
        super().__init__(
            command=command,
            parameter=parameter,
            name="help",
            container=None,
            type=bool,
            positional=None,
            default=False,
            choices=None,
            help=None,
            inverse_help=None,
            short_option="-h",
            long_option="--help",
            no_inverse=True,
            inverse_short_option=None,
            inverse_long_option=None,
            action=None,
            nargs=None,
            mutual_exclusion_group=None,
            envvar=None,
        )


class bool_or:

    """Used to indicate that an arg can be a flag or an option.

    Use like this::

        @command
        def local(config, cmd, hide: {'type': bool_or} = False):
            "Run the specified command, possibly hiding its output.

            If ``hide=True``, *all* output will be hidden. It can also
            be set to one of "stdout" or "stderr" to hide just the
            specified output stream.

            "

    .. note:: The default inner type for ``bool_or`` is ``str``.
        ``bool_or(str)`` is equivalent to ``bool_or``.

    Allows for this::

        run local --hide all     # Hide everything
        run local --hide         # Hide everything with less effort
        run local --hide stdout  # Hide stdout only
        run local --no-hide      # Don't hide anything

    This can also be combined with the ``container`` option like so::

        @command
        def fetch(fields: {'container': dict, type: bool_or(int)}):
            "Get data from somewhere and show the specified fields.

            If ``fields=True``, all fields will be shown with their
            original names. If fields are specified, only those fields
            will be shown, with their names mapped. For example,
            ``fields`` could be::

                {'givenName': 'first_name', 'sn': 'last_name'}

            "

    .. note:: When combined with ``container``, the type passed to
        ``bool_or`` is applied to the *values* in the container rather
        than being applied to the literal strings passed on the command
        line.

    """

    type = str

    def __new__(cls, type, *, _type_cache={}):
        if type not in _type_cache:
            name = f"BoolOr{type.__name__.title()}"
            _type_cache[type] = builtins.type(name, (cls,), {"type": type})
        return _type_cache[type]


def add_items_to_container(
    container_type,
    item_type,
    existing_items,
    new_items,
    option_string,
):
    """Return a new container with existing plus new items."""
    items = []
    if is_mapping(existing_items):
        if existing_items is not None:
            items.extend(existing_items.items())
        for value in new_items:
            try:
                name, value = value.split(":", 1)
            except ValueError:
                raise CommandError(
                    f"Bad format for {option_string}; "
                    f"expected `name:<value>` but got `{value}`"
                )
            value = item_type(value)
            items.append((name, value))
        return container_type(items)
    elif is_sequence(existing_items):
        if existing_items is not None:
            items.extend(existing_items)
        items.extend(item_type(value) for value in new_items)
    else:
        raise ValueError(f"Not a mapping or sequence: {existing_items!r}")
    return container_type(items)


class BoolOrAction(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        if value is None:
            value = True
        setattr(namespace, self.dest, value)


class BoolOrContainerAction(argparse.Action):
    @classmethod
    def make(cls, container_type, item_type):
        return type(
            "BoolOrContainerAction",
            (cls,),
            {
                "container_type": container_type,
                "item_type": item_type,
            },
        )

    def __call__(self, parser, namespace, value, option_string=None):
        if value == []:
            setattr(namespace, self.dest, True)
        else:
            existing_items = getattr(namespace, self.dest)
            if isinstance(existing_items, bool):
                # XXX: The default value is False
                existing_items = self.container_type()
            items = add_items_to_container(
                self.container_type,
                self.item_type,
                existing_items,
                value,
                option_string,
            )
            setattr(namespace, self.dest, items)


class ContainerAction(argparse.Action):
    @classmethod
    def make(cls, container_type):
        return type("ContainerAction", (cls,), {"container_type": container_type})

    def __call__(self, parser, namespace, values, option_string=None):
        items = add_items_to_container(
            self.container_type,
            self.type,
            getattr(namespace, self.dest, self.container_type()),
            values,
            option_string,
        )
        setattr(namespace, self.dest, items)


def json_value(string):
    """Convert string to JSON if possible; otherwise, return as is."""
    try:
        string = json.loads(string)
    except ValueError:
        pass
    return string
