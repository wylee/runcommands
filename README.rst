RunCommands
+++++++++++

A simple command runner that uses ``argparse`` from the Python standard
library under the hood. Runs on Python 3 only (3.5 and up). Uses annotations to
configure options.

There are two basic use cases:

1. Standalone console scripts (including scripts with subcommands).
2. Collections of commands (similar to make, Fabric, etc).

Building on these, especially #2, there are a couple of more advanced
use cases:

1. A simple orchestration/deployment tool. If you have a simple build
   process and just need to ``rsync`` some files to a server, a few
   simple commands might be all you need.
2. A wrapper for more sophisticated orchestration/deployment tools--an
   alternative to the Bash scripts you might use to drive Ansible
   playbooks and the like.

Basic Usage
===========

Define a command:

.. code-block:: python

    from runcommands import arg, command
    from runcommands.commands import local

    @command
    def test(*tests: arg(help='Specific tests to run (instead of using discovery)')):
        if tests:
            local(('python', '-m', 'unittest', tests))
        else:
            local('python -m unittest discover .')

Show its help::

    > run test -h
    test [-h] [TESTS [TESTS ...]]

    positional arguments:
      TESTS       Specific tests to run (instead of using discovery)

    optional arguments:
      -h, --help  show this help message and exit

Run it::

    > run test
    ..........
    ----------------------------------------------------------------------
    Ran 0 tests in 0.000s

    OK

Create a standalone console script using a standard setuptools entry
point:

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

See the `main documentation`_ for more information on installation,
defining & running commands, configuration, etc.

Features
========

* Easily create standalone console scripts: simply define a function and
  wrap it with the ``@command`` decorator.
* Easily create standalone console scripts that have subcommands (a la
  ``git``).
* Create collections of commands (similar to make, Fabric, etc).
* Run multiple commands in sequence: ``run build deploy``.
* Uses ``argparse`` under the hood so command line usage is familiar.
* Provides built-in help/usage for all commands via ``argparse``.
* Provides command line completion (including example scripts for bash
  and fish).

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
