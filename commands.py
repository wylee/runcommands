#!/usr/bin/env python3
import getpass
import importlib
import os
import shutil
import sys
import unittest


if os.path.abspath(sys.argv[0]) == os.path.abspath(__file__):
    # When running this module directly via `./commands.py` or
    # `python commands.py`:
    #
    # - Ensure virtual env is activated and minimal
    # - Ensure minimal set of dependencies are installed
    # - Ensure runcommands project directory is first in sys.path

    def check_dependency(name, dist_name=None, action=None):
        if sys.version_info > (3, 5):
            exc_type = ModuleNotFoundError  # noqa
        else:
            exc_type = ImportError
        try:
            importlib.import_module(name)
        except exc_type:
            if action:
                action(name)
            else:
                dist_name = dist_name or name
                sys.stderr.write('Run `pip install {dist_name}` first\n'.format_map(locals()))
                sys.exit(2)

    virtual_env = os.getenv('VIRTUAL_ENV')
    if not virtual_env:
        sys.stderr.write('No virtual env active\n')
        sys.stderr.write('Run `python -m venv .venv` first, then activate the virtual env\n')
        sys.exit(1)

    check_dependency('jinja2')
    check_dependency('yaml', 'pyyaml')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from runcommands import command  # noqa: E402
from runcommands.args import arg  # noqa: E402
from runcommands.commands import copy_file as _copy_file, local  # noqa: E402
from runcommands.commands import git_version, release  # noqa: E402,F401
from runcommands.commands.release import get_current_branch, get_latest_tag  # noqa: E402
from runcommands.util import abort, asset_path, confirm, printer  # noqa: E402


@command
def virtualenv(where='.venv', python='python', overwrite=False):
    exists = os.path.exists(where)

    def create():
        local((python, '-m', 'venv', where))
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
def install(where='.venv', python='python', upgrade=False, overwrite=False):
    virtualenv(where=where, python=python, overwrite=overwrite)
    pip = '{where}/bin/pip'.format(where=where)
    local((
        pip, 'install',
        ('--upgrade', '--upgrade-strategy', 'eager') if upgrade else None,
        '--editable', '.[dev]',
        ('pip', 'setuptools') if upgrade else None,
    ), echo=True)


@command
def install_completion(
    shell: arg(
        choices=('bash', 'fish'),
        help='Shell to install completion for',
    ),
    to: arg(
        help='~/.bashrc.d/runcommands.rc or ~/.config/fish/runcommands.fish',
    ) = None,
    base_command: arg(
        help='Dotted path to base command',
    ) = None,
    base_command_name: arg(
        short_option='-B',
        help='Name of base command (if different from implementation name)'
    ) = None,
    overwrite: arg(
        help='Overwrite if exists',
    ) = False,
):
    """Install command line completion script.

    Currently, bash and fish are supported. The corresponding script
    will be copied to an appropriate directory. If the script already
    exists at that location, it will be overwritten by default.

    """
    if base_command:
        if not base_command_name:
            _, base_command_name = base_command.rsplit('.', 1)
        source_base_name = 'runcommands-base-command'
        to_file_name = base_command_name
        template_type = 'string'
        template_context = {
            'base_command_path': base_command,
            'base_command_name': base_command_name,
        }
    else:
        source_base_name = 'runcommands'
        to_file_name = ''
        template_type = None
        template_context = {}

    if shell == 'bash':
        ext = 'rc'
        to = to or '~/.bashrc.d'
    elif shell == 'fish':
        ext = 'fish'
        to = to or '~/.config/fish'

    if base_command:
        to = '{to}/{base_command_name}.{ext}'.format_map(locals())

    source_path = 'runcommands:completion/{shell}/{source_base_name}.{ext}'
    source_path = source_path.format_map(locals())
    source = asset_path(source_path)

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

    _copy_file(source, destination, template=template_type, context=template_context)
    printer.info('Installed; remember to:\n    source {destination}'.format_map(locals()))


@command
def test(*tests, fail_fast=False, with_coverage=True, with_lint=True):
    original_working_directory = os.getcwd()

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
        runner.run(loader.loadTestsFromNames(tests))
    else:
        tests = loader.discover('.')
        result = runner.run(tests)
        if not result.errors:
            if with_coverage:
                coverage.stop()
                coverage.report()
            if with_lint:
                printer.header('Checking for lint...')
                # XXX: The test runner apparently changes CWD.
                os.chdir(original_working_directory)
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
def lint(show_errors: arg(help='Show errors') = True,
         disable_ignore: arg(no_inverse=True, help='Don\'t ignore any errors') = False,
         disable_noqa: arg(no_inverse=True, help='Ignore noqa directives') = False):
    result = local((
        'flake8', '.',
        '--ignore=' if disable_ignore else None,
        '--disable-noqa' if disable_noqa else None,
    ), stdout='capture', raise_on_error=False)
    pieces_of_lint = len(result.stdout_lines)
    if pieces_of_lint:
        ess = '' if pieces_of_lint == 1 else 's'
        colon = ':' if show_errors else ''
        message = ['{pieces_of_lint} piece{ess} of lint found{colon}'.format_map(locals())]
        if show_errors:
            message.append(result.stdout.rstrip())
        message = '\n'.join(message)
        abort(1, message)
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
    root = os.getcwd()

    rmdir('build', verbose)
    rmdir('dist', verbose)

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
                rmfile(os.path.join(rel_path, f), verbose)


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


@command
def make_dist(
    version: arg(help='Tag/version to release [latest tag]') = None,
    quiet=False
):
    """Make a distribution for upload to PyPI.

    Switches to the specified tag or branch, makes the distribution,
    then switches back to the original branch.

    Intended to be run from the develop branch. If a tag is already
    checked out, the develop branch will be checked out first and then
    switched back to after making the distribution.

    """
    current_branch = get_current_branch()
    original_branch = 'develop' if current_branch == 'HEAD' else current_branch
    version = version or get_latest_tag()
    stdout = 'hide' if quiet else None

    printer.header('Making dist for {version}'.format_map(locals()))

    if version != current_branch:
        if current_branch == 'HEAD':
            printer.warning('Not on a branch; checking out develop first')
        else:
            printer.info('Currently on branch', current_branch)
        printer.info('Checking out', version)
        # XXX: Hide warning about detached HEAD state
        result = local(('git', 'checkout', version), stdout=stdout, stderr='capture')
        if result.failed:
            print(result.stderr, file=sys.stderr)

    printer.info('Removing dist directory')
    rmdir('dist', verbose=not quiet)

    printer.info('Making sdist for', version)
    local('python setup.py sdist', stdout=stdout)

    if version != current_branch:
        printer.info('Switching back to', original_branch)
        # XXX: Hide message about previous HEAD state and branch info
        result = local(('git', 'checkout', original_branch), stdout='hide', stderr='capture')
        if result.failed:
            print(result.stderr, file=sys.stderr)


@command
def upload_dists(
    make: arg(help='Make dist first? [yes]') = True,
    version: arg(help='Version/tag to release [latest tag]') = None,
    quiet: arg(help='Make dist quietly? [no]') = False,
    username: arg(help='Twine username [$USER]') = None,
    password_command: arg(
        help='Command to retrieve twine password '
             '(e.g. `password-manager show-password PyPI`) '
             '[twine prompt]'
    ) = None
):
    """Upload distributions in ./dist using ``twine``."""
    if make:
        printer.header('Making and uploading distributions')
        make_dist(quiet)
    else:
        printer.header('Uploading distributions')

    dists = os.listdir('dist')
    if not dists:
        abort(1, 'No distributions found in dist directory')

    paths = [os.path.join('dist', file) for file in dists]

    printer.info('Found distributions:')
    for path in paths:
        printer.info('  -', path)

    if not confirm('Continue?'):
        abort()

    if not username:
        username = getpass.getuser()
    environ = {'TWINE_USERNAME': username}

    if password_command:
        printer.info('Retrieving password via `{password_command}`...'.format_map(locals()))
        result = local(password_command, stdout='capture')
        password = result.stdout.strip()
        environ['TWINE_PASSWORD'] = password

    printer.warning('TWINE_USERNAME:', username)
    if password:
        printer.warning('TWINE_PASSWORD:', '*' * len(password))

    for path in paths:
        if confirm('Upload dist?: {path}'.format_map(locals())):
            local(('twine', 'upload', path), environ=environ)
        else:
            printer.warning('Skipped dist:', path)


# Utilities


def rmfile(name, verbose=False):
    if os.path.isfile(name):
        os.remove(name)
        if verbose:
            printer.info('Removed file:', name)
    else:
        if verbose:
            printer.info('File not present:', name)


def rmdir(name, verbose=False):
    if os.path.isdir(name):
        shutil.rmtree(name)
        if verbose:
            printer.info('Removed directory:', name)
    else:
        if verbose:
            printer.info('Directory not present:', name)


if __name__ == '__main__':
    from runcommands.__main__ import main
    sys.exit(main())
