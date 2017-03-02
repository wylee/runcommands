from taskrunner import task
from taskrunner.tasks import *
from taskrunner.util import printer


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
