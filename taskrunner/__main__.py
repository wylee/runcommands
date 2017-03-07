import os
import sys

from .config import RawConfig
from .runner import run, TaskRunnerError
from .task import task
from .util import printer


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    run_args = []
    run_task = task(run)

    optionals = run_task.optionals.values()
    options_with_values = set()
    for param in optionals:
        if not param.is_bool:
            options_with_values.update(run_task.arg_names_for_param(param))

    option_value_expected = False

    for i, s in enumerate(argv):
        if s == '--':
            task_args = argv[i:]
            break
        elif s.startswith('-'):
            run_args.append(s)
            if s in options_with_values:
                option_value_expected = '=' not in s
        elif option_value_expected:
            run_args.append(s)
            option_value_expected = False
        else:
            task_args = argv[i:]
            break
    else:
        # No args or all args consumed
        task_args = []

    config = RawConfig(debug=False)
    args = run_task.parse_args(config, run_args)

    config_file = args.get('config_file')
    if config_file is None:
        if os.path.exists('tasks.cfg'):
            args['config_file'] = 'tasks.cfg'

    options = args.get('options', {})
    for name, value in options.items():
        if name in run_task.optionals:
            printer.error(
                'Cannot pass {name} via -o; use --{option_name} instead'
                .format(name=name, option_name=name.replace('_', '-')))
            return 1

    if args.get('list_tasks'):
        args['list_tasks'] = 'short' if '-l' in run_args else 'long'

    try:
        run((argv, run_args, task_args), **args)
    except TaskRunnerError as exc:
        printer.error(exc, file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
