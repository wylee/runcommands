class RunCommandsError(Exception):

    pass


class RunAborted(RunCommandsError):
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

    pass


class CommandError(RunCommandsError):

    pass
