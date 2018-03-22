from itertools import chain

from .exc import RunnerError
from .util import printer


class CommandRunner:

    """A runner for a given collection of commands."""

    def __init__(self, collection, debug=False):
        self.collection = collection
        self.debug = debug

    def run(self, argv):
        results = []
        commands_to_run = self.get_commands_to_run(self.collection, argv)

        if self.debug:
            for command in commands_to_run:
                self.print_debug('Command to run:', command)

        help_requested = False
        if len(commands_to_run) > 1:
            for command in commands_to_run:
                if command.help_requested:
                    printer.hr()
                    command.show_help()
                    help_requested = True

        if not help_requested:
            for command in commands_to_run:
                result = command.run()
                results.append(result)

        return results

    def get_commands_to_run(self, collection, argv):
        commands_to_run = []
        while argv:
            command, command_argv = self.partition_args(collection, argv)
            commands_to_run.append(CommandToRun(command, command_argv))
            num_consumed = len(command_argv) + 1
            argv = argv[num_consumed:]
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
        next_args = chain(args[1:], [None])

        for prev_arg, arg, next_arg in zip(prev_args, args, next_args):
            if arg in collection:
                option = command.option_map.get(prev_arg)
                if option is None or not option.takes_value:
                    break
            if arg.startswith(':') and arg != ':':
                arg = arg[1:]
            command_args.append(arg)

        return partition

    def print_debug(self, *args, **kwargs):
        if self.debug:
            printer.debug(*args, **kwargs)

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
        self.name = command.name
        self.command = command
        self.argv = argv
        self.help_requested = '-h' in argv or '--help' in argv

    def run(self):
        return self.command.run(self.argv)

    def show_help(self):
        print(self.command.help)

    def __repr__(self):
        return 'Command(name={self.name}, argv={self.argv})'.format(self=self)
