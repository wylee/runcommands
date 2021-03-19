from typing import MutableMapping

from .command import Command


class Collection(MutableMapping):

    """A collection of commands."""

    def __init__(self, commands):
        self.commands = commands

    @classmethod
    def load_from_module(cls, module):
        commands = {
            obj.name: obj
            for name, obj in vars(module).items()
            if isinstance(obj, Command) and not name.startswith("_")
        }
        return cls(commands)

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
