import argparse
import inspect
import signal
import sys
import time
from collections import OrderedDict
from inspect import Parameter
from typing import Mapping

from .args import POSITIONAL_PLACEHOLDER, Arg, ArgConfig, HelpArg
from .exc import CommandError, RunCommandsError
from .util import cached_property, camel_to_underscore, get_hr, printer


__all__ = ['command', 'subcommand', 'Command']


class Command:

    """Wraps a callable and provides a command line argument parser.

    Args:
        implementation (callable): A callable that implements the
            command's functionality. The command's console script will
            be generated by inspecting this callable.
        name (str): Name of command as it will be called from the
            command line. Defaults to ``implementation.__name__`` (with
            underscores replaced with dashes).
        description (str): Description of command shown in command
            help. Defaults to ``implementation.__doc__``.
        timed (bool): Whether the command should be timed. Will print an
            info message showing how long the command took to complete
            when ``True``. Defaults to ``False``.
        arg_config (dict): For commands defined as classes, this can be
            used to configure common base args instead of repeating the
            configuration for each subclass. Note that its keys should
            be actual parameter names and not normalized arg names.
        debug (bool): When this is set, additional debugging info will
            be shown.

    Other attributes:
        module: Module containing command
            For a class, this is just ``self.__class__.__module__``
            For a function, this is ``self.implementation.__module__``
        qualname: Qualified name of command within module
            For a class, this is just ``self.__class__.__qualname``
            For a function, this is ``self.implementation.__qualname__``

    This is typically used via the :func:`command` decorator::

        from runcommands import command

        @command
        def my_command():
            ...

    Decorating a function with :func:`command` will create an instance
    of :class:`Command` with the wrapped function as its implementation.

    Args can be passed to :func:`command`, which will be passed through
    to the :class:`Command` constructor::

        @command(name='better-name')
        def my_command():
            ...

    It's also possible to use a class directly as a command::

        @command
        class MyCommand(Command):

            def implementation(self):
                ...

    Using the :func:`command` decorator on a class will create an
    instance of the class in the namespace where the class is defined.

    Command Names:

    A command's name is derived from the normalized name of its
    implementation function by default::

        @command
        def some_command():
            ...

        # Command name: some-command

    A name can be set explicitly instead, in which case it *won't* be
    normalized::

        @command(name='do_stuff')
        def some_command():
            ...

        # Command name: do_stuff

    If the command is defined as a class, its name will be derived from
    its class name by default (split into words then normalized)::

        class SomeCommand(Command):
            ...

        # Command name: some-command

    The `command` decorator or a class-level attribute can be used to
    set the command's name explicitly::

        @command(name='do_stuff')
        class SomeCommand(Command):
            ...

        class SomeCommand(Command):
            name = 'do_stuff'

        # Command name in both cases: do_stuff

    """

    def __init__(self, implementation=None, name=None, description=None, base_command=None,
                 timed=False, arg_config=None, default_args=None, debug=False):
        if implementation is None:
            if not hasattr(self, 'implementation'):
                raise CommandError(
                    'Missing implementation; it must be passed in as a function or defined as a '
                    'method on the command class')
            self.module = self.__class__.__module__
            self.qualname = self.__class__.__qualname__
            default_name = self.normalize_class_name(self.__class__.__name__)
        else:
            self.implementation = implementation
            self.module = implementation.__module__
            self.qualname = implementation.__qualname__
            default_name = self.normalize_name(implementation.__name__)

        name = name or getattr(self.__class__, 'name', None) or default_name

        is_subcommand = base_command is not None

        if is_subcommand:
            name = ':'.join((base_command.name, name))

        description = description or self.get_description_from_docstring(self.implementation)
        short_description = description.splitlines()[0] if description else None

        self.name = name
        self.description = description
        self.short_description = short_description
        self.timed = timed
        self.arg_config = arg_config or {}
        self.debug = debug
        self.default_args = default_args or {}
        self.mutual_exclusion_groups = {}

        # Subcommand-related attributes
        first_arg = next(iter(self.args.values()), None)
        self.base_command = base_command
        self.is_subcommand = is_subcommand
        self.subcommands = []
        self.first_arg = first_arg
        self.first_arg_has_choices = False if first_arg is None else bool(first_arg.choices)

        if is_subcommand:
            base_command.add_subcommand(self)

    def subcommand(self, name=None, description=None, timed=False):
        """Create a subcommand of the specified base command."""
        base_command = self
        return command(name, description, base_command, timed, cls=self.__class__)

    @property
    def is_base_command(self):
        return bool(self.subcommands)

    @property
    def subcommand_depth(self):
        depth = 0
        base_command = self.base_command
        while base_command:
            depth += 1
            base_command = base_command.base_command
        return depth

    @cached_property
    def base_name(self):
        if self.is_subcommand:
            return self.name.split(':', self.subcommand_depth)[-1]
        return self.name

    @cached_property
    def prog_name(self):
        if self.is_subcommand:
            return ' '.join(self.name.split(':', self.subcommand_depth))
        return self.base_name

    def add_subcommand(self, subcommand):
        name = subcommand.base_name
        self.subcommands.append(subcommand)
        if not self.first_arg_has_choices:
            if self.first_arg.choices is None:
                self.first_arg.choices = []
            self.first_arg.choices.append(name)

    def get_description_from_docstring(self, implementation):
        description = implementation.__doc__
        if description is not None:
            description = description.strip() or None
        if description is not None:
            lines = description.splitlines()
            title = lines[0]
            if title.endswith('.'):
                title = title[:-1]
            lines = [title] + [line[4:] for line in lines[1:]]
            description = '\n'.join(lines)
        return description

    def run(self, argv=None, **overrides):
        if self.timed:
            start_time = time.monotonic()

        empty = Parameter.empty
        debug = self.debug
        positionals = self.positionals
        var_positional = self.var_positional
        default_args = self.default_args

        if argv is None:
            argv = sys.argv[1:]

        parsed_args = argv if isinstance(argv, dict) else self.parse_args(argv)

        args = []
        var_args = ()
        kwargs = parsed_args.copy()
        kwargs.update(overrides)

        if debug:
            # Names of all positional args.
            arg_names = []
            # Positional args passed via command line (name, value pairs).
            args_passed = []
            # Name of the var args arg.
            var_args_name = None
            # Positional args added from command's default args.
            from_default_args = {}
            # Positional args added from arg defaults.
            from_arg_defaults = {}

        # Map command line args to the command's parameters. Extract
        # positional args from the parsed args dict so they can be
        # passed positionally, using defaults for positionals that
        # weren't passed. Nothing special needs to be done for optional
        # args.
        for arg in positionals.values():
            name = arg.parameter.name
            value = kwargs.pop(name, POSITIONAL_PLACEHOLDER)
            if value is POSITIONAL_PLACEHOLDER:
                if name in default_args:
                    value = default_args[name]
                    if debug:
                        from_default_args[name] = value
                elif arg.default is not empty:
                    value = arg.default
                    if debug:
                        from_arg_defaults[name] = value
                else:
                    raise AssertionError('This should never happen')
            elif debug:
                args_passed.append((name, value))
            if debug:
                arg_names.append(name)
            args.append(value)

        if var_positional:
            var_args_name = var_positional.parameter.name
            if var_args_name in kwargs:
                var_args = kwargs.pop(var_args_name)
                if debug:
                    args_passed.append((var_args_name, var_args))

        if debug:
            printer.debug('Command called via command line:', self.name)
            printer.debug('    Parsed args:', parsed_args)
            printer.debug('    Overrides:', overrides)
            printer.debug('    Received positional args:', tuple(args_passed))
            printer.debug('    Received optional args:', kwargs)
            printer.debug('    Added positionals from default args:', ', '.join(from_default_args))
            printer.debug('    Added positionals from arg defaults:', ', '.join(from_arg_defaults))
            printer.debug('Running command via command line:', self.name)
            printer.debug('    Positional args:', tuple(zip(arg_names, args)))
            printer.debug('    Var args:', (var_args_name, var_args) if var_args else var_args)
            printer.debug('    Optional args:', kwargs)

        if var_args:
            args = tuple(args) + tuple(var_args)

        result = self(*args, **kwargs)

        if self.timed:
            self.print_elapsed_time(time.monotonic() - start_time)

        return result

    def console_script(self, argv=None, **overrides):
        debug = self.debug
        argv = sys.argv[1:] if argv is None else argv
        is_base_command = self.is_base_command

        if hasattr(self, 'sigint_handler'):
            signal.signal(signal.SIGINT, self.sigint_handler)

        if is_base_command:
            commands = self.partition_subcommands(argv)
        else:
            commands = [(self, argv)]

        for cmd, cmd_argv in commands:
            try:
                result = cmd.run(cmd_argv, **overrides)
            except RunCommandsError as result:
                if debug:
                    raise
                return_code = result.return_code if hasattr(result, 'return_code') else 1
                result_str = str(result)
                if result_str:
                    if return_code:
                        printer.error(result_str, file=sys.stderr)
                    else:
                        printer.print(result_str)
            else:
                return_code = result.return_code if hasattr(result, 'return_code') else 0

        return return_code

    def partition_subcommands(self, argv, base=True):
        debug = self.debug
        base_argv = []
        base_args = {}
        commands = [(self, base_args)]
        subcommand_map = {sub.name: sub for sub in self.subcommands}

        if debug:
            printer.debug('Parsing command for subcommands:', self.name)
            printer.debug('    argv:', argv)

        for i, arg in enumerate(argv):
            if arg.startswith(':'):
                base_argv.append(arg[1:])
            else:
                base_argv.append(arg)
                qualified_name = '{self.name}:{arg}'.format_map(locals())

                if qualified_name in subcommand_map:
                    subcmd = subcommand_map[qualified_name]
                    remaining_argv = argv[i + 1:]

                    if debug:
                        printer.debug('Found subcommand:', subcmd.name)
                        printer.debug('    Base argv:', base_argv)
                        printer.debug('    Remaining argv:', remaining_argv)

                    base_args.update(self.parse_args(base_argv))

                    if subcmd.is_base_command:
                        commands.extend(subcmd.partition_subcommands(remaining_argv, False))
                    else:
                        subcmd_args = subcmd.parse_args(remaining_argv)
                        commands.append([subcmd, subcmd_args])

                    break
        else:
            # No subcommand found
            if debug:
                printer.debug('Found command with no subcommand:', self.name)
                printer.debug('    argv:', base_argv)
            base_args.update(self.parse_args(base_argv))

        if base:
            # Pass base args down to subcommands. Each subcommand will
            # receive args from *all* preceding base commands.
            base_cmd, base_args = commands[0]
            base_args = base_args.copy()
            for i, (subcmd, subcmd_args) in enumerate(commands[1:], 1):
                for name, value in base_args.items():
                    if (
                        name not in subcmd_args and
                        base_cmd.args[name].is_optional and
                        subcmd.find_arg(name)
                    ):
                        subcmd_args[name] = value
                base_cmd = subcmd
                base_args.update(subcmd_args)
            if self.debug:
                printer.debug('Subcommands:')
                for cmd, cmd_argv in commands:
                    printer.debug('   ', cmd.name, cmd_argv)

        return commands

    def __call__(self, *passed_args, **passed_kwargs):
        empty = Parameter.empty
        debug = self.debug
        positionals = tuple(self.positionals.values())
        num_positionals = len(positionals)
        var_positional = self.var_positional
        default_args = self.default_args

        num_passed_args = len(passed_args)
        args = []
        var_args = ()
        kwargs = passed_kwargs.copy()

        if debug:
            # Positional args passed (name, value pairs).
            args_passed = []
            # Name of the var args arg.
            var_args_name = None
            # Args added from command's default args.
            from_default_args = {}
            # Args added from arg defaults.
            from_arg_defaults = {}

        # The N passed positional args are mapped to the first N
        # positional parameters.
        for arg, value in zip(positionals, passed_args):
            name = arg.parameter.name
            args.append((name, value))
            if debug:
                args_passed.append((name, value))

        # Use defaults for positionals that weren't passed. This is done
        # here instead of below with the optionals so they'll be passed
        # positionally.
        for arg in positionals[len(args):]:
            name = arg.parameter.name
            if name in default_args:
                value = default_args[name]
                args.append((name, value))
                if debug:
                    from_default_args[name] = value
            elif arg.default is not empty:
                value = arg.default
                args.append((name, value))
                if debug:
                    from_arg_defaults[name] = value

        # If the command has var args, it consumes any remaining passed
        # positional args.
        if var_positional:
            var_args_name = var_positional.parameter.name
            var_args = passed_args[len(args):]
            if var_args:
                if debug:
                    args_passed.append((var_args_name, var_args))
            elif var_args_name in default_args:
                var_args = default_args[var_args_name]
            elif var_positional.default is not empty:
                var_args = var_positional.default

        # Otherwise, the remaining N passed positionals args correspond
        # to the first N optionals.
        elif num_passed_args > num_positionals:
            for arg, value in zip(self.optionals.values(), passed_args[num_positionals:]):
                name = arg.name
                args.append((name, value))
                if debug:
                    args_passed.append((name, value))

        # Use defaults for any optionals that weren't passed that have a
        # default. Positionals that weren't passed have already had
        # their defaults set above.
        arg_names = tuple(item[0] for item in args)
        get_from_default_args = set(default_args).difference(arg_names, passed_kwargs)
        for name in get_from_default_args:
            value = default_args[name]
            kwargs[name] = value
            if debug:
                from_default_args[name] = value

        if debug:
            var_args_display = (var_args_name, tuple(var_args)) if var_args else ()
            printer.debug('Command called:', self.name)
            printer.debug('    Received positional args:', args_passed)
            printer.debug('    Received keyword args:', passed_kwargs)
            printer.debug('    Added from default args:', from_default_args)
            printer.debug('    Added from arg defaults:', from_arg_defaults)
            printer.debug('Running command:', self.name)
            printer.debug('    Positional args:', args)
            printer.debug('    Var args:', var_args_display)
            printer.debug('    Keyword args:', kwargs)

        args = tuple(item[1] for item in args)

        if var_args:
            args = args + tuple(var_args)

        return self.implementation(*args, **kwargs)

    def parse_args(self, argv, expand_short_options=True):
        if self.debug:
            printer.debug('Parsing args for command `{self.name}`: {argv}'.format_map(locals()))
        if expand_short_options:
            argv = self.expand_short_options(argv)
        parsed_args = self.arg_parser.parse_args(argv)
        parsed_args = vars(parsed_args)
        for k, v in parsed_args.items():
            if v == '':
                parsed_args[k] = None
        return parsed_args

    def parse_optional(self, string):
        """Parse string into name, option, and value (if possible).

        If the string is a known option name, the string, the
        corresponding option, and ``None`` will be returned.

        If the string has the form ``--option=<value>`` or
        ``-o=<value>``, it will be split on equals into an option name
        and value. If the option name is known, the option name, the
        corresponding option, and the value will be returned.

        In all other cases, ``None`` will be returned to indicate that
        the string doesn't correspond to a known option.

        """
        option_map = self.option_map
        if string in option_map:
            return string, option_map[string], None
        if '=' in string:
            name, value = string.split('=', 1)
            if name in option_map:
                return name, option_map[name], value
        return None

    def expand_short_options(self, argv):
        """Convert grouped short options like `-abc` to `-a, -b, -c`.

        This is necessary because we set ``allow_abbrev=False`` on the
        ``ArgumentParser`` in :attr:`self.arg_parser`. The argparse docs
        say ``allow_abbrev`` applies only to long options, but it also
        affects whether short options grouped behind a single dash will
        be parsed into multiple short options.

        See :meth:`parse_multi_short_option` for details on how multi
        short options are parsed.

        Returns:
            list: Original argv if no multi short options found
            list: Expanded argv if multi short options found

        """
        if self.debug:
            printer.debug('Expanding short options for `{self.name}`: {argv}'.format_map(locals()))
        has_multi_short_options = False
        parse_multi_short_option = self.parse_multi_short_option
        new_argv = []
        for i, arg in enumerate(argv):
            if arg == '--':
                new_argv.extend(argv[i:])
                break
            short_options, value = parse_multi_short_option(arg)
            if short_options:
                new_argv.extend(short_options)
                if value is not None:
                    new_argv.append(value)
                has_multi_short_options = True
            else:
                new_argv.append(arg)
        if self.debug and not has_multi_short_options:
            printer.debug('No multi short options found')
        return new_argv if has_multi_short_options else argv

    def parse_multi_short_option(self, arg):
        """Parse args like '-xyz' into ['-x', '-y', '-z'].

        Examples::

            'abc' -> None, None                   # not an option
            '--option' -> None, None              # long option
            '-a' -> None, None                    # short option but not multi
            '-xyz' -> ['-x', '-y', '-z'], None    # multi short option
            '-xyz12' -> ['-x', '-y', '-z'], '12'  # multi short option w/ value

        Note that parsing stops when a short option that takes a value
        is encountered--the rest of the arg string is considered the
        value for that option.

        Returns:
            (None, None): The arg is not a multi short option
            (list, str|None): The arg is a multi short option (perhaps
                including a value for the last option)

        """
        if len(arg) < 3 or arg[0] != '-' or arg[1] == '-' or arg[2] == '=':
            # Not a multi short option like '-abc'.
            return None, None
        # Appears to be a multi short option.
        option_map = self.option_map
        short_options = []
        value = None
        for i, char in enumerate(arg[1:], 1):
            name = '-{char}'.format(char=char)
            short_options.append(name)
            option = option_map.get(name)
            if option is not None and option.takes_value:
                j = i + 1
                if j < len(arg):
                    value = arg[j:]
                break
        if self.debug and short_options:
            printer.debug('Parsed multi short option:', arg, '=>', short_options)
        return short_options, value

    @staticmethod
    def normalize_name(name):
        # Chomp a single trailing underscore *if* the name ends with
        # just one trailing underscore. This accommodates the convention
        # of adding a trailing underscore to reserved/built-in names.
        if name.endswith('_'):
            if name[-2] != '_':
                name = name[:-1]
        name = name.replace('_', '-')
        return name

    @staticmethod
    def normalize_class_name(name):
        name = camel_to_underscore(name)
        name = name.replace('_', '-')
        name = name.lower()
        return name

    def find_arg(self, name):
        """Find arg by normalized arg name or parameter name."""
        name = self.normalize_name(name)
        return self.args.get(name)

    def find_parameter(self, name):
        """Find parameter by name or normalized arg name."""
        name = self.normalize_name(name)
        arg = self.args.get(name)
        return None if arg is None else arg.parameter

    def get_arg_config(self, param):
        annotation = param.annotation
        if annotation is param.empty:
            annotation = self.arg_config.get(param.name) or ArgConfig()
        elif isinstance(annotation, type):
            annotation = ArgConfig(type=annotation)
        elif isinstance(annotation, str):
            annotation = ArgConfig(help=annotation)
        elif isinstance(annotation, Mapping):
            annotation = ArgConfig(**annotation)
        return annotation

    def get_short_option_for_arg(self, name, used):
        first_char = name[0]
        first_char_upper = first_char.upper()

        if name == 'help':
            candidates = (first_char,)
        elif name.startswith('h'):
            candidates = (first_char_upper,)
        else:
            candidates = (first_char, first_char_upper)

        for char in candidates:
            short_option = '-{char}'.format_map(locals())
            if short_option not in used:
                return short_option

    def get_long_option_for_arg(self, name):
        return '--{name}'.format_map(locals())

    def get_inverse_short_option_for_arg(self, short_option, used):
        inverse_short_option = short_option.upper()
        if inverse_short_option not in used:
            return inverse_short_option

    def get_inverse_long_option_for_arg(self, long_option):
        if long_option == '--yes':
            return '--no'
        if long_option == '--no':
            return '--yes'
        if long_option.startswith('--no-'):
            return long_option.replace('--no-', '--', 1)
        if long_option.startswith('--is-'):
            return long_option.replace('--is-', '--not-', 1)
        if long_option.startswith('--with-'):
            return long_option.replace('--with-', '--without-', 1)
        return long_option.replace('--', '--no-', 1)

    def print_elapsed_time(self, elapsed_time):
        m, s = divmod(elapsed_time, 60)
        m = int(m)
        hr = get_hr()
        msg = '{hr}\nElapsed time for {self.name} command: {m:d}m {s:.3f}s\n{hr}'
        msg = msg.format_map(locals())
        printer.info(msg)

    @cached_property
    def parameters(self):
        implementation = self.implementation
        signature = inspect.signature(implementation)
        return signature.parameters

    @cached_property
    def has_kwargs(self):
        return any(p.kind is p.VAR_KEYWORD for p in self.parameters.values())

    @cached_property
    def args(self):
        """Create args from function parameters."""
        params = self.parameters
        args = OrderedDict()

        empty = Parameter.empty
        keyword_only = Parameter.KEYWORD_ONLY
        var_keyword = Parameter.VAR_KEYWORD
        var_positional = Parameter.VAR_POSITIONAL

        normalize_name = self.normalize_name
        get_arg_config = self.get_arg_config
        get_short_option = self.get_short_option_for_arg
        get_long_option = self.get_long_option_for_arg
        get_inverse_short_option = self.get_inverse_short_option_for_arg
        get_inverse_long_option = self.get_inverse_long_option_for_arg

        params = OrderedDict((
            (normalize_name(n), p)
            for n, p in params.items()
            if not (
                (n.startswith('_')) or
                (p.kind is keyword_only and p.default is empty) or
                (p.kind is var_keyword)
            )
        ))

        used_short_options = set()
        for param in params.values():
            annotation = get_arg_config(param)
            short_option = annotation.short_option
            if short_option:
                used_short_options.add(short_option)

        for name, param in params.items():
            annotation = get_arg_config(param)
            container = annotation.container
            type = annotation.type
            choices = annotation.choices
            help = annotation.help
            inverse_help = annotation.inverse_help
            short_option = annotation.short_option
            long_option = annotation.long_option
            no_inverse = annotation.no_inverse
            inverse_short_option = annotation.inverse_short_option
            inverse_long_option = annotation.inverse_long_option
            action = annotation.action
            nargs = annotation.nargs
            mutual_exclusion_group = annotation.mutual_exclusion_group

            default = param.default
            is_var_positional = param.kind is var_positional
            is_positional = default is empty and not is_var_positional

            if annotation.default is not empty:
                if is_positional or is_var_positional:
                    default = annotation.default
                else:
                    message = (
                        'Got default for `{self.name}` command\'s optional arg `{name}` via '
                        'arg annotation. Optional args must specify their defaults via keyword '
                        'arg values.'
                    ).format_map(locals())
                    raise CommandError(message)

            if not (is_positional or is_var_positional):
                if not short_option:
                    short_option = get_short_option(name, used_short_options)
                    used_short_options.add(short_option)
                if not long_option:
                    long_option = get_long_option(name)
                if not no_inverse:
                    if short_option and not inverse_short_option:
                        inverse_short_option = get_inverse_short_option(
                            short_option,
                            used_short_options,
                        )
                        used_short_options.add(inverse_short_option)
                    if not inverse_long_option:
                        inverse_long_option = get_inverse_long_option(long_option)

            args[name] = Arg(
                command=self,
                parameter=param,
                name=name,
                container=container,
                type=type,
                positional=is_positional,
                default=default,
                choices=choices,
                help=help,
                inverse_help=inverse_help,
                short_option=short_option,
                long_option=long_option,
                no_inverse=no_inverse,
                inverse_short_option=inverse_short_option,
                inverse_long_option=inverse_long_option,
                action=action,
                nargs=nargs,
                mutual_exclusion_group=mutual_exclusion_group,
            )

        if 'help' not in args:
            args['help'] = HelpArg(command=self)

        option_map = OrderedDict()
        for arg in args.values():
            for option in arg.options:
                option_map.setdefault(option, [])
                option_map[option].append(arg)

        for option, option_args in option_map.items():
            if len(option_args) > 1:
                names = ', '.join(a.parameter.name for a in option_args)
                message = (
                    'Option {option} of command {self.name} maps to multiple parameters: {names}')
                message = message.format_map(locals())
                raise CommandError(message)

        return args

    @cached_property
    def arg_parser(self):
        use_default_help = isinstance(self.args['help'], HelpArg)

        parser = argparse.ArgumentParser(
            prog=self.prog_name,
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            argument_default=argparse.SUPPRESS,
            add_help=use_default_help,
            allow_abbrev=False,  # See note in `self.parse_args()`
        )

        default_args = self.default_args

        for name, arg in self.args.items():
            if name == 'help' and use_default_help:
                continue

            param = arg.parameter
            options, kwargs = arg.add_argument_args

            if arg.is_positional and param.name in default_args:
                # Positionals are made optional if a default value is
                # specified via config.
                options = (self.get_long_option_for_arg(arg.name),)

            mutual_exclusion_group_name = arg.mutual_exclusion_group
            if mutual_exclusion_group_name:
                if mutual_exclusion_group_name not in self.mutual_exclusion_groups:
                    self.mutual_exclusion_groups[mutual_exclusion_group_name] = \
                        parser.add_mutually_exclusive_group()
                mutual_exclusion_group = self.mutual_exclusion_groups[mutual_exclusion_group_name]
                mutual_exclusion_group.add_argument(*options, **kwargs)
            else:
                parser.add_argument(*options, **kwargs)

            inverse_args = arg.add_argument_inverse_args
            if inverse_args is not None:
                options, kwargs = inverse_args
                parser.add_argument(*options, **kwargs)

        return parser

    @cached_property
    def positionals(self):
        args = self.args.items()
        return OrderedDict((name, arg) for (name, arg) in args if arg.is_positional)

    @cached_property
    def var_positional(self):
        args = self.args.items()
        for name, arg in args:
            if arg.is_var_positional:
                return arg
        return None

    @cached_property
    def optionals(self):
        args = self.args.items()
        return OrderedDict((name, arg) for (name, arg) in args if arg.is_optional)

    @cached_property
    def option_map(self):
        """Map command-line options to args."""
        option_map = OrderedDict()
        for arg in self.args.values():
            for option in arg.options:
                option_map[option] = arg
        return option_map

    @property
    def help(self):
        help_ = self.arg_parser.format_help()
        help_ = help_.split(': ', 1)[1]
        help_ = help_.strip()
        return help_

    @property
    def usage(self):
        usage = self.arg_parser.format_usage()
        usage = usage.split(': ', 1)[1]
        usage = usage.strip()
        return usage

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.usage

    def __repr__(self):
        return 'Command(name={self.name})'.format(self=self)


def command(name=None, description=None, base_command=None, timed=False, cls=Command):
    args = dict(description=description, base_command=base_command, timed=timed)

    if isinstance(name, type):
        # Bare class decorator
        name.implementation.__name__ = camel_to_underscore(name.__name__)
        return name(**args)

    if callable(name):
        # Bare function decorator
        return cls(implementation=name, **args)

    def wrapper(wrapped):
        if isinstance(wrapped, type):
            wrapped.implementation.__name__ = camel_to_underscore(wrapped.__name__)
            return wrapped(name=name, **args)
        return cls(implementation=wrapped, name=name, **args)

    return wrapper


def subcommand(base_command, name=None, description=None, timed=False, cls=Command):
    return command(name, description, base_command, timed, cls)
