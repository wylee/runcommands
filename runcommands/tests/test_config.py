import os
from unittest import TestCase

from ..collection import Collection
from ..command import command
from ..run import run
from ..runner import CommandRunner


CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'commands.yaml')


@command
def test(a, b, c, d=None):
    return a, b, c, d


class TestConfig(TestCase):

    def setUp(self):
        self.collection = Collection({'test': test})

    def read_config_file(self, config_file=CONFIG_FILE):
        return run.read_config_file(config_file, self.collection)

    def interpolate(self, config):
        globals_, default_args, environ = run.interpolate(
            config.get('globals') or {},
            config.get('args') or {},
            config.get('environ') or {},
        )
        return {
            'globals': globals_,
            'args': default_args,
            'environ': environ,
        }

    def test_read_config(self):
        config = self.read_config_file()
        self.assertIn('globals', config)
        self.assertIn('args', config)
        self.assertIn('environ', config)
        self.assertIn('env', config['globals'])
        self.assertEqual('test', config['globals']['env'])

    def test_read_config_and_interpolate(self):
        config = self.read_config_file()
        config = self.interpolate(config)
        self.assertEqual({'env': 'test', 'a': 'b', 'b': 'b', 'd': 'd'}, config['globals'])
        self.assertEqual({'test': {'a': 'b', 'b': 'b', 'd': 'x'}}, config['args'])
        self.assertEqual({'XXX': 'b', 'XYZ': 'b'}, config['environ'])

    def test_read_config_then_call_command(self):
        config = self.read_config_file()
        config = self.interpolate(config)
        runner = CommandRunner(self.collection)
        self.collection.set_default_args(config['args'])

        # Uses default args
        result = runner.run(['test', 'c'])[0]
        self.assertEqual(('b', 'b', 'c', 'x'), result)

        # Uses some default args
        result = runner.run(['test', '--a', 'a', 'c'])[0]
        self.assertEqual(('a', 'b', 'c', 'x'), result)

        # Uses no default args
        result = runner.run(['test', '--a', 'x', '--b', 'y', 'c', '-d', 'z'])[0]
        self.assertEqual(('x', 'y', 'c', 'z'), result)
