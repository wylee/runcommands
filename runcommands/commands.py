import os
import shlex
import shutil
import string
import subprocess
import sys
import tempfile

from .args import arg, bool_or
from .command import command
from .result import Result
from .util import abs_path, flatten_args, isatty, printer, StreamOptions


__all__ = ['copy_file', 'git_version', 'local', 'remote', 'sync']


@command
def copy_file(source, destination, follow_symlinks=True,
              template: arg(type=bool_or(str), choices=('format', 'string')) = False,
              context=None):
    """Copy source file to destination.

    The destination may be a file path or a directory. When it's a
    directory, the source file will be copied into the directory
    using the file's base name.

    When the source file is a template, ``context`` will be used as the
    template context. The supported template types are 'format' and
    'string'. The former uses ``str.format_map()`` and the latter uses
    ``string.Template()``.

    .. note:: :func:`shutil.copy()` from the standard library is used to
        do the copy operation.

    """
    if not template:
        # Fast path for non-templates.
        return shutil.copy(source, destination, follow_symlinks=follow_symlinks)

    if os.path.isdir(destination):
        destination = os.path.join(destination, os.path.basename(source))

    with open(source) as source:
        contents = source.read()

    if template is True or template == 'format':
        contents = contents.format_map(context)
    elif template == 'string':
        string_template = string.Template(contents)
        contents = string_template.substitute(context)
    else:
        raise ValueError('Unknown template type: %s' % template)

    with tempfile.NamedTemporaryFile('w', delete=False) as temp_file:
        temp_file.write(contents)

    path = shutil.copy(temp_file.name, destination)
    os.remove(temp_file.name)
    return path


@command
def git_version(short: 'Get short hash' = True, show: 'Print version to stdout' = False):
    """Get tag associated with HEAD; fall back to SHA1.

    If HEAD is tagged, return the tag name; otherwise fall back to
    HEAD's short SHA1 hash.

    .. note:: Only annotated tags are considered.

    .. note:: The output isn't shown by default. To show it, pass the
        ``--show`` flag.

    """
    result = local(
        ['git', 'rev-parse', '--is-inside-work-tree'],
        stdout='hide', stderr='hide', raise_on_error=False)

    if not result:
        # Not a git directory
        return None

    # Return a tag if possible
    result = local(
        ['git', 'describe', '--exact-match'],
        stdout='capture', stderr='hide', raise_on_error=False)

    if result:
        return result.stdout

    # Fall back to hash
    result = local(
        ['git', 'rev-parse', '--short' if short else None, 'HEAD'],
        stdout='capture', stderr='hide', raise_on_error=False)

    if result:
        version = result.stdout.strip()
        if show:
            print(version)
        return version

    return None


@command
def local(args,
          cd=None,
          environ: arg(type=dict) = None,
          replace_env=False,
          paths=(),
          shell: arg(type=bool) = None,
          stdout: arg(type=StreamOptions) = None,
          stderr: arg(type=StreamOptions) = None,
          echo=False,
          raise_on_error=True,
          ) -> Result:
    """Run a local command via :func:`subprocess.run`.

    Args:
        args (list|str): A list of args or a shell command.
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

    Returns:
        Result

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
        cd = os.path.normpath(os.path.abspath(cd))
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
        current_path = subprocess_env.get('PATH')
        if current_path:
            paths.append(current_path)
        path = ':'.join(paths)
        subprocess_env['PATH'] = path

    if stdout:
        stdout = StreamOptions[stdout] if isinstance(stdout, str) else stdout
        stdout = stdout.option

    if stderr:
        stderr = StreamOptions[stderr] if isinstance(stderr, str) else stderr
        stderr = stderr.option

    kwargs = {
        'cwd': cd,
        'env': subprocess_env,
        'shell': shell,
        'stdout': stdout,
        'stderr': stderr,
        'universal_newlines': True,
    }

    if echo:
        if cd_passed:
            printer.echo('{cd}>'.format_map(locals()), end=' ')
        printer.echo(args if shell else ' '.join(shlex.quote(a) for a in args))

    result = subprocess.run(args, **kwargs)
    result = Result.from_subprocess_result(result)

    if result.return_code and raise_on_error:
        raise result

    return result


@command
def remote(cmd,
           host,
           user=None,
           port=None,
           sudo=False,
           run_as=None,
           shell='/bin/sh',
           cd=None,
           environ: arg(type=dict) = None,
           paths=(),
           # Args passed through to local command:
           stdout: arg(type=StreamOptions) = None,
           stderr: arg(type=StreamOptions) = None,
           echo=False,
           raise_on_error=True,
           ) -> Result:
    """Run a remote command via SSH.

    Runs a remote shell command using ``ssh`` in a subprocess like so:

    ssh -q [-t] [<user>@]<host> [sudo [-u <run_as>] -H] /bin/sh -c '
        [cd <cd> &&]
        [export XYZ="xyz" &&]
        [export PATH="<path>" &&]
        <cmd>
    '

    Args:
        cmd (list|str): The command to run. If this is a list, it will
            be flattened into a string.
        host (str): Remote host to SSH into.
        user (str): Remote user to log in as (defaults to current local
            user).
        sudo (bool): Run the remote command as root using ``sudo``.
        run_as (str): Run the remote command as a different user using
            ``sudo -u <run_as>``.
        shell (str): The remote user's default shell will be used to run
            the remote command unless this is set to a different shell.
        cd (str): Where to run the command on the remote host.
        environ (dict): Extra environment variables to set on the remote
            host.
        paths (list): Additional paths to prepend to the remote
            ``$PATH``.
        stdout: See :func:`local`.
        stderr: See :func:`local`.
        echo: See :func:`local`.
        raise_on_error: See :func:`local`.

    """
    if not isinstance(cmd, str):
        cmd = flatten_args(cmd)
        cmd = ' '.join(cmd)

    ssh_options = ['-q']
    if isatty(sys.stdin):
        ssh_options.append('-t')
    if port is not None:
        ssh_options.extend(('-p', port))

    ssh_connection_str = '{user}@{host}'.format_map(locals()) if user else host

    remote_cmd = []

    if sudo:
        remote_cmd.extend(('sudo', '-H'))
    elif run_as:
        remote_cmd.extend(('sudo', '-H', '-u', run_as))

    remote_cmd.extend((shell, '-c'))

    inner_cmd = []

    if cd:
        inner_cmd.append('cd {cd}'.format_map(locals()))

    if environ:
        inner_cmd.extend('export {k}="{v}"'.format_map(locals()) for k, v in environ.items())

    if paths:
        inner_cmd.append('export PATH="{path}:$PATH"'.format(path=':'.join(paths)))

    inner_cmd.append(cmd)
    inner_cmd = ' &&\n    '.join(inner_cmd)
    inner_cmd = '\n    {inner_cmd}\n'.format_map(locals())
    inner_cmd = shlex.quote(inner_cmd)

    remote_cmd.append(inner_cmd)
    remote_cmd = ' '.join(remote_cmd)

    args = ('ssh', ssh_options, ssh_connection_str, remote_cmd)
    return local(args, stdout=stdout, stderr=stderr, echo=echo, raise_on_error=raise_on_error)


@command
def sync(source,
         destination,
         host,
         user=None,
         sudo=False,
         run_as=None,
         options=('-rltvz', '--no-perms', '--no-group'),
         excludes=(),
         exclude_from=None,
         delete=False,
         dry_run=False,
         mode='u=rwX,g=rwX,o=',
         quiet=True,
         pull=False,
         # Args passed through to local command:
         stdout: arg(type=StreamOptions) = None,
         stderr: arg(type=StreamOptions) = None,
         echo=False,
         raise_on_error=True,
         ) -> Result:
    """Sync files using rsync.

    By default, a local ``source`` is pushed to a remote
    ``destination``. To pull from a remote ``source`` to a local
    ``destination`` instead, pass ``pull=True``.

    """
    source = abs_path(source, keep_slash=True)
    destination = abs_path(destination, keep_slash=True)
    connection_str = '{user}@{host}'.format_map(locals()) if user else host
    push = not pull

    if sudo:
        rsync_path = ('--rsync-path', 'sudo rsync')
    elif run_as:
        rsync_path = ('--rsync-path', 'sudo -u {run_as} rsync'.format_map(locals()))
    else:
        rsync_path = None

    if push:
        destination = '{connection_str}:{destination}'.format_map(locals())
    else:
        source = '{connection_str}:{source}'.format_map(locals())

    args = (
        'rsync',
        rsync_path,
        options,
        ('--chmod', mode) if mode else None,
        tuple(('--exclude', exclude) for exclude in excludes),
        ('--exclude-from', exclude_from) if exclude_from else None,
        '--delete' if delete else None,
        '--dry-run' if dry_run else None,
        '--quiet' if quiet else None,
        source,
        destination,
    )
    return local(args, stdout=stdout, stderr=stderr, echo=echo, raise_on_error=raise_on_error)
