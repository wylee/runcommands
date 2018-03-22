import glob
import os
import shlex

from ..args import arg
from ..collection import Collection
from ..command import command
from ..const import DEFAULT_COMMANDS_MODULE
from ..run import run


@command
def complete(command_line,
             current_token,
             position,
             shell: arg(choices=('bash', 'fish'))):
    """Find completions for current command.

    This assumes that we'll handle all completion logic here and that
    the shell's automatic file name completion is disabled.

    Args:
        command_line: Command line
        current_token: Token at cursor
        position: Current cursor position
        shell: Name of shell

    """
    position = int(position)
    tokens = shlex.split(command_line[:position])

    all_argv, run_argv, command_argv = run.partition_argv(tokens[1:])
    run_args = run.parse_args(run_argv)

    module = run_args.get('commands_module')
    module = module or DEFAULT_COMMANDS_MODULE
    module = normalize_path(module)

    try:
        collection = Collection.load_from_module(module)
    except Exception:
        collection = {}

    found_command = find_command(collection, tokens) or run

    if current_token:
        # Completing either a command name, option name, or path.
        if current_token.startswith('-'):
            if current_token not in found_command.option_map:
                print_command_options(found_command, current_token)
        else:
            print_commands(collection, shell)
            path = os.path.expanduser(current_token)
            path = os.path.expandvars(path)
            paths = glob.glob('%s*' % path)
            if paths:
                for entry in paths:
                    if os.path.isdir(entry):
                        print('%s/' % entry)
                    else:
                        print(entry)
    else:
        # Completing option value. If a value isn't expected, show the
        # options for the current command and the list of commands
        # instead.
        option = found_command.option_map.get(tokens[-1])

        if option and option.takes_value:
            if option.choices:
                for choice in option.choices:
                    print(choice)
            else:
                for entry in os.listdir():
                    if os.path.isdir(entry):
                        print('%s/' % entry)
                    else:
                        print(entry)
        else:
            print_command_options(found_command)
            print_commands(collection, shell)


def normalize_path(path):
    if not path:
        return path
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    path = os.path.abspath(path)
    return path


def find_command(collection, tokens):
    for token in reversed(tokens):
        if token in collection:
            return collection[token]


def print_commands(collection, shell):
    for name in collection:
        cmd = collection[name]
        description = cmd.description.splitlines()[0].strip() if cmd.description else ''
        if shell in ('sh', 'bash'):
            print(name)
        elif shell == 'fish':
            print('{name}\t{description}'.format_map(locals()))


def print_command_options(cmd, prefix=''):
    for name, cmd_arg in cmd.args.items():
        for option in cmd_arg.options:
            if option.startswith(prefix):
                print(option)
