Built In Commands
+++++++++++++++++

A few commands are provided out of the box. To use them in a project, import
them:

.. code-block:: python

    # E.g., commands.py at the top level of your project
    from runcommands.commands import local, remote

.. code-block:: bash

    runcommand local --help

Or call them from your own commands:

.. code-block:: python

    from runcommands import command
    from runcommands.commands import local

    @command
    def test():
        local('python -m unittest discover .')

Copy files locally
==================

.. automethod:: runcommands.commands.copy_file.implementation

Sync files with remote
======================

.. automethod:: runcommands.commands.sync.implementation

Git version
===========

.. automethod:: runcommands.commands.git_version.implementation

Run local commands
==================

.. automethod:: runcommands.commands.local.implementation

Run remote commands
===================

.. automethod:: runcommands.commands.remote.implementation
