from ..command import command
from .local import local


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
        stdout='hide', stderr='hide', echo=False, raise_on_error=False)

    if not result:
        # Not a git directory
        return None

    # Return a tag if possible
    result = local(
        ['git', 'describe', '--exact-match'],
        stdout='capture', stderr='hide', echo=False, raise_on_error=False)

    if not result:
        # Fall back to hash
        result = local(
            ['git', 'rev-parse', '--short' if short else None, 'HEAD'],
            stdout='capture', stderr='hide', echo=False, raise_on_error=False)

    if result:
        version = result.stdout.strip()
        if show:
            print(version)
        return version

    return None
