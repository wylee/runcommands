import getpass
import json
import os
from collections import Mapping, OrderedDict, Sequence
from configparser import RawConfigParser
from copy import copy
from locale import getpreferredencoding
from subprocess import check_output, CalledProcessError, DEVNULL

from .command import command
from .const import DEFAULT_COMMANDS_MODULE
from .exc import ConfigError, ConfigKeyError, ConfigTypeError, ConfigValueError
from .util import abort, abs_path, load_object

try:
    # Python 3.5 and up
    from collections import _OrderedDictItemsView, _OrderedDictValuesView
except ImportError:
    # Python 3.4 and below
    from collections import ItemsView, ValuesView

    class _OrderedDictItemsView(ItemsView):

        def __reversed__(self):
            for key in reversed(self._mapping):
                yield (key, self._mapping[key])

    class _OrderedDictValuesView(ValuesView):

        def __reversed__(self):
            for key in reversed(self._mapping):
                yield self._mapping[key]


__all__ = ['show_config']


NO_DEFAULT = object()


class RawConfig(OrderedDict):

    def __init__(self, *defaults, **overrides):
        self._parent = None
        super().__init__()
        self._update_dotted(*defaults)
        self._update_dotted(overrides)

    def __getitem__(self, name):
        try:
            value = super().__getitem__(name)
        except KeyError:
            raise ConfigKeyError(name) from None
        if not isinstance(value, RawConfig):
            value = self._interpolate(value)
        if isinstance(value, JSONValue):
            value = value.load()
        return value

    def __setitem__(self, name, value):
        super().__setitem__(name, value)
        if isinstance(value, RawConfig):
            value._parent = self

    def __getattr__(self, name):
        # This will be called only when the named attribute isn't found
        # on the config instance. Attributes have priority over config
        # keys with the same name.
        if name.startswith('_OrderedDict__'):
            return super().__getattribute__(name)
        return self[name]

    def __setattr__(self, name, value):
        # Public names are added as dict items. Private names are set as
        # attributes.
        if name.startswith('_'):
            return super().__setattr__(name, value)
        self[name] = value

    def __delattr__(self, name):
        try:
            super().__delattr__(name)
        except AttributeError:
            del self[name]

    def __copy__(self):
        config = self._make_empty()
        for k in super().__iter__():
            v = super().__getitem__(k)
            config[k] = copy(v)
        return config

    def copy(self, *args, **kwargs):
        clone = copy(self)
        for overrides in args:
            clone._update_dotted(overrides)
        clone._update_dotted(kwargs)
        return clone

    # -----------------------------------------------------------------
    # These overrides are necessary because CPython implements a C
    # version of OrderedDict that won't call our __getitem__.

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def pop(self, name, default=NO_DEFAULT):
        try:
            value = self[name]
        except KeyError:
            if default is NO_DEFAULT:
                raise ConfigKeyError(name) from None
            value = default
        else:
            del self[name]
        return value

    items = lambda self: _OrderedDictItemsView(self)
    values = lambda self: _OrderedDictValuesView(self)

    # -----------------------------------------------------------------

    @classmethod
    def _make_empty(cls):
        instance = cls.__new__(cls)
        RawConfig.__init__(instance)
        return instance

    @property
    def _root(self):
        return self if self._parent is None else self._parent._root

    def _interpolate(self, obj):
        """Interpolate root config into ``obj``.

        >>> config = RawConfig()
        >>> config.a = 'a'
        >>> config.b = '${a}'
        >>> config.b
        'a'

        >>> config.a = {'a': 1}
        >>> config.b = '${a}'
        >>> config.b
        '{"a": 1}'

        Escaping to allow literal '${'

        >>> config.a = '$${'
        >>> config.a
        '${'

        >>> config.a = '$${xyz}'
        >>> config.a
        '${xyz}'

        Literal dollar signs

        >>> config.a = '$'
        >>> config.a
        '$'
        >>> config.a = '$$'
        >>> config.a
        '$$'

        """
        if isinstance(obj, str):
            root = self._root
            obj_type = type(obj)
            changed = True
            while changed:
                obj, changed = self._inject(obj, root)
            obj = obj.replace('$${', '${')
            if not isinstance(obj, obj_type):
                obj = obj_type(obj)
        elif isinstance(obj, Mapping):
            for key in obj:
                obj[key] = self._interpolate(obj[key])
        elif isinstance(obj, Sequence):
            obj = obj.__class__(self._interpolate(thing) for thing in obj)
        return obj

    def _inject(self, value, root=None):
        root = self._root if root is None else root

        begin, end = '${', '}'

        if begin not in value:
            return value, False

        new_value = value
        begin_pos, end_pos = 0, None
        len_begin, len_end = len(begin), len(end)
        len_value = len(new_value)
        f = locals()

        while begin_pos < len_value:
            # Find next ${.
            begin_pos = new_value.find(begin, begin_pos)

            if begin_pos == -1:
                break

            if begin_pos > 0:
                peek_behind_index = begin_pos - 1
                if new_value[peek_behind_index] == '$':
                    begin_pos += 2
                    continue

            # Save everything before ${.
            before = new_value[:begin_pos]

            # Find } after ${.
            begin_pos += len_begin
            end_pos = new_value.find(end, begin_pos)
            if end_pos == -1:
                message = 'Unmatched {begin}...{end} in {value}'.format_map(f)
                raise ConfigValueError(message) from None

            # Get name between ${ and }, ignoring leading and trailing
            # whitespace.
            name = new_value[begin_pos:end_pos]
            name = name.strip()

            if not name:
                message = 'Empty name in {value}'.format_map(f)
                raise ConfigValueError(message) from None

            # Save everything after }.
            after_pos = end_pos + len_end
            after = new_value[after_pos:]

            # Retrieve string value for named setting (the "injection
            # value").
            try:
                injection_value = root._get_dotted(name)
            except KeyError:
                context = 'while interpolating into {value}'.format_map(f)
                raise ConfigKeyError(name, context=context) from None
            else:
                if not isinstance(injection_value, str):
                    injection_value = JSONValue.dumps(injection_value, name=name)

            # Combine before, inject value, and after to get the new
            # value.
            new_value = ''.join((before, injection_value, after))

            # Continue after injected value.
            begin_pos = len(before) + len(injection_value)
            len_value = len(new_value)

        return new_value, (new_value != value)

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

    def _iter_dotted(self, root=''):
        for k in super().__iter__():
            v = super().__getitem__(k)
            qualified_k = '.'.join((root, k)) if root else k
            if isinstance(v, RawConfig) and v:
                yield from v._iter_dotted(qualified_k)
            else:
                yield qualified_k

    def _to_string(self, flat=False, values_only=False, exclude=(), level=0, root=''):
        out = []
        if flat or values_only:
            keys = sorted(self._iter_dotted())
            for k in keys:
                v = self._get_dotted(k)
                if values_only:
                    out.append(str(v))
                else:
                    if isinstance(v, RawConfig) and not v:
                        v = ''
                    out.append('{k} => {v}'.format_map(locals()))
        else:
            keys = sorted(self)
            indent = ' ' * (level * 4)
            for k in keys:
                v = self[k]
                qualified_k = '.'.join((root, k)) if root else k
                if qualified_k in exclude:
                    continue
                if isinstance(v, RawConfig):
                    v = v._to_string(flat, values_only, exclude, level + 1, qualified_k)
                    if v:
                        out.append('{indent}{k} =>\n{v}'.format_map(locals()))
                    else:
                        out.append('{indent}{k} =>'.format_map(locals()))
                else:
                    out.append('{indent}{k} => {v}'.format_map(locals()))
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

    def __init__(self, *defaults, **overrides):
        super().__init__(self._known_options, options=RawConfig())
        self._update_dotted(*defaults)
        self._update_dotted(overrides)

    def __setitem__(self, name, value):
        if name not in self._known_options:
            raise ConfigKeyError(name, 'not allowed in RunConfig')
        super().__setitem__(name, value)


class Config(RawConfig):

    """A container for configuration options.

    It's constructed like so:

        - Add base defaults
        - Update with user-supplied defaults
        - Update with options read from config file; these override
          defaults
        - Update with user-supplied overrides; these override defaults
          and options read from config file
        - Update with options specified on command line

    """

    def __init__(self, *defaults, run=None, **overrides):
        run_config = RunConfig() if run is None else run
        super().__init__(
            run=run_config,
            cwd=os.getcwd(),
            current_user=getpass.getuser(),
            version=self._get_default_version(),
        )
        self._update_dotted(*defaults)
        self._read_from_file(run_config.config_file, run_config.env)
        self._update_dotted(overrides)
        self._update_dotted(run_config.options)

    def __contains__(self, name):
        contains = super().__contains__(name)
        if not contains:
            contains = super().__contains__('run') and name in super().__getitem__('run')
        return contains

    def __getitem__(self, name):
        try:
            value = super().__getitem__(name)
        except KeyError:
            try:
                value = super().__getitem__('run').__getitem__(name)
            except KeyError:
                raise ConfigKeyError(name) from None
        return value

    def __iter__(self):
        yield from self.keys()

    def keys(self):
        yield from super().keys()
        for k in super().get('run', ()):
            if not super().__contains__(k):
                yield k

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
    def _get_envs(cls, file_name):
        parser = cls._make_config_parser(file_name)
        sections = set(parser.sections())
        for name in parser:
            extends = parser.get(name, 'extends', fallback=None)
            if extends:
                extends = JSONValue(extends, name='extends').load()
                sections.update(cls._get_envs(extends))
        return sorted(sections)

    def _read_from_file(self, file_name, env=None):
        def read(f):
            nonlocal env_found_in

            parser = self._make_config_parser(f)

            if env:
                if env in parser:
                    section = parser[env]
                    if env_found_in is None:
                        env_found_in = f
                else:
                    section = parser.defaults()
            else:
                section = parser.defaults()

            extends = section.get('extends')
            if extends:
                extends = JSONValue(extends, name='extends').load()
                read(extends)

            for name, value in section.items():
                self._set_dotted(name, JSONValue(value, name=name))

        env_found_in = None
        read(file_name)

        if env and env_found_in is None:
            raise ConfigError('Env/section not found while reading config: {env}'.format(env=env))

    def _get_default_version(self):
        getter = self.get('version_getter')
        if not getter:
            getter = version_getter
        if isinstance(getter, str):
            getter = load_object(getter)
        return getter(self)

    def setdefault(self, name, default=None, lazy=False, args=(), kwargs=None):
        if lazy and name not in self:
            default = default(*args, **(kwargs or {}))
        return super().setdefault(name, default)


class ConfigParser(RawConfigParser):

    optionxform = lambda self, name: name


class JSONValue(str):

    def __new__(cls, string, *, name=None):
        if not isinstance(string, str):
            raise ConfigTypeError('Expected str; got %s' % string.__class__, name)
        instance = super().__new__(cls, string)
        instance.name = name
        return instance

    @classmethod
    def from_object(cls, obj, name=None):
        value = json.dumps(obj)
        return cls(value, name=name)

    @classmethod
    def loads(cls, value, name=None, tolerant=False):
        """JSON str -> object"""
        try:
            obj = json.loads(value)
        except TypeError as exc:
            if not tolerant:
                args = exc.args + (name,)
                raise ConfigTypeError(*args) from None
            obj = value
        except ValueError as exc:
            if not tolerant:
                args = exc.args + (name,)
                raise ConfigValueError(*args) from None
            obj = value
        return obj

    @classmethod
    def dumps(cls, obj, name=None):
        """object -> JSON str"""
        try:
            value = json.dumps(obj)
        except TypeError as exc:
            args = exc.args + (name,)
            raise ConfigTypeError(*args)
        except ValueError as exc:
            args = exc.args + (name,)
            raise ConfigValueError(*args)
        return value

    def load(self, tolerant=False):
        """JSON str (self) -> object"""
        return self.loads(self, self.name, tolerant)


def version_getter(config):
    """Get tag associated with HEAD; fall back to SHA1.

    If HEAD is tagged, return the tag name; otherwise fall back to
    HEAD's short SHA1 hash.

    .. note:: Only annotated tags are considered.

    TODO: Support non-annotated tags?

    """
    try:
        check_output(['git', 'rev-parse', '--is-inside-work-tree'], stderr=DEVNULL)
    except CalledProcessError:
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
