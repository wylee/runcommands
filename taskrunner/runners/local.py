import os
import shlex
import sys
import time
from queue import Empty, Queue
from subprocess import PIPE, Popen
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
                path = path + [append_path]
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
                    out = NonBlockingStreamReader(proc.stdout, [], hide_stdout, sys.stdout)
                    err = NonBlockingStreamReader(proc.stderr, [], hide_stderr, sys.stderr)
                    while proc.poll() is None:
                        out.consume()
                        err.consume()
                        time.sleep(0.1)
                    out.consume()
                    err.consume()
                    return_code = proc.wait(timeout=timeout)
                except KeyboardInterrupt:
                    proc.kill()
                    proc.wait()
                    raise RunAborted('\nAborted')
                except Exception:
                    proc.kill()
                    proc.wait()
                    raise
        except FileNotFoundError:
            raise RunAborted('Command not found: {exe}'.format(exe=exe))

        out_str = out.get_string()
        err_str = err.get_string()

        if return_code:
            raise RunError(return_code, out_str, err_str)

        return Result(return_code, out_str, err_str)


class NonBlockingStreamReader(Thread):

    def __init__(self, stream, buffer, hide, file):
        super().__init__(daemon=True)
        self.stream = stream
        self.buffer = buffer
        self.hide = hide
        self.file = file
        self.queue = Queue()
        self.start()

    def run(self):
        bytes_ = self.stream.read(128)
        while bytes_:
            self.queue.put(bytes_)
            self.stream.flush()
            bytes_ = self.stream.read(128)

    def consume(self):
        while True:
            try:
                bytes_ = self.queue.get_nowait()
            except Empty:
                return None
            else:
                # TODO: Get encoding from env
                text = bytes_.decode('utf-8')
                self.buffer.append(text)
                if not self.hide:
                    self.file.write(text)
                    self.file.flush()
                self.queue.task_done()

    def get_string(self):
        return ''.join(self.buffer)
