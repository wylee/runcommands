Console Scripts
+++++++++++++++

|project| makes it simple to create console scripts. First, define a command:

.. code-block:: python

    # project/package/commands.py
    from runcommands import command

    @command
    def do_stuff(required_arg, optional_arg=None):
        print(required_arg)
        if optional_arg is not None:
            print(optional_arg)

Then add an entry point:

.. code-block:: python

    # project/setup.py
    setup(
        name='package',
        ...,
        entry_points="""
        [console_scripts]
        do-stuff = package.commands:do_stuff.console_script

        """
    )

After reinstalling the package, the console script will now be directly
runnable:

.. code-block:: shell

    > do-stuff things
    things
    > do-stuff things -o wow
    things
    wow

Console Scripts with Subcommands
================================

It's also possible to create console scripts with subcommands a la `git`:

.. code-block:: python

    # project/package/scripts/base.py
    from runcommands import arg, command, subcommand

    @command
    def base(subcommand: arg(default=None)):
        # The base command will be called before the subcommand, so it
        # can be used to do common work or show info.
        print('Running base command')
        if subcommand is None:
            print('Running subcommand:', subcommand)

     @subcommand
     def sub(flag=False):
        print('Sub...', flag)

Add the base command as a console script entry point:

.. code-block:: python

    # project/setup.py
    setup(
        name='package',
        ...,
        entry_points="""
        [console_scripts]
        do-stuff = package.scripts.base:base.console_script

        """
    )

.. note:: Generally, only the base command should be added.

Reinstall the package, then run the base command by itself or with a
subcommand:

.. code-block:: shell

    > base
    Running base command
    > base sub
    Running base command
    Sub... False
    > base sub --flag
    Running base command
    Sub... True

Subcommand Notes
----------------

- The base command's subcommand arg--i.e., its first arg--will have its
  `choices` automatically populated with the names of its subcommands (unless
  `choices` is explictly set on the subcommand arg).
- The example above doesn't require a subcommand to be passed to the base
  command, because that's probably the most common scenario. To require a
  subcommand, change `subcommand: arg(default=None)` to just `subcommand`
  (i.e., just a regular positional arg).
- Subcommands can also have subcommands, which can also have subcommands, and
  so on.
- Although subcommands are mostly intended to be run via console scripts
  rather than via `runcommands`, they *can* be imported into a project's
  `commands.py`. The base command can then be run with `runcommands base`.
  Subcommands can be run with `runcommands base base:sub` or
  `runcommands base:sub` (in the latter case, the base command(s) won't be
  run).
