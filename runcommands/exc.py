class RunCommandsError(Exception):

    pass


class RunnerError(RunCommandsError):

    pass


class CommandError(RunCommandsError):

    pass


class ConfigError(RunCommandsError):

    pass


class ConfigKeyError(ConfigError, KeyError):

    def __init__(self, *args, context=None):
        self.context = context
        super().__init__(*(args + (context,)))
        KeyError.__init__(self, *args)

    def __str__(self):
        args = ', '.join(str(arg) for arg in self.args)
        context = ' ({self.context})'.format(self=self) if self.context is not None else ''
        string = '{self.__class__.__name__}{context}: {args}'
        return string.format_map(locals())


class ConfigTypeError(ConfigError, TypeError):

    def __init__(self, *args):
        super().__init__(*args)
        TypeError.__init__(self, *args)


class ConfigValueError(ConfigError, ValueError):

    def __init__(self, *args, name=None):
        self.name = name
        super().__init__(*(args + (name,)))
        ValueError.__init__(self, *args)

    def __str__(self):
        args = ', '.join(str(arg) for arg in self.args)
        context = ' ({self.name})'.format(self=self) if self.name is not None else ''
        string = '{self.__class__.__name__}{context}: {args}'
        return string.format_map(locals())
