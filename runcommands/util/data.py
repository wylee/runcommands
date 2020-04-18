class Data:

    """A bucket for arbitrary data.

    Data can be added and retrieved as attributes (dot notation) or
    items (bracket notation).

    """

    def __init__(self, **data):
        super().__setattr__('__data', {})
        for name, value in data.items():
            self[name] = value

    def __getattr__(self, name):
        return self.__data[name]

    __getitem__ = __getattr__

    def __setattr__(self, name, value):
        self.__data[name] = value

    __setitem__ = __setattr__
