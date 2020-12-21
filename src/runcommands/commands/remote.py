import shlex
import sys

from ..args import arg
from ..command import command
from ..result import Result
from ..util import flatten_args, isatty, StreamOptions
from .local import local


@command
def remote(
    cmd: arg(container=list),
    host,
    user=None,
    port=None,
    sudo=False,
    run_as=None,
    shell="/bin/sh",
    cd=None,
    environ: arg(container=dict) = None,
    paths=(),
    # Args passed through to local command:
    stdout: arg(type=StreamOptions) = None,
    stderr: arg(type=StreamOptions) = None,
    echo=False,
    raise_on_error=True,
    dry_run=False,
) -> Result:
    """Run a remote command via SSH.

    Runs a remote shell command using ``ssh`` in a subprocess like so::

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
        port (int): SSH port on remote host.
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
        stdout: See :obj:`runcommands.commands.local`.
        stderr: See :obj:`runcommands.commands.local`.
        echo: See :obj:`runcommands.commands.local`.
        raise_on_error: See :obj:`runcommands.commands.local`.
        dry_run: See :obj:`runcommands.commands.local`.

    """
    if not isinstance(cmd, str):
        cmd = flatten_args(cmd, join=True)

    ssh_options = ["-q"]
    if isatty(sys.stdin):
        ssh_options.append("-t")
    if port is not None:
        ssh_options.extend(("-p", port))

    ssh_connection_str = f"{user}@{host}" if user else host

    remote_cmd = []

    if sudo:
        remote_cmd.extend(("sudo", "-H"))
    elif run_as:
        remote_cmd.extend(("sudo", "-H", "-u", run_as))

    remote_cmd.extend((shell, "-c"))

    inner_cmd = []

    if cd:
        inner_cmd.append(f"cd {cd}")

    if environ:
        inner_cmd.extend(f'export {k}="{v}"' for k, v in environ.items())

    if paths:
        paths_str = ":".join(paths)
        inner_cmd.append(f'export PATH="{paths_str}:$PATH"')

    inner_cmd.append(cmd)
    inner_cmd = " &&\n    ".join(inner_cmd)
    inner_cmd = f"\n    {inner_cmd}\n"
    inner_cmd = shlex.quote(inner_cmd)

    remote_cmd.append(inner_cmd)
    remote_cmd = " ".join(remote_cmd)

    args = ("ssh", ssh_options, ssh_connection_str, remote_cmd)
    return local(
        args,
        stdout=stdout,
        stderr=stderr,
        echo=echo,
        raise_on_error=raise_on_error,
        dry_run=dry_run,
    )
