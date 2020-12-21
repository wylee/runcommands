import datetime
import os
import pathlib
import re
from collections import namedtuple

from ..args import arg
from ..command import command
from ..util import abort, printer, confirm, prompt
from .local import local


@command
def release(
    version: "Version to release" = None,
    version_file: arg(type=pathlib.Path, help="File __version__ is in") = None,
    date: "Release data" = None,
    tag_name: "Release tag (defaults to version)" = None,
    next_version: "Anticipated version of next release" = None,
    prepare: "Run release preparation tasks?" = True,
    merge: "Run merge tasks" = True,
    target_branch: "Branch to merge into" = "master",
    create_tag: "Create tag when merging?" = True,
    resume: "Run resume development tasks?" = True,
    test: "Run tests first?" = True,
    test_command: "Test command" = "tox",
    yes: "Run without being prompted for any confirmations" = False,
):
    """Make a release.

    Tries to guess the release version based on the current version and
    the next version based on the release version.

    Steps:
        - Prepare release:
            - Update ``version`` in ``pyproject.toml`` (if present)
            - Update ``__version__`` in version file (if present;
              typically ``package/__init__.py`` or
              ``src/package/__init__.py``)
            - Update next version header in change log
            - Commit version file and change log with prepare message
        - Merge to target branch (master by default):
            - Merge current branch into target branch with merge message
        - Create tag:
            - Add annotated tag for latest version; when merging, the
              tag will point at the merge commit on the target branch;
              when not merging, the tag will point at the prepare
              release commit on the current branch
        - Resume development:
            - Update version in pyproject.toml to next version (if
              present)
            - Update version in version file to next version (if
              present)
            - Add in-progress section for next version to change log
            - Commit version file and change log with resume message

    Caveats:
        - Releases cannot be made from the target branch; some other
          branch must be checked out before running the ``release``
          command
        - The next version will have the dev marker '.dev0' appended to
          it
        - Change log must be in Markdown format; release section headers
          must be second-level (i.e., start with ##)
        - Change log must be named CHANGELOG or CHANGELOG.md
        - The first release section header in the change log will be
          updated, so there always needs to be an in-progress section
          for the next version
        - Building distributions and uploading to PyPI isn't handled;
          you'll need to run `python setup.py sdist` (for example) and
          upload the result with `twine upload` (or by some other means)

    """
    cwd = pathlib.Path.cwd()

    current_branch = get_current_branch()
    if current_branch == target_branch:
        abort(1, f"Cannot release from {target_branch} branch")

    print_step("Preparing?", prepare)
    print_step("Merging?", merge)
    print_step("Tagging?", create_tag)
    print_step("Resuming development?", resume)
    print_step("Testing?", test)

    pyproject_file = pathlib.Path("pyproject.toml")
    if pyproject_file.is_file():
        pyproject_version_info = get_current_version(pyproject_file, "version")
        (
            pyproject_version_line_number,
            pyproject_version_quote,
            pyproject_current_version,
        ) = pyproject_version_info
        printer.info("Found pyproject.toml")
    else:
        pyproject_file = None
        pyproject_version_line_number = None
        pyproject_version_quote = None
        pyproject_current_version = None

    if version_file:
        version_file = pathlib.Path(version_file)
        version_info = get_current_version(version_file)
        version_line_number, version_quote, current_version = version_info
        printer.info(f"Version file: {version_file.relative_to(cwd)}")
    else:
        version_info = find_version_file()
        if version_info is not None:
            (
                version_file,
                version_line_number,
                version_quote,
                current_version,
            ) = version_info
            printer.info(f"Found version file: {version_file.relative_to(cwd)}")
        else:
            version_file = None
            version_line_number = None
            version_quote = None
            current_version = pyproject_current_version

    if (
        current_version
        and pyproject_current_version
        and current_version != pyproject_current_version
    ):
        abort(
            2,
            f"Version in pyproject.toml and "
            f"{version_file.relative_to(cwd)} don't match",
        )

    if not version:
        if current_version:
            version = current_version
        else:
            message = (
                "Current version not set in version file, so release "
                "version needs to be passed explicitly"
            )
            abort(3, message)

    if not tag_name:
        tag_name = version

    date = date or datetime.date.today().isoformat()

    if not next_version:
        next_version = get_next_version(version)

    change_log = find_change_log()
    change_log_line_number = find_change_log_section(change_log, version)

    info = ReleaseInfo(
        current_branch,
        target_branch,
        pyproject_file,
        pyproject_version_line_number,
        pyproject_version_quote,
        version_file,
        version_line_number,
        version_quote,
        version,
        tag_name,
        date,
        next_version,
        change_log,
        change_log_line_number,
        not yes,
    )

    printer.info("Version:", info.version)
    printer.info("Tag name:", info.tag_name)
    printer.info("Release date:", info.date)
    printer.info("Next version:", info.next_version)

    if info.confirmation_required:
        msg = f"Continue with release?: {info.version} - {info.date}"
        confirm(msg, abort_on_unconfirmed=True)
    else:
        printer.warning("Continuing with release: {info.version} - {info.date}")

    if test:
        print_step_header("Testing")
        local(test_command)
    else:
        printer.warning("Skipping tests")

    if prepare:
        prepare_release(info)

    if merge:
        merge_to_target_branch(info)

    if create_tag:
        create_release_tag(info, merge)

    if resume:
        resume_development(info)


ReleaseInfo = namedtuple(
    "ReleaseInfo",
    (
        "current_branch",
        "target_branch",
        "pyproject_file",
        "pyproject_version_line_number",
        "pyproject_version_quote",
        "version_file",
        "version_line_number",
        "version_quote",
        "version",
        "tag_name",
        "date",
        "next_version",
        "change_log",
        "change_log_line_number",
        "confirmation_required",
    ),
)


# Steps


def prepare_release(info):
    version = info.version
    print_step_header("Preparing release", version, "on", info.date)

    if info.pyproject_file:
        quote = info.pyproject_version_quote
        update_line(
            info.pyproject_file,
            info.pyproject_version_line_number,
            f"version = {quote}{version}{quote}",
        )

    if info.version_file:
        quote = info.version_quote
        update_line(
            info.version_file,
            info.version_line_number,
            f"__version__ = {quote}{version}{quote}",
        )

    update_line(
        info.change_log,
        info.change_log_line_number,
        f"## {version} - {info.date}",
    )

    commit_files = info.pyproject_file, info.version_file, info.change_log
    commit_files = tuple(f for f in commit_files if f)
    local(("git", "diff", *commit_files))

    if info.confirmation_required:
        confirm("Commit these changes?", abort_on_unconfirmed=True)
    else:
        printer.warning("Committing changes")

    msg = f"Prepare release {version}"
    msg = prompt("Commit message", default=msg)
    local(("git", "commit", commit_files, "-m", msg))


def merge_to_target_branch(info):
    print_step_header(
        "Merging",
        info.current_branch,
        "into",
        info.target_branch,
        "for release",
        info.version,
    )

    local(
        (
            "git",
            "log",
            "--oneline",
            "--reverse",
            f"{info.target_branch}..",
        )
    )

    if info.confirmation_required:
        msg = (
            f"Merge these changes from {info.current_branch} "
            f"into {info.target_branch} "
            f"for release {info.version}?"
        )
        confirm(msg, abort_on_unconfirmed=True)
    else:
        printer.warning(
            "Merging changes from",
            info.current_branch,
            "into",
            info.target_branch,
            "for release",
            info.release,
        )

    local(("git", "checkout", info.target_branch))

    msg = f"Merge branch '{info.current_branch}' for release {info.version}"
    msg = prompt("Commit message", default=msg)
    local(("git", "merge", "--no-ff", info.current_branch, "-m", msg))

    local(("git", "checkout", info.current_branch))


def create_release_tag(info, merge):
    print_step_header("Tagging release", info.version)

    if merge:
        local(("git", "checkout", info.target_branch))

    local("git log -1 --oneline")

    if info.confirmation_required:
        confirmed = confirm("Tag this commit?")
    else:
        printer.warning("Tagging commit")
        confirmed = True

    if confirmed:
        msg = f"Release {info.version}"
        local(("git", "tag", "-a", "-m", msg, info.tag_name))

    if merge:
        local(("git", "checkout", info.current_branch))

    if not confirmed:
        abort()


def resume_development(info):
    next_version = info.next_version
    dev_version = f"{next_version}.dev0"
    print_step_header(f"Resuming development at {next_version} ({dev_version})")

    if info.pyproject_file:
        quote = info.pyproject_version_quote
        update_line(
            info.pyproject_file,
            info.pyproject_version_line_number,
            f"version = {quote}{dev_version}{quote}",
        )

    if info.version_file:
        quote = info.version_quote
        update_line(
            info.version_file,
            info.version_line_number,
            f"__version__ = {quote}{dev_version}{quote}",
        )

    new_change_log_lines = [
        f"## {next_version} - unreleased\n\n",
        "In progress...\n\n",
    ]
    with info.change_log.open() as fp:
        lines = fp.readlines()
    lines = (
        lines[: info.change_log_line_number]
        + new_change_log_lines
        + lines[info.change_log_line_number :]
    )
    with info.change_log.open("w") as fp:
        fp.writelines(lines)

    commit_files = info.pyproject_file, info.version_file, info.change_log
    commit_files = tuple(f for f in commit_files if f)
    local(("git", "diff", *commit_files))

    if info.confirmation_required:
        confirm("Commit these changes?", abort_on_unconfirmed=True)
    else:
        printer.warning("Committing changes")

    msg = f"Resume development at {next_version}"
    msg = prompt("Commit message", default=msg)
    local(("git", "commit", commit_files, "-m", msg))


# Utilities


def print_step(message, flag):
    printer.info(message, end=" ", flush=True)
    printer.print("yes" if flag else "no", color="green" if flag else "red")


def print_step_header(arg, *args):
    printer.hr("\n%s" % arg, *args, end="\n\n")


def get_current_branch():
    result = local("git rev-parse --abbrev-ref HEAD", stdout="capture")
    return result.stdout.strip()


def get_latest_tag():
    result = local("git rev-list --tags --max-count=1", stdout="capture")
    revision = result.stdout.strip()
    result = local(("git", "describe", "--tags", revision), stdout="capture")
    tag = result.stdout.strip()
    return tag


def find_version_file():
    # Try to find __version__ in:
    #
    # - package/__init__.py
    # - namespace_package/package/__init__.py
    # - src/package/__init__.py
    # - src/namespace_package/package/__init__.py
    cwd = pathlib.Path.cwd()
    candidates = []
    candidates.extend(cwd.glob("*/__init__.py"))
    candidates.extend(cwd.glob("*/*/__init__.py"))
    candidates.extend(cwd.glob("src/*/__init__.py"))
    candidates.extend(cwd.glob("src/*/*/__init__.py"))
    for candidate in candidates:
        result = get_current_version(candidate, "__version__", False)
        if result is not None:
            return (candidate,) + result
    candidates = "\n    ".join(str(candidate) for candidate in candidates)
    printer.warning(
        f"Could not find file containing __version__; tried:\n    {candidates}",
    )
    return None


def get_current_version(file, name, abort_on_not_found=True):
    # Extract current version from __version__ in version file.
    #
    # E.g.: __version__ = '1.0.dev0'
    version_re = (
        fr"""^{name}"""
        r""" *= *"""
        r"""(?P<quote>['"])((?P<version>.+?)(?P<dev_marker>\.dev\d+)?)?\1 *$"""
    )
    with file.open() as fp:
        for line_number, line in enumerate(fp):
            match = re.search(version_re, line)
            if match:
                return line_number, match.group("quote"), match.group("version")
    if abort_on_not_found:
        abort(4, f"Could not find {name} in {file}")


def get_next_version(current_version):
    next_version_re = r"^(?P<major>\d+)\.(?P<minor>\d+)(?P<rest>.*)$"
    match = re.search(next_version_re, current_version)

    if match:
        major = match.group("major")
        minor = match.group("minor")

        major = int(major)
        minor = int(minor)

        rest = match.group("rest")
        patch_re = r"^\.(?P<patch>\d+)$"
        match = re.search(patch_re, rest)

        if match:
            # X.Y.Z
            minor += 1
            patch = match.group("patch")
            next_version = f"{major}.{minor}.{patch}"
        else:
            pre_re = r"^(?P<pre_marker>a|b|rc)(?P<pre_version>\d+)$"
            match = re.search(pre_re, rest)
            if match:
                # X.YaZ
                pre_marker = match.group("pre_marker")
                pre_version = match.group("pre_version")
                pre_version = int(pre_version)
                pre_version += 1
                next_version = f"{major}.{minor}{pre_marker}{pre_version}"
            else:
                # X.Y or starts with X.Y (but is not X.Y.Z or X.YaZ)
                minor += 1
                next_version = f"{major}.{minor}"

        return next_version

    abort(5, f"Cannot automatically determine next version from {current_version}")


def find_change_log():
    change_log_candidates = ["CHANGELOG", "CHANGELOG.md"]
    for candidate in change_log_candidates:
        path = pathlib.Path.cwd() / candidate
        if path.is_file():
            return path
    abort(6, f"Could not find change log; tried {', '.join(change_log_candidates)}")


def find_change_log_section(change_log, version):
    # Find the first line that starts with '##'. Extract the version and
    # date from that line. The version must be the specified release
    # version OR the date must be the literal string 'unreleased'.

    # E.g.: ## 1.0.0 - unreleased
    change_log_header_re = r"^## (?P<version>.+) - (?P<date>.+)$"

    with change_log.open() as fp:
        for line_number, line in enumerate(fp):
            match = re.search(change_log_header_re, line)
            if match:
                found_version = match.group("version")
                found_date = match.group("date")
                if found_version == version:
                    if found_date != "unreleased":
                        printer.warning("Re-releasing", version)
                elif found_date == "unreleased":
                    if found_version != version:
                        printer.warning("Replacing", found_version, "with", version)
                else:
                    msg = (
                        f"Expected version {version} or release date "
                        f'"unreleased"; got:\n\n    {line}'
                    )
                    abort(7, msg)
                return line_number

    abort(8, "Could not find section in change log")


def update_line(path, line_number, content, append_newline=True):
    with path.open() as fp:
        lines = fp.readlines()
    if append_newline:
        content = content + os.linesep
    lines[line_number] = content
    with path.open("w") as fp:
        fp.writelines(lines)
