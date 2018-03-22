Built In Commands
+++++++++++++++++


A few commands are provided out of the box:

- `copy-file`: Copy a local file, optionally as a template.
- `git-version`: Show the tag or SHA1 corresponding to `HEAD`.
- `local`: Run a local command via :func:`subprocess.run()`.
- `remote`: Run a remote command via SSH.
- `sync`: Sync local files to remote server or vice versa using `rsync`.

These can be added to a project's command set like so:

.. code-block:: python

    # commands.py in your project
    from runcommands.commands import copy_file, git_version, local, remote, sync

To see what these do, run `run local -h`, etc.
