import os
import sys
import toml
from importlib import import_module
from pathlib import Path

from . import __version__
from .args import arg, json_value
from .command import Command
from .collection import Collection
from .exc import RunAborted, RunnerError
from .runner import CommandRunner
from .util import (
    abs_path,
    is_mapping,
    is_project_root,
    is_sequence,
    merge_dicts,
    module_from_path,
    printer,
)


class Run(Command):

    name = "runcommands"

    allowed_config_file_args = (
        "globals",
        "envs",
        "args",
        "environ",
    )

    def implementation(
        self,
        commands_module: arg(
            short_option="-m",
        ) = None,
        config_file: arg(
            short_option="-f",
        ) = None,
        # Globals
        globals_: arg(
            container=dict,
            type=json_value,
            help="Global variables & default args for *all* commands; will be "
            "injected into itself, default args, and environment variables "
            "(higher precedence than keyword args)",
        ) = None,
        # Special globals (for command line convenience)
        env: arg(
            help="env will be added to globals if specified",
        ) = None,
        version: arg(
            help="version will be added to globals if specified",
        ) = None,
        echo: arg(
            type=bool,
            help="echo=True will be added to globals",
            inverse_help="echo=False will be added to globals",
        ) = None,
        # Environment variables
        environ: arg(
            container=dict,
            help="Additional environment variables; "
            "added just before commands are run",
        ) = None,
        # Meta
        info: arg(
            no_inverse=True,
            help="Show info and exit",
            mutual_exclusion_group="meta-show",
        ) = False,
        list_commands: arg(
            no_inverse=True,
            help="Show info & commands and exit",
            mutual_exclusion_group="meta-show",
        ) = False,
        debug: arg(
            type=bool,
            help="Print debugging info & re-raise exceptions; also added to globals",
        ) = None,
        *,
        all_argv=(),
        run_argv=(),
        command_argv=(),
    ):
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
        commands_module = self.find_commands_module(commands_module)

        if commands_module is None:
            raise RunnerError("Could not find commands module")

        config_file = self.find_config_file(config_file)
        collection = Collection.load_from_module(commands_module)
        cli_globals = globals_ or {}

        if env:
            cli_globals["env"] = env
        if version:
            cli_globals["version"] = version
        if echo is not None:
            cli_globals["echo"] = echo
        if debug is not None:
            cli_globals["debug"] = debug

        if config_file:
            args_from_file = self.read_config_file(config_file, collection)
            args = merge_dicts(args_from_file, {"environ": environ or {}})
            config_file_globals = args["globals"]
            env = env or config_file_globals.get("env")

            if env:
                envs = args["envs"]

                try:
                    env_globals = envs[env]
                except KeyError:
                    raise RunnerError(f"Unknown env: {env}")

                # Don't add the selected env's default args dict to
                # globals, but save it so it can be added back to the
                # the global envs dict (for inspection purposes).
                env_default_args = env_globals.pop("args")

                globals_ = merge_dicts(config_file_globals, env_globals, cli_globals)
                globals_["envs"] = envs

                env_globals["args"] = env_default_args
            else:
                env_default_args = {}
                globals_ = merge_dicts(config_file_globals, cli_globals)

            base_default_args = merge_dicts(args["args"], env_default_args)

            default_args = {name: {} for name in collection}
            default_args = merge_dicts(default_args, base_default_args)

            for command_name, command_default_args in default_args.items():
                command = collection[command_name]

                # Add globals that correspond to this command (that
                # aren't present in default args section).
                for name, value in globals_.items():
                    param = command.find_parameter(name)
                    if param is not None:
                        if param.name not in command_default_args:
                            command_default_args[param.name] = value
                    elif command.has_kwargs:
                        name = Command.normalize_name(name)
                        command_default_args[name] = value

                if "default_args" not in default_args:
                    # This gives commands access to both their own and
                    # other commands' default args.
                    if command.find_parameter("default_args"):
                        command_default_args["default_args"] = base_default_args

                # Convert lists to tuples for the command's args that are
                # specified as being tuples.
                for name, value in command_default_args.items():
                    command_arg = command.find_arg(name)
                    if (
                        command_arg
                        and command_arg.container
                        and isinstance(value, list)
                    ):
                        command_default_args[name] = command_arg.container(value)

            default_args = {name: args for name, args in default_args.items() if args}

            environ = args["environ"]
        else:
            globals_ = cli_globals
            default_args = {}
            environ = environ or {}

        debug = globals_.get("debug", False)
        show_info = info or list_commands or not command_argv or debug
        print_and_exit = info or list_commands

        globals_, default_args, environ = self.interpolate(
            globals_, default_args, environ
        )

        if show_info:
            print("RunCommands", __version__)

        if debug:
            printer.debug("Commands module:", commands_module)
            printer.debug("Config file:", config_file)
            printer.debug("All args:", all_argv)
            printer.debug("Run args:", run_argv)
            printer.debug("Command args:", command_argv)
            items = (
                ("Globals:", globals_),
                ("Default args:", default_args),
                ("Env default args:", env_default_args),
                ("Environment variables:", environ),
            )
            for label, data in items:
                if data:
                    printer.debug(label)
                    for k in sorted(data):
                        v = data[k]
                        printer.debug(f"  - {k} = {v!r}")
                else:
                    printer.debug(label, data)

        if environ:
            os.environ.update(environ)

        collection.set_attrs(debug=debug)
        collection.set_default_args(default_args)
        runner = CommandRunner(collection, debug)

        if print_and_exit:
            if list_commands:
                runner.print_usage()
        elif not command_argv:
            printer.warning("\nNo command(s) specified")
            runner.print_usage()
        else:
            runner.run(command_argv)

    def run(self, argv, **kwargs):
        all_argv, run_argv, command_argv = self.partition_argv(argv)
        if "-d" in run_argv or "--debug" in run_argv:
            self.debug = True
        kwargs.update(
            {
                "all_argv": all_argv,
                "run_argv": run_argv,
                "command_argv": command_argv,
            }
        )
        return super().run(run_argv, **kwargs)

    def console_script(self, argv=None, **overrides):
        _argv = sys.argv[1:] if argv is None else argv
        if "-d" in _argv or "--debug" in _argv:
            self.debug = True
        return super().console_script(argv, **overrides)

    def partition_argv(self, argv=None):
        if argv is None:
            argv = sys.argv[1:]

        if not argv:
            return argv, [], []

        # Consume all args that appear to be options (and their values,
        # if applicable), even those that aren't know run options, up
        # until the first non-option word is reached. That word is
        # assumed to be the start of commands.

        def looks_like_option(s):
            return bool(
                (s.startswith("-") or s.startswith("--"))
                and not s.startswith("---")
                and s.strip("-")
            )

        i = 0
        argc = len(argv)
        run_argv = []
        parse_optional = self.parse_optional
        parse_multi_short_option = self.parse_multi_short_option

        while i < argc:
            a = argv[i]

            if a == "--":
                # Explicit end of run args.
                i += 1
                break

            option_data = parse_optional(a)

            if option_data is not None:
                # Arg is a known run option.
                name, option, value = option_data
                run_argv.append(a)

                if a in ("-d", "--debug"):
                    self.debug = True
                elif value is None and option.takes_value:
                    # Collect the option's value if it takes one and one
                    # wasn't provided via --opt=<value>.
                    j = i + 1
                    if j < argc:
                        run_argv.append(argv[j])
                        i = j
            else:
                if not looks_like_option(a):
                    # Non-option word; assumed to be start of commands.
                    break

                short_options, value = parse_multi_short_option(a)

                if short_options is None:
                    run_argv.append(a)
                else:
                    run_argv.extend(short_options)

                    if "-d" in short_options:
                        self.debug = True

                    if value is not None:
                        run_argv.append(value)
                    else:
                        # Collect the last short option's value if it
                        # takes one and one wasn't provided via
                        # -abc<value>.
                        option_data = parse_optional(short_options[-1])
                        if option_data is not None:
                            name, option, value = option_data
                            if value is None and option.takes_value:
                                j = i + 1
                                if j < argc:
                                    run_argv.append(argv[j])
                                    i = j

            i += 1

        command_argv = argv[i:]
        return argv, run_argv, command_argv

    def find_commands_module(self, commands_module, start_dir="."):
        if commands_module:
            if commands_module.endswith(".py"):
                commands_module = abs_path(commands_module)
                if not os.path.isfile(commands_module):
                    raise RunnerError(
                        f"Commands file does not exist: {commands_module}"
                    )
                else:
                    return module_from_path("commands", commands_module)
            else:
                try:
                    return import_module(commands_module)
                except ImportError:
                    raise RunnerError(
                        f"Commands module could not be imported: {commands_module}"
                    )
        current_dir = Path(start_dir).resolve()
        file_system_root = Path(current_dir.root)
        checked_file_system_root = False
        candidates = ("runcommands.py", "commands.py")
        while not checked_file_system_root:
            for candidate in candidates:
                candidate = current_dir / candidate
                if candidate.is_file():
                    return module_from_path("commands", candidate)
            if current_dir == file_system_root:
                checked_file_system_root = True
            if is_project_root(current_dir):
                break
            current_dir = current_dir.parent
        return None

    def find_config_file(self, config_file, start_dir="."):
        if config_file:
            config_file = abs_path(config_file)
            if not os.path.exists(config_file):
                raise RunnerError(f"Config file does not exists: {config_file}")
            return config_file
        current_dir = Path(start_dir).resolve()
        file_system_root = Path(current_dir.root)
        checked_file_system_root = False
        candidates = ("runcommands.toml", "commands.toml", "pyproject.toml")
        while not checked_file_system_root:
            for candidate in candidates:
                candidate = current_dir / candidate
                if candidate.is_file():
                    return candidate
            if current_dir == file_system_root:
                checked_file_system_root = True
            if is_project_root(current_dir):
                break
            current_dir = current_dir.parent
        return None

    def read_config_file(self, config_file, collection):
        return self._read_config_file(config_file, collection)

    def _read_config_file(self, config_file, collection):
        with open(config_file) as fp:
            args = toml.load(fp)

        if os.path.basename(config_file) == "pyproject.toml":
            tool = args.get("tool") or {}
            args = tool.get("runcommands") or {}

        for name in self.allowed_config_file_args:
            # Not present or present but not set
            if args.get(name) is None:
                args[name] = {}

        extends = args.pop("extends", None)

        for name in tuple(args):
            if name not in self.allowed_config_file_args:
                raise RunnerError(f"Arg cannot be specified in config file: {name}")

        self.normalize_command_and_arg_names(args["args"], collection)

        envs = args["envs"]
        for env, data in envs.items():
            if data is None:
                data = {}
                envs[env] = data
            data.setdefault("args", {})
            self.normalize_command_and_arg_names(data["args"], collection)

        if extends:
            extends = abs_path(extends, relative_to=os.path.dirname(config_file))
            extended_args = self._read_config_file(extends, collection)
            args = merge_dicts(extended_args, args)

        return args

    def normalize_command_and_arg_names(self, config, collection):
        for command_name in tuple(config):
            try:
                command = collection[command_name]
            except KeyError:
                raise RunnerError(
                    f"Unknown command in default args section of "
                    f"config file: {command_name}"
                )

            if command.name != command_name:
                config[command.name] = config.pop(command_name)

            command_default_args = config[command.name]
            for name in tuple(command_default_args):
                param = command.find_parameter(name)
                if param is None:
                    raise RunnerError(
                        f"Unknown arg for command {command_name} in "
                        f"default args section of config file: {name}"
                    )
                if param is not None and name != param.name:
                    command_default_args[param.name] = command_default_args.pop(name)

    def interpolate(self, globals_, default_args, environ):
        if globals_:
            globals_ = self._interpolate(globals_, globals_)

        if default_args:
            context = merge_dicts(globals_, default_args)
            default_args = self._interpolate(default_args, context)

        if environ:
            environ = self._interpolate(environ, globals_)

        return globals_, default_args, environ

    def _interpolate(self, obj, context):
        if is_mapping(obj):
            items = ((k, self._interpolate(v, context)) for k, v in obj.items())
            obj = obj.__class__(items)
        elif is_sequence(obj):
            items = (self._interpolate(v, context) for v in obj)
            obj = obj.__class__(items)
        else:
            obj = self._inject(obj, context)
        return obj

    def _inject(self, value, context, start=0):
        if not isinstance(value, str):
            return value
        i = value.find("{{", start)
        if i == -1:
            return value
        h = i - 1
        if h >= 0 and value[h] == "\\":
            return self._inject(value, context, h + 2)
        j = value.rfind("}}", i + 2)
        if j == -1:
            # String looks like "{{ abc"
            # XXX: Error?
            if self.debug:
                printer.warning(f'Unclosed interpolation group in value: "{value}"')
            return value
        k = j + 2
        key = value[i + 2 : j].strip()
        if not key:
            # String looks like "{{}} xyz"
            # XXX: Error?
            if self.debug:
                printer.warning(f'Empty interpolation group in value: "{value}"')
            return value
        context_value = self._find_in_context(context, key)
        context_value = self._inject(context_value, context)
        if i == 0 and k == len(value):
            value = context_value
        else:
            value = f"{value[:i]}{context_value}{value[k:]}"
            value = self._inject(value, context)
        return value

    def _find_in_context(self, context, key):
        value = context
        parts = key.split(".")
        for segment in parts:
            value = value[segment]
        return value

    def sigint_handler(self, _sig_num, _frame):
        raise RunAborted(0, message="\nAborted by Ctrl-C (SIGINT)")


run = Run()
