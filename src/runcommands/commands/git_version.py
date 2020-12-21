from .. import arg, bool_or
from ..command import command
from .local import local


@command
def git_version(
    short: arg(
        type=bool_or(int),
        help="Get short hash; optionally specify minimum length of hash",
    ) = True,
    show: "Print version to stdout" = False,
):
    """Get tag associated with HEAD; fall back to SHA1.

    If HEAD is tagged, return the tag name; otherwise fall back to
    HEAD's short SHA1 hash.

    .. note:: Only annotated tags are considered.

    .. note:: When no minimum hash length is specified, the minimum
        length is determined by ``git rev-parse`` based on git's
        ``core.abbrev`` config variable.

    .. note:: The output isn't shown by default. To show it, pass the
        ``--show`` flag.

    """
    result = local(
        ["git", "rev-parse", "--is-inside-work-tree"],
        stdout="hide",
        stderr="hide",
        echo=False,
        raise_on_error=False,
    )

    if not result:
        # Not a git directory
        return None

    # Return a tag if possible
    result = local(
        ["git", "describe", "--exact-match"],
        stdout="capture",
        stderr="hide",
        echo=False,
        raise_on_error=False,
    )

    if not result:
        # Fall back to hash
        args = ["git", "rev-parse"]
        if short:
            arg = "--short" if isinstance(short, bool) else f"--short={short}"
            args.append(arg)
        args.append("HEAD")
        result = local(
            args, stdout="capture", stderr="hide", echo=False, raise_on_error=False
        )

    if result:
        version = result.stdout.strip()
        if show:
            print(version)
        return version

    return None
