# RunCommands

## 1.0a53 - 2020-03-23

- Added `module` and `qualname` attributes to `Command` instances. These
  correspond to the built in `__module__` and `__qualname__` attributes of
  classes and can be used for introspection of a command. E.g., `module` can be
  used to order commands by module in a command listing.
- Added support for command line completion for base commands used as console
  scripts.

## 1.0a52 - 2020-03-18

- Improve inverse options.

## 1.0a51 - 2020-02-06

- Commonly-used utilities are now exported from the top level package. This is
  intended to reduce tedium when creating lots of commands spread across many
  modules.  Includes `abort`, `confirm`, and `printer`.
- Made it somewhat easier to specify subcommands by allowing
  `@base_command.subcommand` to be used as a decorator. This reduces the number
  of imports needed when creating subcommands. It also looks nicer than
  `@subcommand(base_command)` IMO.
- Changed the default color of `printer.hr()` from info (blue) to header
  (magenta) since that's the color I usually want HRs to be.
- Made it a little easier to specify colors in `printer` by allowing colors in
  the color map to be accessed as attributes (in addition to item access).

## 1.0a50 - 2020-01-03

- Common base command args are now passed down to subcommands.

## 1.0a49 - 2019-12-19

- Fixed normalization of default args read from config file. Command and arg
  names are now normalized immediately as they're read from config instead of
  merging them all together and then normalizing them. This ensures all the
  default args are consistently and correctly merged.

## 1.0a48 - 2019-12-16

- Fixed an issue with positional args that have a default value and
  `nargs=N`. Previously, `nargs` would be set to `*` or `?` (depending
  on whether the arg is a container type or not), but that doesn't work
  when `nargs=N`. Such args are now converted to options and must be
  passed via `--arg ...` from the command line.

## 1.0a47 - 2019-12-03

- Fixed/improved handling of args in `Command.__call__()` and `Command.run()`.
  In particular, handle args as much as possible as they would be when doing
  a normal call, with the primary difference being that positionals can have
  default values.
- Improved normalization of command names. In particular, it was previously
  possible to call a command named `xyz` as `XYZ` on the command line since
  command-line args were always lower-cased when checking to see if they were
  command names.
- Added the option to specify a default value for a command's var args.
- Added `background` flag to `local` command. This provides an easy way to run
  a command as a background process (e.g., a file watcher).

## 1.0a46 - 2019-11-22

- Fixed an issue with default args being added to globals breaking
  interpolation. Instead of adding the default to globals so that they can be
  added to commands' default args (if requested), they're now added  directly
  to commands' default args (when requested). When they're added to globals,
  that can cause circularity issues when interpolating.

## 1.0a45 - 2019-11-22

- Fixed handling of default args for var args (`*args`).
- Added `default_args` to globals so commands can request their own and other
  commands' default args by adding a `default_args` arg. This allows, for
  example, setting a default arg for a command that another command can then
  access via `default_args` instead of duplicating the arg for both commands or
  adding the arg to globals.

## 1.0a44 - 2019-11-19

- Fixed a couple regressions regarding default args introduced in 1.0a40:
  - Add globals to keyword args for commands that have `**kwargs`.
  - Track args that came from defaults.
- Fixed/improved handling of args in `Command.__call__()` introduced in 1.0a40:
  - Ensure positional args can be passed via keyword args.
  - Ensure optional args can be passed positionally.
- Fixed `complete` command so it doesn't show command usage when parsing args.
- Added `make-dist` and `upload-dists` commands.
- Revamped `Printer` utility.

## 1.0a43 - 2019-11-18

- Fixed some issues with parsing short option group, especially during the
  initial partitioning of `argv`:
  - Made sure the last option in a short option group gets a value.
  - Stopped reparsing `run` args for short option groups since they're parsed
    when partitioning `argv`.
  - Moved parsing of short option groups for commands to an earlier point in
    the process so it's possible to tell if help was requested if the help
    option was passed as part of a multi short option group.

## 1.0a42 - 2019-11-17

- Improved `release` command.

## 1.0a41 - 2019-11-14

- The `run` console script alias is now installed by default along with the
  `runcommand` and `runcommands` aliases. The `RUNCOMMANDS_CONSOLE_SCRIPTS`
  environment variable can be used to specify different aliases or to disable
  installation of the RunCommands console script altogether.
- The `RUNCOMMANDS_INSTALL_COMPLETE_CONSOLE_SCRIPT` environment variable can be
  used to *disable* the installation of the `runcommands-complete` console
  script.
- The `RUNCOMMANDS_INSTALL_RELEASE_CONSOLE_SCRIPT` environment variable can be
  used to *enable* installation of the `make-release` console script.
- Fixed regular expression used to check long options (again). This time, add
  support for `--multiple-words`.
- Improved parsing of multi short options. In particular, added support for
  specifying a value for the last option in the group: `-xyzValue`.
- Improved partitioning of initial `argv`:
  - `argv` is now partitioned into `run` args versus commands and their args by
    finding the first non-option word. This allows for better, more intuitive
    feedback when bad args are passed to `run` (allowing `argparse` to do its
    validation instead of aborting with an unhelpful error).
  - In addition, don't attempt to parse *every* arg in `argv` as a multi short
    option. Only attempt to parse those that appear to be `run` args (i.e.,
    those before the first non-option word).
- Added option to pass a minimum hash length via the `git-version` command's
  `--short` option. `--short` by itself, as a flag, means let git determine the
  minimum has length. `--short=N` means use `N` as the minimum.

## 1.0a40 - 2019-11-12

- Added support for commands with subcommands (like `git log`).
- Added support for mutually exclusive command args. Corresponds to
  `argparse.ArgumentParser.add_mutually_exclusive_group()`.
- Added support for positional args that have a default value. These are args
  that you want to pass positionally but that are optional.
- Added `release` command to built-in commands.
- Removed `collect_commands()` utility function. It was too magical without
  providing much benefity.
- The `run` console script is now only installed when an active virtualenv is
  detected (indicated by the presence of the `VIRTUAL_ENV` environment
  variable). "Run" is pretty generic and only installing `run` in virtualenvs
  is intended to reduce the possibility of conflicts.
- The `runcmd` console script is no longer installed. It was a not-very-useful
  alias.
- Improved internals, esp. wrt. handling of positional args.

## 1.0a39 - 2019-11-02

- Added support for positional args that have a default value. Includes
  handling of `choices` args when no choice is passed.
- Fixed conversion of list-arg-to-tuple for cases where arg doesn't exist on
  command. This can happen when, for example, a command is run with `run
  --debug` and the command doesn't have a `debug` arg.
- Added check to ensure long options are valid. Short options were already
  being checked.
- Added the option to pass enum choices via `choices` rather than via `type`.
  Using `choices` is more natural. The reason `type` was used initially is
  because such enums are passed to `argparse.add_argument()` as the type
  converter.

## 1.0a38 - 2019-10-25

- Support Python 3.8.
- Don't attempt to parse command args after `--` as multi short options. Args
  after `--` should be passed verbatim.
- When determining if help was requested for a command, ignore args after `--`.
  Args after `--` aren't command options.

## 1.0a37 - 2019-05-22

- Allow env-specific default args, which take precedence over top level default
  args (the default default args).

## 1.0a36 - 2019-04-29

- Default args read from config are now checked and a useful exception is
  raised if an unknown arg is encountered.
- Fixed/improved handling of container args. This deconflates the type of
  a container from the type of values it contains. It also allows commands to
  use `*args` to collect an arbitrary number of positional args.
- Fixed handling of `--` on the command line. Now, each command can make use of
  `--` to specify the end of options and that the remaining args are
  positional.
- The command to run via the `local` or `remote` commands no longer needs to be
  quoted on the command line.
- Improved parsing and expansion of grouped short options like `-xyz`.

## 1.0a35 - 2019-03-17

- Upgraded PyYAML 3.13 => 5.1. Depending on your setup, this may require
  upgrading PyYAML to 5.1 first before upgrading to this version of
  RunCommands (e.g., if you have a command that wraps `pip install`).

## 1.0a34 - 2019-03-10

- Arg values are now collected into tuples when appropriate--when an arg's
  default value is a tuple or its type is explicitly set to `tuple`.
- Positional args can now be specified with a type of `dict`, `list`, or
  `tuple`. Previously, specifying one of these types didn't work as expected
  because only one value would be read from the command line and that value
  would be converted to a `list` or `tuple` of characters (and using `dict`
  would cause an error).
- Multiple short options can now be grouped on the command line like `abc`.
- The inverse option for `bool` args can now be disabled.
- Fixed some issues related to linting.

## 1.0a33 - 2018-11-26

- Fixed precedence of globals in `run` command. In particular, globals passed
  via the command line have higher precedence than globals specified in the
  `envs` section of the config file.
- Fixed a logic bug in `util.misc._merge_dicts()`.

## 1.0a32 - 2018-11-22

- Convert `cd` arg passed to `local` command to an absolute path via the
  `abs_path` utility function. This is mainly so that asset paths like
  `'package.module:file'` will be handled correctly.
- Normalize default arg names read from config file. E.g., if a command has
  an arg named `dir_` with a trailing slash to avoid clashing with the builtin
  `dir` function, allow the arg to specified as `dir` in the config file.

## 1.0a31 - 2018-10-04

- Reworked new config system introduced in 1.0a28. Removed `defaults`. Added
  `envs` and support environment-specific globals.

## 1.0a30 - 2018-05-22

- Fixed handling of `**kwargs`. When collecting the args/options for a command,
  `kwargs` is skipped instead of inadvertantly being added to the command's
  options.

## 1.0a29 - 2018-04-09


- Added `keep_slash` flag to path utility functions, because sometimes slashes
  need to be preserved (e.g., with `rsync`).
- Fixed `sync` command so that it preserves trailing slashes on the `source`
  and `destination` paths its passed.
- Tweaked version regex in `release` task (don't require dev marker).
- Fixed some `local` git commands in release task.

## 1.0a28 - 2018-04-07

Big rewrite. See the git log for tag 1.0a28 to see all the details. Here's
a summary:

- Focus is more on console scripts and collections of commands rather than
  being a Farbric-esque deployment tool, although simplified versions of the
  `local` and `remote` commands are still available for simple deployment
  scenarios.
- Config files are YAML now instead of custom INI/JSON format.
- Global config is no longer passed to commands as first positional arg.

## 1.0a27 - 2017-12-21

- Fixed reading of stdin by unbuffering it. The approach used here is derived
  from Fabric.
- Added `copy_file` command.
- Added `get_all_list` utility function.

## 1.0a26 - 2017-10-18

- Fixed a bug in `util.confirm()` relating to its abort-on-unconfirmed logic.
  The abort logic was being triggered in practically all cases when something
  wasn't confirmed (notably, in the default case where
  `abort_on_unconfirmed=False`).

## 1.0a25 - 2017-07-14

- Changed mapping operations on `Config` so that `__contains__()` no longer
  looks in the `run` config and `__iter__()` no longer yields `run` config
  keys. I'm not sure why I thought would be useful in the first place, but it
  was tricky to get right and confusing (and causing duplicates in the output
  of the `show-config` command).
- Added `--python` option to `install` command so the Python version for the
  virtualenv can be specified.
- All extras are no installed when the `install` command is run. This is so
  testing dependencies will be installed.
- Fixed a bootstrapping issue in `commands.py`: import `coverage.Coverage` in
  the `test` command instead of globally because coverage might not be
  installed yet.

## 1.0a24 - 2017-07-06

- Fixed/simplified iteration in `Config`. The previous implementation worked on
  Python 3.5 and 3.6 but not 3.3 and 3.4, causing infinite recursion on those
  versions. The new implementation is simpler because it only defines
  `__iter__()` instead of both `__iter__()` and `keys()`.

## 1.0a23 - 2017-07-06

### Major Changes

- Replacement commands are now called automatically when commands are called
  directly. A "replacement command" is a command with the same name as an
  already-defined command. When the original command is called, it will check
  to see if it has been replaced and call the replacement command if it has
  been. The original command implementation can always be called via
  `Command.implementation()`. This is intended to mirror CLI behavior (where
  only replacement commands are available) and to make it easy to swap command
  implementations in wrapper commands. [NOTE: This probably needs a bit more
  thought put into it and perhaps a less-magical API].
- Command default options can now be specified via a shorter config path:
  `defaults.{command-name}.xyz`. The old method of using the full module path
  is still supported, which may be useful when commands are replaced and the
  original defaults shouldn't be applied to the replacement command. Defaults
  specified via the short path are merged over defaults specified using the
  module path.
- Added `Command.get_default()` to make getting at individual default options
  easy.

### Other Changes

- Added `use_pty` flag to `remote` command. It's passed through to the remote
  runner strategy (strategies already had a `use_pty` flag).
- Added `RawConfig.update()` so that `RawConfig.__getitem__()` will be used
  when updating (like `get()` and `pop()`).
- A `RawConfig` object is now always returned from `Command.get_defaults()`
  instead of returning a plain `dict` when there are no defaults. This is for
  consistency; not sure it has any practical/noticeable effect.
- Added `commands` to default `RunConfig` options. `commands` is populated in
  `Runner` with the commands it loads and in `Command.console_script()` with
  the command being wrapped.

### Fixed

- When loading JSON values tolerantly (i.e., treating bad values as strings),
  values are now explicitly cast to `str` to avoid returning non-string values
  (in `JSONValue.loads()`).

## 1.0a22 - 2017-06-05

- When running a subprocess via the `local` command, on `Ctrl-C` `SIGINT` is
  now sent to the subprocess for handling and the `local` command is aborted
  only after/if the subprocess exits. The idea is to allow interactive commands
  like `less` to exit cleanly and to obviate the need for the `stty sane` hack
  added in the 1.0a20 release.
- When a `local` subprocess times out, `Popen.terminate()` is now used to shut
  down the subprocess instead of `.kill()`. `.terminate()` gives subprocesses
  a chance to exit cleanly.
- `remote` commands are now allocated a pseudo-terminal (using `ssh -t`) when
  run interactively (when `stdout` is detected to be a TTY). This is to allow
  interaction with remote commands that prompt for input. TODO: Investigate
  downsides.

## 1.0a21 - 2017-05-22

- Made `Config.__contains__()` look in `run` config like `.__getitem__()` does.
- Made `Config.keys()` and `.__iter__()` yield `run` config keys.
- Made `Config.values()` yield `run` config values.
- Made `Config.items()` yield `run` config items.
- Changed all `str.format(**x)` to `str.format_map(x)` for consistency.

## 1.0a20 - 2017-05-16

### Added

- Started adding tests.
- `stty sane` is now run when a local process exits. This feels pretty hacky
  and probably won't work on Windows.

### Changed

- Re-revamped config stuff

    Interpolation-related changes:

        - Interpolation is now done when config values are retrieved instead of
          interpolating all values up front. This allows a value to be changed
          and any dependent values to be updated automatically.
        - Interpolation now works with any value type, not just strings.
        - It's now possible to do things like this in config files:

            x = [1, 2, 3]
            ; y will be a list
            y = ${y}
            ; z will be a string
            z = "${y}"

    Breaking changes:

      - Renamed `RawConfig._clone()` to `copy()`.
      - Removed `RawConfig._overrides()` context manager because it didn't seem
        all that useful (just copy instead).
      - `${...}` is now used instead of `{...}` for interpolation. Config
        values are now parsed instead of using `str.format()`.
      - When a `dict` or other mapping type is added to a config object, it
        will no longer be converted to a `RawConfig` object.

    Other changes:

      - Added `RawConfig._iter_dotted()`; this was added to make
        `RawConfig._to_string()` simpler, but it may have other uses.

- Added `util` package and moved the utilities from the `util` module into
  various modules in that package.

### Fixed

- Made `Config._get_default_version()` refer directly to
  `config.version_getter()` instead of loading it from a string so it works in
  subclasses.
- Made `config.version_getter()` work if it's run from anywhere within a git
  work tree and not just at the root.
- The `cd` arg passed to `local` command is converted to an absolute path. This
  is mainly to support asset paths (which was supported before).
- Added support for `flush` to `Printer.print()` (by not passing it through
  to `Printer.colorize()`).

### Removed

- `RawConfig._overrides()`
- `RawConfig._clone()` (renamed to `copy()`)
- `util.as_list()` and `util.as_tuple()`; these were holdovers from before
  list-type options were supported.

## 1.0a19 - 2017-04-27

- When getting the default version in `Config`, if a tag is checked out, use
  the tag name instead of the short hash.

## 1.0a18 - 2017-04-27

- Renamed `runners.commands.get_default_prepend_path` utility function to
  `get_default_local_prepend_path`.
- Fixed some issues with creating & copying config objects. On Python 3.3
  & 3.4, `OrderedDict.__init__` needs to be called.
- Made some internal improvements to local & remote runners.

## 1.0a17 - 2017-04-26

- When the `--debug` flag is passed to the main script, `RunCommandsError`
  exceptions are now raised instead of being caught. Raising these exceptions
  actually facilitates debugging. ;)
- Default command options specified via config are now validated. Previously,
  nonexistent default options would be silently ignored. Now a `CommandError`
  will be raised.
- When reading streams (e.g., when the `local` command is run), `EIO` errors
  are now caught and ignored. We already do this when writing, so it makes
  sense to do it also when reading. TODO: Review which OS/IO errors can be
  caught and safely ignored.
- Revamped config handling. Mainly, this is internal facing. Creation and
  handling of config objects is simpler and more consistent.

## 1.0a16 - 2017-04-18

- Added more documentation.
- `configure()` is now "officially" exported from the top level package (by
  adding it to `__all__`).
- The `env` and `debug` config keys are now both copied from the `RunConfig` to
  the top level `Config` so you can do `config.env` instead of `config.run.env`
  in commands. This is somewhat for backward compatibility and somewhat just
  for convenience.
- Improved `util.confirms()`'s `abort_on_unconfirmed` option.
- Fixed a little glitch in the output of `show-config`.

## 1.0a15 - 2017-04-13

- Default run options can now be specified for individual commands in
  `setup.cfg` or `runcommands.cfg` (in sections like `[runcommands:local]`).
- Default `list` and `dict` run options read from `setup.cfg` are now handled
  correctly.
- Added support for environment variables corresponding to various run options
  (`RUNCOMMANDS_ECHO`, `RUNCOMMANDS_HIDE`, etc). They can be set directly or
  via the `runcommands.configure()` function. Environment variables take
  precedence over run options read from `setup.cfg`.
- Made it easy to export console scripts for individual commands (by adding
  something like `deploy = my.package:deploy.console_script` to a project's
  `console_scripts` entry point).
- `list` options are now processed the same way `dict` options are: attempt to
  parse them as JSON and fall back to str if that fails.
- Empty command line options are now converted to `None`. Empty values can be
  passed using `--opt=` or `--opt ''`.
- Revamped env handling.
- Added handling of keyword-only command function args. Keyword-only args can
  only be passed in direct/programmatic calls to a command; they aren't
  included in the command line options.
- Made the project bootstrappable. It should be possible now to `git clone` the
  project and then run `./commands.py install` to create a virtualenv for
  development.
- Reorganized and cleaned up a bunch of stuff.
- Started writing Sphinx/RTD docs.
- Added tox configuration.

### Fixed

- Fixed the `@command` decorator's first arg: renamed it from `name_or_wrapped`
  to `name`.
- When getting the default version via get in `Config`, return `None` if the
  current directory isn't a git repo.

## 1.0a14 - 2017-04-06

### Added

- Default args for the main script will now be read from `runcommands.cfg` or
  `setup.cfg` if one of those is present and contains a `[runcommands]`
  section.
- Added ability to list available envs to main script (`--list-envs`).
- Added support for bool-or-type options. This is used with `hide` options.
- Added support for args that specify choices. Added `choices` arg to
  `Command`.
- Added support for `Enum` args. These args will be limited to the choices
  specified by the enum.
- `commands_module` is now included in config.

### Changed/Improved

- Command line option names for `dict` and `list` args are now made singular
  when they end with an `s`. From the command line, dicts and lists are created
  by using a given option multiple times. Using a singular name makes this more
  clear.
- Improved `show-config` command. Added `--flat` flag (don't nest config).
  Added `--values` flag (show values only without keys. Added ability to
  specify multiple items. Added `--exclude` option.
- Made default type of `hide` args for all commands `bool_or(Hide)`.
- Improved handling of arg types in general.
- Removed fill/wrap code; use `textwrap.fill()` from the stdlib instead.
- Wrapped entire body of main script in try block. `RunCommandsError` is now
  raised in some places. These keep the main script from blowing up with
  a stack trace in cases where it's better to abort with a nice error message.

### Fixed

- Fixed a one-off bug with `--` in the main script. Skip over it so it's not
  treated as a command arg.
- Fixed an issue in `Printer.print()` where the `file` arg wasn't being passed
  down to `print()`, which was causing warning, error, and debug messages to be
  sent to stdout instead of stderr.
- Fixed `RawConfig` so it doesn't read files when adding items or cloning.

## 1.0a13 - 2017-03-30

- Improved command env handling and options.

## 1.0a12 - 2017-03-29

- Fixed a bug when raising `TimeoutExpired` exception in `LocalRunner`. The
  captured output data is bytes and needs to be decoded.
- Improved handling of non-existent commands module or config file. Catch
  exceptions and raise an appropriate `RunCommandsError` instead. The main
  script catches these errors and aborts with a useful message instead of
  spewing a traceback.
- Improved `release` command's automatic next version detection. In particular,
  it can now derive `1.0aN` from `1.0aM`.

## 1.0a11 - 2017-03-29

- Fixed potential decoding errors when capturing subprocess data. Captured data
  is no longer decoded eagerly, which avoids decoding errors when the data read
  ends with an incomplete Unicode byte sequence. This was an issue for commands
  that output a lot of data, like `npm install`.

## 1.0a10 - 2017-03-29

- Improved input/output mirroring/capture in `LocalRunner`.
  - Fixed input mirroring issue with subprocesses that accept single character
    input (like `less`).
  - Added loop to read until no more data is available after subprocess exits.
  - Added `COLUMNS` and `LINES` to subprocess environment when using PTY so
    output isn't constrained to the default terminal size.
  - Made more robust by checking for closed streams when reading, closing PTY
    file descriptors, etc.
  - Moved read/mirror/capture code into its own module for potential reuse.
- Made an attempt to fix the Paramiko remote runner strategy using the
  `select`-based reader, but it didn't work because the file handles returned
  by `SSHClient.exec_command()` aren't "real" files (they don't have
  a `fileno()` method).

## 1.0a9 - 2017-03-28

- Simplified handling of input/output in `LocalRunner`. Instead of firing up
  reader threads, this version uses `select`. This seems to actually work in
  all cases now (PTY vs non-PTY), but it won't work on Windows. It also breaks
  the Paramiko remote runner strategy (since `NonBlockingStreamReader` was
  removed). It might be possible to create a thread-based version of the same
  logic...
- In `get_default_prepend_path`, bad asset paths are now skipped over and
  a warning is printed. This fits with how non-existent path directories are
  skipped. Previously, a bad asset path would cause a nasty `ImportError`.
- Improved `util.asset_path`:
  - Inject `config` into path at top instead of at bottom.
  - Raise a better error when a path contains an unimportable package.
- Added `clean` command.

## 1.0a8 - 2017-03-27

- Underscores in command names are now replaced with dashes. This is just an
  aesthetic preference.
- Fixed an issue with completion where it would always provide options for the
  last command on the command line even if the cursor was moved before the last
  command.
- Removed distinction between `-l` and `--list` main script options. `-l` used
  to show a short listing of commands (i.e., just their names) and `--list`
  would show a long listing with usage strings. Both now show the short
  listing. The output of `--list` was long and cluttered and with completion
  working it no longer seems necessary.
- When printing help for a command, the command function's entire docstring is
  now shown.
- When running the main script, we now check for any kind of `RunCommandsError`
  and print an error message (instead of spewing a traceback) when one is
  raised.  In particular, this catches a bad/missing `--env`.
- Made some low-level improvements to the local runner class:
  - Fixed some issues with prompting for user input by fixing issues with how
    subprocesses' stdout/stderr are read and mirrored back to the controlling
    terminal.
  - Added initial PTY support.

## 1.0a7 - 2017-03-21

- Renamed package from `taskrunner` to `runcommands`. The latter name is
  available on PyPI and the term "command" is perhaps less ambiguous
  than "task".
- Fleshed out the Paramiko remote runner a bit. It now A) works and B) caches
  connections per user/host. Needs review/testing. Should be made more robust
  in dealing with auth and network issues.

## 1.0a6 - 2017-03-20

- Added `RemoteRunner` class.
- Added a start at a Paramiko-based remote runner as an alternative to shelling
  out to `ssh`. Work in progress.
- Moved `NonBlockingStreamReader` into a separate module for potential reuse.
  E.g., it might be useful in the Paramiko-based remote runner.
- Made `NonBlockingStreamReader` handle text streams. I.e., we no longer assume
  all streams are byte streams.
- Improved handling of output in `LocalRunner`/`NonBlockingStreamReader`.
  Streams can be closed after a subprocess exits, so we have to account for
  this.
- Added `Parameter.takes_value` and `Parameter.takes_option_value`. These can
  be easier to use in some cases than checking for `is_bool` (just because the
  meaning is more clear).
- Improved completion by correctly handling options that don't take values.
  This makes use of `Parameter.takes_option_value`.
- Added `abort_on_unconfirmed` option to `confirm`.
- Added `prompt` utility function.
- Added `release` command.

## 1.0a5 - 2017-03-15

- Added `timeout` option to `local` command. Set default timeout for `local`
  command to `None` (no timeout by default).
- Added `timeout` option to `remote` command. The default timeout for remote
  commands is 30 seconds.
- Fleshed out command line completion, especially for Bash. It now works pretty
  well.
- Fixed a bug in the `show_config` command where it failed to abort when a bad
  `name` was passed.

## 1.0a4 - 2017-03-13

### Major changes

- Added `config` option to `Command`/`@command`. This makes specifying override
  config for a command easy. Useful for overriding default command config
  options when most commands use those defaults but one or two don't.
- Added initial handling of `dict`. The logic for parsing `-o name=value`
  options was moved into the `command` module.
- Added initial handling of `list`/`tuple` command options.
- Added initial completion support; a sample bash completion script is
  provided.
- Added `Result.__bool__()` because `if command(config): ...` is convenient in
  some cases.
- The default version set in `Config` is now the short hash of the HEAD of the
  git repo in the current directory instead of `'X.Y.Z'`. This is easy to
  override by setting `version_getter = module:getter` in the project's command
  config.
- Revamped internals of `LocalRunner`. In particular, improved handling of
  in/out/err stream data (but this is tricky to get right, so more work may be
  needed). When decoding stream data, the encoding is now read from the locale
  instead of hard coding 'UTF-8'.
- Reimplemented `main` script so that it's just an entry point; moved the logic
  of running commands into `commands.run()`.
- Fixed a typo/bug in `RawConfig._clone()`; was calling `clone()` instead of
  `_clone()` when descending into sub-config objects.

### Other changes

- Made the `commands_module` arg to `CommandRunner.load_commands()` optional;
  use `self.commands_module` by default.
- Limited width of short command listing to 80 columns.
- Improved output of `show_config` when `--name` is used and refers to a config
  object (by descending into the config object).
- Added `Printer.echo()` for echoing commands and the like; it uses the same
  color as `Printer.debug()` because A) echoing is largely used for debugging
  and B) there aren't that many colors to choose from.
- Fixed "danger" color in printer utility; was cyan for some reason instead of
  red.

## 1.0a3 - 2017-03-03

Third alpha version.

- Don't allow options to be passed via `-o` when there's a corresponding
  script option; being able to pass the same option via two different vectors
  seems like it could be confusing.
- Add `_overrides` option to `RawConfig`; simplifies updating a config object
  with overrides without needing to make a separate call to do the update.
- Add `RawConfig._clone(**overrides)` method.
- Improve output of `runcommands -l`, the condensed command listing. Use the
  current terminal width to format commands into rows without mid-word
  wrapping.
- Show condensed command listing when no commands are specified. The long
  command listing is really verbose and not that useful in this case.
- Add `-H` alias for `--hide` to main script.
- Standardize on `-E` for commands that have and `echo` option  and `-H` for
  commands that have a `hide` option. This also leaves `-h` available for
  command help.
- Use `-h` for command help. If a command has multiple H options, the first
  will get `-H` (unless the command also has a `hide` option) and the second
  won't get a short option name.
- Normalize command option names more by stripping dashes (after converting
  underscores to dashes) and lower-casing.

## 1.0a2 - 2017-03-02

Second alpha version.

- Attempt to fix buffering issues when running subprocesses via `LocalRunner`.
  I say "attempt" because this is pretty complex and hard to get just right.
- Allow arbitrary config options to passed via the command line via `-o`; these
  options take precedence over config set via config file.
- Improve (color) printer utility. Put the various color printing functions in
  a class and create a default instance of that class so that this instance can
  be imported instead of having to import the functions individually.
- Print warning, error, and debug messages to stderr by default.
- Make it easier to determine if stdout and/or stderr should be hidden by
  adding some utility class methods to the `Hide` enum.
- Only set the `hide` option for a command from the global config value if the
  command's default is `hide=None`. TODO: Something similar for `echo`, but
  that's a bit harder.
- Remove unused imports, clean other lint, add `__all__` lists where
  appropriate, etc.

## 1.0a1 - 2017-02-25

First alpha version.
