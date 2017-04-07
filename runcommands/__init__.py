import os

from .command import DEFAULT_ENV, bool_or, command


__all__ = ['__version__', 'DEFAULT_ENV', 'bool_or', 'command']
__version__ = '1.0a14'


def configure(default_env=None):
    if default_env is not None:
        os.environ['RUNCOMMANDS_DEFAULT_ENV'] = 'dev'
