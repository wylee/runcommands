Defining Commands
+++++++++++++++++

Commands are defined like so:

.. code-block:: python

    from runcommands import command

    # Pull in some pre-defined commands
    from runcommands.commands import copy_file, local

    @command
    def hello(name=None):
        """Greet someone (or the whole world)."""
        if name:
            print('Hello,', name)
        else:
            print('Hello, World')

Listing Commands
================

Once some commands are defined (and/or imported), they can be listed on
the command line like this::

    > run -l
    RunCommands 1.0a28

    Available commands:

        copy-file
        hello
        local

    For detailed help on a command: runcommands <command> --help

Showing a Command's Help/Usage
==============================

Help for a command can be shown like this::

    > run hello --help
    usage: hello [-h] [-n NAME]

    Greet someone (or the whole world)

    optional arguments:
      -h, --help            show this help message and exit
      -n NAME, --name NAME

Note that the `hello` command's docstring is shown too.
