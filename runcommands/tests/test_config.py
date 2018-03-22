import os
from unittest import TestCase

from ..collection import Collection
from ..command import command
from ..run import run
from ..runner import CommandRunner


CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'commands.yaml')


@command
def test(a, b, c=None):
    return a, b, c


class TestConfig(TestCase):

    def setUp(self):
        self.collection = Collection({'test': test})

    def read_config_file(self, config_file=CONFIG_FILE):
        return run.read_config_file(config_file, self.collection)

    def interpolate(self, config):
        defaults, globals_, default_args, environ = run.interpolate(
            config.get('defaults') or {},
            config.get('globals_') or {},
            config.get('default_args') or {},
            config.get('environ') or {},
        )
        return {
            'defaults': defaults,
            'globals_': globals_,
            'default_args': default_args,
            'environ': environ,
        }

    def test_read_config(self):
        config = self.read_config_file()
        self.assertIn('env', config)
        self.assertIn('defaults', config)
        self.assertIn('globals_', config)
        self.assertIn('default_args', config)
        self.assertIn('environ', config)
        self.assertEqual('test', config['env'])

    def test_read_config_and_interpolate(self):
        config = self.read_config_file()
        config = self.interpolate(config)
        defaults = config['defaults']
        self.assertEqual({'a': 'a', 'b': 'a', 'c': 'a'}, defaults)
        self.assertEqual({'a': 'a', 'b': 'b'}, config['globals_'])
        self.assertEqual({'test': {'a': 'a', 'b': 'b'}}, config['default_args'])
        self.assertEqual({'XYZ': 'a'}, config['environ'])

    def test_read_config_then_call_command(self):
        config = self.read_config_file()
        config = self.interpolate(config)
        runner = CommandRunner(self.collection)
        self.collection.set_default_args(config['default_args'])

        # Uses default args
        result = runner.run(['test'])[0]
        self.assertEqual(('a', 'b', None), result)

        # Uses some default args
        result = runner.run(['test', 'x'])[0]
        self.assertEqual(('x', 'b', None), result)

        # Uses no default args
        result = runner.run(['test', 'x', 'y', '-c', 'z'])[0]
        self.assertEqual(('x', 'y', 'z'), result)
