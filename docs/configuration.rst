Configuration
+++++++++++++

Configuration is read from an INI file where the values are encoded as JSON.
This allows for rich values without requiring third party libraries.

A config file looks like this, with sections for different environments::

    ; commands.cfg
    [DEFAULT]
    project_name = "My Project"

    [dev]
    debug = true

    [stage]
    debug = true
    defaults.remote.host = "stage_host"

    [prod]
    debug = false
    remote.host = "prod_host"
    defaults.remote.host = "{remote.host}"

Accessing Config
================

When the above config file is read, its values can be accessed using item or
attribute syntax. The following are equivalent::

    >>> config.remote.host
    >>> config['remote']['host']

In some situations, it's convenient to be able to get at config values using
a special dotted notation::

    >> key = 'remote.host'
    >>> config._get_dotted(key)
    >>> config._get_dotted('does.not.exist', default='some default')

Extending Config
================

A config file can extend another config file using the ``extends`` key. This
example uses an "asset path" where the config file lives in a Python package
named ``mypackage``::

    extends = "mypackage:my.cfg"

A relative or absolute file system can be specified instead::

    extends = "/path/to/my.cfg"

.. note:: The same env/section will always be extended from; there's no way to
          extend from a different env/section.

Interpolation
=============

Config values can contain Python format strings like ``${remote.host}``. These
will be replaced with the corresponding config values.

.. note:: Only works with string values.

Default Option Values
=====================

As shown above, default option values can be specified for a command via
configuration. These defaults will take precedence over option values defined
on the command but can be overridden via command line options.

.. note:: This works whether a command is called via the command line *or*
          called directly in Python code.
