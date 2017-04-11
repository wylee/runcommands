class RunCommandsError(Exception):

    pass


class RunnerError(RunCommandsError):

    pass


class CommandError(RunCommandsError):

    pass


class ConfigError(RunCommandsError):

    pass


class ConfigKeyError(ConfigError, KeyError):

    def __init__(self, key, context=None):
        self.key = key
        self.context = context
        super().__init__(key, context)
        KeyError.__init__(self, key)

    def __str__(self):
        string = '{self.__class__.__name__}{context}: {self.key}'
        context = ' ({self.context})'.format(self=self) if self.context else ''
        return string.format_map(locals())
