from contextlib import contextmanager


@contextmanager
def replace(obj, name, replacement_value):
    original_value = getattr(obj, name)
    setattr(obj, name, replacement_value)
    yield obj
    setattr(obj, name, original_value)
