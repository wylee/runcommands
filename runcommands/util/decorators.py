class cached_property:

    """Cache property value on first access.

    >>> value = object()
    >>>
    >>> class C:
    ...    @cached_property
    ...    def x(self):
    ...        return value
    ...
    >>> isinstance(C.x, cached_property)
    True
    >>> c = C()
    >>> 'x' in c.__dict__
    False
    >>> c.x is value
    True
    >>> 'x' in c.__dict__
    True

    """

    def __init__(self, fget):
        self.fget = fget
        self.__name__ = fget.__name__
        self.__doc__ = fget.__doc__

    def __get__(self, obj, cls=None):
        if obj is None:  # Property accessed via class
            return self
        obj.__dict__[self.__name__] = self.fget(obj)
        return obj.__dict__[self.__name__]
