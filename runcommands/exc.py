class RunCommandsError(Exception):

    pass


class RunnerError(RunCommandsError):

    pass


class CommandError(RunCommandsError):

    pass


class ConfigError(RunCommandsError):

    pass
