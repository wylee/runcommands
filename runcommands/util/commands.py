import os
import shutil
import string
import tempfile

from runcommands.command import bool_or, command


@command(
    type={
        'template': bool_or(str),
    },
    choices={
        'template': ('format', 'string'),
    },
)
def copy_file(config, source, destination, follow_symlinks=True, template=False,
              inject_config=True):
    """Copy source file to destination.

    ``.format_map(config)`` will be applied to the source and
    destination paths. Pass ``--no-inject-config`` to disable this.

    The destination may be a file path or a directory. When it's a
    directory, the source file will be copied into the directory
    using the file's base name.

    When the source file is a template, ``config`` will be used as the
    template context. The supported template types are 'format' and
    'string'. The former uses ``str.format_map()`` and the latter uses
    ``string.Template()``.

    .. note:: :func:`shutil.copy()` from the standard library is used to
        do the copy operation.

    """
    if inject_config:
        source = source.format_map(config)
        destination = destination.format_map(config)

    if not template:
        # Fast path for non-templates.
        return shutil.copy(source, destination, follow_symlinks=follow_symlinks)

    if os.path.isdir(destination):
        destination = os.path.join(destination, os.path.basename(source))

    with open(source) as source:
        contents = source.read()

    if template is True or template == 'format':
        contents = contents.format_map(config)
    elif template == 'string':
        string_template = string.Template(contents)
        contents = string_template.substitute(config)
    else:
        raise ValueError('Unknown template type: %s' % template)

    with tempfile.NamedTemporaryFile('w', delete=False) as temp_file:
        temp_file.write(contents)

    path = shutil.copy(temp_file.name, destination)
    os.remove(temp_file.name)
    return path
