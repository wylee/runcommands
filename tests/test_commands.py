import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import TestCase

from runcommands import arg, command, subcommand
from runcommands.commands import local
from runcommands.exc import RunAborted
from runcommands.result import Result
from runcommands.run import run


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
    return MockResult(f"base {subcommand}")


@subcommand(base)
def sub(subcommand: arg(default=None), optional=None):
    return MockResult(f"sub {subcommand} {optional}")


@subcommand(sub)
def subsub(positional, optional=None):
    return MockResult(f"subsub {positional} {optional}")


@base.subcommand
def sub_abort():
    raise RunAborted()


@command
def container_args(
    positional: arg(container=tuple, type=int),
    optional: arg(type=int) = (),
    another_optional: arg(container=list, type=float) = None,
    third_optional=(42,),
):
    return MockResult((positional, optional, another_optional, third_optional))


@command(creates="tests/created.temp", sources="tests/**/*.py")
def create_from_sources():
    path = Path("tests/created.temp")
    path.touch()
    return MockResult(f"Created {path}")


@command(creates="tests/created.temp")
def create_without_sources():
    path = Path("tests/created.temp")
    path.touch()
    return MockResult(f"Created {path}")


class SysExitMixin:
    """Make sys.exit() return its arg rather than actually exiting."""

    @classmethod
    def setUpClass(cls):
        cls.original_sys_exit = sys.exit
        sys.exit = lambda arg=0: arg

    @classmethod
    def tearDownClass(cls):
        sys.exit = cls.original_sys_exit


class TestLocalCommand(TestCase):
    def test_local_ls(self):
        result = local(["ls", "-1"], cd=os.path.dirname(__file__), stdout="capture")
        self.assertIn("__init__.py", result.stdout_lines)
        self.assertTrue(result)


class TestCommandWithContainerArgs(SysExitMixin, TestCase):
    def test_positional(self):
        result = container_args.console_script(argv=["1"])
        self.assertEqual(result, ((1,), (), None, (42,)))

    def test_positional_and_optional(self):
        result = container_args.console_script(argv=["1", "--optional", "2"])
        self.assertEqual(result, ((1,), (2,), None, (42,)))

    def test_positional_and_optional_and_optional(self):
        argv = ["1", "--optional", "2", "--another-optional", "3.14"]
        result = container_args.console_script(argv=argv)
        self.assertEqual(result, ((1,), (2,), [3.14], (42,)))

    def test_positional_and_optional_and_optional_and_optional(self):
        argv = [
            "1",
            "--optional",
            "2",
            "--another-optional",
            "3.14",
            "--third-optional",
            "13",
        ]
        result = container_args.console_script(argv=argv)
        self.assertEqual(result, ((1,), (2,), [3.14], (13,)))


class TestRun(SysExitMixin, TestCase):
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
        self._run(["local", "ls", "-1", "--stdout", "hide"])

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
            print("local callback implementation")

        run_callback = Callback()
        run.add_callback(run_callback)
        local_callback = Callback(implementation=local_callback_implementation)
        local.add_callback(local_callback)
        self._run(["local", "ls", "-1", "--stdout", "capture"])
        self.assertTrue(local_callback.called)
        self.assertIs(local_callback.cmd, local)
        self.assertIsNotNone(local_callback.result)
        self.assertFalse(local_callback.aborted)
        self.assertIn("local callback implementation", self.stdout.getvalue())
        run.callbacks = []
        local.callbacks = []


class TestSubcommand(SysExitMixin, TestCase):
    def test_base_command_subcommand_choices(self):
        arg = base.args["subcommand"]
        self.assertIsNotNone(arg.choices)
        self.assertEqual(arg.choices, ["sub", "sub-abort"])

    def test_call_base_command(self):
        result = base.console_script(argv=[])
        self.assertEqual(result, "base None")

    def test_call_subcommand(self):
        result = base.console_script(argv=["sub"])
        self.assertEqual(result, "sub None None")

    def test_call_subcommand_with_optional(self):
        result = base.console_script(argv=["sub", "--optional", "b"])
        self.assertEqual(result, "sub None b")

    def test_call_subsubcommand(self):
        result = base.console_script(argv=["sub", "subsub", "a"])
        self.assertEqual(result, "subsub a None")

    def test_call_subsubcommand_with_optional(self):
        result = base.console_script(argv=["sub", "subsub", "a", "--optional", "b"])
        self.assertEqual(result, "subsub a b")

    def test_call_subsubcommand_with_shared_args(self):
        @command
        def base1(cmd, a=None):
            return MockResult(f"base1({cmd}, {a})")

        @subcommand(base1)
        def sub1(cmd: arg(default=None), a=None, flag=True):
            return MockResult(f"sub1({cmd}, {a}, {flag})")

        @sub1.subcommand
        def subsub1(a=None, flag=True):
            return MockResult(f"subsub1({a}, {flag})")

        result = base1.console_script(argv=["-a", "A", "sub1", "--no-flag"])
        self.assertEqual(result, "sub1(None, A, False)")

        result = base1.console_script(argv=["-a", "A", "sub1", "--no-flag", "subsub1"])
        self.assertEqual(result, "subsub1(A, False)")


class TestSubcommandCallbacks(SysExitMixin, TestCase):
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
        base.console_script(argv=["sub"])
        self._check(base, base_callback)
        self._check(sub, sub_callback)

    def test_abort_in_subcommand(self):
        base_callback = Callback()
        base.add_callback(base_callback)
        sub_callback = Callback()
        sub_abort.add_callback(sub_callback)
        with redirect_stdout(io.StringIO()):
            base.console_script(argv=["sub-abort"])
        self._check(base, base_callback, aborted=True)
        self._check(sub_abort, sub_callback, called=False, aborted=True)


class TestSourcesAndCreates(SysExitMixin, TestCase):
    def setUp(self):
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()

    def tearDown(self):
        self.stderr = None
        self.stdout = None
        path = Path("tests/created.temp")
        if path.exists():
            path.unlink()

    def test_run(self):
        result = create_from_sources.run([])
        self.assertEqual(result.return_code, "Created tests/created.temp")
        with redirect_stderr(self.stderr):
            result = create_from_sources.run([])
        self.assertEqual(result, None)

    def test_console_script(self):
        result = create_from_sources.console_script([])
        self.assertEqual(result, "Created tests/created.temp")
        with redirect_stderr(self.stderr):
            result = create_from_sources.console_script([])
        self.assertEqual(result, 0)

    def test_sources_without_creates(self):
        def make_command():
            @command(sources="tests/**/*.py")
            def sources_without_creates():
                raise NotImplementedError("This should never run")

        self.assertRaises(ValueError, make_command)

    def test_create_without_sources(self):
        result = create_without_sources.run([])
        self.assertEqual(result.return_code, "Created tests/created.temp")
        with redirect_stderr(self.stderr):
            result = create_without_sources.run([])
        self.assertEqual(result, None)
