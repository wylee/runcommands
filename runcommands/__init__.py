import json
import os

from .command import bool_or, command
from .const import DEFAULT_ENV


__all__ = ['__version__', 'DEFAULT_ENV', 'bool_or', 'command', 'configure']
__version__ = '1.0a22'


def configure(commands_module=None, config_file=None, default_env=None, env=None, echo=None,
              hide=None, debug=None):
    """Set environment variables.

    String values will be left as is; other types of values will be JSON
    encoded.

    """
    def encode(v):
        if isinstance(v, str):
            return v
        return json.dumps(v)

    os.environ['RUNCOMMANDS_COMMANDS_MODULE'] = encode(commands_module)
    os.environ['RUNCOMMANDS_CONFIG_FILE'] = encode(config_file)
    os.environ['RUNCOMMANDS_DEFAULT_ENV'] = encode(default_env)
    os.environ['RUNCOMMANDS_ENV'] = encode(env)
    os.environ['RUNCOMMANDS_ECHO'] = encode(echo)
    os.environ['RUNCOMMANDS_HIDE'] = encode(hide)
    os.environ['RUNCOMMANDS_DEBUG'] = encode(debug)
