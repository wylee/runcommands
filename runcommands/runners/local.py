import os
import pty
import shlex
import sys
from subprocess import PIPE, Popen, TimeoutExpired

from ..util import Hide, printer
from .base import Runner
from .exc import RunAborted, RunError
from .result import Result
from .streams import NonBlockingStreamReader


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

        try:
            stdin = None

            if use_pty:
                out_pty_fd, stdout = pty.openpty()
                err_pty_fd, stderr = pty.openpty()
            else:
                stdout = PIPE
                stderr = PIPE

            streams = {
                'stdin': stdin,
                'stdout': stdout,
                'stderr': stderr,
            }

            with Popen(cmd, bufsize=0, cwd=cwd, env=env, shell=shell, **streams) as proc:
                if use_pty:
                    os.close(stdout)
                    os.close(stderr)

                out_stream = os.fdopen(out_pty_fd, 'rb', 0) if use_pty else proc.stdout
                err_stream = os.fdopen(err_pty_fd, 'rb', 0) if use_pty else proc.stderr

                try:
                    out = NonBlockingStreamReader('out', out_stream, hide_stdout, sys.stdout)
                    err = NonBlockingStreamReader('err', err_stream, hide_stderr, sys.stderr)
                    return_code = proc.wait(timeout=timeout)
                    out.finish()
                    err.finish()
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

        out_str = out.get_string()
        err_str = err.get_string()

        if return_code:
            raise RunError(return_code, out_str, err_str)

        return Result(return_code, out_str, err_str)
