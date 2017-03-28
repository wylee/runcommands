import locale
import os
import pty
import shlex
import sys
from select import select
from subprocess import PIPE, Popen, TimeoutExpired
from time import monotonic

from ..util import Hide, printer
from .base import Runner
from .exc import RunAborted, RunError
from .result import Result


class LocalRunner(Runner):

    """Run a command on the local host."""

    def run(self, cmd, cd=None, path=None, prepend_path=None, append_path=None, echo=False,
            hide=None, timeout=None, use_pty=True, debug=False):
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

        if use_pty:
            use_pty = pty and sys.stdout.isatty()
            if not use_pty:
                printer.warning('PTY not available')

        env = os.environ.copy()

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

        out_buffer = []
        err_buffer = []

        chunk_size = 8192
        encoding = locale.getpreferredencoding(do_setlocale=False)

        if use_pty:
            in_master, stdin = pty.openpty()
            out_master, stdout = pty.openpty()
            err_master, stderr = pty.openpty()
        else:
            stdin = PIPE
            stdout = PIPE
            stderr = PIPE

        streams = {
            'stdin': stdin,
            'stdout': stdout,
            'stderr': stderr,
        }

        try:
            with Popen(cmd, bufsize=0, cwd=cwd, env=env, shell=shell, **streams) as proc:
                if timeout is not None:
                    end_time = monotonic() + timeout

                if not use_pty:
                    in_master = proc.stdin.fileno()
                    out_master = proc.stdout.fileno()
                    err_master = proc.stderr.fileno()

                rstreams = [out_master, err_master, sys.stdin]

                try:
                    while proc.poll() is None:
                        rlist, wlist, xlist = select(rstreams, [], [], 0.05)

                        if out_master in rlist:
                            data = os.read(out_master, chunk_size)
                            text = data.decode(encoding)
                            out_buffer.append(text)
                            if not hide_stdout:
                                sys.stdout.write(text)
                                sys.stdout.flush()

                        if err_master in rlist:
                            data = os.read(err_master, chunk_size)
                            text = data.decode(encoding)
                            err_buffer.append(text)
                            if not hide_stderr:
                                sys.stderr.write(text)
                                sys.stderr.flush()

                        if sys.stdin in rlist:
                            in_data = os.read(sys.stdin.fileno(), chunk_size)
                            os.write(in_master, in_data)

                        if timeout is not None and monotonic() > end_time:
                            raise TimeoutExpired(proc.args, timeout, ''.join(out_buffer))

                    return_code = proc.wait()
                except:
                    proc.kill()
                    proc.wait()
                    raise
        except FileNotFoundError:
            raise RunAborted('Command not found: {exe}'.format(exe=exe))
        except KeyboardInterrupt:
            raise RunAborted('\nAborted')
        except TimeoutExpired:
            raise RunAborted('Subprocess {cmd_str} timed out after {timeout}s'.format(**locals()))

        out_string = ''.join(out_buffer)
        err_string = ''.join(err_buffer)

        if return_code:
            raise RunError(return_code, out_string, err_string)

        return Result(return_code, out_string, err_string)
