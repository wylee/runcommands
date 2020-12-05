import os
from contextlib import contextmanager
from doctest import DocTestSuite
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest import TestCase

from runcommands.commands import copy_file


def load_tests(loader, tests, ignore):
    tests.addTests(DocTestSuite('runcommands.util.decorators'))
    tests.addTests(DocTestSuite('runcommands.util.misc'))
    tests.addTests(DocTestSuite('runcommands.util.path'))
    tests.addTests(DocTestSuite('runcommands.util.string'))
    return tests


@contextmanager
def copy(contents, destination_dir=False, **kwargs):
    with NamedTemporaryFile('w', delete=False) as tp:
        tp.write(contents)

    source = tp.name

    if destination_dir:
        with TemporaryDirectory() as destination:
            path = copy_file(source, destination, **kwargs)
            yield source, destination, path
            os.remove(source)
    else:
        destination = source + '.copy'
        path = copy_file(source, destination, **kwargs)
        yield source, destination, path
        os.remove(source)
        os.remove(path)


class TestCopyFileCommand(TestCase):

    def assertDestination(self, source, destination, path, expected_contents):
        self.assertExists(path)
        self.assertNotEqual(source, destination)
        self.assertNotEqual(source, path)
        self.assertContentsEqual(path, expected_contents)
        if not os.path.isdir(destination):
            self.assertTrue(path.endswith('.copy'))

    def assertExists(self, path):
        self.assertTrue(os.path.isfile(path))

    def assertContentsEqual(self, path, expected_contents):
        with open(path) as fp:
            read_contents = fp.read()
        self.assertEqual(read_contents, expected_contents)

    def test_copy(self):
        with copy('xyz') as (source, destination, path):
            self.assertDestination(source, destination, path, 'xyz')

    def test_copy_template_format(self):
        with copy('{xyz} ${{xyz}}', template=True, context={'xyz': 123}) as paths:
            source, destination, path = paths
            self.assertDestination(source, destination, path, '123 ${xyz}')

    def test_copy_template_string(self):
        with copy('${xyz} $${xyz}', template='string', context={'xyz': 123}) as paths:
            source, destination, path = paths
            self.assertDestination(source, destination, path, '123 ${xyz}')

    def test_copy_to_directory(self):
        with copy('xyz', destination_dir=True) as paths:
            source, destination, path = paths
            self.assertDestination(source, destination, path, 'xyz')
            self.assertEqual(os.path.dirname(path), destination)
            self.assertNotEqual(os.path.dirname(source), os.path.dirname(path))
            self.assertEqual(os.path.basename(source), os.path.basename(path))
