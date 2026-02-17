from contextlib import redirect_stderr, redirect_stdout
from doctest import DocTestSuite
from io import StringIO
from unittest import TestCase

import runcommands.util.misc
import runcommands.util.path
import runcommands.util.string
from runcommands.util.enums import PrinterColor

from runcommands.util.printer import printer


def load_tests(loader, tests, ignore):
    tests.addTests(DocTestSuite(runcommands.util.misc))
    tests.addTests(DocTestSuite(runcommands.util.path))
    tests.addTests(DocTestSuite(runcommands.util.string))
    return tests


class TestPrinter(TestCase):
    def test_prints_to_stdout(self):
        stdout = StringIO()
        stderr = StringIO()
        for attr in ("print", "header", "info", "success", "echo"):
            with self.subTest(printer=attr):
                with redirect_stdout(stdout):
                    with redirect_stderr(stderr):
                        attr = getattr(printer, attr)
                        attr("stdout")
            self.assertIn("stdout", stdout.getvalue())
            self.assertEqual(stderr.getvalue(), "")

    def test_prints_to_stderr(self):
        stdout = StringIO()
        stderr = StringIO()
        for attr in ("warning", "error", "danger", "debug"):
            with self.subTest(printer=attr):
                with redirect_stdout(stdout):
                    with redirect_stderr(stderr):
                        attr = getattr(printer, attr)
                        attr("stderr")
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("stderr", stderr.getvalue())

    def test_print_no_args(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            printer.print()
        self.assertEqual(stdout.getvalue(), "\n")

    def test_print_info(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            printer.info("info")
        self.assertEqual(
            "\x1b[94minfo\x1b[0m\n",
            stdout.getvalue(),
        )

    def test_print_red(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            printer.red("red")
        self.assertEqual(
            "\x1b[91mred\x1b[0m\n",
            stdout.getvalue(),
        )

    def test_print_info_with_nested(self):
        stdout = StringIO()
        with redirect_stdout(stdout):
            printer.info("info", "text", PrinterColor.green, "green text")
        self.assertEqual(
            "\x1b[94minfo text \x1b[0m\x1b[92mgreen text\x1b[0m\n",
            stdout.getvalue(),
        )
