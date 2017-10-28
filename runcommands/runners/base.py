import abc
import locale
import os
import pty
import sys
import termios
import tty

from .result import Result
from ..util import isatty, printer


class Runner(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, *args, **kwargs) -> Result:
        raise NotImplementedError('The run method must be implemented in subclasses')

    def unbuffer_stdin(self, stdin):
        """Make ``stdin`` char buffered instead of line buffered.

        Return a function that resets ``stdin`` to its previous buffer
        settings. This is intended to be used with try/finally like so::

        reset_stdin = self.unbuffer_stdin(sys.stdin)
        try:
            # do stuff with unbuffered stdin
        finally:
            reset_stdin()

        .. note:: This was taken from Fabric's ``char_buffered`` context
                  manager and tweaked slightly to work with try/finally.

        """
        if not isatty(stdin):
            return lambda: None

        original_term_settings = termios.tcgetattr(stdin)
        tty.setcbreak(stdin)

        def reset():
            termios.tcsetattr(stdin, termios.TCSADRAIN, original_term_settings)

        return reset

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
