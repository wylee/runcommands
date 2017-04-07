import os
import re
import sys
from configparser import ConfigParser

from .config import RawConfig
from .exc import RunCommandsError
from .runner import run, run_command
from .util import printer


def main(argv=None):
    try:
        all_argv, run_argv, command_argv = partition_argv(argv)

        config = RawConfig(debug=False)
        passed_run_args = run_command.parse_args(config, run_argv)

        run_args = {}
        config_parser = make_run_args_config_parser()

        main_run_args = {}
        main_run_args.update(read_run_args_from_file(config_parser, 'runcommands'))
        main_run_args.update(passed_run_args)

        for section in config_parser:
            match = re.search(r'^runcommands:(?P<name>.+)$', section)
            if match:
                name = match.group('name')
                command_run_args = {}
                command_run_args.update(read_run_args_from_file(config_parser, section))
                command_run_args.update(passed_run_args)
                run_args[name] = command_run_args

        run((all_argv, run_argv, command_argv, run_args), **main_run_args)
    except RunCommandsError as exc:
        printer.error(exc, file=sys.stderr)
        return 1

    return 0


def read_run_args_from_file(parser, section):
    if section == 'runcommands':
        sections = ['runcommands']
    elif section.startswith('runcommands:'):
        sections = ['runcommands', section]
    else:
        raise ValueError('Bad section: %s' % section)

    sections = [section for section in sections if section in parser]

    if not sections:
        return {}

    items = {}
    for section in sections:
        items.update(parser[section])

    if not items:
        return {}

    arg_map = run_command.arg_map
    arg_parser = run_command.get_arg_parser()
    option_template = '--{name} {value}'
    argv = []

    for name, value in items.items():
        option_name = '--{name}'.format(name=name)
        option = arg_map.get(option_name)

        value = value.strip()

        true_values = ('true', 't', 'yes', 'y', '1')
        false_values = ('false', 'f', 'no', 'n', '0')
        bool_values = true_values + false_values

        if option is not None:
            is_bool = option.is_bool
            if option.name == 'hide' and value not in bool_values:
                is_bool = False
            is_dict = option.is_dict
            is_list = option.is_list
        else:
            is_bool = False
            is_dict = False
            is_list = False

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
            argv.append(item)
        elif is_dict or is_list:
            values = value.splitlines()
            if len(values) == 1:
                values = values[0].split()
            values = (v.strip() for v in values)
            values = (v for v in values if v)
            argv.extend(option_template.format(name=name, value=v) for v in values)
        else:
            item = option_template.format(name=name, value=value)
            argv.append(item)

    args, remaining = arg_parser.parse_known_args(argv)

    if remaining:
        raise RunCommandsError('Unknown args read from setup.cfg: %s' % ' '.join(remaining))

    return vars(args)


def make_run_args_config_parser():
    file_names = ('runcommands.cfg', 'setup.cfg')

    config_parser = ConfigParser(empty_lines_in_values=False)
    config_parser.optionxform = lambda s: s

    for file_name in file_names:
        if os.path.isfile(file_name):
            with open(file_name) as config_parser_fp:
                config_parser.read_file(config_parser_fp)
            break

    return config_parser


def partition_argv(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        return argv, [], []

    if '--' in argv:
        i = argv.index('--')
        return argv, argv[:i], argv[i + 1:]

    run_argv = []
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
            run_argv.append(arg)
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
                run_argv.append(arg)
                option = None
            elif arg in choices or hasattr(choices, arg):
                run_argv.append(arg)
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

    return argv, run_argv, remaining


if __name__ == '__main__':
    sys.exit(main())
