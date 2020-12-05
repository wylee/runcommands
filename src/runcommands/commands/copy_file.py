import os
import shutil
import string
import tempfile

from ..args import arg, bool_or
from ..command import command


@command
def copy_file(
    source,
    destination,
    follow_symlinks=True,
    template: arg(type=bool_or(str), choices=("format", "string")) = False,
    context=None,
):
    """Copy source file to destination.

    The destination may be a file path or a directory. When it's a
    directory, the source file will be copied into the directory
    using the file's base name.

    When the source file is a template, ``context`` will be used as the
    template context. The supported template types are 'format' and
    'string'. The former uses ``str.format_map()`` and the latter uses
    ``string.Template()``.

    .. note:: :func:`shutil.copy()` from the standard library is used to
        do the copy operation.

    """
    if not template:
        # Fast path for non-templates.
        return shutil.copy(source, destination, follow_symlinks=follow_symlinks)

    if os.path.isdir(destination):
        destination = os.path.join(destination, os.path.basename(source))

    with open(source) as source:
        contents = source.read()

    if template is True or template == "format":
        contents = contents.format_map(context)
    elif template == "string":
        string_template = string.Template(contents)
        contents = string_template.substitute(context)
    else:
        raise ValueError("Unknown template type: %s" % template)

    with tempfile.NamedTemporaryFile("w", delete=False) as temp_file:
        temp_file.write(contents)

    path = shutil.copy(temp_file.name, destination)
    os.remove(temp_file.name)
    return path
