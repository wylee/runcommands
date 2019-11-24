import os
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from typing import MutableMapping

from .command import Command
from .exc import RunnerError
from .util import abs_path


class Collection(MutableMapping):

    """A collection of commands."""

    def __init__(self, commands):
        self.commands = commands

    @classmethod
    def load_from_module(cls, module):
        module = cls.get_module(module)

        commands = {
            obj.name: obj for name, obj in vars(module).items()
            if isinstance(obj, Command) and not name.startswith('_')
        }

        return cls(commands)

    @classmethod
    def get_module(cls, path):
        raise_does_not_exist = False

        if path.endswith('.py'):
            commands_module = abs_path(path)
            if not os.path.isfile(commands_module):
                raise_does_not_exist = True
                does_not_exist_message = 'Commands file does not exist: {commands_module}'
            else:
                spec = spec_from_file_location('commands', commands_module)
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
        else:
            try:
                module = import_module(path)
            except ImportError:
                raise_does_not_exist = True
                does_not_exist_message = 'Commands module could not be imported: {commands_module}'

        if raise_does_not_exist:
            raise RunnerError(does_not_exist_message.format_map(locals()))

        return module

    def set_attrs(self, **attrs):
        """Set the given attributes on *all* commands in collection."""
        commands = tuple(self.values())
        for name, value in attrs.items():
            for command in commands:
                setattr(command, name, value)

    def set_default_args(self, default_args):
        """Set default args for commands in collection.

        Default args are used when the corresponding args aren't passed
        on the command line or in a direct call.

        """
        for name, args in default_args.items():
            command = self[name]
            command.default_args = default_args.get(command.name) or {}

    def __getitem__(self, name):
        commands = self.commands
        if name in commands:
            return commands[name]
        name = Command.normalize_name(name)
        return commands[name]

    def __setitem__(self, name, command):
        self.commands[name] = command

    def __delitem__(self, name):
        del self.commands[name]

    def __iter__(self):
        return iter(self.commands)

    def __len__(self):
        return len(self.commands)
