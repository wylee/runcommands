import datetime
import os
import re
import shutil

from runcommands import command
from runcommands.commands import *
from runcommands.util import abort, asset_path, confirm, printer, prompt


@command
def install(config, where='.env', upgrade=False):
    pip = '{where}/bin/pip'.format(where=where)
    local(config, (pip, 'install', '--upgrade' if upgrade else '', '-e .[dev]'))


@command
def install_completion(config, shell='bash', to='~/.bashrc.d', overwrite=True):
    """Install command line completion script.
    
    Currently, only Bash is supported. The script will be copied to the
    directory ``~/.bashrc.d`` by default. If the script already exists
    at that location, it will be overwritten by default.
    
    """
    source = 'runcommands:completion/{shell}/runcommands.rc'.format(shell=shell)
    source = asset_path(source)

    destination = os.path.expanduser(to)

    if os.path.isdir(destination):
        to = os.path.join(to, 'runcommands.rc')
        destination = os.path.join(destination, 'runcommands.rc')

    printer.info('Installing', shell, 'completion script to', to)

    if os.path.exists(destination):
        if not overwrite:
            overwrite = confirm(config, 'Overwrite?', abort_on_unconfirmed=True)
        if overwrite:
            printer.info('Overwriting', to)

    shutil.copyfile(source, destination)
    printer.info('Installed; remember to `source {to}`'.format(to=to))


@command
def test(config):
    local(config, 'python -m unittest discover .')
    lint(config)


@command
def lint(config):
    result = local(config, 'flake8 runcommands', abort_on_failure=False)
    pieces_of_lint = len(result.stdout_lines)
    if pieces_of_lint:
        s = '' if pieces_of_lint == 1 else 's'
        printer.error('{pieces_of_lint} piece{s} of lint found'.format_map(locals()))
    else:
        printer.success('No lint found')


@command
def clean(config, verbose=False):
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

    init_module = 'runcommands/__init__.py'
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
