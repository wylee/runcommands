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
    ./commands.py install

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
