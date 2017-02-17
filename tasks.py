import os
import shutil

from taskrunner import task
from taskrunner.tasks import *
from taskrunner.util import print_warning


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
    local(config, 'flake8 taskrunner')
