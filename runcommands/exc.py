class RunCommandsError(Exception):

    pass


class RunAborted(RunCommandsError):

    def __init__(self, return_code=0, message='Aborted'):
        self.message = message
        self.return_code = return_code
        super().__init__(message, return_code)

    def __str__(self):
        return self.message


class RunnerError(RunCommandsError):

    pass


class CommandError(RunCommandsError):

    pass
