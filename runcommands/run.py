import ast
import os
import sys
import yaml

from jinja2 import Environment as TemplateEnvironment, TemplateRuntimeError

from . import __version__
from .args import arg, NestedDictAddAction
from .command import Command
from .collection import Collection
from .const import DEFAULT_COMMANDS_MODULE
from .exc import RunnerError
from .runner import CommandRunner
from .util import abs_path, merge_dicts, printer


class Run(Command):

    name = 'runcommands'

    allowed_config_file_args = (
        'defaults',
        'globals_',
        'env',
        'version',
        'environ',
        'default_args',
    )

    raise_on_error = True

    def implementation(self,
                       commands_module: arg(short_option='-m') = DEFAULT_COMMANDS_MODULE,
                       config_file: arg(short_option='-f') = None,
                       # Variables
                       defaults: arg(
                           type=dict,
                           short_option='-s',
                           long_option='--set',
                           action=NestedDictAddAction,
                           help='Default variables; will be injected into itself, globals, '
                                'default args, and environment variables'
                       ) = None,
                       globals_: arg(
                           type=dict,
                           action=NestedDictAddAction,
                           help='Global variables & default args for *all* commands; will be '
                                'injected into itself, default args, and environment variables '
                                '(higher precedence than defaults and keyword args)'
                       ) = None,
                       # Special variables
                       env: arg(help='Will be added to globals') = None,
                       version: arg(help='Will be added to globals') = None,
                       echo: arg(type=bool, help='Will be added to globals') = None,
                       # Environment variables
                       environ: arg(
                           type=dict,
                           help='Additional environment variables; '
                                'added just before commands are run',
                       ) = None,
                       # Meta
                       info: arg(help='Show info and exit') = False,
                       list_commands: arg(help='Show info & commands and exit') = False,
                       debug: arg(
                           type=bool,
                           help='Print debugging info & re-raise exceptions; also added to globals'
                       ) = None,
                       *,
                       all_argv=(),
                       run_argv=(),
                       command_argv=(),
                       cli_args=None):
        """Run one or more commands in succession.

        For example, assume the commands ``local`` and ``remote`` have been
        defined; the following will run ``ls`` first on the local host and
        then on the remote host::

            runcommands local ls remote <host> ls

        When a command name is encountered in ``argv``, it will be considered
        the starting point of the next command *unless* the previous item in
        ``argv`` was an option like ``--xyz`` that expects a value (i.e.,
        it's not a flag).

        To avoid ambiguity when an option value matches a command name, the
        value can be prepended with a colon to force it to be considered
        a value and not a command name.

        """
        self.raise_on_error = bool(debug)

        collection = Collection.load_from_module(commands_module)
        config_file = self.find_config_file(config_file)
        defaults = defaults or {}
        globals_ = globals_ or {}
        environ = environ or {}
        cli_args = cli_args or {}

        if env or version or echo is not None or debug is not None:
            cli_args.setdefault('globals_', globals_)
            if env:
                globals_['env'] = env
            if version:
                globals_['version'] = version
            if echo is not None:
                globals_['echo'] = echo
            if debug is not None:
                globals_['debug'] = debug

        if config_file:
            args = {k: v for (k, v) in locals().copy().items() if k in cli_args}
            args_from_file = self.read_config_file(config_file, collection)
            args = merge_dicts(args_from_file, args)

            defaults = args.get('defaults', defaults)
            globals_ = args.get('globals_', globals_)
            env = args.get('env', env)
            version = args.get('version', version)
            echo = args.get('echo', version)
            environ = args.get('environ', environ)
            debug = args.get('debug', debug)

            default_args = {name: {} for name in collection}
            default_args = merge_dicts(default_args, args_from_file.get('default_args') or {})

            for command_name, command_default_args in default_args.items():
                command = collection[command_name]
                for name, value in globals_.items():
                    param = command.find_parameter(name)
                    if param is not None:
                        if param.name not in command_default_args:
                            command_default_args[param.name] = value
                    elif command.has_kwargs:
                        name = name.replace('-', '_')
                        command_default_args[name] = value

            default_args = {name: args for name, args in default_args.items() if args}
        else:
            default_args = {}

        show_info = info or list_commands or not command_argv or debug
        print_and_exit = info or list_commands

        results = self.interpolate(defaults, globals_, default_args, environ)
        defaults, globals_, default_args, environ = results

        if show_info:
            print('RunCommands', __version__)

        if debug:
            print()
            printer.debug('Commands module:', commands_module)
            printer.debug('Config file:', config_file)
            printer.debug('All args:', all_argv)
            printer.debug('Run args:', run_argv)
            printer.debug('Command args:', command_argv)
            items = (
                ('Defaults:', defaults),
                ('Globals:', globals_),
                ('Default args:', default_args),
                ('Environment variables:', environ),
            )
            for label, data in items:
                if data:
                    printer.debug(label)
                    for k in sorted(data):
                        v = data[k]
                        printer.debug('  - {k} = {v!r}'.format_map(locals()))

        if environ:
            os.environ.update(environ)

        collection.set_attrs(debug=debug)
        collection.set_default_args(default_args)
        runner = CommandRunner(collection, debug)

        if print_and_exit:
            if list_commands:
                runner.print_usage()
        elif not command_argv:
            printer.warning('\nNo command(s) specified')
            runner.print_usage()
        else:
            runner.run(command_argv)

    def run(self, argv, **kwargs):
        all_argv, run_argv, command_argv = self.partition_argv(argv)
        cli_args = self.parse_args(run_argv)
        kwargs.update({
            'all_argv': all_argv,
            'run_argv': run_argv,
            'command_argv': command_argv,
            'cli_args': cli_args,
        })
        return super().run(run_argv, **kwargs)

    def partition_argv(self, argv=None):
        if argv is None:
            argv = sys.argv[1:]

        if not argv:
            return argv, [], []

        if '--' in argv:
            i = argv.index('--')
            return argv, argv[:i], argv[i + 1:]

        run_argv = []
        option = None
        option_map = self.option_map
        parser = self.arg_parser
        parse_optional = parser._parse_optional

        for i, a in enumerate(argv):
            option_data = parse_optional(a)
            if option_data is not None:
                # Arg looks like an option (according to argparse).
                action, name, value = option_data
                if name not in option_map:
                    # Unknown option.
                    break
                run_argv.append(a)
                if value is None:
                    # The option's value will be expected on the next pass.
                    option = option_map[name]
                else:
                    # A value was supplied with -nVALUE, -n=VALUE, or
                    # --name=VALUE.
                    option = None
            elif option is not None:
                choices = action.choices or ()
                if option.takes_value:
                    run_argv.append(a)
                    option = None
                elif a in choices or hasattr(choices, a):
                    run_argv.append(a)
                    option = None
                else:
                    # Unexpected option value
                    break
            else:
                # The first arg doesn't look like an option (it's probably
                # a command name).
                break
        else:
            # All args were consumed by run command; none remain.
            i += 1

        remaining = argv[i:]

        return argv, run_argv, remaining

    def find_config_file(self, config_file):
        if config_file:
            config_file = abs_path(config_file)
        elif os.path.exists('commands.yaml'):
            config_file = abs_path('commands.yaml')
        return config_file

    def read_config_file(self, config_file, collection):
        return self._read_config_file(config_file, collection)

    def _read_config_file(self, config_file, collection):
        with open(config_file) as fp:
            args = yaml.load(fp) or {}

        extends = args.pop('extends', None)
        default_args = args.pop('default_args', args.pop('default-args', None)) or {}

        for name in tuple(args):
            parameter = self.find_parameter(name)
            if parameter is None:
                raise RunnerError(
                    'Unknown arg specified in config file {config_file}: {name}'
                    .format_map(locals()))
            if parameter.name not in self.allowed_config_file_args:
                raise RunnerError(
                    'Arg cannot be specified in config file: {name}'
                    .format_map(locals()))
            if parameter.name != name:
                args[parameter.name] = args.pop(name)

        for command_name in tuple(default_args):
            try:
                command = collection[command_name]
            except KeyError:
                raise RunnerError(
                    'Unknown command in default args section of {config_file}: {command_name}'
                    .format_map(locals()))
            if command.name != command_name:
                default_args[command.name] = default_args.pop(command_name)

        if default_args:
            args['default_args'] = default_args

        if extends:
            extends = abs_path(extends, relative_to=os.path.dirname(config_file))
            extended_args = self._read_config_file(extends, collection)
            args = merge_dicts(extended_args, args)

        return args

    def interpolate(self, defaults, globals_, default_args, environ):
        environment = TemplateEnvironment()
        environment.globals = defaults

        if defaults:
            defaults = self._interpolate(environment, defaults)

        if globals_:
            globals_ = self._interpolate(environment, globals_, globals_)
            # HACK: Covers the case where a global value refers to an
            #       item that's in both defaults and globals.
            globals_ = self._interpolate(environment, globals_)

        if default_args:
            context = merge_dicts(globals_, default_args)
            default_args = self._interpolate(environment, default_args, context)

        if environ:
            environ = self._interpolate(environment, environ, globals_)

        return defaults, globals_, default_args, environ

    def _interpolate(self, environment, obj, context=None):
        context = context or {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self._interpolate(environment, v, context)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                obj[i] = self._interpolate(environment, v, context)
        elif isinstance(obj, str):
            while True:
                if '{{' not in obj:
                    break
                original_obj = obj
                template = environment.from_string(obj)
                try:
                    obj = template.render(context)
                except TemplateRuntimeError as exc:
                    raise RunnerError(
                        'Could not render template {obj!r} with context {context!r}: {exc}'
                        .format_map(locals()))
                if obj == original_obj:
                    break
            try:
                obj = ast.literal_eval(obj)
            except (SyntaxError, ValueError):
                pass
        return obj

    def sigint_handler(self, _sig_num, _frame):
        printer.warning('Aborted')
        sys.exit(0)


run = Run()
