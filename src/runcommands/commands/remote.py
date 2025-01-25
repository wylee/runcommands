import shlex
import sys
from pathlib import Path

import rich.markup

from ..args import arg
from ..command import command
from ..result import Result
from ..util import flatten_args, isatty, printer, prompt, StreamOptions
from .local import local


@command
def remote(
    cmd: arg(container=list),
    host,
    user=None,
    port=None,
    sudo=False,
    run_as=None,
    sudo_prompt=False,
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
    use_shared_connection=True,
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
        sudo_prompt (bool): When set, a prompt for the sudo password
            will be shown on the *local* machine. The main use case for
            this is when the ``user`` requires a password to use sudo on
            the remote host. For passwordless sudo, this isn't needed.
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
    # Process Options --------------------------------------------------

    if not isinstance(cmd, str):
        cmd = flatten_args(cmd, join=True)

    tty_arg = "-t" if isatty(sys.stdin) else None
    port_args = ("-p", port) if port else ()
    ssh_connection_str = f"{user}@{host}" if user else host
    using_sudo = sudo or run_as

    if stdout:
        stdout = StreamOptions[stdout] if isinstance(stdout, str) else stdout

    # Build Remote Command ---------------------------------------------

    remote_cmd = []

    if sudo:
        remote_cmd.extend(("sudo", "-H"))
    elif run_as:
        remote_cmd.extend(("sudo", "-H", "-u", run_as))

    if using_sudo and sudo_prompt:
        remote_cmd.extend(("--prompt=", "--stdin"))

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

    if using_sudo and sudo_prompt:
        sudo_prompt_message = rich.markup.escape("[sudo] password")
        sudo_password = prompt(sudo_prompt_message, password=True)
    else:
        sudo_password = None

    # Start Shared SSH Connection --------------------------------------
    #
    # TODO: Extract to utility function

    if use_shared_connection:
        try:
            home = Path.home()
        except RuntimeError:
            use_shared_connection = false
            printer.warning(
                "Could not create shared SSH connection: "
                "could not determine HOME directory"
            )
        else:
            socket_path = home / ".ssh" / f"runcommands-control-{user}-{host}-{port}"
            port_args = ("-p", port) if port else ()
            shared_connection_args = (
                "-S",
                socket_path,
                "-o",
                "ControlPersist=2m",
                tty_arg,
                port_args,
                ssh_connection_str,
            )
            check_result = local(
                ("ssh", "-O", "check", shared_connection_args),
                stderr=StreamOptions.hide,
                raise_on_error=False,
            )
            if check_result.failed:
                printer.info(f"Starting shared SSH connection: {socket_path}")
                local(("ssh", "-MN", shared_connection_args))
            else:
                printer.info(f"Reusing shared SSH connection: {socket_path}")

    # Run Remote Command -----------------------------------------------

    if use_shared_connection:
        tty_arg = None

    args = ("ssh", tty_arg, port_args, ssh_connection_str, remote_cmd)

    return local(
        args,
        input=sudo_password,
        stdout=stdout,
        stderr=stderr,
        echo=echo,
        raise_on_error=raise_on_error,
        dry_run=dry_run,
    )
