"""Arg actions."""

import argparse

from runcommands.exc import ArgError
from runcommands.util import is_mapping, is_sequence


class BoolOrAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values is None:
            values = True
        setattr(namespace, self.dest, values)


class BoolOrContainerAction(argparse.Action):
    @classmethod
    def make(cls, container_type, item_type):
        return type(
            "BoolOrContainerAction",
            (cls,),
            {
                "container_type": container_type,
                "item_type": item_type,
            },
        )

    def __call__(self, parser, namespace, values, option_string=None):
        if values == []:
            setattr(namespace, self.dest, True)
        else:
            existing_items = getattr(namespace, self.dest)
            if isinstance(existing_items, bool):
                # XXX: The default value is False
                existing_items = self.container_type()
            items = add_items_to_container(
                self.container_type,
                self.item_type,
                existing_items,
                values,
                option_string,
            )
            setattr(namespace, self.dest, items)


class ContainerAction(argparse.Action):
    @classmethod
    def make(cls, container_type):
        return type("ContainerAction", (cls,), {"container_type": container_type})

    def __call__(self, parser, namespace, values, option_string=None):
        items = add_items_to_container(
            self.container_type,
            self.type,
            getattr(namespace, self.dest, self.container_type()),
            values,
            option_string,
        )
        setattr(namespace, self.dest, items)


def add_items_to_container(
    container_type,
    item_type,
    existing_items,
    new_items,
    option_string,
):
    """Return a new container with existing plus new items."""
    items = []
    if is_mapping(existing_items):
        if existing_items is not None:
            items.extend(existing_items.items())
        for value in new_items:
            try:
                name, value = value.split(":", 1)
            except ValueError:
                raise ArgError(
                    f"Bad format for {option_string}; expected `name:<value>` "
                    f"but got `{value}`"
                )
            value = item_type(value)
            items.append((name, value))
        return container_type(items)
    elif is_sequence(existing_items):
        if existing_items is not None:
            items.extend(existing_items)
        items.extend(item_type(value) for value in new_items)
    else:
        raise ArgError(f"Not a mapping or sequence: {existing_items!r}")
    return container_type(items)
