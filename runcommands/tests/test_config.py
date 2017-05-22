from doctest import DocTestSuite
from unittest import TestCase

from runcommands.config import RawConfig, RunConfig
from runcommands.exc import ConfigKeyError, ConfigValueError

from .config import Config


def load_tests(loader, tests, ignore):
    tests.addTests(DocTestSuite('runcommands.config'))
    return tests


class TestRawConfig(TestCase):

    def test_get_missing_raises_config_key_error(self):
        config = RawConfig()
        self.assertRaises(ConfigKeyError, config.__getitem__, 'nope')

    def test_iterate_over_dotted_keys(self):
        config = RawConfig()
        config['a'] = 1
        config['b'] = 2
        config['x.y.z'] = 3
        keys = list(config._iter_dotted())
        self.assertEqual(keys, ['a', 'b', 'x.y.z'])

    # Copying ---------------------------------------------------------

    def test_copy(self):
        config = RawConfig(a=1, b=2)
        copy = config.copy()
        self.assertEqual(config, copy)

    def test_copy_with_overrides(self):
        config = RawConfig(a=1, b=2)
        copy = config.copy(b=3)
        self.assertNotEqual(config, copy)
        self.assertEqual(config.b, 2)
        self.assertEqual(copy.b, 3)

    def test_copy_with_dotted_overrides(self):
        config = RawConfig({'a.b': '1', 'x.y': '2'})
        copy = config.copy({'a.b': '3'})
        self.assertNotEqual(config, copy)
        self.assertEqual(config.a.b, '1')
        self.assertEqual(copy.a.b, '3')

    # Access ----------------------------------------------------------

    def test_get_via_get_method(self):
        config = RawConfig()
        config.x = 'x'
        config.y = '${x}'
        self.assertEqual(config.get('y'), 'x')

    def test_item_can_be_retrieved_via_attribute_access(self):
        config = RawConfig()
        config['name'] = 'value'
        self.assertIn('name', config)
        self.assertEqual(config['name'], 'value')
        self.assertTrue(hasattr(config, 'name'))
        self.assertEqual(config.name, 'value')

    def test_attribute_cannot_be_retrieved_via_item_access(self):
        config = RawConfig()
        config._name = 'value'
        self.assertTrue(hasattr(config, '_name'))
        self.assertEqual(config._name, 'value')
        self.assertNotIn('_name', config)
        self.assertRaises(KeyError, lambda: config['_name'])

    def test_attribute_has_priority_over_item_when_using_attribute_access(self):
        config = RawConfig()
        config._name = 'attr-value'
        config['_name'] = 'item-value'
        self.assertEqual(config._name, 'attr-value')
        self.assertEqual(config['_name'], 'item-value')

    def test_add_item_with_leading_underscore(self):
        config = RawConfig()
        config['_name'] = 'value'
        self.assertIn('_name', config)
        self.assertEqual(config['_name'], 'value')
        self.assertTrue(hasattr(config, '_name'))
        self.assertEqual(config._name, 'value')

    # Removal ---------------------------------------------------------

    def test_remove_attribute(self):
        config = RawConfig()
        config.x = 'x'
        self.assertIn('x', config)
        del config.x
        self.assertNotIn('x', config)

    def test_remove_item(self):
        config = RawConfig()
        config.x = 'x'
        self.assertIn('x', config)
        del config['x']
        self.assertNotIn('x', config)

    def test_remove_via_pop_method(self):
        config = RawConfig()
        config.x = 'x'
        config.y = '${x}'
        self.assertIn('y', config)
        y = config.pop('y')
        self.assertNotIn('y', config)
        self.assertEqual(y, 'x')

    # Iteration -------------------------------------------------------

    def test_keys(self):
        config = RawConfig()
        config.a = 1
        config.b = 2
        self.assertEqual(list(config.keys()), ['a', 'b'])

    def test_items(self):
        config = RawConfig()
        config.a = 1
        config.b = 2
        config.c = '${b}'
        self.assertEqual(list(config.items()), [('a', 1), ('b', 2), ('c', '2')])

    def test_values(self):
        config = RawConfig()
        config.a = 1
        config.b = 2
        config.c = '${b}'
        self.assertEqual(list(config.values()), [1, 2, '2'])


class TestRunConfig(TestCase):

    def test_has_expected_items(self):
        config = RunConfig()
        self.assertIn('commands_module', config)
        self.assertEqual(config.commands_module, 'commands.py')
        self.assertIn('config_file', config)
        self.assertIs(config.config_file, None)

    def test_cannot_add_unexpected_items(self):
        config = RunConfig()
        self.assertRaises(KeyError, lambda: config.__setitem__('name', 'value'))

    def test_can_add_private_attributes(self):
        config = RunConfig()
        config._attr = 'value'


class TestConfig(TestCase):

    def test_read_file(self):
        config = Config()
        self.assertEqual(config.version, 'X.Y.Z')
        self.assertEqual(config.a, 1)
        self.assertEqual(config.b, 2)
        self.assertEqual(config.c, 2)
        self.assertEqual(config.d.e, '2')
        self.assertEqual(config._get_dotted('x.y.z'), 'xyz')
        self.assertEqual(config.list.a, [1, 2, 3])
        self.assertEqual(config.list.b, [1, 2, 3])
        self.assertEqual(config.list.c, '[1, 2, 3]')
        self.assertEqual(config.my.list, ['item'])
        self.assertEqual(config.my.other_list, ['item'])
        self.assertEqual(config.my.dict, {'key': ['item']})
        self.assertEqual(config.dollar_sign, '$')
        self.assertEqual(config.not_interpolated.a, '${xyz}')
        self.assertEqual(config.not_interpolated.b, '${')

    def test_simple_interpolation(self):
        version = 'X.Y.Z'
        config = Config(run=RunConfig())
        config.version = version
        config.other = '${version}'
        self.assertEqual(config.version, version)
        self.assertEqual(config.other, version)

    def test_moderately_complex_interpolation(self):
        version = 'X.Y.Z'
        config = Config(run=RunConfig())
        config.version = version
        config.other = '${version}'
        config._set_dotted('x.y', '${other}')
        config._set_dotted('a.b.c', '${x.y}')
        self.assertEqual(config.version, version)
        self.assertEqual(config.other, version)
        self.assertEqual(config.x.y, version)
        self.assertEqual(config.a.b.c, version)

    def test_unclosed_interpolation_group(self):
        config = Config(run=RunConfig())
        config.name = '${xyz'
        self.assertRaises(ConfigValueError, lambda: config.name)

    def test_interpolation_escapes(self):
        config = Config(run=RunConfig())
        config.name = '$${'
        self.assertEqual(config.name, '${')
        config.name = '$${{'
        self.assertEqual(config.name, '${{')

    def test_dollar_signs(self):
        config = Config(run=RunConfig())
        config.name = '$'
        self.assertEqual(config.name, '$')
        config.name = '$$'
        self.assertEqual(config.name, '$$')
        config.name = '$$$'
        self.assertEqual(config.name, '$$$')

    def test_contains(self):
        config = Config(run=RunConfig())
        config['x'] = 'x'
        self.assertIn('x', config)
        self.assertIn('env', config)  # via run config

    def test_iter(self):
        config = Config(run=RunConfig())
        config.debug = 'DEBUG'

        self.assertEqual(config.debug, 'DEBUG')
        self.assertEqual(config.run.debug, False)

        keys = list(config.keys())
        iter_keys = list(iter(config))
        values = list(config.values())
        items = list(config.items())
        item_keys = list(item[0] for item in items)
        item_values = list(item[1] for item in items)

        self.assertEqual(keys, iter_keys)
        self.assertEqual(keys, item_keys)
        self.assertEqual(values, item_values)
        self.assertEqual(items, list(zip(keys, values)))

        self.assertIn('run', keys)
        self.assertIn('env', keys)
        self.assertEqual(keys.count('debug'), 1)

    def test_format(self):
        config = Config(run=RunConfig())
        config['x'] = 'x'

        formatted_value = '{x}:{run.env}'.format(**config)
        self.assertEqual(formatted_value, 'x:None')

        formatted_value = '{x}:{run.env}'.format_map(config)
        self.assertEqual(formatted_value, 'x:None')

        formatted_value = '{x}:{env}'.format(**config)
        self.assertEqual(formatted_value, 'x:None')

        formatted_value = '{x}:{env}'.format_map(config)
        self.assertEqual(formatted_value, 'x:None')
