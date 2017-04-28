import getpass
import json
import os
from collections import Mapping, OrderedDict, Sequence
from configparser import RawConfigParser
from contextlib import contextmanager
from copy import copy
from locale import getpreferredencoding
from subprocess import check_output, CalledProcessError, DEVNULL

from .command import command
from .const import DEFAULT_COMMANDS_MODULE
from .exc import ConfigError, ConfigKeyError
from .util import abort, abs_path, load_object


__all__ = ['show_config']


NO_DEFAULT = object()


class RawConfig(OrderedDict):

    def __getitem__(self, name):
        try:
            value = super().__getitem__(name)
        except KeyError:
            raise ConfigKeyError(name) from None
        return value

    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattr__(name)
        return self[name]

    def __setattr__(self, name, value):
        if name.startswith('_'):
            return super().__setattr__(name, value)
        self[name] = value

    def __setitem__(self, name, value):
        if isinstance(value, Mapping) and not isinstance(value, RawConfig):
            value = RawConfig(value)
        super().__setitem__(name, value)

    def __copy__(self):
        # Recursive shallow copy
        config = self.__class__.__new__(self.__class__)
        # NOTE: The intent is to call OrderedDict's __init__ here.
        super(RawConfig, config).__init__()
        for k, v in self.items():
            config[k] = copy(v)
        return config

    def _clone(self, *args, **kwargs):
        clone = copy(self)
        for overrides in args:
            clone._update_dotted(overrides)
        clone._update_dotted(kwargs)
        return clone

    @contextmanager
    def _override(self, *args, **kwargs):
        config = self._clone(*args, **kwargs)
        yield config

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

    def _update_dotted(self, *args, **kwargs):
        if args:
            items, *rest = args
            if rest:
                raise TypeError('Expected at most 1 argument; got {n}'.format(n=len(args)))
            if isinstance(items, Mapping):
                items = items.items()
            for name, value in items:
                self._set_dotted(name, value)
        if kwargs:
            for name, value in kwargs.items():
                self._set_dotted(name, value)

    def _to_string(self, flat=False, values_only=False, exclude=(), level=0, root=''):
        out = []

        flat = flat or values_only
        indent = '' if flat else ' ' * (level * 4)

        keys = sorted(self)
        keys = [k for k in keys if not k.startswith('_')]
        if level == 0 and 'defaults' in keys:
            keys.remove('defaults')
            keys.append('defaults')

        for k in keys:
            v = self[k]

            qualified_k = '.'.join((root, k)) if root else k
            if qualified_k in exclude:
                continue

            if flat:
                k = qualified_k

            if isinstance(v, RawConfig):
                if not flat:
                    out.append('{indent}{k} =>'.format(**locals()))
                v = v._to_string(flat, values_only, exclude, level + 1, qualified_k)
                if v:
                    out.append(v)
            else:
                if values_only:
                    out.append(str(v))
                else:
                    out.append('{indent}{k} => {v}'.format(**locals()))

        return '\n'.join(out)


class RunConfig(RawConfig):

    """Container for run-related config options."""

    _known_options = {
        'commands_module': DEFAULT_COMMANDS_MODULE,
        'config_file': None,
        'env': None,
        'default_env': None,
        'options': None,
        'echo': False,
        'hide': False,
        'debug': False,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(self._known_options)
        self['options'] = {}
        self.update(*args)
        self.update(**kwargs)

    def __setitem__(self, name, value):
        if name not in self._known_options:
            raise ConfigKeyError(name, 'not allowed in RunConfig')
        super().__setitem__(name, value)


class Config(RawConfig):

    def __init__(self, *args, **kwargs):
        super().__init__()

        bootstrap_config = RawConfig()
        bootstrap_config._update_dotted(*args, **kwargs)
        run_config = bootstrap_config.get('run')
        run_config = RunConfig() if run_config is None else run_config

        self['run'] = run_config

        # XXX: It's possible this could override run options. Not
        #      sure if that's okay...
        self._read_from_file(self.run.config_file, self.run.env)

        self._update_dotted(*args, **kwargs)

        self.setdefault('cwd', os.getcwd, lazy=True)
        self.setdefault('current_user', getpass.getuser, lazy=True)
        self.setdefault('version', self._get_default_version, lazy=True)
        self.setdefault('env', lambda: self.run.env, lazy=True)
        self.setdefault('debug', lambda: self.run.debug, lazy=True)

        # Run options are specified on the command line and have higher
        # precedence than config options read from elsewhere.
        if self.run.options:
            self._update_dotted(self.run.options)

        self._interpolate()

    @classmethod
    def _make_config_parser(cls, file_name=None, _cache={}):
        if file_name:
            file_name = abs_path(file_name)

        if file_name in _cache:
            return _cache[file_name]

        parser = ConfigParser()

        if file_name:
            try:
                with open(file_name) as fp:
                    parser.read_file(fp)
            except FileNotFoundError:
                raise ConfigError('Config file does not exist: {file_name}'.format_map(locals()))

        _cache[file_name] = parser

        return parser

    @classmethod
    def _decode_value(cls, name, value, tolerant=False):
        try:
            value = json.loads(value)
        except ValueError:
            if tolerant:
                return value
            msg = 'Could not read {name} from config (not valid JSON): {value}'
            raise ConfigError(msg.format_map(locals()))
        return value

    @classmethod
    def _get_envs(cls, file_name):
        parser = cls._make_config_parser(file_name)
        sections = set(parser.sections())
        for name in parser:
            extends = parser.get(name, 'extends', fallback=None)
            if extends:
                extends = cls._decode_value('extends', extends)
                sections.update(cls._get_envs(extends))
        return sorted(sections)

    def _read_from_file(self, file_name, env=None):
        parser = self._make_config_parser(file_name)

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
            extends = self._decode_value('extends', extends)
            self._read_from_file(extends, env)

        for name, value in section.items():
            value = self._decode_value(name, value)
            self._set_dotted(name, value)

        if env and '__ENV_SECTION_FOUND_IN_FILE__' not in self:
            raise ConfigError('Env/section not found while reading config: {env}'.format(env=env))

    def _interpolate(self):
        interpolated = []
        self._do_interpolation(self, interpolated)
        while interpolated:
            interpolated = []
            self._do_interpolation(self, interpolated)

    def _do_interpolation(self, obj, interpolated):
        if isinstance(obj, str):
            try:
                new_value = obj.format(**self)
            except ConfigKeyError as exc:
                context = 'while interpolating into "{obj}"'.format(obj=obj)
                raise ConfigKeyError(exc.args[0], context) from None
            if new_value != obj:
                obj = new_value
                interpolated.append(obj)
        elif isinstance(obj, Mapping):
            for key in obj:
                obj[key] = self._do_interpolation(obj[key], interpolated)
        elif isinstance(obj, Sequence):
            obj = obj.__class__(self._do_interpolation(thing, interpolated) for thing in obj)
        return obj

    def _get_default_version(self):
        getter = self.get('version_getter')
        if not getter:
            getter = '{self.__class__.__module__}:version_getter'.format(self=self)
        if isinstance(getter, str):
            getter = load_object(getter)
        return getter(self)

    def setdefault(self, name, default=None, lazy=False, args=(), kwargs=None):
        if lazy and name not in self:
            default = default(*args, **(kwargs or {}))
        return super().setdefault(name, default)


class ConfigParser(RawConfigParser):

    optionxform = lambda self, name: name


def version_getter(config):
    if not os.path.isdir('.git'):
        return None
    encoding = getpreferredencoding(do_setlocale=False)
    try:
        version = check_output(['git', 'describe', '--exact-match'], stderr=DEVNULL)
    except CalledProcessError:
        version = check_output(['git', 'rev-parse', '--short', 'HEAD'])
    version = version.decode(encoding).strip()
    return version


@command
def show_config(config, name=(), flat=False, values=False, exclude=(), defaults=True):
    """Show config.

    By default, all config items are shown using a nested format::

        > show-config
        remote =>
            host => example.com
            user => user

    To show the items in a flat list, use ``--flat``::

        > show-config -f
        remote.host => example.com
        remote.user => user

    To show selected items only, use ``--name`` one more times::

        > show-config -n remote.host
        remote.host => example.com

    To show just just values, pass ``--values``::

        > show-config -n remote.host -v
        example.com

        > ssh $(show-config -n remote.host -v)

    .. note:: ``--values`` implies ``--flat``.

    To exclude config items, use ``--exclude`` with dotted key names::

        > show-config -n remote -e remote.host -f
        remote.user => ec2-user

    To exclude ``defaults.`` config items (default args for commands),
    pass ``--no-defaults``.

    """
    flat = flat or values

    exclude = list(exclude)
    if not defaults:
        exclude.append('defaults')

    if name:
        for n in name:
            try:
                value = config._get_dotted(n)
            except KeyError:
                abort(1, 'Unknown config key: {name}'.format(name=n))
            else:
                if isinstance(value, RawConfig):
                    if not flat:
                        print(n, '=>')
                    value = value._to_string(flat, values, exclude, 1, n)
                    if value:
                        print(value)
                else:
                    if values:
                        print(value)
                    else:
                        print(n, '=>', value)
    else:
        print(config._to_string(flat, values, exclude, 0))
