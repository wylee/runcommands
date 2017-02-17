import getpass
import json
import os
from collections import Mapping, OrderedDict, Sequence
from configparser import RawConfigParser

from .task import task
from .util import abs_path, print_error


__all__ = ['show_config']


NO_DEFAULT = object()


class RawConfig(OrderedDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config_file = self.get('config_file')
        if config_file:
            self._read_from_file(config_file, self.get('env'))

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattr__(name)
        return self[name]

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super().__setattr__(name, value)
        self[name] = value

    def __setitem__(self, name, value):
        if isinstance(value, dict):
            value = RawConfig(value)
        super().__setitem__(name, value)

    def _get_dotted(self, name, default=NO_DEFAULT):
        obj = self
        segments = name.split('.')
        for segment in segments:
            if not isinstance(obj, RawConfig):
                raise TypeError('{obj!r} is not a Config object'.format_map(locals()))
            try:
                obj = obj[segment]
            except KeyError:
                if default is not NO_DEFAULT:
                    return default
                raise
        return obj

    def _set_dotted(self, name, value):
        obj = self
        segments = name.split('.')
        last_segment = segments[-1]
        for segment in segments[:-1]:
            if not isinstance(obj, RawConfig):
                raise TypeError('{obj!r} is not a Config object'.format_map(locals()))
            if segment not in obj:
                obj[segment] = RawConfig()
            obj = obj[segment]
        obj[last_segment] = value

    def _read_from_file(self, file_name, env=None):
        file_name = abs_path(file_name)
        parser = ConfigParser()

        with open(file_name) as fp:
            parser.read_file(fp)

        if env:
            if env in parser:
                section = parser[env]
                self['__ENV_SECTION_FOUND_IN_FILE__'] = file_name
            else:
                section = parser.defaults()
        else:
            section = parser.defaults()

        extends = section.get('extends')
        if extends:
            extends = json.loads(extends)
            extends = abs_path(extends)
            self._read_from_file(extends, env)

        for name, value in section.items():
            value = json.loads(value)
            self._set_dotted(name, value)

        if env and '__ENV_SECTION_FOUND_IN_FILE__' not in self:
            raise ConfigError('Env/section not found while reading config: {env}'.format(env=env))


class Config(RawConfig):

    """Config that adds defaults and does interpolation on values."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('cwd', os.getcwd())
        kwargs.setdefault('current_user', getpass.getuser())
        kwargs.setdefault('version', 'X.Y.Z')
        super().__init__(*args, **kwargs)
        self._interpolate()

    def _interpolate(self):
        interpolated = []
        self._do_interpolation(self, interpolated)
        while interpolated:
            interpolated = []
            self._do_interpolation(self, interpolated)

    def _do_interpolation(self, obj, interpolated):
        if isinstance(obj, str):
            new_value = obj.format(**self)
            if new_value != obj:
                obj = new_value
                interpolated.append(obj)
        elif isinstance(obj, Mapping):
            for key in obj:
                obj[key] = self._do_interpolation(obj[key], interpolated)
        elif isinstance(obj, Sequence):
            obj = obj.__class__(self._do_interpolation(thing, interpolated) for thing in obj)
        return obj


class ConfigError(Exception):

    pass


class ConfigParser(RawConfigParser):

    optionxform = lambda self, name: name


@task
def show_config(config, name=None, defaults=True, initial_level=0):
    """Show config; pass --name=<name> to show just one item."""
    if name is not None:
        try:
            value = config._get_dotted(name)
        except KeyError:
            print_error('Unknown config key:', name)
        else:
            print(name, '=', value)
    else:
        def as_string(c, skip, level):
            out = []
            indent = ' ' * (level * 4)
            for k, v in c.items():
                if k.startswith('_') or k in skip:
                    continue
                if isinstance(v, RawConfig):
                    out.append('{indent}{k} =>'.format(**locals()))
                    out.append(as_string(v, skip, level + 1))
                else:
                    out.append('{indent}{k} = {v}'.format(**locals()))
            return '\n'.join(out)
        print(as_string(config, ['defaults'] if not defaults else [], initial_level))
