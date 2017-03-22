RunCommands
+++++++++++

A simple command runner that uses ``argparse`` from the Python standard library
under the hood. Somewhat inspired by Invoke_. Python 3 only (3.3 and up).

This started out as an experiment to automatically generate shell commands by
inspecting function definitions. I wanted something that would allow multiple
commands to be run in succession (like make, Fabric, Invoke, etc), produce
help/usage strings like ``argparse``, allow command-line completion, and
provide an easy way to specify global environment-specific configuration.

For example::

    runcommands --env production deploy --version X.Y.Z restart

This can be broken down into three parts:

* Main script: ``runcommands --env production``
* First command: ``deploy --version X.Y.Z``
* Second command: ``restart``

``--env production`` refers to a section named ``production`` in the project's
config file (more on this below).

The commands ``deploy`` and ``restart`` are defined in the project's
``commands.py`` module (or elsewhere if the ``--module`` option is specified).

.. _Invoke: http://www.pyinvoke.org/

License
=======

MIT

Defining Commands
=================

::

    from runcommands import command

    @command
    def hello(config, name=None):
        if name:
            print('Hello,', name)
        else:
            print('Hello, World')

Listing Commands
================

::

    > runcommands --list
    RunCommands 1.0

    Available commands:

        hello

    For detailed help on a command: run <command> --help

    > runcommands hello --help
    usage: hello [-h] [-n NAME]

    optional arguments:
      -h, --help            show this help message and exit
      -n NAME, --name NAME

Running Commands
================

::

    > runcommands hello
    Hello, World
    > runcommands hello -n You
    Hello, You

Built in Commands
=================

A few commands are provided out of the box:

* ``local``
* ``remote``
* ``show_config``

To see what these do, run ``runcommands local -h``, etc.

Configuration
=============

Configuration is read from an INI file where the values are encoded as JSON.
This allows for rich values without requiring third party libraries.

A config file looks like this, with sections for different environments::

    ; commands.cfg
    [DEFAULT]
    project_name = "My Project"

    [dev]
    debug = true

    [stage]
    debug = true
    defaults.runcommands.runners.commands.remote.host = "stage_host"

    [prod]
    debug = false
    remote.host = "prod_host"
    defaults.runcommands.runners.commands.remote.host = "{remote.host}"

Accessing Config
----------------

When the above config file is read, its values can be accessed using item or
attribute syntax. The following are equivalent::

    >>> config.remote.host
    >>> config['remote']['host']

In some situations, it's convenient to be able to get at config values using
a special dotted notation::

    >> key = 'remote.host'
    >>> config._get_dotted(key)
    >>> config._get_dotted('does not exist', default='some default')

Extending Config
----------------

A config file can extend another config file using the ``extends`` key. This
example uses an "asset path" where the config file lives in a Python package
named ``mypackage``::

    extends = "mypackage:my.cfg"

A relative or absolute file system can be specified instead::

    extends = "/path/to/my.cfg"

.. note:: The same env/section will always be extended from; there's no way to
          extend from a different env/section.

Interpolation
-------------

Config values can contain Python format strings like ``{remote.host}``. These
will be replaced with the corresponding config values.

.. note:: Only works with string values.

Default Option Values
---------------------

As shown above, default option values can be specified for a command via
configuration. These defaults will take precedence over option values defined
on the command but can be overridden via command line options.

.. note:: This works whether a command is called via the command line *or*
          called directly in Python code.

Features
========

* Easy help for commands: ``runcommands hello --help``
* Global env-specific config is built in: ``runcommands --env staging deploy
  ...`` (no default envs are built in though; these must be defined as needed)
* Default env and command options can be defined in a config file

TODO
====

* Improve command line completion
* Add more documentation and examples
* Write tests
