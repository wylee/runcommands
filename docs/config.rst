Configuration
+++++++++++++

RunCommands can be configured via a YAML file. The options that can be
specified are:

- `globals` -> A dictionary containing global variables that are
  also used as default args for *all* commands.
- `envs` -> A dictionary containing env-specific global variables. When
  an env is specified, the corresponding env-specific variables will be
  merged into `globals` *and* the entire `envs` dict will be added to
  `globals`.
- `args` -> A dictionary containing default arg values for specific
  commands.
- `environ` -> Environment variables.

All of these except `default` correspond to options of the
:func:`runcommands.run.run` command.

Order of Precedence
===================

Lowest to highest:

1. Keyword args
2. Global args from config file
3. Global args passed via `run` command
3. Env-specific global args from config file
4. Default args from config file
5. Command line args
6. Direct call args

Interpolation
=============

- Globals are injected into other global args, default args, and environment
  variables (after env-specific args are merged in).
- Default args are injected into other default args.
