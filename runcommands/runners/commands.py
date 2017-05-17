from functools import partial

from ..command import command
from ..util import abort, abs_path, args_to_str, format_if, paths_to_str

from .exc import RunAborted, RunError
from .local import LocalRunner
from .remote import RemoteRunner


__all__ = ['local', 'remote']


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


@command
def remote(config, cmd, host, user=None, cd=None, path=None, prepend_path=None,
           append_path=None, sudo=False, run_as=None, echo=False, hide=False, timeout=30,
           abort_on_failure=True, inject_config=True, strategy='ssh'):
    """Run a command on the remote host via SSH.

    Args:
        cmd (str|list): The command to run on the remote host; if it
            contains format strings, those will be filled from
            ``config``
        user (str): The user to log in as; command will be run as this
            user unless ``sudo`` or ``run_as`` is specified
        host (str): The remote host
        cd (str): Where to run the command on the remote host
        path (str|list): Replace ``$PATH`` on remote host with path(s)
        prepend_path (str|list): Add extra path(s) to front of remote
            ``$PATH``
        append_path (str|list): Add extra path(s) to end of remote
            ``$PATH``
        sudo (bool): Run as sudo?
        run_as (str): Run command as a different user with
            ``sudo -u <run_as>``
        inject_config (bool): Whether to inject config into the ``cmd``,
            ``host``, ``user``, ``cd``, the various path args, and
            ``run_as``

    """
    debug = config.run.debug
    format_kwargs = config if inject_config else {}
    path_converter = partial(paths_to_str, format_kwargs=format_kwargs)

    cmd = args_to_str(cmd, format_kwargs=format_kwargs)
    user = format_if(user, format_kwargs)
    host = format_if(host, format_kwargs)
    cd = format_if(cd, format_kwargs)
    run_as = format_if(run_as, format_kwargs)

    path = path_converter(path)
    prepend_path = path_converter(prepend_path)
    append_path = path_converter(append_path)

    runner = RemoteRunner.from_name(strategy)

    try:
        return runner.run(
            cmd, host, user=user, cd=cd, path=path, prepend_path=prepend_path,
            append_path=append_path, sudo=sudo, run_as=run_as, echo=echo, hide=hide,
            timeout=timeout, debug=debug)
    except RunAborted as exc:
        if debug:
            raise
        abort(1, str(exc))
    except RunError as exc:
        if abort_on_failure:
            abort(2, 'Remote command failed with exit code {exc.return_code}'.format_map(locals()))
        return exc
