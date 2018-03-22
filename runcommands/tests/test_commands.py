import os
from unittest import TestCase

from ..commands import local


class TestLocalCommand(TestCase):

    def test_local_ls(self):
        result = local(['ls', '-1'], cd=os.path.dirname(__file__), stdout='capture')
        self.assertIn('__init__.py', result.stdout_lines)
        self.assertTrue(result)
