#!/usr/bin/env python3
import datetime
import os
import re
import shutil
import sys
import unittest

if 'runcommands' not in sys.path:
    sys.path.insert(0, os.path.abspath('.'))

from runcommands import command  # noqa: E402
from runcommands.args import arg  # noqa: E402
from runcommands.commands import copy_file, git_version, local  # noqa: E402,F401
from runcommands.util import abort, asset_path, confirm, printer, prompt  # noqa: E402


@command
def virtualenv(where='.venv', python='python3', overwrite=False):
    exists = os.path.exists(where)

    def create():
        local(('virtualenv', '-p', python, where))
        printer.success(
            'Virtualenv created; activate it by running `source {where}/bin/activate`'
            .format_map(locals()))

    if exists:
        if overwrite:
            printer.warning('Overwriting virtualenv', where, 'with', python)
            shutil.rmtree(where)
            create()
        else:
            printer.info('Virtualenv', where, 'exists; pass --overwrite to re-create it')
    else:
        printer.info('Creating virtualenv', where, 'with', python)
        create()


@command
def install(where='.venv', python='python3', upgrade=False, overwrite=False):
    virtualenv(where=where, python=python, overwrite=overwrite)
    pip = '{where}/bin/pip'.format(where=where)
    local((pip, 'install', '--upgrade' if upgrade else '', '-e', '.[dev,tox]'))


@command
def install_completion(
        shell: arg(choices=('bash', 'fish'), help='Shell to install completion for'),
        to: arg(help='~/.bashrc.d/runcommands.rc or ~/.config/fish/runcommands.fish') = None,
        overwrite: 'Overwrite if exists' = False):
    """Install command line completion script.

    Currently, bash and fish are supported. The corresponding script
    will be copied to an appropriate directory. If the script already
    exists at that location, it will be overwritten by default.

    """
    if shell == 'bash':
        source = 'runcommands:completion/bash/runcommands.rc'
        to = to or '~/.bashrc.d'
    elif shell == 'fish':
        source = 'runcommands:completion/fish/runcommands.fish'
        to = to or '~/.config/fish/runcommands.fish'

    source = asset_path(source)
    destination = os.path.expanduser(to)

    if os.path.isdir(destination):
        destination = os.path.join(destination, os.path.basename(source))

    printer.info('Installing', shell, 'completion script to:\n    ', destination)

    if os.path.exists(destination):
        if overwrite:
            printer.info('Overwriting:\n    {destination}'.format_map(locals()))
        else:
            message = 'File exists. Overwrite?'.format_map(locals())
            overwrite = confirm(message, abort_on_unconfirmed=True)

    copy_file(source, destination)
    printer.info('Installed; remember to:\n    source {destination}'.format_map(locals()))


@command
def test(tests=(), fail_fast=False, with_coverage=True, with_lint=True):
    if tests:
        num_tests = len(tests)
        s = '' if num_tests == 1 else 's'
        printer.header('Running {num_tests} test{s}...'.format_map(locals()))
    else:
        coverage_message = ' with coverage' if with_coverage else ''
        printer.header('Running tests{coverage_message}...'.format_map(locals()))

    runner = unittest.TextTestRunner(failfast=fail_fast)
    loader = unittest.TestLoader()

    if with_coverage:
        from coverage import Coverage
        coverage = Coverage(source=['runcommands'])
        coverage.start()

    if tests:
        for name in tests:
            runner.run(loader.loadTestsFromName(name))
    else:
        tests = loader.discover('.')
        result = runner.run(tests)
        if not result.errors:
            if with_coverage:
                coverage.stop()
                coverage.report()
            if with_lint:
                printer.header('Checking for lint...')
                lint()


@command
def tox(envs: 'Pass -e option to tox with the specified environments' = (),
        recreate: 'Pass --recreate flag to tox' = False,
        clean: 'Remove tox directory first' = False):
    if clean:
        local('rm -rf .tox', echo=True)
    local((
        'tox',
        ('-e', ','.join(envs)) if envs else None,
        '--recreate' if recreate else None,
    ))


@command
def lint():
    result = local('flake8 .', stdout='capture', raise_on_error=False)
    pieces_of_lint = len(result.stdout_lines)
    if pieces_of_lint:
        s = '' if pieces_of_lint == 1 else 's'
        printer.error('{pieces_of_lint} piece{s} of lint found:'.format_map(locals()))
        print(result.stdout, end='')
    else:
        printer.success('No lint found')


@command
def clean(verbose=False):
    """Clean up.

    Removes:

        - ./build/
        - ./dist/
        - **/__pycache__
        - **/*.py[co]

    Skips hidden directories.

    """
    def rm(name):
        if os.path.isfile(name):
            os.remove(name)
            if verbose:
                printer.info('Removed file:', name)
        else:
            if verbose:
                printer.info('File not present:', name)

    def rmdir(name):
        if os.path.isdir(name):
            shutil.rmtree(name)
            if verbose:
                printer.info('Removed directory:', name)
        else:
            if verbose:
                printer.info('Directory not present:', name)

    root = os.getcwd()

    rmdir('build')
    rmdir('dist')

    for path, dirs, files in os.walk(root):
        rel_path = os.path.relpath(path, root)

        if rel_path == '.':
            rel_path = ''

        if rel_path.startswith('.'):
            continue

        for d in dirs:
            if d == '__pycache__':
                rmdir(os.path.join(rel_path, d))

        for f in files:
            if f.endswith('.pyc') or f.endswith('.pyo'):
                rm(os.path.join(rel_path, f))


@command
def release(version=None, date=None, tag_name=None, next_version=None, prepare=True, merge=True,
            create_tag=True, resume=True, yes=False, tests=True):

    def update_line(file_name, line_number, content):
        with open(file_name) as fp:
            lines = fp.readlines()
        lines[line_number] = content
        with open(file_name, 'w') as fp:
            fp.writelines(lines)

    result = local('git rev-parse --abbrev-ref HEAD', stdout='capture')
    current_branch = result.stdout.strip()
    if current_branch == 'master':
        abort(1, 'Cannot release from master branch')

    init_module = 'runcommands/__init__.py'
    changelog = 'CHANGELOG'

    # E.g.: __version__ = '1.0.dev0'
    version_re = r"^__version__ = '(?P<version>.+?)(?P<dev_marker>\.dev\d+)?'$"

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
            abort(3, msg)

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
    printer.info('Tag name:', tag_name)
    printer.info('Release date:', date)
    printer.info('Next version:', next_version)
    msg = 'Continue with release?: {version} - {date}'.format_map(locals())
    yes or confirm(msg, abort_on_unconfirmed=True)

    if tests:
        printer.header('Testing...')
        tox()
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
            local(('git', 'tag', '-a', '-m', msg, version))
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

        with open(changelog) as fp:
            lines = fp.readlines()
        lines = lines[:changelog_line_number] + new_changelog_lines + lines[changelog_line_number:]
        with open(changelog, 'w') as fp:
            fp.writelines(lines)

        local(('git', 'diff', init_module, changelog))
        yes or confirm('Commit these changes?', abort_on_unconfirmed=True)
        msg = 'Resume development at {next_version}'.format_map(locals())
        msg = prompt('Commit message', default=msg)
        local(('git', 'commit', init_module, changelog, '-m', msg))


@command
def build_docs(source='docs', destination='docs/_build', builder='html', clean=False):
    if clean:
        printer.info('Removing {destination}...'.format_map(locals()))
        shutil.rmtree(destination)
    local((
        'sphinx-build',
        '-b',
        builder,
        source,
        destination,
    ))


if __name__ == '__main__':
    from runcommands.__main__ import main
    sys.exit(main())
