import datetime
import re

from taskrunner import task
from taskrunner.tasks import *
from taskrunner.util import abort, confirm, printer, prompt


@task
def install(config, where='.env', upgrade=False):
    pip = '{where}/bin/pip'.format(where=where)
    local(config, (pip, 'install', '--upgrade' if upgrade else '', '-e .[dev]'))


@task
def test(config):
    local(config, 'python -m unittest discover .')
    lint(config)


@task
def lint(config):
    result = local(config, 'flake8 taskrunner', abort_on_failure=False)
    pieces_of_lint = len(result.stdout_lines)
    if pieces_of_lint:
        s = '' if pieces_of_lint == 1 else ''
        printer.error('{pieces_of_lint} piece{s} lint found'.format_map(locals()))
    else:
        printer.success('No lint found')


@task
def release(config, version=None, date=None, tag_name=None, next_version=None, prepare=True,
            merge=True, create_tag=True, resume=True, yes=False):
    def update_line(file_name, line_number, content):
        with open(file_name) as fp:
            lines = fp.readlines()
        lines[line_number] = content
        with open(file_name, 'w') as fp:
            fp.writelines(lines)

    result = local(config, 'git rev-parse --abbrev-ref HEAD', hide='stdout')
    current_branch = result.stdout.strip()
    if current_branch != 'develop':
        abort(1, 'Must be on develop branch to make a release')

    init_module = 'taskrunner/__init__.py'
    changelog = 'CHANGELOG'

    # E.g.: __version__ = '1.0.dev0'
    version_re = r"^__version__ = '(?P<version>.+)(?P<dev_marker>\.dev\d+)'$"

    # E.g.: ## 1.0.0 - 2017-04-01
    changelog_header_re = r'^## (?P<version>.+) - (?P<date>.+)$'

    with open(init_module) as fp:
        for init_line_number, line in enumerate(fp):
            if line.startswith('__version__'):
                match = re.search(version_re, line)
                if match:
                    current_version = match.group('version')
                    if not version:
                        version = current_version
                    break
        else:
            abort(1, 'Could not find __version__ in {init_module}'.format_map(locals()))

    date = date or datetime.date.today().isoformat()

    tag_name = tag_name or version

    if next_version is None:
        next_version_re = r'^(?P<major>\d+)\.(?P<minor>\d+)(?P<rest>(\.|a|b|rc).+)?$'
        match = re.search(next_version_re, version)
        if match:
            major = match.group('major')
            minor = match.group('minor')
        if not match or not minor.isdecimal():
            msg = 'Cannot automatically determine next version from {version}'.format_map(locals())
            abort(3, msg)
        minor = int(minor)
        minor += 1
        next_version = '{major}.{minor}'.format_map(locals())

    next_version_dev = '{next_version}.dev0'.format_map(locals())

    # Find the first line that starts with '##'. Extract the version and
    # date from that line. The version must be the specified release
    # version OR the date must be the literal string 'unreleased'.
    with open(changelog) as fp:
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
                        abort(4, msg)
                    break
        else:
            abort(5, 'Could not find section in change log')

    printer.info('Version:', version)
    printer.info('Release date:', date)
    printer.info('Tag name:', tag_name)
    printer.info('Next version:', next_version)
    msg = 'Continue with release?: {version} - {date}'.format_map(locals())
    yes or confirm(config, msg, abort_on_unconfirmed=True)

    # Prepare
    if prepare:
        printer.header('Preparing release', version, 'on', date)

        updated_init_line = "__version__ = '{version}'\n".format_map(locals())
        updated_changelog_line = '## {version} - {date}\n'.format_map(locals())

        update_line(init_module, init_line_number, updated_init_line)
        update_line(changelog, changelog_line_number, updated_changelog_line)

        local(config, ('git diff', init_module, changelog))
        yes or confirm(config, 'Commit these changes?', abort_on_unconfirmed=True)
        msg = prompt('Commit message', default='Prepare release {version}'.format_map(locals()))
        msg = '-m "{msg}"'.format_map(locals())
        local(config, ('git commit', init_module, changelog, msg))

    # Merge and tag
    if merge:
        printer.header('Merging develop into master for release', version)
        local(config, 'git log --oneline --reverse master..')
        msg = 'Merge these changes from develop into master for release {version}?'
        msg = msg.format_map(locals())
        yes or confirm(config, msg, abort_on_unconfirmed=True)
        local(config, 'git checkout master')
        msg = '"Merge branch \'develop\' for release {version}"'.format_map(locals())
        local(config, ('git merge --no-ff develop -m', msg))
        if create_tag:
            printer.header('Tagging release', version)
            msg = '"Release {version}"'.format_map(locals())
            local(config, ('git tag -a -m', msg, version))
        local(config, 'git checkout develop')

    # Resume
    if resume:
        printer.header('Resuming development at', next_version)

        updated_init_line = "__version__ = '{next_version_dev}'\n".format_map(locals())
        new_changelog_lines = [
            '## {next_version} - unreleased\n\n'.format_map(locals()),
            'In progress...\n\n',
        ]

        update_line(init_module, init_line_number, updated_init_line)

        with open(changelog) as fp:
            lines = fp.readlines()
        lines = lines[:changelog_line_number] + new_changelog_lines + lines[changelog_line_number:]
        with open(changelog, 'w') as fp:
            fp.writelines(lines)

        local(config, ('git diff', init_module, changelog))
        yes or confirm(config, 'Commit these changes?', abort_on_unconfirmed=True)
        msg = prompt(
            'Commit message', default='Resume development at {next_version}'.format_map(locals()))
        msg = '-m "{msg}"'.format_map(locals())
        local(config, ('git commit', init_module, changelog, msg))
