import re
import sys

from .config import RawConfig
from .exc import RunCommandsError
from .run import (
    run, run_command, partition_argv, make_run_args_config_parser, read_run_args_from_file)
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

        config.update(
            argv=all_argv,
            run_argv=run_argv,
            command_argv=command_argv,
            run_args=run_args,
        )
        run(config, **main_run_args)
    except RunCommandsError as exc:
        printer.error(exc, file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
