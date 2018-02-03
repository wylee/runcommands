import glob
import os
import shlex

from ..command import command
from ..const import DEFAULT_COMMANDS_MODULE, DEFAULT_CONFIG_FILE
from ..exc import RunnerError
from ..run import run, partition_argv, read_run_args
from ..runner import CommandRunner


@command
def complete(config, command_line, current_token, position, shell: dict(choices=('bash', 'fish'))):
    """Find completions for current command.

    This assumes that we'll handle all completion logic here and that
    the shell's automatic file name completion is disabled.

    Args:
        config: Config
        command_line: Command line
        current_token: Token at cursor
        position: Current cursor position
        shell: Name of shell

    """
    debug = config.run.debug
    position = int(position)
    tokens = shlex.split(command_line[:position])

    all_argv, run_argv, command_argv = partition_argv(tokens[1:])
    run_args = read_run_args(run)
    debug = run_args.get('debug', debug)

    module = run_args.get('module')
    module = extract_from_argv(run_argv, run.args['module'].options) or module
    module = module or DEFAULT_COMMANDS_MODULE
    module = normalize_path(module)

    config_file = run_args.get('config-file')
    config_file = extract_from_argv(run_argv, run.args['config-file'].options) or config_file
    if not config_file and os.path.exists(DEFAULT_CONFIG_FILE):
        config_file = DEFAULT_CONFIG_FILE
    config_file = normalize_path(config_file)

    try:
        runner = CommandRunner(module, config_file=config_file, debug=debug)
    except RunnerError:
        commands = {}
    else:
        commands = runner.commands

    found_command = find_command(commands, tokens)

    if current_token:
        # Completing either a command name, option name, or path.
        if current_token.startswith('-'):
            if current_token not in found_command.option_map:
                print_command_options(found_command, current_token)
        else:
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
                print_commands(commands, shell)
    else:
        # Completing option value. If a value isn't expected, show the
        # options for the current command and the list of commands
        # instead.
        arg = found_command.option_map.get(tokens[-1])

        if arg and arg.takes_value:
            if arg.choices:
                for choice in arg.choices:
                    print(choice)
            elif found_command is run and arg.name == 'env' and os.path.exists(config_file):
                print('\n'.join(config._get_envs(config_file)))
            else:
                for entry in os.listdir():
                    if os.path.isdir(entry):
                        print('%s/' % entry)
                    else:
                        print(entry)
        else:
            print_command_options(found_command)
            print_commands(commands, shell)


def extract_from_argv(argv, options):
    for option in options:
        try:
            i = argv.index(option)
        except ValueError:
            pass
        else:
            try:
                value = argv[i + 1]
            except IndexError:
                pass
            else:
                if not value.startswith('-'):
                    return value


def normalize_path(path):
    if not path:
        return path
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    path = os.path.abspath(path)
    return path


def find_command(commands, tokens):
    for token in reversed(tokens):
        if token in commands:
            return commands[token]
    return run


def print_commands(commands, shell):
    for name in commands:
        cmd = commands[name]
        description = cmd.description.splitlines()[0].strip() if cmd.description else ''
        if shell in ('sh', 'bash'):
            print(name)
        elif shell == 'fish':
            print('{name}\t{description}'.format_map(locals()))


def print_command_options(cmd, prefix=''):
    for name, arg in cmd.args.items():
        for option in arg.options:
            if option.startswith(prefix):
                print(option)
