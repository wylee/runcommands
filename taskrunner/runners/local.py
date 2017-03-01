import os
import shlex
import sys
from subprocess import PIPE, Popen

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

        stdout = stderr = PIPE

        env = None
        munge_path = path or prepend_path or append_path

        if munge_path:
            env = os.environ.copy()
            path = [path] if path else [env['PATH']]
            if prepend_path:
                path = [prepend_path] + path
            if append_path:
                path = path + [append_path]
            path = ':'.join(path)
            env['PATH'] = path

        if echo:
            printer.hr()
            printer.info('RUNNING:', cmd_str)
            if cwd:
                printer.info('    CWD:', cwd)
            if munge_path:
                printer.info('   PATH:', path)
            printer.hr()

        try:
            with Popen(cmd, cwd=cwd, env=env, stdout=stdout, stderr=stderr, shell=shell) as proc:
                try:
                    out, err = proc.communicate(timeout=timeout)
                except:
                    proc.kill()
                    proc.wait()
                    raise
                return_code = proc.poll()
        except FileNotFoundError:
            raise RunAborted('Command not found: {exe}'.format(exe=exe))
        except Exception:
            raise RunAborted('Could not run command')

        out = out.decode()
        err = err.decode()

        if out and not hide_stdout:
            print(out, end='')

        if err and not hide_stderr:
            print(err, end='', file=sys.stderr)

        if return_code:
            raise RunError(return_code, out, err)

        return Result(return_code, out, err)
