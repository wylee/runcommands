RunCommands
+++++++++++

A simple command runner that uses ``argparse`` from the Python standard library
under the hood. Python 3 only (3.3 and up).

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

See the `main documentation`_ for more information on
installation, defining & running commands, configuration, etc.

Features
========

* Multiple commands can be run in sequence: ``run --env staging build deploy``
* Commands can be run in a specified environment
* Built-in help/usage via ``argparse``
* Command line completion

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
