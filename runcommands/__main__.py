import os
import sys

from .config import RawConfig
from .exc import RunCommandsError
from .runner import run
from .command import bool_or, command
from .util import printer


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    run_args = []
    run_command = command(run, type={'hide': bool_or(str)})

    optionals = run_command.optionals.values()
    optionals_that_take_values = [option for option in optionals if option.takes_option_value]
    optionals_that_take_values.append(run_command.parameters['hide'])

    options_with_values = set()
    for param in optionals_that_take_values:
        options_with_values.update(run_command.arg_names_for_param(param))

    option = None
    option_value_expected = False

    for i, s in enumerate(argv):
        if s == '--':
            command_args = argv[i + 1:]
            break

        is_option = s.startswith('-')

        if option and option.name == 'hide':
            if is_option or s not in Hide.choices():
                option_value_expected = False

        if is_option:
            run_args.append(s)
            if s in options_with_values:
                option_value_expected = '=' not in s
            option = run_command.arg_map.get(s)
        elif option_value_expected:
            run_args.append(s)
            option_value_expected = False
        else:
            command_args = argv[i:]
            break
    else:
        # No args or all args consumed
        command_args = []

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


if __name__ == '__main__':
    sys.exit(main())
