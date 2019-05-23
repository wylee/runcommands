Configuration
+++++++++++++

RunCommands can be configured via a YAML file. The options that can be
specified are:

- `globals` -> A dictionary containing global variables that are also
  used as default args for *all* commands.

- `envs` -> A dictionary containing env-specific global variables and/or
  default args.

  When an env is specified, the corresponding env-specific variables
  will be merged into `globals` *and* the entire `envs` dict will be
  added to `globals`.

  In addition, if an env specifies `args`, these will be used as default
  args when the env is selected. These default args have higher
  precedence than default args specified via the top level `args` option
  (see below).

  The selected env's `args` will *not* be added to `globals`.

- `args` -> A dictionary containing default arg values for specific
  commands.  Note that if an env is specified, the env's default args,
  if any, will take precedence over `args` (see above).

- `environ` -> Environment variables.

`globals` and `environ` correspond to the `globals` and `environ`
options of the :func:`runcommands.run.run` command.

Order of Precedence
===================

Lowest to highest:

1. Keyword args
2. Global args from config file
3. Global args passed via `run` command
3. Env-specific global args from config file
4. Env-specific default args from config file
5. Default args from config file
6. Command line args
7. Direct call args

Interpolation
=============

- Globals are injected into other global args, default args, and environment
  variables (after env-specific args are merged in).

- Default args are injected into other default args.
