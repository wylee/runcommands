Quick Start
+++++++++++

Existing Project
================

Summary
-------

- Add `runcommands` dependency
- Add `commands.py` to top level project directory
- Import built in commands
- Write custom commands

Details
-------

First, add `runcommands` to the project's requirements. If you're using
setuptools, add it to `install_requires` in `setup.py`. Or you can add
it to your pip requirements file.

Optionally, you can just run `pip install runcommands` or use one of the
other :doc:`installation` methods.

Next, create a Python module named `commands.py` in the top level of the
project. In that module, you can import the built-in commands like this:

.. code-block:: python

    # commands.py
    from runcommands.commands import copy_file, local

And then run them like this::

    > run local --help
    usage: local [-h] [-c CD] [-e ENVIRON] [-r] [--no-replace-env] [-p PATH] [-s]
                 [--no-shell] [-S STDOUT] [--stderr STDERR] [-E] [--no-echo] [-R]
                 [--no-raise-on-error]
                 ARGS
    ...
    > run local ls
    ...

Here's how you define a custom command:

.. code-block:: python

    # commands.py
    from runcommands import command
    from runcommands.commands import copy_file, local

    @command
    def test(where='.'):
        local(['python -m unittest discover', where])

The new `test` command can be run like this::

    > run test
    ....................
