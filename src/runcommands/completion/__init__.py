import glob
import importlib
import os
import shlex
from contextlib import redirect_stderr

from ..args import arg
from ..collection import Collection
from ..command import command
from ..run import run


@command
def complete(
    command_line,
    current_token,
    position,
    shell: arg(choices=("bash", "fish")),
):
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

    with open(os.devnull, "w") as devnull_fp:
        with redirect_stderr(devnull_fp):
            run_args = run.parse_args(run_argv)

    try:
        module = run.find_commands_module(run_args.get("commands_module"))
        base_collection = Collection.load_from_module(module)
    except Exception:
        base_collection = {}

    return _complete(run, base_collection, command_line, current_token, position, shell)


@command
def complete_base_command(
    base_command,
    command_line,
    current_token,
    position,
    shell: arg(choices=("bash", "fish")),
):
    """Find completions for a base command and its subcommands.

    This assumes that we'll handle all completion logic here and that
    the shell's automatic file name completion is disabled.

    Args:
        base_command: Path to base command as package.module:command
        command_line: Command line
        current_token: Token at cursor
        position: Current cursor position
        shell: Name of shell

    """
    module_name, base_command_name = base_command.rsplit(".", 1)
    module = importlib.import_module(module_name)
    base_command = getattr(module, base_command_name)
    base_collection = {c.base_name: c for c in base_command.subcommands}
    return _complete(
        base_command, base_collection, command_line, current_token, position, shell
    )


def _complete(
    base_command,
    base_collection,
    command_line,
    current_token,
    position,
    shell,
):
    position = int(position)
    tokens = shlex.split(command_line[:position])

    # XXX: This isn't quite correct because it will return the base
    #      command in case where it shouldn't. E.g., if `run xxx` is
    #      typed in, you'll get completions for `run` when you should
    #      probably just get nothing.
    found_command = find_command(base_collection, tokens) or base_command

    if found_command.is_subcommand:
        if found_command.is_base_command:
            collection = {c.base_name: c for c in found_command.subcommands}
        else:
            collection = {}
    else:
        collection = base_collection

    if current_token:
        # Completing either a command name, option name, or path.
        if current_token.startswith("-"):
            if current_token not in found_command.option_map:
                print_command_options(found_command, current_token)
        else:
            print_commands(collection, shell)
            path = os.path.expanduser(current_token)
            path = os.path.expandvars(path)
            paths = glob.glob("%s*" % path)
            if paths:
                for entry in paths:
                    if os.path.isdir(entry):
                        print("%s/" % entry)
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
                        print("%s/" % entry)
                    else:
                        print(entry)
        else:
            print_command_options(found_command)
            print_commands(collection, shell)


def find_command(collection, tokens):
    for token in reversed(tokens):
        if token in collection:
            return collection[token]


def print_commands(collection, shell):
    for name in collection:
        cmd = collection[name]
        description = cmd.description.splitlines()[0].strip() if cmd.description else ""
        if shell in ("sh", "bash"):
            print(name)
        elif shell == "fish":
            print(f"{name}\t{description}")


def print_command_options(cmd, prefix=""):
    for name, cmd_arg in cmd.args.items():
        for option in cmd_arg.all_options:
            if option.startswith(prefix):
                print(option)
