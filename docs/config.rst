Configuration
+++++++++++++

RunCommands can be configured via a YAML file. The options that can be
specified are:

- `defaults` -> A dictionary containing defaults that will be injected
  into itself, `globals`, `default_args`, and `environ`.
- `globals` -> A dictionary containing global variables that are also
  used as default args for *all* commands.
- `env`, `version`, `echo` -> Special globals that will be added to the
  `globals` dict if present. They take precedence if their corresponding
  entries are already present in `globals`.
- `default_args` -> A dictionary containing default arg values for
  specific commands.

All of these except `default_args` correspond to options of the
:func:`runcommands.run.run` command.

Order of Precedence
===================

Lowest to highest:

1. Defaults
2. Keyword args
3. Globals
4. Default args
5. Command line args
6. Direct call args

Interpolation
=============

- Defaults are injected into other defaults, globals, default args, and
  environment variables.
- Globals are injected into other globals, default args, and environment
  variables.
- Default args are injected into other default args.
