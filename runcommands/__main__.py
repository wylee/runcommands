import os
import sys
from configparser import ConfigParser

from .config import RawConfig
from .exc import RunCommandsError
from .runner import run, run_command
from .util import printer


def main(argv=None):
    try:
        config = RawConfig(debug=False)
        run_argv, command_argv = partition_argv(argv)
        run_args = read_default_args_from_file()
        run_args.update(run_command.parse_args(config, run_argv))
        run((argv, run_argv, command_argv), **run_args)
    except RunCommandsError as exc:
        printer.error(exc, file=sys.stderr)
        return 1

    return 0


def read_default_args_from_file():
    """Read default run args from file.

    Defaults will be read from the ``[runcommands]`` section of either
    ``runcommands.cfg`` or ``setup.cfg`` (if one of these files exists
    and has that section).

    """
    file_names = ('runcommands.cfg', 'setup.cfg')

    for file_name in file_names:
        if os.path.isfile(file_name):
            break
    else:
        return {}

    config_parser = ConfigParser()
    config_parser.optionxform = lambda s: s
    with open(file_name) as config_parser_fp:
        config_parser.read_file(config_parser_fp)

    if 'runcommands' not in config_parser:
        return {}

    items = config_parser.items('runcommands')
    arg_map = run_command.arg_map
    arg_parser = run_command.get_arg_parser()
    argv = []

    for name, value in items:
        option_name = '--{name}'.format(name=name)
        option = arg_map.get(option_name)

        true_values = ('true', 't', 'yes', 'y', '1')
        false_values = ('false', 'f', 'no', 'n', '0')
        bool_values = true_values + false_values

        if option is not None:
            is_bool = option.is_bool
            if option.name == 'hide' and value not in bool_values:
                is_bool = False
        else:
            is_bool = False

        if is_bool:
            true = value in true_values
            if name == 'no':
                item = '--no' if true else '--yes'
            elif name.startswith('no-'):
                option_yes_name = '--{name}'.format(name=name[3:])
                item = option_name if true else option_yes_name
            elif name == 'yes':
                item = '--yes' if true else '--no'
            else:
                option_no_name = '--no-{name}'.format(name=name)
                item = option_name if true else option_no_name
        else:
            item = '--{name}={value}'.format(name=name, value=value)

        argv.append(item)

    args, remaining = arg_parser.parse_known_args(argv)

    if remaining:
        raise RunCommandsError('Unknown args read from setup.cfg: %s' % ' '.join(remaining))

    return vars(args)


def partition_argv(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        return [], []

    if '--' in argv:
        i = argv.index('--')
        return argv[:i], argv[i + 1:]

    args = []
    option = None
    arg_map = run_command.arg_map
    parser = run_command.get_arg_parser()
    parse_optional = parser._parse_optional

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
            choices = action.choices or ()
            if option.takes_value:
                args.append(arg)
                option = None
            elif arg in choices or hasattr(choices, arg):
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
