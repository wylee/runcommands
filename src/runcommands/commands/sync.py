from ..args import arg
from ..command import command
from ..result import Result
from ..util import abs_path, StreamOptions
from .local import local


@command
def sync(
    source,
    destination,
    host,
    user=None,
    sudo=False,
    run_as=None,
    options=("-rltvz", "--no-perms", "--no-group"),
    excludes=(),
    exclude_from=None,
    delete=False,
    dry_run=False,
    mode="u=rwX,g=rwX,o=",
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
    connection_str = f"{user}@{host}" if user else host
    push = not pull

    if sudo:
        rsync_path = ("--rsync-path", "sudo rsync")
    elif run_as:
        rsync_path = ("--rsync-path", f"sudo -u {run_as} rsync")
    else:
        rsync_path = None

    if push:
        destination = f"{connection_str}:{destination}"
    else:
        source = f"{connection_str}:{source}"

    args = (
        "rsync",
        rsync_path,
        options,
        ("--chmod", mode) if mode else None,
        tuple(("--exclude", exclude) for exclude in excludes),
        ("--exclude-from", exclude_from) if exclude_from else None,
        "--delete" if delete else None,
        "--dry-run" if dry_run else None,
        "--quiet" if quiet else None,
        source,
        destination,
    )
    return local(
        args, stdout=stdout, stderr=stderr, echo=echo, raise_on_error=raise_on_error
    )
