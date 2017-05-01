import io
import os
import sys
from unittest import TestCase

from runcommands.commands import local, show_config

from .config import Config
from .util import replace


class TestLocalCommand(TestCase):

    def test_local_ls(self):
        config = Config()
        result = local(config, 'ls -1', cd=os.path.dirname(__file__), hide='all')
        self.assertIn('__init__.py', result.stdout_lines)
        self.assertIn('commands.cfg', result.stdout_lines)
        self.assertTrue(result)


class TestShowConfigCommand(TestCase):

    def test_show_config(self):
        config = Config()
        stdout = io.StringIO()
        with replace(sys, 'stdout', stdout):
            show_config(config, flat=True)
        result = stdout.getvalue()
        lines = result.splitlines()
        self.assertIn('run.commands_module => commands.py', lines)
        self.assertIn('run.config_file => runcommands.tests:commands.cfg', lines)
        self.assertIn('run.env => None', lines)
        self.assertIn('run.default_env => None', lines)
        self.assertIn('run.options => ', lines)
        self.assertIn('run.echo => False', lines)
        self.assertIn('run.hide => False', lines)
        self.assertIn('run.debug => False', lines)
        self.assertIn('version => X.Y.Z', lines)
