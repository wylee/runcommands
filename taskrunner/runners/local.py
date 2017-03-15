import locale
import os
import shlex
import sys
from subprocess import PIPE, Popen, TimeoutExpired
from threading import Thread

from ..util import Hide, printer
from .base import Runner
from .exc import RunAborted, RunError
from .result import Result


class LocalRunner(Runner):

    """Run a command on the local host."""

    def run(self, cmd, cd=None, path=None, prepend_path=None, append_path=None, echo=False,
            hide=None, timeout=None, debug=False):
        if isinstance(cmd, str):
            cmd_str = cmd
            exe = shlex.split(cmd)[0]
            shell = True
        else:
            cmd_str = ' '.join(cmd)
            exe = cmd[0]
            shell = False

        cwd = os.path.normpath(os.path.abspath(cd)) if cd else None

        hide_stdout = Hide.hide_stdout(hide)
        hide_stderr = Hide.hide_stderr(hide)
        echo = echo and not hide_stdout

        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'

        munge_path = path or prepend_path or append_path

        if munge_path:
            path = [path] if path else [env['PATH']]
            if prepend_path:
                path = [prepend_path] + path
            if append_path:
                path += [append_path]
            path = ':'.join(path)
            env['PATH'] = path

        if echo:
            printer.hr(color='echo')
            printer.echo('RUNNING:', cmd_str)
            if cwd:
                printer.echo('    CWD:', cwd)
            if munge_path:
                printer.echo('   PATH:', path)
            printer.hr(color='echo')

        try:
            with Popen(cmd, bufsize=0, cwd=cwd, shell=shell, stdout=PIPE, stderr=PIPE) as proc:
                try:
                    out = NonBlockingStreamReader('out', proc.stdout, [], hide_stdout, sys.stdout)
                    err = NonBlockingStreamReader('err', proc.stderr, [], hide_stderr, sys.stderr)
                    return_code = proc.wait(timeout)
                except KeyboardInterrupt:
                    proc.kill()
                    proc.wait()
                    raise RunAborted('\nAborted')
                except TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    raise RunAborted(
                        'Subprocess {cmd_str} timed out after {timeout}s'
                        .format(**locals()))
                except Exception:
                    proc.kill()
                    proc.wait()
                    raise
        except FileNotFoundError:
            raise RunAborted('Command not found: {exe}'.format(exe=exe))

        out.join()
        err.join()

        out_str = out.get_string()
        err_str = err.get_string()

        if return_code:
            raise RunError(return_code, out_str, err_str)

        return Result(return_code, out_str, err_str)


class NonBlockingStreamReader(Thread):

    def __init__(self, name, stream, buffer, hide, file, encoding=None):
        name = '{name}-reader'.format(name=name)
        super().__init__(name=name, daemon=True)
        self.stream = stream
        self.buffer = buffer
        self.hide = hide
        self.file = file
        self.encoding = encoding or locale.getpreferredencoding(do_setlocale=False)
        self.start()

    def run(self):
        while not self.stream.closed:
            try:
                bytes_ = self.stream.readline()
            except ValueError:
                break
            if bytes_:
                text = bytes_.decode(self.encoding)
                self.buffer.append(text)
                if not self.hide:
                    self.file.write(text)
                    self.file.flush()

    def get_string(self):
        return ''.join(self.buffer)
