from ..util import cached_property


class Result:

    def __init__(self, return_code, stdout_data, stderr_data, encoding):
        self.return_code = return_code
        self.stdout_data = stdout_data
        self.stderr_data = stderr_data
        self.encoding = encoding
        self.succeeded = self.return_code == 0
        self.failed = not self.succeeded

    @cached_property
    def stdout(self):
        if self.stdout_data:
            stdout = b''.join(self.stdout_data)
            stdout = stdout.decode(self.encoding)
        else:
            stdout = ''
        return stdout

    @cached_property
    def stderr(self):
        if self.stderr_data:
            stderr = b''.join(self.stderr_data)
            stderr = stderr.decode(self.encoding)
        else:
            stderr = ''
        return stderr

    @cached_property
    def stdout_lines(self):
        return self.stdout.splitlines() if self.stdout else []

    @cached_property
    def stderr_lines(self):
        return self.stderr.splitlines() if self.stderr else []

    def __bool__(self):
        return self.succeeded

    def __str__(self):
        return self.stdout

    def __repr__(self):
        return repr(self.stdout)
