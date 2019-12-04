import os
from itertools import chain

from .exc import RunnerError
from .util import printer


class CommandRunner:

    """A runner for a given collection of commands."""

    def __init__(self, collection, debug=False):
        self.collection = collection
        self.debug = debug

    def run(self, argv):
        commands_to_run = self.get_commands_to_run(self.collection, argv)

        show_help_for = [c for c in commands_to_run if c.help_requested]
        if show_help_for:
            count = len(show_help_for)
            for command in show_help_for:
                if count > 1:
                    printer.hr('Help for', command.name, end=os.linesep * 2)
                command.show_help()
            return ()

        return tuple(command.run() for command in commands_to_run)

    def get_commands_to_run(self, collection, argv):
        debug = self.debug
        partition_args = self.partition_args
        commands_to_run = []
        while argv:
            command, command_argv = partition_args(collection, argv)
            command_to_run = CommandToRun(command, command_argv)
            commands_to_run.append(command_to_run)
            num_consumed = len(command_argv) + 1
            argv = argv[num_consumed:]
            if debug:
                printer.debug('Command to run:', command_to_run)
        return commands_to_run

    def partition_args(self, collection, args):
        name = args[0]

        try:
            command = collection[name]
        except KeyError:
            raise RunnerError('Unknown command: {name}'.format(name=name))

        args = args[1:]
        command_args = []
        partition = [command, command_args]

        prev_args = chain([None], args[:-1])

        for prev_arg, arg in zip(prev_args, args):
            if arg in collection:
                # Found a command name. If the previous arg wasn't an
                # option expecting a value, assume the command name is
                # the next command to run and not an option value or
                # positional.
                option = command.option_map.get(prev_arg)
                if option is None or not option.takes_value:
                    break
            if arg and arg[0] == ':' and arg != ':' and arg[1:] in collection:
                # Found an escaped command name. Unescape it.
                arg = arg[1:]
            command_args.append(arg)

        return partition

    def print_usage(self):
        if not self.collection:
            printer.warning('No commands available')
            return
        print('\nAvailable commands:\n')
        for name in sorted(self.collection):
            print('    {name}'.format(name=name))
        print('\nFor detailed help on a command: runcommands <command> --help')


class CommandToRun:

    __slots__ = ('name', 'command', 'argv', 'help_requested')

    def __init__(self, command, argv):
        argv = command.expand_short_options(argv)
        self.name = command.name
        self.command = command
        self.argv = argv

        # Ignore args after -- when determining whether help was
        # requested for a command because such args aren't command
        # options.
        try:
            dash_dash_index = argv.index('--')
        except ValueError:
            help_requested_argv = argv
        else:
            help_requested_argv = argv[:dash_dash_index]

        self.help_requested = '-h' in help_requested_argv or '--help' in help_requested_argv

    def run(self):
        argv_dict = self.command.parse_args(self.argv, False)
        return self.command.run(argv_dict)

    def show_help(self):
        print(self.command.help)

    def __repr__(self):
        return 'Command(name={self.name}, argv={self.argv})'.format(self=self)
