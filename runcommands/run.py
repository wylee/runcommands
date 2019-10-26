import ast
import os
import sys
import yaml

from jinja2 import Environment as TemplateEnvironment, TemplateRuntimeError

from . import __version__
from .args import arg, json_value
from .command import Command
from .collection import Collection
from .const import DEFAULT_COMMANDS_MODULE
from .exc import RunnerError
from .runner import CommandRunner
from .util import abs_path, merge_dicts, printer


class Run(Command):

    name = 'runcommands'

    allowed_config_file_args = (
        'globals',
        'envs',
        'args',
        'environ',
    )

    def implementation(self,
                       commands_module: arg(short_option='-m') = DEFAULT_COMMANDS_MODULE,
                       config_file: arg(short_option='-f') = None,
                       # Globals
                       globals_: arg(
                           container=dict,
                           type=json_value,
                           help='Global variables & default args for *all* commands; will be '
                                'injected into itself, default args, and environment variables '
                                '(higher precedence than keyword args)'
                       ) = None,
                       # Special globals (for command line convenience)
                       env: arg(help='env will be added to globals if specified') = None,
                       version: arg(help='version will be added to globals if specified') = None,
                       echo: arg(
                           type=bool,
                           help='echo=True will be added to globals',
                           inverse_help='echo=False will be added to globals'
                       ) = None,
                       # Environment variables
                       environ: arg(
                           container=dict,
                           help='Additional environment variables; '
                                'added just before commands are run'
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
                       cli_args=()):
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
        collection = Collection.load_from_module(commands_module)
        config_file = self.find_config_file(config_file)
        cli_globals = globals_ or {}

        if env:
            cli_globals['env'] = env
        if version:
            cli_globals['version'] = version
        if echo is not None:
            cli_globals['echo'] = echo
        if debug is not None:
            cli_globals['debug'] = debug

        if config_file:
            args_from_file = self.read_config_file(config_file, collection)
            args = merge_dicts(args_from_file, {'environ': environ or {}})

            config_file_globals = args['globals']

            env = cli_globals.get('env') or config_file_globals.get('env')
            if env:
                envs = args['envs']
                try:
                    env_globals = envs[env]
                except KeyError:
                    raise RunnerError('Unknown env: {env}'.format_map(locals()))

                # Don't add env's default args to globals, but save them
                # so they they can be included in the global envs dict
                # (for inspection purposes).
                env_default_args = env_globals.pop('args')

                globals_ = merge_dicts(config_file_globals, env_globals, cli_globals)
                globals_['envs'] = envs

                env_globals['args'] = env_default_args
            else:
                env_default_args = {}
                globals_ = merge_dicts(config_file_globals, cli_globals)

            default_args = {name: {} for name in collection}
            default_args = merge_dicts(default_args, args['args'], env_default_args)

            for command_name, command_default_args in default_args.items():
                command = collection[command_name]

                # Normalize arg names from default args section.
                for name in tuple(command_default_args):
                    param = command.find_parameter(name)
                    if param is None:
                        raise RunnerError(
                            'Unknown arg for command {command_name} in default args section of '
                            '{config_file}: {name}'
                            .format_map(locals()))
                    if param is not None and name != param.name:
                        command_default_args[param.name] = command_default_args.pop(name)

                # Add globals that correspond to this command (that
                # aren't present in default args section).
                for name, value in globals_.items():
                    param = command.find_parameter(name)
                    if param is not None:
                        if param.name not in command_default_args:
                            command_default_args[param.name] = value
                    elif command.has_kwargs:
                        name = name.replace('-', '_')
                        command_default_args[name] = value

                # Convert lists to tuples for the command's args that are
                # specified as being tuples.
                for name, value in command_default_args.items():
                    command_arg = command.find_arg(name)
                    if command_arg.container and isinstance(value, list):
                        command_default_args[name] = command_arg.container(value)

            default_args = {name: args for name, args in default_args.items() if args}

            environ = args['environ']
        else:
            globals_ = cli_globals
            default_args = {}
            environ = environ or {}

        debug = globals_.get('debug', False)
        show_info = info or list_commands or not command_argv or debug
        print_and_exit = info or list_commands

        globals_, default_args, environ = self.interpolate(globals_, default_args, environ)

        if show_info:
            print('RunCommands', __version__)

        if debug:
            printer.debug('Commands module:', commands_module)
            printer.debug('Config file:', config_file)
            printer.debug('All args:', all_argv)
            printer.debug('Run args:', run_argv)
            printer.debug('Command args:', command_argv)
            items = (
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
        if '-d' in run_argv or '--debug' in run_argv:
            self.debug = True
        cli_args = tuple(self.parse_args(run_argv))
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

        argv = self.expand_short_options(argv)
        argc = len(argv)
        run_argv = []
        parse_optional = self.parse_optional

        i = 0
        while i < argc:
            a = argv[i]

            if a == '--':
                # Explicit end of run args.
                i += 1
                break

            option_data = parse_optional(a)

            if option_data is not None:
                # Arg is a known run option.
                name, option, value = option_data
                run_argv.append(a)

                if value is None and option.takes_value:
                    # Collect the option's value if it takes one and one
                    # wasn't provided via --opt=<value>.
                    j = i + 1
                    if j < argc:
                        run_argv.append(argv[j])
                        i = j
            else:
                # Arg is not an option.
                break

            i += 1

        return argv, run_argv, argv[i:]

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
            args = yaml.load(fp, Loader=yaml.FullLoader) or {}

        for name in self.allowed_config_file_args:
            # Not present or present but not set
            if args.get(name) is None:
                args[name] = {}

        extends = args.pop('extends', None)

        for name in tuple(args):
            if name not in self.allowed_config_file_args:
                raise RunnerError(
                    'Arg cannot be specified in config file: {name}'
                    .format_map(locals()))

        envs = args['envs']
        for env, data in envs.items():
            if data is None:
                data = {}
                envs[env] = data
            data.setdefault('args', {})

        default_args = args.pop('args')

        for command_name in tuple(default_args):
            try:
                command = collection[command_name]
            except KeyError:
                raise RunnerError(
                    'Unknown command in default args section of {config_file}: {command_name}'
                    .format_map(locals()))
            if command.name != command_name:
                default_args[command.name] = default_args.pop(command_name)

        args['args'] = default_args

        if extends:
            extends = abs_path(extends, relative_to=os.path.dirname(config_file))
            extended_args = self._read_config_file(extends, collection)
            args = merge_dicts(extended_args, args)

        return args

    def interpolate(self, globals_, default_args, environ):
        environment = TemplateEnvironment()

        if globals_:
            globals_ = self._interpolate(environment, globals_, globals_)

        if default_args:
            context = merge_dicts(globals_, default_args)
            default_args = self._interpolate(environment, default_args, context)

        if environ:
            environ = self._interpolate(environment, environ, globals_)

        return globals_, default_args, environ

    def _interpolate(self, environment, obj, context):
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = self._interpolate(environment, v, context)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                obj[i] = self._interpolate(environment, v, context)
        elif isinstance(obj, tuple):
            obj = tuple(self._interpolate(environment, v, context) for v in obj)
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
                        .format(exc=exc))
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
