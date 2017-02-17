import os

from ..task import task
from ..util import abort, abs_path, args_to_str, as_list

from .exc import RunAborted, RunError
from .local import LocalRunner


__all__ = ['local', 'remote']


def get_default_prepend_path(config):
    prepend_path = as_list(config._get_dotted('bin.dirs', []))
    prepend_path = [abs_path(p, format_kwargs=config) for p in prepend_path]
    prepend_path = [p for p in prepend_path if os.path.isdir(p)]
    prepend_path = ':'.join(prepend_path)
    return prepend_path or None


@task
def local(config, cmd, cd=None, path=None, prepend_path=None, append_path=None, sudo=False,
          run_as=None, echo=False, hide=None, abort_on_failure=True, inject_context=True):
    """Run a command locally.

    Args:
        cmd (str|list): The command to run locally; if it contains
            format strings, those will be filled from ``config``
        cd: Where to run the command on the remote host
        path: Replace ``$PATH`` with path(s)
        prepend_path: Add extra path(s) to front of ``$PATH``
        append_path: Add extra path(s) to end of ``$PATH``
        sudo: Run as sudo?
        run_as: Run command as a different user with
            ``sudo -u <run_as>``

    If none of the path options are specified, the default is prepend
    ``config.bin.dirs`` to the front of ``$PATH``

    """
    if sudo and run_as:
        abort(1, 'Only one of --sudo or --run-as may be passed')
    if sudo:
        cmd = ('sudo', cmd)
    elif run_as:
        cmd = ('sudo', '-u', run_as, cmd)

    cmd = args_to_str(cmd, format_kwargs=(config if inject_context else None))

    if path is prepend_path is append_path is None:
        prepend_path = get_default_prepend_path(config)

    runner = LocalRunner()

    try:
        return runner.run(
            cmd, cd=cd, path=path, prepend_path=prepend_path, append_path=append_path, echo=echo,
            hide=hide, debug=config.debug)
    except RunAborted as exc:
        if config.debug:
            raise
        abort(1, str(exc))
    except RunError as exc:
        if abort_on_failure:
            abort(2, 'Local command failed with exit code {exc.return_code}'.format_map(locals()))
        return exc


@task
def remote(config, cmd, host=None, user=None, cd=None, path=None, prepend_path=None,
           append_path=None, sudo=False, run_as=None, echo=False, hide=None, abort_on_failure=True,
           inject_context=True):
    """Run a command on the remote host via SSH.

    Args:
        cmd (str|list): The command to run on the remote host; if it
            contains format strings, those will be filled from ``config``
        user: The user to log in as; command will be run as this user
            unless ``sudo`` or ``run_as`` is specified
        host: The remote host
        cd: Where to run the command on the remote host
        path: Replace ``$PATH`` on remote host with path(s)
        prepend_path: Add extra path(s) to front of remote ``$PATH``
        append_path: Add extra path(s) to end of remote ``$PATH``
        sudo: Run as sudo?
        run_as: Run command as a different user with
            ``sudo -u <run_as>``

    """
    cmd = args_to_str(cmd, format_kwargs=(config if inject_context else None))
    user = args_to_str(user, format_kwargs=config)
    host = args_to_str(host, format_kwargs=config)
    cd = args_to_str(cd, format_kwargs=config)
    path = args_to_str(path, format_kwargs=config)
    run_as = args_to_str(run_as, format_kwargs=config)

    if not host:
        raise ValueError('host must be specified')

    if user:
        ssh_connection_str = '{user}@{host}'.format(user=user, host=host)
    else:
        ssh_connection_str = host

    if path or prepend_path or append_path:
        if path:
            path = [path]
        else:
            path = ['$PATH']
        if prepend_path:
            path = [prepend_path] + path
        if append_path:
            path = path + [append_path]
        path = ':'.join(path)

    remote_cmd = []

    if sudo:
        remote_cmd.append('sudo')
    elif run_as and run_as != user:
        remote_cmd.append('sudo -u {run_as}'.format(run_as=run_as))

    bash_cmd = ["bash <<'EOBASH'"]
    if cd:
        bash_cmd.append('  cd {cd} || exit 1\n'.format(cd=cd))
    if path:
        bash_cmd.append('  export PATH="{path}"\n'.format(path=path))
    bash_cmd.append('  {cmd}'.format(cmd=cmd))
    bash_cmd.append('EOBASH')
    bash_cmd = '\n'.join(bash_cmd)
    remote_cmd.append(bash_cmd)

    remote_cmd = ' '.join(remote_cmd)

    # ssh -T someone@somehost sudo -u svusrXYZ bash <<'EOBASH'
    #     cd <cd> || exit 1
    #     export PATH="<path>"
    #     <cmd>
    # EOBASH
    ssh_cmd = ['ssh', '-T', ssh_connection_str, remote_cmd]

    runner = LocalRunner()

    try:
        return runner.run(ssh_cmd, echo=echo, hide=hide, debug=config.debug)
    except RunAborted as exc:
        if config.debug:
            raise
        abort(1, str(exc))
    except RunError as exc:
        if abort_on_failure:
            abort(2, 'Remote command failed with exit code {exc.return_code}'.format(**locals()))
        return exc
