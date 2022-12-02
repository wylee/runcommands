#!/usr/bin/env python3
import glob
import os
import pathlib
import shutil
import subprocess
import sys
import unittest


if os.path.abspath(sys.argv[0]) == os.path.abspath(__file__):
    # When running this module directly via `./commands.py` or
    # `python commands.py`:
    #
    # - Ensure virtual env is created and dependencies are installed
    # - Ensure virtual env is activated
    # - Ensure virtual env site packages directory is at front of sys.path
    # - Ensure package src directory is first in sys.path
    if shutil.which("poetry") is None:
        sys.stderr.write("poetry not installed or not on $PATH\n")
        sys.exit(1)

    if not os.getenv("VIRTUAL_ENV"):

        def activate_venv(root="./.venv"):
            sys.stderr.write(f"Attempting to activate virtual env at {root} -> ")
            venv_root = os.path.abspath(root)
            venv_bin = os.path.join(venv_root, "bin")
            venv_python = os.path.join(venv_bin, "python")
            venv_site_packages = os.path.join(venv_root, "lib/python*/site-packages")
            if os.path.isfile(venv_python):
                paths = os.environ["PATH"].split(os.pathsep)
                for path in paths:
                    if os.path.normpath(os.path.abspath(path)) == venv_bin:
                        # Virtual env bin directory IS in $PATH
                        break
                else:
                    # Virtual env bin directory is NOT in $PATH; prepend it
                    os.environ["PATH"] = os.pathsep.join([venv_bin] + paths)
                os.environ["VIRTUAL_ENV"] = os.path.abspath(venv_root)
                for path in glob.glob(venv_site_packages):
                    sys.path.insert(0, path)
                sys.stderr.write(f"activated\n")
                return True
            sys.stderr.write(f"FAILED\n")
            return False

        if not activate_venv():
            sys.stderr.write("Creating virtual env and installing dependencies\n")
            if os.path.exists("poetry.lock"):
                os.remove("poetry.lock")
            subprocess.run(["poetry", "install"])
            activate_venv()

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


from make_release.util import get_current_branch, get_latest_tag  # noqa: E402

from runcommands import command  # noqa: E402
from runcommands.args import arg  # noqa: E402
from runcommands.commands import copy_file as _copy_file, local  # noqa: E402
from runcommands.commands import git_version  # noqa: E402,F401
from runcommands.util import (
    abort,
    asset_path,
    confirm,
    find_project_root,
    printer,
)  # noqa: E402


@command(creates=(".venv", "poetry.lock"), sources="pyproject.toml")
def install():
    """Create virtualenv & install dependencies by running `poetry install`."""
    local("poetry install")
    pathlib.Path(".venv").touch()
    pathlib.Path("poetry.lock").touch()


@command
def update():
    """Update dependencies by running `poetry update`."""
    local("poetry update")


@command
def install_completion(
    shell: arg(
        choices=("bash", "fish"),
        help="Shell to install completion for",
    ),
    to: arg(
        help="~/.bashrc.d/runcommands.rc or ~/.config/fish/runcommands.fish",
    ) = None,
    base_command: arg(
        help="Dotted path to base command",
    ) = None,
    base_command_name: arg(
        short_option="-B",
        help="Name of base command (if different from implementation name)",
    ) = None,
    overwrite: arg(
        help="Overwrite if exists",
    ) = False,
):
    """Install command line completion script.

    Currently, bash and fish are supported. The corresponding script
    will be copied to an appropriate directory. If the script already
    exists at that location, it will be overwritten by default.

    """
    if base_command:
        if not base_command_name:
            _, base_command_name = base_command.rsplit(".", 1)
        source_base_name = "runcommands-base-command"
        template_type = "string"
        template_context = {
            "base_command_path": base_command,
            "base_command_name": base_command_name,
        }
    else:
        source_base_name = "runcommands"
        template_type = None
        template_context = {}

    if shell == "bash":
        ext = "rc"
        to = to or "~/.bashrc.d"
    elif shell == "fish":
        ext = "fish"
        to = to or "~/.config/fish"

    if base_command:
        to = f"{to}/{base_command_name}.{ext}"

    source = asset_path(f"runcommands:completion/{shell}/{source_base_name}.{ext}")
    destination = os.path.expanduser(to)

    if os.path.isdir(destination):
        destination = os.path.join(destination, os.path.basename(source))

    printer.info("Installing", shell, "completion script to:\n    ", destination)

    if os.path.exists(destination):
        if overwrite:
            printer.info(f"Overwriting:\n    {destination}")
        else:
            confirm(f"File exists. Overwrite?", abort_on_unconfirmed=True)

    _copy_file(source, destination, template=template_type, context=template_context)
    printer.info(f"Installed; remember to:\n    source {destination}")


@command
def test(
    *tests,
    fail_fast=False,
    verbosity=1,
    with_coverage: arg(short_option="-c") = True,
    with_lint: arg(short_option="-l") = True,
):
    top_level_dir = find_project_root()
    os.chdir(top_level_dir)

    if tests:
        num_tests = len(tests)
        s = "" if num_tests == 1 else "s"
        printer.hr(f"Running {num_tests} test{s}")
    else:
        coverage_message = " with coverage" if with_coverage else ""
        printer.hr(f"Running tests{coverage_message}")

    runner = unittest.TextTestRunner(failfast=fail_fast, verbosity=verbosity)
    loader = unittest.TestLoader()

    if with_coverage:
        from coverage import Coverage

        source_dir = str(top_level_dir / "src/runcommands")
        coverage = Coverage(source=[source_dir])
        coverage.start()

    if tests:
        sys.path.insert(0, str(top_level_dir))
        runner.run(loader.loadTestsFromNames(tests))
    else:
        tests_dir = str(top_level_dir / "tests")
        top_level_dir = str(top_level_dir)
        tests = loader.discover(tests_dir, top_level_dir=top_level_dir)
        result = runner.run(tests)
        if not result.errors:
            if with_coverage:
                coverage.stop()
                coverage.report()
            if with_lint:
                # XXX: The test runner apparently changes CWD.
                os.chdir(top_level_dir)
                printer.hr("Checking code formatting")
                format_code(check=True)
                printer.hr("Checking for lint")
                lint()


@command
def tox(
    envs: "Pass -e option to tox with the specified environments" = (),
    recreate: "Pass --recreate flag to tox" = False,
    clean: "Remove tox directory first" = False,
):
    if clean:
        local("rm -rf .tox", echo=True)
    local(
        (
            "tox",
            ("-e", ",".join(envs)) if envs else None,
            "--recreate" if recreate else None,
        )
    )


@command
def format_code(check=False, where="./"):
    printer.header("Formatting code...")
    if check:
        check_arg = "--check"
        raise_on_error = False
    else:
        check_arg = None
        raise_on_error = True
    result = local(("black", check_arg, where), raise_on_error=raise_on_error)
    return result


@command
def lint(
    show_errors: arg(help="Show errors") = True,
    disable_ignore: arg(no_inverse=True, help="Don't ignore any errors") = False,
    disable_noqa: arg(no_inverse=True, help="Ignore noqa directives") = False,
):
    result = local(
        (
            "flake8",
            ".",
            "--ignore=" if disable_ignore else None,
            "--disable-noqa" if disable_noqa else None,
        ),
        stdout="capture",
        raise_on_error=False,
    )
    pieces_of_lint = len(result.stdout_lines)
    if pieces_of_lint:
        ess = "" if pieces_of_lint == 1 else "s"
        colon = ":" if show_errors else ""
        message = [
            f"{pieces_of_lint} piece{ess} of lint found{colon}",
        ]
        if show_errors:
            message.append(result.stdout.rstrip())
        message = "\n".join(message)
        abort(1, message)
    else:
        printer.success("No lint found")


@command
def clean(verbose=False, more=False):
    """Clean up.

    Removes:

        - ./build/
        - ./dist/
        - **/__pycache__
        - **/*.py[co]

    When more cleaning is requested, removes:

        - ./.venv/
        - ./runcommands.egg-info/
        - ./poetry.lock

    Skips hidden directories.

    """
    root = os.getcwd()

    rmdir("build", verbose)
    rmdir("dist", verbose)

    for path, dirs, files in os.walk(root):
        rel_path = os.path.relpath(path, root)

        if rel_path == ".":
            rel_path = ""

        if rel_path.startswith("."):
            continue

        for d in dirs:
            if d == "__pycache__":
                rmdir(os.path.join(rel_path, d))

        for f in files:
            if f.endswith(".pyc") or f.endswith(".pyo"):
                rmfile(os.path.join(rel_path, f), verbose)

    if more:
        rmdir(".venv", verbose)
        rmdir("runcommands.egg-info", verbose)
        rmfile("poetry.lock", verbose)


@command
def build_docs(source="docs", destination="docs/_build", builder="html", clean=False):
    if clean:
        printer.info(f"Removing {destination}...")
        shutil.rmtree(destination)
    local(("sphinx-build", "-b", builder, source, destination))


@command
def make_dist(
    version: arg(help="Tag/version to release [latest tag]") = None,
    formats=("sdist", "wheel"),
    quiet=False,
):
    """Make a distribution for upload to PyPI.

    Switches to the specified tag or branch, makes the distribution,
    then switches back to the original branch.

    Intended to be run from the ``dev`` branch. If a tag is already
    checked out, the ``dev`` branch will be checked out first and then
    switched back to after making the distribution.

    """
    current_branch = get_current_branch()
    original_branch = "dev" if current_branch == "HEAD" else current_branch
    version = version or get_latest_tag()
    stdout = "hide" if quiet else None

    printer.header(f"Making dist for {version}")

    if version != current_branch:
        if current_branch == "HEAD":
            printer.warning("Not on a branch; checking out `dev` first")
        else:
            printer.info("Currently on branch", current_branch)
        printer.info("Checking out", version)
        # XXX: Hide warning about detached HEAD state
        result = local(("git", "checkout", version), stdout=stdout, stderr="capture")
        if result.failed:
            print(result.stderr, file=sys.stderr)

    printer.info("Removing dist directory")
    rmdir("dist", verbose=not quiet)

    printer.info("Making dists for", version)
    for format_ in formats:
        local(("poetry", "build", "--format", format_), stdout=stdout)

    if version != current_branch:
        printer.info("Switching back to", original_branch)
        # XXX: Hide message about previous HEAD state and branch info
        result = local(
            ("git", "checkout", original_branch), stdout="hide", stderr="capture"
        )
        if result.failed:
            print(result.stderr, file=sys.stderr)


@command
def upload_dists(
    make: arg(help="Make dist first? [yes]") = True,
    version: arg(help="Version/tag to release [latest tag]") = None,
    quiet: arg(help="Make dist quietly? [no]") = False,
):
    """Upload distributions in ./dist using ``twine``.

    This requires a project token on PyPI, which must be saved in the
    runcommands section of ~/.pypirc::

        [runcommands]
        repository = https://upload.pypi.org/legacy/
        username = __token__
        password = <project token copied from PyPI>

    """
    if make:
        printer.header("Making and uploading distributions")
        make_dist(version=version, quiet=quiet)
    else:
        printer.header("Uploading distributions")

    dists = os.listdir("dist")
    if not dists:
        abort(1, "No distributions found in dist directory")

    paths = [os.path.join("dist", file) for file in dists]

    printer.info("Found distributions:")
    for path in paths:
        printer.info("  -", path)

    if not confirm("Continue?"):
        abort()

    for path in paths:
        if confirm(f"Upload dist?: {path}"):
            local(("twine", "upload", "--repository", "runcommands", path))
        else:
            printer.warning("Skipped dist:", path)


# Utilities


def rmfile(name, verbose=False):
    if os.path.isfile(name):
        os.remove(name)
        if verbose:
            printer.info("Removed file:", name)
    else:
        if verbose:
            printer.info("File not present:", name)


def rmdir(name, verbose=False):
    if os.path.isdir(name):
        shutil.rmtree(name)
        if verbose:
            printer.info("Removed directory:", name)
    else:
        if verbose:
            printer.info("Directory not present:", name)


if __name__ == "__main__":
    from runcommands.__main__ import main

    main()
