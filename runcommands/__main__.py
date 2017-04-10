import sys

from .config import RawConfig
from .exc import RunCommandsError
from .run import run, partition_argv, read_run_args_from_file


def main(argv=None):
    try:
        all_argv, run_argv, command_argv = partition_argv(argv)
        cli_args = run.parse_args(RawConfig(debug=False), run_argv)
        run_args = read_run_args_from_file(run)
        run_args.update(cli_args)
        run.implementation(
            None, all_argv=all_argv, run_argv=run_argv, command_argv=command_argv,
            cli_args=cli_args, **run_args)
    except RunCommandsError:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
