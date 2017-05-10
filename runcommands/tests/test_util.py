from doctest import DocTestSuite


def load_tests(loader, tests, ignore):
    tests.addTests(DocTestSuite('runcommands.util.decorators'))
    tests.addTests(DocTestSuite('runcommands.util.path'))
    return tests
