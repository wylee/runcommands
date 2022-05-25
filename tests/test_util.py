from doctest import DocTestSuite

import runcommands.util.misc
import runcommands.util.path
import runcommands.util.string


def load_tests(loader, tests, ignore):
    tests.addTests(DocTestSuite(runcommands.util.misc))
    tests.addTests(DocTestSuite(runcommands.util.path))
    tests.addTests(DocTestSuite(runcommands.util.string))
    return tests
