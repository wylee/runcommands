Configuration
+++++++++++++

RunCommands can be configured using TOML. The following config files can be
used (in order of precedence):

- ./runcommands.toml
- ./commands.toml
- ./pyproject.toml

For the first two of these, the option keys (see below) should be specified
like so::

    [globals]
    x = 1

    [envs]
    test = {}
    prod = {}

When using `pyproject.toml`, the option keys (see below) need to be prefixed
with `tool.runcommands` like so::

    [tool.runcommands.globals]
    x = 1

    [tool.runcommands.envs]
    test = {}
    prod = {}

The options that can be specified are:

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
4. Env-specific global args from config file
5. Env-specific default args from config file
6. Default args from config file
7. Default args read from environment variables
8. Command line args
9. Direct call args

Interpolation
=============

*String* values may contain interpolation groups using dotted notation to refer
to other configuration values like so::

    [globals]
    x = "{{ y }}"
    y = 1
    z = "z {{ y }} z"

When a value contains a *single* interpolation group and nothing else, it will
be replaced with the exact value that it refers to, so in the example above,
`x` will be equal to the integer `1` and `z` will be equal to the string
`"z 1 z"`.

Globals are injected into other global args, default args, and environment
variables (after env-specific args are merged in).

Default args are injected into other default args.
