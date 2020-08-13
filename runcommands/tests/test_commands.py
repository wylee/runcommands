import io
import os
from contextlib import redirect_stderr, redirect_stdout
from unittest import TestCase

from .. import arg, command, subcommand
from ..commands import local
from ..exc import RunAborted
from ..result import Result
from ..run import run


class MockResult:

    def __init__(self, return_code):
        self.return_code = return_code


class Callback:

    def __init__(self, implementation=None):
        self.called = False
        self.cmd = None
        self.result = None
        self.aborted = None
        self.implementation = implementation

    def __call__(self, cmd, result, aborted):
        self.called = True
        self.cmd = cmd
        self.result = result
        self.aborted = aborted
        if self.implementation:
            self.implementation(cmd, result, aborted)


@command
def base(subcommand: arg(default=None)):
    return MockResult('base {subcommand}'.format_map(locals()))


@subcommand(base)
def sub(subcommand: arg(default=None), optional=None):
    return MockResult('sub {subcommand} {optional}'.format_map(locals()))


@subcommand(sub)
def subsub(positional, optional=None):
    return MockResult('subsub {positional} {optional}'.format_map(locals()))


@base.subcommand
def sub_abort():
    raise RunAborted()


class TestLocalCommand(TestCase):

    def test_local_ls(self):
        result = local(['ls', '-1'], cd=os.path.dirname(__file__), stdout='capture')
        self.assertIn('__init__.py', result.stdout_lines)
        self.assertTrue(result)


class TestRun(TestCase):

    def setUp(self):
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()

    def tearDown(self):
        self.stderr = None
        self.stdout = None

    def _run(self, argv=None):
        if argv is None:
            argv = []
        with redirect_stderr(self.stderr):
            with redirect_stdout(self.stdout):
                return_code = run.console_script(argv)
        return return_code

    def test_run_with_no_args(self):
        self._run()

    def test_run_local_command(self):
        self._run(['local', 'ls', '-1', '--stdout', 'hide'])

    def test_run_with_callback(self):
        callback = Callback()
        run.add_callback(callback)
        self._run()
        self.assertTrue(callback.called)
        self.assertIs(callback.cmd, run)
        self.assertIsInstance(callback.result, Result)
        self.assertEqual(callback.result.return_code, 0)
        self.assertFalse(callback.aborted)
        run.callbacks = []

    def test_run_local_command_with_callback(self):
        def local_callback_implementation(cmd, result, aborted):
            self.assertIs(cmd, local)
            self.assertTrue(len(result.stdout_lines))
            self.assertFalse(aborted)
            print('local callback implementation')

        run_callback = Callback()
        run.add_callback(run_callback)
        local_callback = Callback(implementation=local_callback_implementation)
        local.add_callback(local_callback)
        self._run(['local', 'ls', '-1', '--stdout', 'capture'])
        self.assertTrue(local_callback.called)
        self.assertIs(local_callback.cmd, local)
        self.assertIsNotNone(local_callback.result)
        self.assertFalse(local_callback.aborted)
        self.assertIn('local callback implementation', self.stdout.getvalue())
        run.callbacks = []
        local.callbacks = []


class TestSubcommand(TestCase):

    def test_base_command_subcommand_choices(self):
        arg = base.args['subcommand']
        self.assertIsNotNone(arg.choices)
        self.assertEqual(arg.choices, ['sub', 'sub-abort'])

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
            return MockResult('base1({cmd}, {a})'.format_map(locals()))

        @subcommand(base1)
        def sub1(cmd: arg(default=None), a=None, flag=True):
            return MockResult('sub1({cmd}, {a}, {flag})'.format_map(locals()))

        @sub1.subcommand
        def subsub1(a=None, flag=True):
            return MockResult('subsub1({a}, {flag})'.format_map(locals()))

        result = base1.console_script(argv=['-a', 'A', 'sub1', '--no-flag'])
        self.assertEqual(result, 'sub1(None, A, False)')

        result = base1.console_script(argv=['-a', 'A', 'sub1', '--no-flag', 'subsub1'])
        self.assertEqual(result, 'subsub1(A, False)')


class TestSubcommandCallbacks(TestCase):

    def tearDown(self):
        base.callbacks = []
        sub.callbacks = []
        subsub.callbacks = []
        sub_abort.callbacks = []

    def _check(self, cmd, callback, called=True, aborted=False):
        if called:
            self.assertTrue(callback.called)
            self.assertIs(callback.cmd, cmd)
            self.assertIsNotNone(callback.result)
            if aborted:
                self.assertTrue(callback.aborted)
            else:
                self.assertFalse(callback.aborted)
        else:
            self.assertFalse(callback.called)
            self.assertIsNone(callback.cmd)
            self.assertIsNone(callback.result)
            self.assertIsNone(callback.aborted)

    def test_callback_on_base_command(self):
        callback = Callback()
        base.add_callback(callback)
        base.console_script(argv=[])
        self._check(base, callback)

    def test_callback_on_subcommand(self):
        base_callback = Callback()
        base.add_callback(base_callback)
        sub_callback = Callback()
        sub.add_callback(sub_callback)
        base.console_script(argv=['sub'])
        self._check(base, base_callback)
        self._check(sub, sub_callback)

    def test_abort_in_subcommand(self):
        base_callback = Callback()
        base.add_callback(base_callback)
        sub_callback = Callback()
        sub_abort.add_callback(sub_callback)
        with redirect_stdout(io.StringIO()):
            base.console_script(argv=['sub-abort'])
        self._check(base, base_callback, aborted=True)
        self._check(sub_abort, sub_callback, called=False, aborted=True)
