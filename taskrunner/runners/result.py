from ..util import cached_property


class Result:

    def __init__(self, return_code, stdout, stderr):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.succeeded = self.return_code == 0
        self.failed = not self.succeeded

    @cached_property
    def stdout_lines(self):
        return self.stdout.splitlines() if self.stdout else []

    @cached_property
    def stderr_lines(self):
        return self.stderr.splitlines() if self.stderr else []

    def __bool__(self):
        return self.succeeded
