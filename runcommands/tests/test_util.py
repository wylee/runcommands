from doctest import DocTestSuite


def load_tests(loader, tests, ignore):
    tests.addTests(DocTestSuite('runcommands.util'))
    return tests
