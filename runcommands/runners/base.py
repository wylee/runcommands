import abc
import locale
import os
import pty
import sys

from .result import Result
from ..util import printer


class Runner(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, *args, **kwargs) -> Result:
        raise NotImplementedError('The run method must be implemented in subclasses')

    def get_encoding(self):
        return locale.getpreferredencoding(do_setlocale=False)

    def munge_path(self, path, prepend_path, append_path, env_path, delimiter=os.pathsep):
        path_specified = any(p for p in (path, prepend_path, append_path))
        if not path_specified:
            return ''
        if path:
            path = [path]
        elif env_path:
            path = [env_path]
        if prepend_path:
            path = [prepend_path] + path
        if append_path:
            path += [append_path]
        path = delimiter.join(path)
        return path

    def use_pty(self, use_pty):
        if use_pty:
            use_pty = pty and sys.stdout.isatty()
            if not use_pty:
                printer.warning('PTY requested but PTY not available')
        return use_pty
