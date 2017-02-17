from .result import Result


class RunAborted(Exception):
    def __init__(self, why):
        super().__init__(why)
        self.why = why


class RunError(Exception, Result):
    def __init__(self, return_code, stdout, stderr):
        super().__init__('Exited with return code {}'.format(return_code))
        Result.__init__(self, return_code, stdout, stderr)
