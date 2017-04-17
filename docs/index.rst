RunCommands Documentation
+++++++++++++++++++++++++

|project| is a simple, Python 3-only command runner that automatically
generates `argparse`-style console scripts from function definitions.

A basic run looks like this::

    > run --env production build-static deploy --version 1.0

In this example, two commands, `build-static` and `deploy`, are being
run with the production environment's configuration.

One nice thing about using `argparse` behind the scenes is that help
is built in::

    > run deploy --help
    usage: deploy [-h] [-v VERSION] ...

    Deploy a new version

Quick Start
===========

Check out the :doc:`quick-start` to get up and running.

Links
=====

* `Source Code (GitHub) <https://github.com/wylee/runcommands>`_

Contents
========

.. toctree::
    :maxdepth: 2

    installation
    quick-start
    defining-commands
    running-commands
    built-in-commands
    configuration
    api/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
