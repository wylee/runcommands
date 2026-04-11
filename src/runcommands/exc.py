class RunCommandsError(Exception):
    """Base of RunCommands exception hierarchy.

    These exception are used in cases where the current run should be
    stopped gracefully, for example, when the user improperly configures
    a command.

    These exceptions should NOT

    """

    pass


class RunAborted(RunCommandsError):
    """Used to explicitly signal that the run should be aborted."""

    def __init__(self, return_code=0, message="Aborted", is_nested=False):
        self.message = message
        self.return_code = return_code
        self.is_nested = is_nested
        super().__init__(message, return_code)

    def __str__(self):
        return self.message

    def create_nested(self):
        return self.__class__(
            return_code=self.return_code,
            message=self.message,
            is_nested=True,
        )


class RunnerError(RunCommandsError):
    """Used for errors encountered in the command runner."""

    pass


class CommandError(RunCommandsError):
    """Used for errors encountered while handling a command."""

    pass


class ArgError(RunCommandsError):
    """Used for errors encountered while handling an arg."""

    pass
