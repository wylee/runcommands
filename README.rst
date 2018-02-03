RunCommands
+++++++++++

A simple command runner that uses ``argparse`` from the Python standard library
under the hood. Python 3 only (3.3 and up).

There are two basic use cases:

1. Standalone console scripts
2. Collections of commands (similar to make, Fabric, etc)

Basic Usage
===========

Define a command:

.. code-block:: python

    from runcommands import command
    from runcommands.commands import local

    @command
    def test(config):
        local(config, 'python -m unittest discover .')

Show its help::

    > runcommands test -h
    usage: test [-h]

    optional arguments:
      -h, --help  show this help message and exit

Run it::

    > runcommands test
    ..........
    ----------------------------------------------------------------------
    Ran 0 tests in 0.000s

    OK

Create a standalone console script using a standard setuptools entry point:

.. code-block:: python

    # setup.py
    setup(
        ...
        entry_points="""
        [console_scripts]
        my-test-script = package.module:test.console_script

        """
    )

Run it (after reinstalling the package)::

    > my-test-script
    ..........
    ----------------------------------------------------------------------
    Ran 0 tests in 0.000s

    OK

See the `main documentation`_ for more information on installation, defining
& running commands, configuration, etc.

Features
========

* Can be used to easily create standalone console scripts by simply defining
  functions
* Can be used to create collections of commands (similar to make, Fabric, etc)
* Can run multiple commands in sequence: ``run --env production build deploy``
* Uses ``argparse`` under the hood so that command line usage is familiar
* Provides built-in help/usage for all commands via ``argparse``
* Has a built-in system for specifying which environment a command should be
  run (``--env production`` in the previous example)
* Has a multi-layered configuration system
* Provides command line completion (including example scripts for bash and
  fish)

Documentation
=============

Detailed documentation is on `Read the Docs`_.

License
=======

MIT. See the LICENSE file in the source distribution.

TODO
====

* Improve command line completion
* Add more documentation and examples
* Write tests

.. _main documentation: http://runcommands.readthedocs.io/
.. _Read the Docs: `main documentation`_
