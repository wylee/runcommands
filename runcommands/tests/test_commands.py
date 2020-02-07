import os
from unittest import TestCase

from .. import arg, command, subcommand
from ..commands import local


class Result:

    def __init__(self, return_code):
        self.return_code = return_code


class TestLocalCommand(TestCase):

    def test_local_ls(self):
        result = local(['ls', '-1'], cd=os.path.dirname(__file__), stdout='capture')
        self.assertIn('__init__.py', result.stdout_lines)
        self.assertTrue(result)


@command
def base(subcommand: arg(default=None)):
    return Result('base {subcommand}'.format_map(locals()))


@subcommand(base)
def sub(subcommand: arg(default=None), optional=None):
    return Result('sub {subcommand} {optional}'.format_map(locals()))


@subcommand(sub)
def subsub(positional, optional=None):
    return Result('subsub {positional} {optional}'.format_map(locals()))


class TestSubcommand(TestCase):

    def test_base_command_subcommand_choices(self):
        arg = base.args['subcommand']
        self.assertIsNotNone(arg.choices)
        self.assertEqual(arg.choices, ['sub'])

    def test_call_base_command(self):
        result = base.console_script(argv=[])
        self.assertEqual(result, 'base None')

    def test_call_subcommand(self):
        result = base.console_script(argv=['sub'])
        self.assertEqual(result, 'sub None None')

    def test_call_subcommand_with_optional(self):
        result = base.console_script(argv=['sub', '--optional', 'b'])
        self.assertEqual(result, 'sub None b')

    def test_call_subsubcommand(self):
        result = base.console_script(argv=['sub', 'subsub', 'a'])
        self.assertEqual(result, 'subsub a None')

    def test_call_subsubcommand_with_optional(self):
        result = base.console_script(argv=['sub', 'subsub', 'a', '--optional', 'b'])
        self.assertEqual(result, 'subsub a b')

    def test_call_subsubcommand_with_shared_args(self):
        @command
        def base1(cmd, a=None):
            return Result('base1({cmd}, {a})'.format_map(locals()))

        @subcommand(base1)
        def sub1(cmd: arg(default=None), a=None, flag=True):
            return Result('sub1({cmd}, {a}, {flag})'.format_map(locals()))

        @sub1.subcommand
        def subsub1(a=None, flag=True):
            return Result('subsub1({a}, {flag})'.format_map(locals()))

        result = base1.console_script(argv=['-a', 'A', 'sub1', '--no-flag'])
        self.assertEqual(result, 'sub1(None, A, False)')

        result = base1.console_script(argv=['-a', 'A', 'sub1', '--no-flag', 'subsub1'])
        self.assertEqual(result, 'subsub1(A, False)')
