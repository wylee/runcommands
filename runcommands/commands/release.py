import datetime
import pathlib
import re

from ..command import command
from ..util import abort, printer, confirm, prompt
from .local import local


@command
def release(package: 'Name of package directory (relative to CWD)',
            version: 'Version to release' = None,
            date: 'Release data' = None,
            tag_name: 'Release tag (defaults to version)' = None,
            next_version: 'Anticipated version of next release' = None,
            prepare: 'Run release preparation tasks?' = True,
            merge: 'Run merge tasks (includes tag creation)' = True,
            create_tag: 'Create tag when merging?' = True,
            resume: 'Run resume development tasks?' = True,
            tests: 'Run tests first?' = True,
            test_command: 'Test command' = 'tox',
            yes: 'Run without being prompted for any confirmations' = False):
    """Make a release of a package.

    Tries to guess the release version based on the current version and
    the next version based on the release version.

    Steps:
        - Prepare release:
            - Update version in {package}/__init__.py
            - Update next version header in change log
            - Commit __init__.py and change log with prepare message
        - Merge to master and tag:
            - Merge current branch into master with merge message
            - Add annotated tag for latest version
        - Resume development:
            - Update version in __init__.py to next version
            - Add in-progress section for next version to change log
            - Commit __init__.py and change log with resume message

    Caveats:
        - Releases must be made from a branch other than master (e.g.,
          develop)
        - The release branch will be merged into master (this isn't
          currently configurable)
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

    def update_line(path, line_number, content):
        with path.open() as fp:
            lines = fp.readlines()
        lines[line_number] = content
        with path.open('w') as fp:
            fp.writelines(lines)

    result = local('git rev-parse --abbrev-ref HEAD', stdout='capture')
    current_branch = result.stdout.strip()
    if current_branch == 'master':
        abort(1, 'Cannot release from master branch')

    init_module = pathlib.Path.cwd() / '{package}/__init__.py'.format_map(locals())

    changelog = None
    changelog_candidates = ['CHANGELOG', 'CHANGELOG.md']
    for candidate in changelog_candidates:
        path = pathlib.Path.cwd() / candidate
        if path.is_file():
            changelog = path
            break
    if changelog is None:
        message = 'Could not find change log; tried {candidates}'
        message = message.format(candidates=', '.join(changelog_candidates))
        abort(2, message)

    # E.g.: __version__ = '1.0.dev0'
    version_re = r"^__version__ = '(?P<version>.+?)(?P<dev_marker>\.dev\d+)?'$"

    # E.g.: ## 1.0.0 - 2017-04-01
    changelog_header_re = r'^## (?P<version>.+) - (?P<date>.+)$'

    with init_module.open() as fp:
        for init_line_number, line in enumerate(fp):
            if line.startswith('__version__'):
                match = re.search(version_re, line)
                if match:
                    current_version = match.group('version')
                    if not version:
                        version = current_version
                    break
        else:
            abort(3, 'Could not find __version__ in {init_module}'.format_map(locals()))

    date = date or datetime.date.today().isoformat()

    tag_name = tag_name or version

    if next_version is None:
        next_version_re = r'^(?P<major>\d+)\.(?P<minor>\d+)(?P<rest>.*)$'
        match = re.search(next_version_re, version)
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

        if next_version is None:
            msg = 'Cannot automatically determine next version from {version}'.format_map(locals())
            abort(4, msg)

    next_version_dev = '{next_version}.dev0'.format_map(locals())

    # Find the first line that starts with '##'. Extract the version and
    # date from that line. The version must be the specified release
    # version OR the date must be the literal string 'unreleased'.
    with changelog.open() as fp:
        for changelog_line_number, line in enumerate(fp):
            if line.startswith('## '):
                match = re.search(changelog_header_re, line)
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
                        abort(5, msg)
                    break
        else:
            abort(6, 'Could not find section in change log')

    printer.info('Version:', version)
    printer.info('Tag name:', tag_name)
    printer.info('Release date:', date)
    printer.info('Next version:', next_version)
    msg = 'Continue with release?: {version} - {date}'.format_map(locals())
    yes or confirm(msg, abort_on_unconfirmed=True)

    if tests:
        printer.header('Testing...')
        local(test_command)
    else:
        printer.warning('Skipping tests')

    # Prepare
    if prepare:
        printer.header('Preparing release', version, 'on', date)

        updated_init_line = "__version__ = '{version}'\n".format_map(locals())
        updated_changelog_line = '## {version} - {date}\n'.format_map(locals())

        update_line(init_module, init_line_number, updated_init_line)
        update_line(changelog, changelog_line_number, updated_changelog_line)

        local(('git', 'diff', init_module, changelog))
        yes or confirm('Commit these changes?', abort_on_unconfirmed=True)
        msg = 'Prepare release {version}'.format_map(locals())
        msg = prompt('Commit message', default=msg)
        local(('git', 'commit', init_module, changelog, '-m', msg))

    # Merge and tag
    if merge:
        printer.header('Merging', current_branch, 'into master for release', version)
        local('git log --oneline --reverse master..')
        msg = 'Merge these changes from {current_branch} into master for release {version}?'
        msg = msg.format_map(locals())
        yes or confirm(msg, abort_on_unconfirmed=True)
        local('git checkout master')
        msg = '"Merge branch \'{current_branch}\' for release {version}"'.format_map(locals())
        local(('git', 'merge', '--no-ff', current_branch, '-m', msg))
        if create_tag:
            printer.header('Tagging release', version)
            msg = '"Release {version}"'.format_map(locals())
            local(('git', 'tag', '-a', '-m', msg, tag_name))
        local(('git', 'checkout', current_branch))

    # Resume
    if resume:
        printer.header('Resuming development at', next_version)

        updated_init_line = "__version__ = '{next_version_dev}'\n".format_map(locals())
        new_changelog_lines = [
            '## {next_version} - unreleased\n\n'.format_map(locals()),
            'In progress...\n\n',
        ]

        update_line(init_module, init_line_number, updated_init_line)

        with changelog.open() as fp:
            lines = fp.readlines()
        lines = lines[:changelog_line_number] + new_changelog_lines + lines[changelog_line_number:]
        with changelog.open('w') as fp:
            fp.writelines(lines)

        local(('git', 'diff', init_module, changelog))
        yes or confirm('Commit these changes?', abort_on_unconfirmed=True)
        msg = 'Resume development at {next_version}'.format_map(locals())
        msg = prompt('Commit message', default=msg)
        local(('git', 'commit', init_module, changelog, '-m', msg))
