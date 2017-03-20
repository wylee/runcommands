from importlib import import_module
from importlib.machinery import SourceFileLoader
from itertools import chain
from shutil import get_terminal_size

from . import __version__
from .config import Config, RawConfig
from .task import Task
from .util import abs_path, get_hr, printer


def run(args,
        config_file=None,
        env=None,
        options={},
        version=None,
        tasks_module='tasks.py',
        list_tasks=False,
        echo=False,
        hide=None,
        info=False,
        debug=False,
        complete=False,
        words=(),
        word_index=0):
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

    if complete:
        runner.complete(words=words, index=word_index)
    elif print_and_exit:
        if list_tasks:
            if list_tasks in ('short', True):
                runner.print_usage(short=True)
            elif list_tasks == 'long':
                print()
                runner.print_usage()
        elif not argv and not info:
            printer.warning('No tasks specified')
            runner.print_usage(short=True)
    else:
        runner.run(task_args)


class TaskRunner:

    def __init__(self, config_file=None, env=None, options=None, tasks_module='tasks.py',
                 default_echo=False, default_hide=None, debug=False):
        self.config_file = config_file
        self.env = env
        self.options = options if options is not None else {}
        self.tasks_module = tasks_module
        self.default_echo = default_echo
        self.default_hide = default_hide
        self.debug = debug

    def run(self, args):
        all_tasks = self.load_tasks()
        tasks_to_run = self.get_tasks_to_run(all_tasks, args)
        configs = {}

        for task, task_args in tasks_to_run:
            self.print_debug('Task to run:', task.name, task_args)

        for task, task_args in tasks_to_run:
            task_env = self.env or task.default_env
            if task_env not in configs:
                configs[task_env] = self.load_config(task_env)
            task_config = configs[task_env]
            task.run(task_config, task_args)

    def load_config(self, env=None):
        return Config(
            config_file=self.config_file,
            env=env or self.env,
            run=RawConfig(echo=self.default_echo, hide=self.default_hide),
            debug=self.debug,
            _overrides=self.options,
        )

    def load_tasks(self, tasks_module=None):
        tasks_module = tasks_module or self.tasks_module
        if tasks_module.endswith('.py'):
            tasks_module = abs_path(tasks_module)
            module_loader = SourceFileLoader('tasks', tasks_module)
            module = module_loader.load_module()
        else:
            module = import_module(tasks_module)
        objects = vars(module).values()
        tasks = {obj.name: obj for obj in objects if isinstance(obj, Task)}
        return tasks

    def get_tasks_to_run(self, all_tasks, args):
        tasks = []
        while args:
            task_and_args = self.partition_args(all_tasks, args)
            tasks.append(task_and_args)
            task_args = task_and_args[1]
            num_consumed = len(task_args) + 1
            args = args[num_consumed:]
        return tasks

    def partition_args(self, all_tasks, args):
        name = args[0]

        try:
            task = all_tasks[name]
        except KeyError:
            raise TaskRunnerError('Unknown task: {name}'.format(name=name)) from None

        args = args[1:]
        task_args = []
        partition = [task, task_args]

        prev_args = chain([None], args[:-1])
        next_args = chain(args[1:], [None])

        for prev_arg, arg, next_arg in zip(prev_args, args, next_args):
            if arg in all_tasks:
                option = task.arg_map.get(prev_arg)
                if option is None or not option.takes_option_value:
                    break
            if arg.startswith(':') and arg != ':':
                arg = arg[1:]
            task_args.append(arg)

        return partition

    def print_debug(self, *args, **kwargs):
        if self.debug:
            printer.debug(*args, **kwargs)

    def print_usage(self, tasks_module=None, short=False):
        tasks = self.load_tasks(tasks_module)
        if tasks:
            sorted_tasks = sorted(tasks)
            if short:
                columns = get_terminal_size((80, 25)).columns
                columns = min(80, columns)
                indent = 4
                rows = []
                row = []
                row_len = indent
                for task in sorted_tasks:
                    task_len = len(task)
                    if row_len + task_len < columns:
                        row.append(task)
                        row_len += task_len + 1
                    else:
                        rows.append(row)
                        row = [task]
                        row_len = indent + task_len
                if row:
                    rows.append(row)
                print('Available tasks:')
                for row in rows:
                    print(' ' * indent, end='')
                    print(*row)
            else:
                hr = get_hr()
                printer.header('Available tasks:\n')
                for name in sorted_tasks:
                    task = tasks[name]
                    task_hr = hr[len(name) + 1:]
                    printer.info(name, task_hr)
                    print('\n', task.usage, '\n', sep='')
        else:
            printer.warning('No tasks available')

    def complete(self, words=(), index=0, tasks_module=None):
        words = [word[1:-1] for word in words]  # Strip quotes
        current_word = words[index]
        previous_word = words[index - 1] if index > 0 else None

        tasks = self.load_tasks(tasks_module)

        def find_task():
            for word in reversed(words):
                if word in tasks:
                    return tasks[word], ()
            return Task(run), {'--complete', '--words', '--word-index'}

        def print_tasks():
            print(' '.join(tasks))

        def print_task_options(task, excluded):
            options = ['--help']
            options.extend(
                opt for opt in task.arg_map
                if opt.startswith('--') and opt not in excluded)
            print(' '.join(options))

        found_task, excluded = find_task()

        if current_word.startswith('-'):
            print_task_options(found_task, excluded)
        else:
            is_task_arg = previous_word in found_task.arg_map
            task_arg = found_task.arg_map[previous_word] if is_task_arg else None
            if is_task_arg and task_arg.takes_option_value:
                # Don't print any candidates; this will cause the shell
                # to display defaults (file names, etc).
                pass
            else:
                print_task_options(found_task, excluded)
                print_tasks()


class TaskRunnerError(Exception):

    pass
