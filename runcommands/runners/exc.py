from ..exc import RunCommandsError
from .result import Result


class RunAborted(RunCommandsError):

    def __init__(self, why):
        super().__init__(why)
        self.why = why


class RunError(RunCommandsError, Result):

    def __init__(self, return_code, stdout_data, stderr_data, encoding):
        super().__init__('Exited with return code {}'.format(return_code))
        Result.__init__(self, return_code, stdout_data, stderr_data, encoding)
