import os
import sys

from .config import RawConfig
from .exc import RunCommandsError
from .runner import run
from .command import bool_or, command
from .util import printer, Hide


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    run_command = command(run, type={'hide': bool_or(str)}, choices={'hide': Hide.choices()})
    run_args, command_args = partition_argv(run_command, argv)

    config = RawConfig(debug=False)
    args = run_command.parse_args(config, run_args)

    config_file = args.get('config_file')
    if config_file is None:
        if os.path.exists('commands.cfg'):
            args['config_file'] = 'commands.cfg'

    options = args.get('options', {})
    for name, value in options.items():
        if name in run_command.optionals:
            printer.error(
                'Cannot pass {name} via -o; use --{option_name} instead'
                .format(name=name, option_name=name.replace('_', '-')))
            return 1

    try:
        run((argv, run_args, command_args), **args)
    except RunCommandsError as exc:
        printer.error(exc, file=sys.stderr)
        return 1

    return 0


def partition_argv(command, argv):
    if not argv:
        return [], []

    if '--' in argv:
        i = argv.index('--')
        return argv[:i], argv[i + 1:]

    args = []
    option = None
    arg_map = command.arg_map
    parser = command.get_arg_parser()
    parse_optional = parser._parse_optional
    hide_choices = Hide.choices()

    for i, arg in enumerate(argv):
        option_data = parse_optional(arg)
        if option_data is not None:
            # Arg looks like an option (according to argparse).
            action, name, value = option_data
            if name not in arg_map:
                # Unknown option.
                break
            args.append(arg)
            if value is None:
                # The option's value will be expected on the next pass.
                option = arg_map[name]
            else:
                # A value was supplied with -nVALUE, -n=VALUE, or
                # --name=VALUE.
                option = None
        elif option is not None:
            if option.takes_option_value:
                args.append(arg)
                option = None
            elif option.name == 'hide' and arg in hide_choices:
                args.append(arg)
                option = None
            else:
                # Unexpected option value
                break
        else:
            # The first arg doesn't look like an option (it's probably
            # a command name).
            break
    else:
        # All args were consumed by command; none remain.
        i += 1

    remaining = argv[i:]

    return args, remaining


if __name__ == '__main__':
    sys.exit(main())
