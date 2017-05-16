import os
import re
import sys
from configparser import ConfigParser

from . import __version__
from .command import command, Command
from .const import DEFAULT_COMMANDS_MODULE, DEFAULT_CONFIG_FILE
from .exc import RunCommandsError, RunnerError
from .runner import CommandRunner
from .util import printer


@command(name='runcommands')
def run(_,
        module=DEFAULT_COMMANDS_MODULE,
        # config
        config_file=None,
        env=None,
        default_env=None,
        # options
        options={},
        version=None,
        # output
        echo=False,
        hide=False,
        debug=False,
        # info/help
        info=False,
        list_commands=False,
        list_envs=False,
        *,
        all_argv=(),
        run_argv=(),
        command_argv=(),
        cli_args=()):
    """Run one or more commands in succession.

    For example, assume the commands ``local`` and ``remote`` have been
    defined; the following will run ``ls`` first on the local host and
    then on the remote host::

        runcommands local ls remote <host> ls

    When a command name is encountered in ``argv``, it will be considered
    the starting point of the next command *unless* the previous item in
    ``argv`` was an option like ``--xyz`` that expects a value (i.e.,
    it's not a flag).

    To avoid ambiguity when an option value matches a command name, the
    value can be prepended with a colon to force it to be considered
    a value and not a command name.

    """
    show_info = info or list_commands or list_envs or not command_argv or debug
    print_and_exit = info or list_commands or list_envs

    if show_info:
        print('RunCommands', __version__)

    if debug:
        printer.debug('All args:', all_argv)
        printer.debug('Run args:', run_argv)
        printer.debug('Command args:', command_argv)
        echo = True

    all_command_run_args = {}
    config_parser = make_run_args_config_parser()

    for section in config_parser:
        match = re.search(r'^runcommands:(?P<name>.+)$', section)
        if match:
            name = match.group('name')
            command_run_args = {}
            command_run_args.update(read_run_args(section, config_parser))
            command_run_args.update(cli_args)
            all_command_run_args[name] = command_run_args

    if config_file is None:
        if os.path.isfile(DEFAULT_CONFIG_FILE):
            config_file = DEFAULT_CONFIG_FILE

    options = options.copy()

    for name, value in options.items():
        if name in run.optionals:
            raise RunnerError(
                'Cannot pass {name} via --option; use --{option_name} instead'
                .format(name=name, option_name=name.replace('_', '-')))

    if version is not None:
        options['version'] = version

    runner = CommandRunner(
        module,
        config_file=config_file,
        env=env,
        default_env=default_env,
        options=options,
        echo=echo,
        hide=hide,
        debug=debug,
    )

    if print_and_exit:
        if list_envs:
            runner.print_envs()
        if list_commands:
            runner.print_usage()
    elif not command_argv:
        printer.warning('\nNo command(s) specified')
        runner.print_usage()
    else:
        runner.run(command_argv, all_command_run_args)


def read_run_args(section, parser=None):
    """Read run args from file and environment."""
    if parser is None:
        parser = make_run_args_config_parser()

    if isinstance(section, Command):
        name = section.name
        if name == 'runcommands':
            section = 'runcommands'
        else:
            section = 'runcommands:{name}'.format(name=name)

    if section == 'runcommands':
        sections = ['runcommands']
    elif section.startswith('runcommands:'):
        sections = ['runcommands', section]
    else:
        raise ValueError('Bad section: %s' % section)

    sections = [section for section in sections if section in parser]

    items = {}
    for section in sections:
        items.update(parser[section])

    arg_map = run.arg_map
    option_template = '--{name}={value}'
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

    if argv:
        arg_parser = run.get_arg_parser()
        args, remaining = arg_parser.parse_known_args(argv)
        if remaining:
            raise RunCommandsError(
                'Unknown args read from {file_name}: {remaining}'
                .format(file_name=parser.file_name, remaining=' '.join(remaining)))
        args = vars(args)
    else:
        args = {}

    prefix = 'RUNCOMMANDS_'
    prefix_len = len(prefix)
    for key in os.environ:
        if not key.startswith(prefix):
            continue
        name = key[prefix_len:].lower()
        if name not in run.optionals:
            raise RunCommandsError('Unknown arg from {key}: {name}'.format_map(locals()))
        value = os.environ[key]
        args[name] = value

    return args


def make_run_args_config_parser():
    file_names = ('runcommands.cfg', 'setup.cfg')

    config_parser = ConfigParser(empty_lines_in_values=False)
    config_parser.optionxform = lambda s: s

    for file_name in file_names:
        if os.path.isfile(file_name):
            with open(file_name) as config_parser_fp:
                config_parser.read_file(config_parser_fp)
            break
    else:
        file_name = None

    config_parser.file_name = file_name
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
    arg_map = run.arg_map
    parser = run.get_arg_parser()
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
        # All args were consumed by run command; none remain.
        i += 1

    remaining = argv[i:]

    return argv, run_argv, remaining
