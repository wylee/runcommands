import datetime
import pathlib
import re
from collections import namedtuple

from ..args import arg
from ..command import command
from ..util import abort, printer, confirm, prompt
from .local import local


@command
def release(version: 'Version to release' = None,
            version_file: arg(type=pathlib.Path, help='File __version__ is in') = None,
            date: 'Release data' = None,
            tag_name: 'Release tag (defaults to version)' = None,
            next_version: 'Anticipated version of next release' = None,
            prepare: 'Run release preparation tasks?' = True,
            merge: 'Run merge tasks' = True,
            target_branch: 'Branch to merge into' = 'master',
            create_tag: 'Create tag when merging?' = True,
            resume: 'Run resume development tasks?' = True,
            test: 'Run tests first?' = True,
            test_command: 'Test command' = 'tox',
            yes: 'Run without being prompted for any confirmations' = False):
    """Make a release.

    Tries to guess the release version based on the current version and
    the next version based on the release version.

    Steps:
        - Prepare release:
            - Update ``__version__`` in version file (typically
              ``package/__init__.py`` or ``src/package/__init__.py``)
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
            - Update version in version file to next version
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
    current_branch = get_current_branch()
    if current_branch == target_branch:
        abort(1, 'Cannot release from {target_branch} branch'.format_map(locals()))

    print_step('Preparing?', prepare)
    print_step('Merging?', merge)
    print_step('Tagging?', create_tag)
    print_step('Resuming development?', resume)
    print_step('Testing?', test)

    if not version_file:
        version_file, version_line_number, current_version = find_version_file()
    else:
        version_line_number, current_version = get_current_version(version_file)

    if not version:
        if current_version:
            version = current_version
        else:
            message = (
                'Current version not set in version file, so release version needs to be passed '
                'explicitly')
            abort(2, message)

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
        version_file,
        version_line_number,
        version,
        tag_name,
        date,
        next_version,
        change_log,
        change_log_line_number,
        not yes,
    )

    printer.info('Version:', info.version)
    printer.info('Tag name:', info.tag_name)
    printer.info('Release date:', info.date)
    printer.info('Next version:', info.next_version)

    if info.confirmation_required:
        msg = 'Continue with release?: {info.version} - {info.date}'.format(info=info)
        confirm(msg, abort_on_unconfirmed=True)
    else:
        printer.warning('Continuing with release: {info.version} - {info.date}')

    if test:
        print_step_header('Testing')
        local(test_command)
    else:
        printer.warning('Skipping tests')

    if prepare:
        prepare_release(info)

    if merge:
        merge_to_target_branch(info)

    if create_tag:
        create_release_tag(info, merge)

    if resume:
        resume_development(info)


ReleaseInfo = namedtuple('ReleaseInfo', (
    'current_branch',
    'target_branch',
    'version_file',
    'version_line_number',
    'version',
    'tag_name',
    'date',
    'next_version',
    'change_log',
    'change_log_line_number',
    'confirmation_required',
))


# Steps


def prepare_release(info):
    print_step_header('Preparing release', info.version, 'on', info.date)

    updated_init_line = "__version__ = '{info.version}'\n".format_map(locals())
    updated_change_log_line = '## {info.version} - {info.date}\n'.format_map(locals())

    update_line(info.version_file, info.version_line_number, updated_init_line)
    update_line(info.change_log, info.change_log_line_number, updated_change_log_line)

    local(('git', 'diff', info.version_file, info.change_log))

    if info.confirmation_required:
        confirm('Commit these changes?', abort_on_unconfirmed=True)
    else:
        printer.warning('Committing changes')

    msg = 'Prepare release {info.version}'.format_map(locals())
    msg = prompt('Commit message', default=msg)
    local(('git', 'commit', info.version_file, info.change_log, '-m', msg))


def merge_to_target_branch(info):
    print_step_header(
        'Merging', info.current_branch, 'into', info.target_branch, 'for release', info.version)

    local(('git', 'log', '--oneline', '--reverse', '{info.target_branch}..'.format_map(locals())))

    if info.confirmation_required:
        msg = (
            'Merge these changes from {info.current_branch} '
            'into {info.target_branch} '
            'for release {info.version}?')
        msg = msg.format_map(locals())
        confirm(msg, abort_on_unconfirmed=True)
    else:
        printer.warning(
            'Merging changes from', info.current_branch,
            'into', info.target_branch,
            'for release', info.release)

    local(('git', 'checkout', info.target_branch))

    msg = '"Merge branch \'{info.current_branch}\' for release {info.version}"'
    msg = msg.format_map(locals())
    msg = prompt('Commit message', default=msg)
    local(('git', 'merge', '--no-ff', info.current_branch, '-m', msg))

    local(('git', 'checkout', info.current_branch))


def create_release_tag(info, merge):
    print_step_header('Tagging release', info.version)

    if merge:
        local(('git', 'checkout', info.target_branch))

    local('git log -1 --oneline')

    if info.confirmation_required:
        confirmed = confirm('Tag this commit?')
    else:
        printer.warning('Tagging commit')
        confirmed = True

    if confirmed:
        msg = '"Release {info.version}"'.format_map(locals())
        local(('git', 'tag', '-a', '-m', msg, info.tag_name))

    if merge:
        local(('git', 'checkout', info.current_branch))

    if not confirmed:
        abort()


def resume_development(info):
    print_step_header('Resuming development at', info.next_version)

    updated_init_line = "__version__ = '{info.next_version}.dev0'\n".format_map(locals())
    new_change_log_lines = [
        '## {info.next_version} - unreleased\n\n'.format_map(locals()),
        'In progress...\n\n',
    ]

    update_line(info.version_file, info.version_line_number, updated_init_line)

    with info.change_log.open() as fp:
        lines = fp.readlines()

    lines = (
        lines[:info.change_log_line_number] +
        new_change_log_lines +
        lines[info.change_log_line_number:]
    )

    with info.change_log.open('w') as fp:
        fp.writelines(lines)

    local(('git', 'diff', info.version_file, info.change_log))

    if info.confirmation_required:
        confirm('Commit these changes?', abort_on_unconfirmed=True)
    else:
        printer.warning('Committing changes')

    msg = 'Resume development at {info.next_version}'.format_map(locals())
    msg = prompt('Commit message', default=msg)
    local(('git', 'commit', info.version_file, info.change_log, '-m', msg))


# Utilities


def print_step(message, flag):
    printer.info(message, end=' ', flush=True)
    printer.print('yes' if flag else 'no', color='green' if flag else 'red')


def print_step_header(arg, *args):
    printer.hr('\n%s' % arg, *args, end='\n\n')


def get_current_branch():
    result = local('git rev-parse --abbrev-ref HEAD', stdout='capture')
    return result.stdout.strip()


def get_latest_tag():
    result = local('git rev-list --tags --max-count=1', stdout='capture')
    revision = result.stdout.strip()
    result = local(('git', 'describe', '--tags', revision), stdout='capture')
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
    candidates.extend(cwd.glob('*/__init__.py'))
    candidates.extend(cwd.glob('*/*/__init__.py'))
    candidates.extend(cwd.glob('src/*/__init__.py'))
    candidates.extend(cwd.glob('src/*/*/__init__.py'))
    for candidate in candidates:
        result = get_current_version(candidate, False)
        if result is not None:
            return (candidate,) + result
    candidates = '\n    '.join(str(candidate) for candidate in candidates)
    message = 'Could not find file containing __version__; tried:\n    {candidates}'
    message = message.format_map(locals())
    abort(3, message)


def get_current_version(version_file, abort_on_not_found=True):
    # Extract current version from __version__ in version file.
    #
    # E.g.: __version__ = '1.0.dev0'
    version_re = r"""^__version__ *= *(['"])((?P<version>.+?)(?P<dev_marker>\.dev\d+)?)?\1 *$"""
    with version_file.open() as fp:
        for line_number, line in enumerate(fp):
            match = re.search(version_re, line)
            if match:
                return line_number, match.group('version')
    if abort_on_not_found:
        abort(4, 'Could not find __version__ in {version_file}'.format_map(locals()))


def get_next_version(current_version):
    next_version_re = r'^(?P<major>\d+)\.(?P<minor>\d+)(?P<rest>.*)$'
    match = re.search(next_version_re, current_version)
    if match:
        major = match.group('major')
        minor = match.group('minor')

        major = int(major)
        minor = int(minor)

        rest = match.group('rest')
        patch_re = r'^\.(?P<patch>\d+)$'
        match = re.search(patch_re, rest)

        if match:
            # X.Y.Z
            minor += 1
            patch = match.group('patch')
            next_version = '{major}.{minor}.{patch}'.format_map(locals())
        else:
            pre_re = r'^(?P<pre_marker>a|b|rc)(?P<pre_version>\d+)$'
            match = re.search(pre_re, rest)
            if match:
                # X.YaZ
                pre_marker = match.group('pre_marker')
                pre_version = match.group('pre_version')
                pre_version = int(pre_version)
                pre_version += 1
                next_version = '{major}.{minor}{pre_marker}{pre_version}'.format_map(locals())
            else:
                # X.Y or starts with X.Y (but is not X.Y.Z or X.YaZ)
                minor += 1
                next_version = '{major}.{minor}'.format_map(locals())

        return next_version

    msg = 'Cannot automatically determine next version from {version}'.format_map(locals())
    abort(5, msg)


def find_change_log():
    change_log_candidates = ['CHANGELOG', 'CHANGELOG.md']
    for candidate in change_log_candidates:
        path = pathlib.Path.cwd() / candidate
        if path.is_file():
            return path
    message = 'Could not find change log; tried {candidates}'
    message = message.format(candidates=', '.join(change_log_candidates))
    abort(6, message)


def find_change_log_section(change_log, version):
    # Find the first line that starts with '##'. Extract the version and
    # date from that line. The version must be the specified release
    # version OR the date must be the literal string 'unreleased'.

    # E.g.: ## 1.0.0 - unreleased
    change_log_header_re = r'^## (?P<version>.+) - (?P<date>.+)$'

    with change_log.open() as fp:
        for line_number, line in enumerate(fp):
            match = re.search(change_log_header_re, line)
            if match:
                found_version = match.group('version')
                found_date = match.group('date')
                if found_version == version:
                    if found_date != 'unreleased':
                        printer.warning('Re-releasing', version)
                elif found_date == 'unreleased':
                    if found_version != version:
                        printer.warning('Replacing', found_version, 'with', version)
                else:
                    msg = (
                        'Expected version {version} or release date "unreleased"; got:\n\n'
                        '    {line}'
                    ).format_map(locals())
                    abort(7, msg)
                return line_number

    abort(8, 'Could not find section in change log')


def update_line(path, line_number, content):
    with path.open() as fp:
        lines = fp.readlines()
    lines[line_number] = content
    with path.open('w') as fp:
        fp.writelines(lines)
