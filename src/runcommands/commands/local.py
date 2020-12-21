import os
import shlex
import subprocess

from ..args import arg
from ..command import command
from ..result import Result
from ..util import abs_path, flatten_args, printer, StreamOptions


@command
def local(
    args: arg(container=list),
    background=False,
    cd=None,
    environ: arg(type=dict) = None,
    replace_env=False,
    paths=(),
    shell: arg(type=bool) = None,
    stdout: arg(type=StreamOptions) = None,
    stderr: arg(type=StreamOptions) = None,
    echo=False,
    raise_on_error=True,
    dry_run=False,
) -> Result:
    """Run a local command via :func:`subprocess.run`.

    Args:
        args (list|str): A list of args or a shell command.
        background (bool): Run process in background? If this is set,
            the command will be run in the background via
            :class:`subprocess.Popen` then this function will
            immediately return. The call site will need to wait on the
            returned :class:`Popen` object using :meth:`Popen.wait` or
            by some other means (perhaps by starting another
            long-running process in the foreground).
        cd (str): Working directory to change to first.
        environ (dict): Additional environment variables to pass to the
            subprocess.
        replace_env (bool): If set, only pass env variables from
            ``environ`` to the subprocess.
        paths (list): A list of additional paths.
        shell (bool): Run as a shell command? The default is to run in
            shell mode if ``args`` is a string. This flag can be used to
            force a list of args to be run as a shell command too.
        stdout (StreamOptions): What to do with stdout (capture, hide,
            or show).
        stderr (StreamOptions): Same as ``stdout``.
        echo (bool): Whether to echo the command before running it.
        raise_on_error (bool): Whether to raise an exception when the
            subprocess returns a non-zero exit code.
        dry_run (bool): If set, print command instead of running it.

    Returns:
        - :class:`Result`: When the command is run in the foreground.
        - :class:`subprocess.Popen`: When the command is run in the
            background.

    Raises:
        Result: When the subprocess returns a non-zero exit code (and
            ``raise_on_error`` is set).

    """
    if isinstance(args, str):
        if shell is None:
            shell = True
    else:
        args = flatten_args(args, join=shell)

    if cd:
        cd = abs_path(cd)
        cd_passed = True
    else:
        cd_passed = False

    environ = {k: str(v) for k, v in (environ or {}).items()}

    if replace_env:
        subprocess_env = environ.copy()
    else:
        subprocess_env = os.environ.copy()
        if environ:
            subprocess_env.update(environ)

    if paths:
        paths = [paths] if isinstance(paths, str) else paths
        paths = [abs_path(p) for p in paths]
        current_path = subprocess_env.get("PATH")
        if current_path:
            paths.append(current_path)
        path = ":".join(paths)
        subprocess_env["PATH"] = path

    if stdout:
        stdout = StreamOptions[stdout] if isinstance(stdout, str) else stdout
        stdout = stdout.option

    if stderr:
        stderr = StreamOptions[stderr] if isinstance(stderr, str) else stderr
        stderr = stderr.option

    kwargs = {
        "cwd": cd,
        "env": subprocess_env,
        "shell": shell,
        "stdout": stdout,
        "stderr": stderr,
        "universal_newlines": True,
    }

    display_str = args if shell else " ".join(shlex.quote(a) for a in args)

    if echo:
        if cd_passed:
            printer.echo(f"{cd}>", end=" ")
        if not dry_run:
            printer.echo(display_str)

    if dry_run:
        printer.echo("[DRY RUN]", display_str)
        result = Result(args, 0, None, None)
    elif background:
        return subprocess.Popen(args, **kwargs)
    else:
        result = subprocess.run(args, **kwargs)
        result = Result.from_subprocess_result(result)

    if result.return_code and raise_on_error:
        raise result

    return result
