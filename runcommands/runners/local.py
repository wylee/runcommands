import os
import pty
import shlex
import shutil
import signal
import sys
from functools import partial
from subprocess import PIPE, Popen, TimeoutExpired
from time import monotonic

from ..util import Hide, printer
from .base import Runner
from .exc import RunAborted, RunError
from .result import Result
from .streams import mirror_and_capture


class LocalRunner(Runner):

    """Run a command on the local host."""

    def run(self, cmd, cd=None, path=None, prepend_path=None, append_path=None, sudo=False,
            run_as=None, echo=False, hide=False, timeout=None, use_pty=True, debug=False):
        if isinstance(cmd, str):
            cmd_str = cmd
            exe = shlex.split(cmd)[0]
            shell = True
            if sudo:
                cmd = ' '.join(['sudo', cmd])
            elif run_as:
                cmd = ' '.join(['sudo', '-u', run_as, cmd])
        else:
            cmd_str = ' '.join(cmd)
            exe = cmd[0]
            shell = False
            if sudo:
                cmd = ['sudo'] + cmd
            elif run_as:
                cmd = ['sudo', '-u', run_as] + cmd

        cwd = os.path.normpath(os.path.abspath(cd)) if cd else None

        hide_stdout = Hide.hide_stdout(hide)
        hide_stderr = Hide.hide_stderr(hide)
        echo = echo and not hide_stdout

        use_pty = self.use_pty(use_pty)

        env = os.environ.copy()

        path = self.munge_path(path, prepend_path, append_path, os.getenv('PATH'))

        if path:
            env['PATH'] = path

        if echo:
            printer.hr(color='echo')
            printer.echo('RUNNING:', cmd_str)
            if cwd:
                printer.echo('    CWD:', cwd)
            if path:
                printer.echo('   PATH:', path)
            printer.hr(color='echo')

        out_buffer = []
        err_buffer = []

        chunk_size = 8192
        encoding = self.get_encoding()

        try:
            if use_pty:
                in_master, stdin = pty.openpty()
                out_master, stdout = pty.openpty()
                err_master, stderr = pty.openpty()
                term_size = shutil.get_terminal_size()
                env['COLUMNS'] = str(term_size.columns)
                env['LINES'] = str(term_size.lines)
            else:
                stdin = PIPE
                stdout = PIPE
                stderr = PIPE

            streams = dict(stdin=stdin, stdout=stdout, stderr=stderr)

            with Popen(cmd, bufsize=0, cwd=cwd, env=env, shell=shell, **streams) as proc:

                end_time = sys.maxsize if timeout is None else (monotonic() + timeout)

                def check_timeout():
                    if monotonic() > end_time:
                        output = b''.join(out_buffer).decode(encoding)
                        raise TimeoutExpired(proc.args, timeout, output)

                if use_pty:
                    os.close(stdin)
                    os.close(stdout)
                    os.close(stderr)
                else:
                    in_master = proc.stdin.fileno()
                    out_master = proc.stdout.fileno()
                    err_master = proc.stderr.fileno()

                in_, out, err = (
                    (sys.stdin.fileno(), in_master, True, None),
                    (out_master, sys.stdout.fileno(), not hide_stdout, out_buffer),
                    (err_master, sys.stderr.fileno(), not hide_stderr, err_buffer),
                )

                abort_requested = False
                read = partial(mirror_and_capture, in_, out, err, chunk_size)

                while True:
                    try:
                        while proc.poll() is None:
                            read()
                            check_timeout()
                        while read(finish=True):
                            check_timeout()
                        return_code = proc.returncode
                    except KeyboardInterrupt:
                        # Send SIGINT to program for handling.
                        sys.stderr.write('[Run will be aborted when current subprocess exits]\n')
                        proc.send_signal(signal.SIGINT)
                        abort_requested = True
                    except TimeoutExpired:
                        sys.stderr.write(
                            '[Run will be aborted when current subprocess exits '
                            '(due to subprocess timeout)]\n')
                        proc.terminate()
                        proc.wait()
                        raise
                    except:
                        proc.kill()
                        proc.wait()
                        raise
                    else:
                        if abort_requested:
                            raise RunAborted('\nAborted')
                        break
        except FileNotFoundError:
            raise RunAborted('Command not found: {exe}'.format(exe=exe))
        except KeyboardInterrupt:
            raise RunAborted('\nAborted')
        except TimeoutExpired:
            raise RunAborted(
                'Subprocess `{cmd_str}` timed out after {timeout}s'.format_map(locals()))
        finally:
            if use_pty:
                os.close(in_master)
                os.close(out_master)
                os.close(err_master)

        result_args = (return_code, out_buffer, err_buffer, encoding)

        if return_code:
            raise RunError(*result_args)

        return Result(*result_args)
