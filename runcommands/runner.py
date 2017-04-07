import os
import textwrap
from importlib import import_module
from importlib.machinery import SourceFileLoader
from itertools import chain
from shutil import get_terminal_size

from . import __version__
from .command import Command
from .config import Config, RawConfig
from .exc import RunnerError
from .util import abs_path, printer


DEFAULT_COMMANDS_MODULE = 'commands.py'
DEFAULT_CONFIG_FILE = 'commands.cfg'


def run(args,
        module=DEFAULT_COMMANDS_MODULE,
        # config
        config_file=None,
        env=None,
        # options
        options={},
        version=None,
        # output
        echo=False,
        hide=False,
        debug=False,
        # info/help
        info=False,
        list_commands=False,
        list_envs=False,
        # completion
        complete=False,
        words=(),
        word_index=0):
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
    argv, run_argv, command_argv, run_args = args

    show_info = info or list_commands or list_envs or not command_argv or debug
    print_and_exit = info or list_commands or list_envs

    if show_info:
        print('RunCommands', __version__)

    if debug:
        printer.debug('All args:', argv)
        printer.debug('Run args:', run_argv)
        printer.debug('Command args:', command_argv)
        echo = True

    if config_file is None:
        if os.path.isfile(DEFAULT_CONFIG_FILE):
            config_file = DEFAULT_CONFIG_FILE

    options = options.copy()

    for name, value in options.items():
        if name in run_command.optionals:
            raise RunnerError(
                'Cannot pass {name} via --option; use --{option_name} instead'
                .format(name=name, option_name=name.replace('_', '-')))

    if version is not None:
        options['version'] = version

    runner = CommandRunner(
        module,
        config_file=config_file,
        env=env,
        options=options,
        echo=echo,
        hide=hide,
        debug=debug,
    )

    if complete:
        runner.complete(words=words, index=word_index)
    elif print_and_exit:
        if list_envs:
            runner.print_envs()
        if list_commands:
            runner.print_usage()
    elif not command_argv:
        printer.warning('\nNo command(s) specified')
        runner.print_usage()
    else:
        runner.run(command_argv, run_args)


run_command = Command(run)


class CommandRunner:

    def __init__(self, commands_module, config_file=None, env=None, options=None, echo=False,
                 hide=False, debug=False):
        self.commands_module = commands_module
        self.commands = self.load_commands_from_module(commands_module)

        # Defaults
        self.config_file = config_file
        self.env = env
        self.options = options if options is not None else {}
        self.echo = echo
        self.hide = hide
        self.debug = debug

    def load_commands_from_module(self, commands_module):
        raise_does_not_exist = False

        if commands_module.endswith('.py'):
            commands_module = abs_path(commands_module)
            if not os.path.isfile(commands_module):
                raise_does_not_exist = True
                does_not_exist_message = 'Commands file does not exist: {commands_module}'
            else:
                module_loader = SourceFileLoader('commands', commands_module)
                module = module_loader.load_module()
        else:
            try:
                module = import_module(commands_module)
            except ImportError:
                raise_does_not_exist = True
                does_not_exist_message = 'Commands module could not be imported: {commands_module}'

        if raise_does_not_exist:
            raise RunnerError(does_not_exist_message.format_map(locals()))

        objects = vars(module).values()
        commands = {obj.name: obj for obj in objects if isinstance(obj, Command)}
        return commands

    def run(self, argv, run_args):
        results = []
        commands_to_run = self.get_commands_to_run(self.commands, argv, run_args)

        if self.debug:
            for command in commands_to_run:
                self.print_debug('Command to run:', command)

        for command in commands_to_run:
            result = command.run()
            results.append(result)

        return results

    def get_commands_to_run(self, commands, argv, run_args):
        commands_to_run = []
        while argv:
            command, command_argv = self.partition_args(commands, argv)

            if command.name in run_args:
                command_run_args = run_args[command.name]
                config_file = command_run_args.get('config_file', self.config_file)
                env = command_run_args.get('env', self.env)
                echo = command_run_args.get('echo', self.echo)
                hide = command_run_args.get('hide', self.hide)
                debug = command_run_args.get('debug', self.debug)
                options = command_run_args.get('options', self.options)
            else:
                config_file = self.config_file
                env = self.env
                echo = self.echo
                hide = self.hide
                debug = self.debug
                options = self.options

            config = Config(
                commands_module=self.commands_module,
                config_file=config_file,
                env=command.get_run_env(env),
                run=RawConfig(echo=echo, hide=hide),
                debug=debug,
                _overrides=options,
            )

            commands_to_run.append(CommandToRun(command, config, command_argv))
            num_consumed = len(command_argv) + 1
            argv = argv[num_consumed:]

        return commands_to_run

    def partition_args(self, all_commands, args):
        name = args[0]

        try:
            command = all_commands[name]
        except KeyError:
            raise RunnerError('Unknown command: {name}'.format(name=name))

        args = args[1:]
        command_args = []
        partition = [command, command_args]

        prev_args = chain([None], args[:-1])
        next_args = chain(args[1:], [None])

        for prev_arg, arg, next_arg in zip(prev_args, args, next_args):
            if arg in all_commands:
                option = command.arg_map.get(prev_arg)
                if option is None or not option.takes_value:
                    break
            if arg.startswith(':') and arg != ':':
                arg = arg[1:]
            command_args.append(arg)

        return partition

    def print_debug(self, *args, **kwargs):
        if self.debug:
            printer.debug(*args, **kwargs)

    def print_envs(self):
        envs = RawConfig._get_envs(self.config_file)
        if not envs:
            printer.warning('No envs available')
            return
        print('\nAvailable envs:\n')
        print(self.fill(envs))

    def print_usage(self):
        if not self.commands:
            printer.warning('No commands available')
            return
        print('\nAvailable commands:\n')
        print(self.fill(sorted(self.commands)))
        print('\nFor detailed help on a command: runcommands <command> --help')

    def fill(self, string, indent='    ', max_width=72):
        """Wrap string so it fits within at most ``max_width`` columns.
        
        If the terminal is less than ``max_width`` columns, the string
        will be filled into that smaller width instead.
        
        """
        if not isinstance(string, str):
            string = ' '.join(string)
        width = min(max_width, get_terminal_size().columns)
        return textwrap.fill(
            string, width=width, initial_indent=indent, subsequent_indent=indent,
            break_on_hyphens=False)

    def complete(self, words=(), index=0):
        words = [word[1:-1] for word in words]  # Strip quotes
        current_word = words[index]
        previous_word = words[index - 1] if index > 0 else None

        commands = self.commands

        def find_command():
            for word in reversed(words[:index]):
                if word in commands:
                    return commands[word], ()
            return run_command, {'--complete', '--words', '--word-index'}

        def print_commands():
            print(' '.join(commands))

        def print_command_options(command, excludes):
            options = [option for option in command.arg_map if option.startswith('--')]
            options = [option for option in options if option not in excludes]
            print(' '.join(options))

        found_command, excluded = find_command()

        if current_word.startswith('-'):
            print_command_options(found_command, excluded)
        else:
            is_command_arg = previous_word in found_command.arg_map
            command_arg = found_command.arg_map[previous_word] if is_command_arg else None
            if is_command_arg and command_arg.takes_value:
                # Don't print any candidates; this will cause the shell
                # to display defaults (file names, etc).
                pass
            else:
                print_command_options(found_command, excluded)
                print_commands()


class CommandToRun:

    __slots__ = ('name', 'command', 'config', 'env', 'argv')

    def __init__(self, command, config, argv):
        self.name = command.name
        self.command = command
        self.config = config
        self.env = config.env
        self.argv = argv

    def run(self):
        return self.command.run(self.config, self.argv)

    def __repr__(self):
        return 'Command(name={self.name}, env={self.env}, args={self.argv})'.format(self=self)
