Built In Commands
+++++++++++++++++


A few commands are provided out of the box::

* `local`
* `remote`
* `show-config`

These can added to a project's command set like so:

.. code-block:: python

    # commands.py in your project
    from runcommands.commands import local, remote, show_config

To see what these do, run `runcommands local -h`, etc.
