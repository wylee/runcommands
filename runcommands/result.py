import os
from subprocess import CompletedProcess

from .exc import RunCommandsError
from .util import cached_property


class Result(RunCommandsError):

    def __init__(self, args, return_code, stdout, stderr):
        self.args = args
        self.args_str = args if isinstance(args, str) else ' '.join(args)
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.succeeded = self.return_code == 0
        self.failed = not self.succeeded

    @classmethod
    def from_subprocess_result(cls, result: CompletedProcess):
        return cls(
            result.args,
            result.returncode,
            result.stdout,
            result.stderr,
        )

    @cached_property
    def stdout_lines(self):
        return self.stdout.splitlines() if self.stdout else []

    @cached_property
    def stderr_lines(self):
        return self.stderr.splitlines() if self.stderr else []

    def __bool__(self):
        return self.succeeded

    def __str__(self):
        output = (self.stderr if self.return_code else self.stdout) or '[NO OUTPUT]'
        if output.endswith(os.linesep):
            output = output[:-1]
        status = 'SUCCEEDED' if self.succeeded else 'FAILED'
        string = '{status} ({self.return_code}): {self.args_str} -> {output}'
        string = string.format_map(locals())
        return string

    def __repr__(self):
        return repr(str(self))
