Installation
++++++++++++

|project| can be installed from PyPI in the usual ways:

- `pip install runcommands`
- Add `runcommands` to `install_requires` in the project's `setup.py`
- Add `runcommands` to the project's Pip requirements file

The latest in-development version can be installed from GitHub::

    pip install https://github.com/wylee/runcommands

Development
===========

To install the project for development::

    git clone https://github.com/wylee/runcommands
    cd runcommands
    python -m venv .venv
    .venv/bin/pip install -e .[dev]

Console Scripts
===============

On installation, a handful of console scripts will be installed:

- Main: ``run``, ``runcommand``, ``runcommand``
- Completion: ``runcommands-complete``

The names of the main console script aliases can be overridden by setting the
``RUNCOMMANDS_CONSOLE_SCRIPTS`` environment variable to a space-separated list
of script names. For example, to install just one alias of the main console
script:

.. code-block:: shell

    RUNCOMMANDS_CONSOLE_SCRIPTS="runcommand" pip install -e .[dev]

Or you can use a custom name:

.. code-block:: shell

    RUNCOMMANDS_CONSOLE_SCRIPTS="do-stuff" pip install -e .[dev]

If ``RUNCOMMANDS_CONSOLE_SCRIPTS`` is set to an empty string or other non-
truthy value, the main console script won't be installed at all.

Likewise, to disable installation of the ``runcommands-complete`` command, set
``RUNCOMMANDS_INSTALL_COMPLETE_CONSOLE_SCRIPT`` to an empty string or other
non-truthy value:

.. code-block:: shell

    RUNCOMMANDS_INSTALL_COMPLETE_CONSOLE_SCRIPT="no" pip install -e .[dev]

There's also a standalone ``make-release`` script that's *not* installed by
default. It can be installed like this:

.. code-block:: shell

    RUNCOMMANDS_INSTALL_RELEASE_CONSOLE_SCRIPT="yes" pip install -e .[dev]

Shell Completion
================

.. note:: Only Bash and Fish completion are currently supported.

Copy the `completion script`_ from the source distribution into
`~/.bashrc`, `~/.config/fish`, or some other file that you `source` into
your profile.  Make sure you `source` the completion script after
initially copying the completion script.

Alternatively, if you've cloned the |project| repo, you can `run
install-completion` from the project directory.

.. _completion script: https://github.com/wylee/runcommands/blob/master/runcommands/completion
