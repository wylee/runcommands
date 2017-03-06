import os
import sys

from . import __version__
from .config import RawConfig
from .runner import TaskRunner, TaskRunnerError
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


def run(args,
        config_file=None,
        env=None,
        version=None,
        options={},
        tasks_module='tasks.py',
        list_tasks=False,
        echo=False,
        hide=None,
        info=False,
        debug=False):
    """Run one or more tasks in succession.

    For example, assume the tasks ``local`` and ``remote`` have been
    defined; the following will run ``ls`` first on the local host and
    then on the remote host::

        runtasks local ls remote --host <host> ls

    When a task name is encountered in ``argv``, it will be considered
    the starting point of the next task *unless* the previous item in
    ``argv`` was an option like ``--xyz`` that expects a value (i.e.,
    it's not a flag).

    To avoid ambiguity when an option value matches a task name, the
    value can be prepended with a colon to force it to be considered
    a value and not a task name.

    """
    argv, run_args, task_args = args

    print_and_exit = any((list_tasks, info, not argv))

    if print_and_exit or debug:
        print('TaskRunner version:', __version__)

    if debug:
        printer.debug('All args:', argv)
        printer.debug('Run args:', run_args)
        printer.debug('Task args:', task_args)
        echo = True

    options = options or {}

    if version is not None:
        options['version'] = version

    runner = TaskRunner(
        config_file=config_file,
        env=env,
        options=options,
        tasks_module=tasks_module,
        default_echo=echo,
        default_hide=hide,
        debug=debug,
    )

    if print_and_exit:
        if list_tasks:
            if list_tasks in ('short', True):
                runner.print_usage(tasks_module, short=True)
            elif list_tasks == 'long':
                print()
                runner.print_usage(tasks_module)
        elif not argv and not info:
            printer.warning('No tasks specified')
            runner.print_usage(tasks_module, short=True)
    else:
        runner.run(task_args)


if __name__ == '__main__':
    sys.exit(main())
