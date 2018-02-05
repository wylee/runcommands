import os
import pty
import shlex
import shutil
import signal
import sys
import time
from functools import partial
from subprocess import PIPE, Popen, TimeoutExpired
from time import monotonic

from ..command import command
from ..util import abort, args_to_str, abs_path, format_if, paths_to_str, printer, Hide
from .base import Runner
from .exc import RunAborted, RunError, RunValueError
from .result import Result
from .streams import mirror_and_capture


class LocalRunner(Runner):

    """Run a command on the local host."""

    def run(self, cmd, cd=None, path=None, prepend_path=None, append_path=None, sudo=False,
            run_as=None, echo=False, hide=False, timeout=None, use_pty=True, debug=False):
        if sudo and run_as:
            raise RunValueError('Only one of `sudo` or `run_as` may be specified')

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

                reset_stdin = self.unbuffer_stdin(sys.stdin)

                while True:
                    try:
                        while proc.poll() is None:
                            read()
                            check_timeout()
                            time.sleep(0.01)
                        while read(finish=True):
                            check_timeout()
                            time.sleep(0.01)
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
                    except Exception:
                        proc.kill()
                        proc.wait()
                        raise
                    else:
                        if abort_requested:
                            raise RunAborted('\nAborted')
                        break
                    finally:
                        reset_stdin()
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


@command
def local(config, cmd, cd=None, path=None, prepend_path=None, append_path=None, sudo=False,
          run_as=None, echo=False, hide=False, timeout=None, use_pty=True, abort_on_failure=True,
          inject_config=True):
    """Run a command locally.

    Args:
        cmd (str|list): The command to run locally; if it contains
            format strings, those will be filled from ``config``
        cd (str): Where to run the command on the remote host
        path (str|list): Replace ``$PATH`` with path(s)
        prepend_path (str|list): Add extra path(s) to front of ``$PATH``
        append_path (str|list): Add extra path(s) to end of ``$PATH``
        sudo (bool): Run as sudo?
        run_as (str): Run command as a different user with
            ``sudo -u <run_as>``
        inject_config (bool): Whether to inject config into the ``cmd``,
            ``cd``, the various path args, and ``run_as``

    If none of the path options are specified, the default is prepend
    ``config.bin.dirs`` to the front of ``$PATH``

    """
    debug = config.run.debug
    format_kwargs = config if inject_config else {}

    cmd = args_to_str(cmd, format_kwargs=format_kwargs)
    cd = abs_path(cd, format_kwargs) if cd else cd
    run_as = format_if(run_as, format_kwargs)

    path_converter = partial(
        paths_to_str, format_kwargs=format_kwargs, asset_paths=True, check_paths=True)

    path = path_converter(path)
    prepend_path = path_converter(prepend_path)
    append_path = path_converter(append_path)

    # Prepend default paths if no paths were specified
    path_specified = any(p for p in (path, prepend_path, append_path))
    if not path_specified:
        prepend_path = get_default_local_prepend_path(config)

    runner = LocalRunner()

    try:
        return runner.run(
            cmd, cd=cd, path=path, prepend_path=prepend_path, append_path=append_path, sudo=sudo,
            run_as=run_as, echo=echo, hide=hide, timeout=timeout, use_pty=use_pty, debug=debug)
    except RunAborted as exc:
        if debug:
            raise
        abort(1, str(exc))
    except RunError as exc:
        if abort_on_failure:
            abort(2, 'Local command failed with exit code {exc.return_code}'.format_map(locals()))
        return exc


def get_default_local_prepend_path(config):
    bin_dirs = config._get_dotted('bin.dirs', [])
    return paths_to_str(bin_dirs, format_kwargs=config, asset_paths=True, check_paths=True)
