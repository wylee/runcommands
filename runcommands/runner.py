import os
import textwrap
from importlib import import_module
from importlib.machinery import SourceFileLoader
from itertools import chain
from shutil import get_terminal_size

from .command import Command
from .config import Config, RunConfig
from .exc import RunnerError
from .util import abs_path, printer


class CommandRunner:

    def __init__(self, commands_module, config_file=None, env=None, default_env=None, options=None,
                 echo=False, hide=False, debug=False):
        self.commands_module = commands_module
        self.commands = self.load_commands_from_module(commands_module)

        # Defaults
        self.config_file = config_file
        self.env = env
        self.default_env = default_env
        self.options = options if options is not None else {}
        self.echo = echo
        self.hide = hide
        self.debug = debug

        self.run_config = RunConfig(
            commands_module=commands_module,
            config_file=config_file,
            env=env,
            default_env=default_env,
            options=options,
            echo=echo,
            hide=hide,
            debug=debug,
        )

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
            command_run_args = run_args.get(command.name, {})
            run_config = self.run_config.copy(command_run_args)
            commands_to_run.append(CommandToRun(command, run_config, command_argv))
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
        envs = Config._get_envs(self.config_file)
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


class CommandToRun:

    __slots__ = ('name', 'command', 'run_config', 'argv')

    def __init__(self, command, config, argv):
        self.name = command.name
        self.command = command
        self.run_config = config
        self.argv = argv

    def run(self):
        return self.command.run(self.run_config, self.argv)

    def __repr__(self):
        return 'Command(name={self.name}, args={self.argv})'.format(self=self)
