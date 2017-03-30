import os

from .command import DEFAULT_ENV, command

__all__ = ['DEFAULT_ENV', 'command', '__version__']
__version__ = '1.0a13'


def configure(default_env=None):
    if default_env is not None:
        os.environ['RUNCOMMANDS_DEFAULT_ENV'] = 'dev'
