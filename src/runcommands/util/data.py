class Data:

    """A bucket for arbitrary data.

    Data can be added and retrieved as attributes (dot notation) or
    items (bracket notation).

    When a ``dict`` is added, it will be converted to an instance of
    :class:`Data`.

    """

    def __init__(self, **data):
        super().__setattr__("__data", {})
        for name, value in data.items():
            self[name] = value

    def __getattr__(self, name):
        data = super().__getattribute__("__data")
        return data[name]

    __getitem__ = __getattr__

    def __setattr__(self, name, value):
        data = super().__getattribute__("__data")
        if isinstance(value, dict):
            value = self.__class__(**value)
        data[name] = value

    __setitem__ = __setattr__
