"""Arg types."""

import builtins
import json


class bool_or:
    """Used to indicate that an arg can be a flag or an option.

    Use like this::

        @command
        def local(config, cmd, hide: arg(type=bool_or) = False):
            "Run the specified command, possibly hiding its output.

            If ``hide=True``, *all* output will be hidden. It can also
            be set to one of "stdout" or "stderr" to hide just the
            specified output stream.

            "

    .. note:: The default inner type for ``bool_or`` is ``str``.
        ``bool_or(str)`` is equivalent to ``bool_or``.

    Allows for this::

        run local --hide all     # Hide everything
        run local --hide         # Hide everything with less effort
        run local --hide stdout  # Hide stdout only
        run local --no-hide      # Don't hide anything

    This can also be combined with the ``container`` option like so::

        @command
        def fetch(fields: arg=(container dict, type=bool_or(int)):
            "Get data from somewhere and show the specified fields.

            If ``fields=True``, all fields will be shown with their
            original names. If fields are specified, only those fields
            will be shown, with their names mapped. For example,
            ``fields`` could be::

                {'givenName': 'first_name', 'sn': 'last_name'}

            "

    .. note:: When combined with ``container``, the type passed to
        ``bool_or`` is applied to the *values* in the container rather
        than being applied to the literal strings passed on the command
        line.

    """

    type = str

    def __new__(cls, type, *, _type_cache={}):
        if type not in _type_cache:
            name = f"BoolOr{type.__name__.title()}"
            _type_cache[type] = builtins.type(name, (cls,), {"type": type})
        return _type_cache[type]


def json_value(string):
    """Convert string to JSON if possible; otherwise, return as is."""
    try:
        string = json.loads(string)
    except ValueError:
        pass
    return string
