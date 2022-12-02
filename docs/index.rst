RunCommands Documentation
+++++++++++++++++++++++++

|project| is a simple, Python 3.7+ command runner that automatically
generates `argparse`-style console scripts from functions.

A basic run looks like this::

    > run build-static deploy --version 1.0

In this example, two commands, `build-static` and `deploy`, are being
run.

Some nice things about using `argparse` behind the scenes is that usage
is familiar and help is built in::

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
    console-scripts
    built-in-commands
    config
    api/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
