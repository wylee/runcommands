from importlib import import_module
from importlib.machinery import SourceFileLoader
from itertools import chain
from shutil import get_terminal_size

from . import __version__
from .config import Config, RawConfig
from .command import Command
from .util import abs_path, get_hr, printer


def run(args,
        config_file=None,
        env=None,
        options={},
        version=None,
        module='commands.py',
        list_commands=False,
        echo=False,
        hide=None,
        info=False,
        debug=False,
        complete=False,
        words=(),
        word_index=0):
    """Run one or more commands in succession.

    For example, assume the commands ``local`` and ``remote`` have been
    defined; the following will run ``ls`` first on the local host and
    then on the remote host::

        runcommands local ls remote --host <host> ls

    When a command name is encountered in ``argv``, it will be considered
    the starting point of the next command *unless* the previous item in
    ``argv`` was an option like ``--xyz`` that expects a value (i.e.,
    it's not a flag).

    To avoid ambiguity when an option value matches a command name, the
    value can be prepended with a colon to force it to be considered
    a value and not a command name.

    """
    argv, run_args, command_args = args

    print_and_exit = any((list_commands, info, not argv))

    if print_and_exit or debug:
        print('RunCommands', __version__)

    if debug:
        printer.debug('All args:', argv)
        printer.debug('Run args:', run_args)
        printer.debug('Command args:', command_args)
        echo = True

    options = options or {}

    if version is not None:
        options['version'] = version

    runner = CommandRunner(
        config_file=config_file,
        env=env,
        options=options,
        commands_module=module,
        default_echo=echo,
        default_hide=hide,
        debug=debug,
    )

    if complete:
        runner.complete(words=words, index=word_index)
    elif print_and_exit:
        if list_commands:
            if list_commands in ('short', True):
                runner.print_usage(short=True)
            elif list_commands == 'long':
                print()
                runner.print_usage()
        elif not argv and not info:
            printer.warning('No commands specified')
            runner.print_usage(short=True)
    else:
        runner.run(command_args)


class CommandRunner:

    def __init__(self, config_file=None, env=None, options=None, commands_module='commands.py',
                 default_echo=False, default_hide=None, debug=False):
        self.config_file = config_file
        self.env = env
        self.options = options if options is not None else {}
        self.commands_module = commands_module
        self.default_echo = default_echo
        self.default_hide = default_hide
        self.debug = debug

    def run(self, args):
        all_commands = self.load_commands()
        commands_to_run = self.get_commands_to_run(all_commands, args)
        configs = {}

        for command, command_args in commands_to_run:
            self.print_debug('Command to run:', command.name, command_args)

        for command, command_args in commands_to_run:
            command_env = self.env or command.default_env
            if command_env not in configs:
                configs[command_env] = self.load_config(command_env)
            command_config = configs[command_env]
            command.run(command_config, command_args)

    def load_config(self, env=None):
        return Config(
            config_file=self.config_file,
            env=env or self.env,
            run=RawConfig(echo=self.default_echo, hide=self.default_hide),
            debug=self.debug,
            _overrides=self.options,
        )

    def load_commands(self, commands_module=None):
        commands_module = commands_module or self.commands_module
        if commands_module.endswith('.py'):
            commands_module = abs_path(commands_module)
            module_loader = SourceFileLoader('commands', commands_module)
            module = module_loader.load_module()
        else:
            module = import_module(commands_module)
        objects = vars(module).values()
        commands = {obj.name: obj for obj in objects if isinstance(obj, Command)}
        return commands

    def get_commands_to_run(self, all_commands, args):
        commands = []
        while args:
            command_and_args = self.partition_args(all_commands, args)
            commands.append(command_and_args)
            command_args = command_and_args[1]
            num_consumed = len(command_args) + 1
            args = args[num_consumed:]
        return commands

    def partition_args(self, all_commands, args):
        name = args[0]

        try:
            command = all_commands[name]
        except KeyError:
            raise RunCommandsError('Unknown command: {name}'.format(name=name)) from None

        args = args[1:]
        command_args = []
        partition = [command, command_args]

        prev_args = chain([None], args[:-1])
        next_args = chain(args[1:], [None])

        for prev_arg, arg, next_arg in zip(prev_args, args, next_args):
            if arg in all_commands:
                option = command.arg_map.get(prev_arg)
                if option is None or not option.takes_option_value:
                    break
            if arg.startswith(':') and arg != ':':
                arg = arg[1:]
            command_args.append(arg)

        return partition

    def print_debug(self, *args, **kwargs):
        if self.debug:
            printer.debug(*args, **kwargs)

    def print_usage(self, commands_module=None, short=False):
        commands = self.load_commands(commands_module)
        if commands:
            sorted_commands = sorted(commands)
            if short:
                columns = get_terminal_size((80, 25)).columns
                columns = min(80, columns)
                indent = 4
                rows = []
                row = []
                row_len = indent
                for command in sorted_commands:
                    command_len = len(command)
                    if row_len + command_len < columns:
                        row.append(command)
                        row_len += command_len + 1
                    else:
                        rows.append(row)
                        row = [command]
                        row_len = indent + command_len
                if row:
                    rows.append(row)
                print('Available commands:')
                for row in rows:
                    print(' ' * indent, end='')
                    print(*row)
            else:
                hr = get_hr()
                printer.header('Available commands:\n')
                for name in sorted_commands:
                    command = commands[name]
                    command_hr = hr[len(name) + 1:]
                    printer.info(name, command_hr)
                    print('\n', command.usage, '\n', sep='')
        else:
            printer.warning('No commands available')

    def complete(self, words=(), index=0, commands_module=None):
        words = [word[1:-1] for word in words]  # Strip quotes
        current_word = words[index]
        previous_word = words[index - 1] if index > 0 else None

        commands = self.load_commands(commands_module)

        def find_command():
            for word in reversed(words):
                if word in commands:
                    return commands[word], ()
            return Command(run), {'--complete', '--words', '--word-index'}

        def print_commands():
            print(' '.join(commands))

        def print_command_options(command, excluded):
            options = ['--help']
            options.extend(
                opt for opt in command.arg_map
                if opt.startswith('--') and opt not in excluded)
            print(' '.join(options))

        found_command, excluded = find_command()

        if current_word.startswith('-'):
            print_command_options(found_command, excluded)
        else:
            is_command_arg = previous_word in found_command.arg_map
            command_arg = found_command.arg_map[previous_word] if is_command_arg else None
            if is_command_arg and command_arg.takes_option_value:
                # Don't print any candidates; this will cause the shell
                # to display defaults (file names, etc).
                pass
            else:
                print_command_options(found_command, excluded)
                print_commands()


class RunCommandsError(Exception):

    pass
