import os
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from .printer import printer


def abs_path(path, format_kwargs={}, relative_to=None, keep_slash=False):
    """Get abs. path for ``path``.

    ``path`` may be a relative or absolute file system path or an asset
    path. If ``path`` is already an abs. path, it will be returned as
    is. Otherwise, it will be converted into a normalized abs. path.

    If ``relative_to`` is passed *and* ``path`` is not absolute, the
    path will be joined to the specified prefix before it's made
    absolute.

    If ``path`` ends with a slash, it will be stripped unless
    ``keep_slash`` is set (for use with ``rsync``, for example).

    >>> file_path = os.path.normpath(__file__)
    >>> dir_name = os.path.dirname(file_path)
    >>> file_name = os.path.basename(file_path)
    >>> os.chdir(dir_name)
    >>>
    >>> abs_path(file_name) == file_path
    True
    >>> abs_path('runcommands.util:') == dir_name
    True
    >>> abs_path('runcommands.util:path.py') == file_path
    True
    >>> abs_path('/{xyz}', format_kwargs={'xyz': 'abc'})
    '/abc'
    >>> abs_path('banana', relative_to='/usr')
    '/usr/banana'
    >>> abs_path('/usr/banana/')
    '/usr/banana'
    >>> abs_path('banana/', relative_to='/usr', keep_slash=True)
    '/usr/banana/'
    >>> abs_path('runcommands.util:banana/', keep_slash=True) == (dir_name + '/banana/')
    True

    """
    if format_kwargs:
        path = path.format_map(format_kwargs)

    has_slash = path.endswith(os.sep)

    if os.path.isabs(path):
        path = os.path.normpath(path)
    elif ":" in path:
        path = asset_path(path, keep_slash=False)
    else:
        path = os.path.expanduser(path)
        if relative_to:
            path = os.path.join(relative_to, path)
        path = os.path.abspath(path)
        path = os.path.normpath(path)

    if has_slash and keep_slash:
        path = f"{path}{os.sep}"

    return path


def asset_path(path, format_kwargs={}, keep_slash=False):
    """Get absolute path to asset in package.

    ``path`` can be just a package name like 'package' or it can be
    a package name and a relative file system path like 'package:util'.

    If ``path`` ends with a slash, it will be stripped unless
    ``keep_slash`` is set (for use with ``rsync``, for example).

    >>> file_path = os.path.normpath(__file__)
    >>> dir_name = os.path.dirname(file_path)
    >>> file_name = os.path.basename(file_path)
    >>> os.chdir(dir_name)
    >>>
    >>> asset_path('runcommands.util') == dir_name
    True
    >>> asset_path('runcommands.util:path.py') == file_path
    True
    >>> asset_path('runcommands.util:{name}.py', format_kwargs={'name': 'path'}) == file_path
    True
    >>> asset_path('runcommands.util:dir/') == (dir_name + '/dir')
    True
    >>> asset_path('runcommands.util:dir/', keep_slash=True) == (dir_name + '/dir/')
    True

    """
    if format_kwargs:
        path = path.format_map(format_kwargs)

    has_slash = path.endswith(os.sep)

    if ":" in path:
        package_name, *rel_path = path.split(":", 1)
    else:
        package_name, rel_path = path, ()

    try:
        package = import_module(package_name)
    except ImportError:
        raise ValueError(
            f"Could not get asset path for {path}; could not import package: "
            f"{package_name}"
        )

    if not hasattr(package, "__file__"):
        raise ValueError("Can't compute path relative to namespace package")

    package_path = os.path.dirname(package.__file__)
    path = os.path.join(package_path, *rel_path)
    path = os.path.normpath(path)

    if has_slash and keep_slash:
        path = f"{path}{os.sep}"

    return path


def paths_to_str(
    paths,
    format_kwargs={},
    delimiter=os.pathsep,
    asset_paths=False,
    check_paths=False,
):
    """Convert ``paths`` to a single string.

    Args:
        paths (str|list): A string like "/a/path:/another/path" or
            a list of paths; may include absolute paths and/or asset
            paths; paths that are relative will be left relative
        format_kwargs (dict): Will be injected into each path
        delimiter (str): The string used to separate paths
        asset_paths (bool): Whether paths that look like asset paths
            will be converted to absolute paths
        check_paths (bool): Whether paths should be checked to ensure
            they exist

    """
    if not paths:
        return ""
    if isinstance(paths, str):
        paths = paths.split(delimiter)
    processed_paths = []
    for path in paths:
        original = path
        path = path.format_map(format_kwargs)
        if not os.path.isabs(path):
            if asset_paths and ":" in path:
                try:
                    path = asset_path(path)
                except ValueError:
                    path = None
        if path is not None and os.path.isdir(path):
            processed_paths.append(path)
        elif check_paths:
            printer.warning(f"Path does not exist: {path} (from {original})")
    return delimiter.join(processed_paths)


def find_project_root(start_dir="."):
    """Find the project root.

    See func:`is_project_root` for details on which directories are
    considered project roots.

    This starts in the current directory and then goes up until the file
    system root is reached. If a project root isn't found,
    a ``ValueError`` will be raised.

    """
    current_dir = Path(start_dir).resolve()
    file_system_root = Path(current_dir.root)
    checked_file_system_root = False
    while not is_project_root(current_dir):
        if current_dir == file_system_root:
            if checked_file_system_root:
                message = f"Could not find project root starting from: {start_dir}"
                raise ValueError(message)
            checked_file_system_root = True
        current_dir = current_dir.parent
    return current_dir


def is_project_root(path):
    """Is the path a project root?

    A project root is a directory that contains a source control
    subdirectory (git, hg, and svn).

    todo:: Be more inclusive.

    """
    candidates = (".git", ".hg", ".svn")
    for candidate in candidates:
        if (path / candidate).is_dir():
            return True
    return False


def module_from_path(name, path):
    """Import a file system path as a Python module.

    The module will be named ``name``.

    """
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
